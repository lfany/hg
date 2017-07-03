# phabricator.py - simple Phabricator integration
#
# Copyright 2017 Facebook, Inc.
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.
"""simple Phabricator integration

This extension provides a ``phabsend`` command which sends a stack of
changesets to Phabricator without amending commit messages.

By default, Phabricator requires ``Test Plan`` which might prevent some
changeset from being sent. The requirement could be disabled by changing
``differential.require-test-plan-field`` config server side.

Config::

    [phabricator]
    # Phabricator URL
    url = https://phab.example.com/

    # API token. Get it from https://$HOST/conduit/login/
    token = cli-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # Repo callsign. If a repo has a URL https://$HOST/diffusion/FOO, then its
    # callsign is "FOO".
    callsign = FOO
"""

from __future__ import absolute_import

import json
import re

from mercurial.i18n import _
from mercurial import (
    encoding,
    error,
    mdiff,
    obsolete,
    patch,
    registrar,
    scmutil,
    tags,
    url as urlmod,
    util,
)

cmdtable = {}
command = registrar.command(cmdtable)

def urlencodenested(params):
    """like urlencode, but works with nested parameters.

    For example, if params is {'a': ['b', 'c'], 'd': {'e': 'f'}}, it will be
    flattened to {'a[0]': 'b', 'a[1]': 'c', 'd[e]': 'f'} and then passed to
    urlencode. Note: the encoding is consistent with PHP's http_build_query.
    """
    flatparams = util.sortdict()
    def process(prefix, obj):
        items = {list: enumerate, dict: lambda x: x.items()}.get(type(obj))
        if items is None:
            flatparams[prefix] = obj
        else:
            for k, v in items(obj):
                if prefix:
                    process('%s[%s]' % (prefix, k), v)
                else:
                    process(k, v)
    process('', params)
    return util.urlreq.urlencode(flatparams)

def readurltoken(repo):
    """return conduit url, token and make sure they exist

    Currently read from [phabricator] config section. In the future, it might
    make sense to read from .arcconfig and .arcrc as well.
    """
    values = []
    section = 'phabricator'
    for name in ['url', 'token']:
        value = repo.ui.config(section, name)
        if not value:
            raise error.Abort(_('config %s.%s is required') % (section, name))
        values.append(value)
    return values

def callconduit(repo, name, params):
    """call Conduit API, params is a dict. return json.loads result, or None"""
    host, token = readurltoken(repo)
    url, authinfo = util.url('/'.join([host, 'api', name])).authinfo()
    urlopener = urlmod.opener(repo.ui, authinfo)
    repo.ui.debug('Conduit Call: %s %s\n' % (url, params))
    params = params.copy()
    params['api.token'] = token
    request = util.urlreq.request(url, data=urlencodenested(params))
    body = urlopener.open(request).read()
    repo.ui.debug('Conduit Response: %s\n' % body)
    parsed = json.loads(body)
    if parsed.get(r'error_code'):
        msg = (_('Conduit Error (%s): %s')
               % (parsed[r'error_code'], parsed[r'error_info']))
        raise error.Abort(msg)
    return parsed[r'result']

@command('debugcallconduit', [], _('METHOD'))
def debugcallconduit(ui, repo, name):
    """call Conduit API

    Call parameters are read from stdin as a JSON blob. Result will be written
    to stdout as a JSON blob.
    """
    params = json.loads(ui.fin.read())
    result = callconduit(repo, name, params)
    s = json.dumps(result, sort_keys=True, indent=2, separators=(',', ': '))
    ui.write('%s\n' % s)

def getrepophid(repo):
    """given callsign, return repository PHID or None"""
    # developer config: phabricator.repophid
    repophid = repo.ui.config('phabricator', 'repophid')
    if repophid:
        return repophid
    callsign = repo.ui.config('phabricator', 'callsign')
    if not callsign:
        return None
    query = callconduit(repo, 'diffusion.repository.search',
                        {'constraints': {'callsigns': [callsign]}})
    if len(query[r'data']) == 0:
        return None
    repophid = encoding.strtolocal(query[r'data'][0][r'phid'])
    repo.ui.setconfig('phabricator', 'repophid', repophid)
    return repophid

_differentialrevisionre = re.compile('\AD([1-9][0-9]*)\Z')

def getmapping(ctx):
    """return (node, associated Differential Revision ID) or (None, None)

    Examines all precursors and their tags. Tags with format like "D1234" are
    considered a match and the node with that tag, and the number after "D"
    (ex. 1234) will be returned.
    """
    unfi = ctx.repo().unfiltered()
    nodemap = unfi.changelog.nodemap
    for n in obsolete.allprecursors(unfi.obsstore, [ctx.node()]):
        if n in nodemap:
            for tag in unfi.nodetags(n):
                m = _differentialrevisionre.match(tag)
                if m:
                    return n, int(m.group(1))
    return None, None

def getdiff(ctx, diffopts):
    """plain-text diff without header (user, commit message, etc)"""
    output = util.stringio()
    for chunk, _label in patch.diffui(ctx.repo(), ctx.p1().node(), ctx.node(),
                                      None, opts=diffopts):
        output.write(chunk)
    return output.getvalue()

def creatediff(ctx):
    """create a Differential Diff"""
    repo = ctx.repo()
    repophid = getrepophid(repo)
    # Create a "Differential Diff" via "differential.createrawdiff" API
    params = {'diff': getdiff(ctx, mdiff.diffopts(git=True, context=32767))}
    if repophid:
        params['repositoryPHID'] = repophid
    diff = callconduit(repo, 'differential.createrawdiff', params)
    if not diff:
        raise error.Abort(_('cannot create diff for %s') % ctx)
    return diff

def writediffproperties(ctx, diff):
    """write metadata to diff so patches could be applied losslessly"""
    params = {
        'diff_id': diff[r'id'],
        'name': 'hg:meta',
        'data': json.dumps({
            'user': ctx.user(),
            'date': '%d %d' % ctx.date(),
        }),
    }
    callconduit(ctx.repo(), 'differential.setdiffproperty', params)

def createdifferentialrevision(ctx, revid=None, parentrevid=None):
    """create or update a Differential Revision

    If revid is None, create a new Differential Revision, otherwise update
    revid. If parentrevid is not None, set it as a dependency.
    """
    repo = ctx.repo()
    diff = creatediff(ctx)
    writediffproperties(ctx, diff)

    transactions = [{'type': 'update', 'value': diff[r'phid']}]

    # Use a temporary summary to set dependency. There might be better ways but
    # I cannot find them for now. But do not do that if we are updating an
    # existing revision (revid is not None) since that introduces visible
    # churns (someone edited "Summary" twice) on the web page.
    if parentrevid and revid is None:
        summary = 'Depends on D%s' % parentrevid
        transactions += [{'type': 'summary', 'value': summary},
                         {'type': 'summary', 'value': ' '}]

    # Parse commit message and update related fields.
    desc = ctx.description()
    info = callconduit(repo, 'differential.parsecommitmessage',
                       {'corpus': desc})
    for k, v in info[r'fields'].items():
        if k in ['title', 'summary', 'testPlan']:
            transactions.append({'type': k, 'value': v})

    params = {'transactions': transactions}
    if revid is not None:
        # Update an existing Differential Revision
        params['objectIdentifier'] = revid

    revision = callconduit(repo, 'differential.revision.edit', params)
    if not revision:
        raise error.Abort(_('cannot create revision for %s') % ctx)

    return revision

@command('phabsend',
         [('r', 'rev', [], _('revisions to send'), _('REV'))],
         _('REV [OPTIONS]'))
def phabsend(ui, repo, *revs, **opts):
    """upload changesets to Phabricator

    If there are multiple revisions specified, they will be send as a stack
    with a linear dependencies relationship using the order specified by the
    revset.

    For the first time uploading changesets, local tags will be created to
    maintain the association. After the first time, phabsend will check
    obsstore and tags information so it can figure out whether to update an
    existing Differential Revision, or create a new one.
    """
    revs = list(revs) + opts.get('rev', [])
    revs = scmutil.revrange(repo, revs)

    # Send patches one by one so we know their Differential Revision IDs and
    # can provide dependency relationship
    lastrevid = None
    for rev in revs:
        ui.debug('sending rev %d\n' % rev)
        ctx = repo[rev]

        # Get Differential Revision ID
        oldnode, revid = getmapping(ctx)
        if oldnode != ctx.node():
            # Create or update Differential Revision
            revision = createdifferentialrevision(ctx, revid, lastrevid)
            newrevid = int(revision[r'object'][r'id'])
            if revid:
                action = _('updated')
            else:
                action = _('created')

            # Create a local tag to note the association
            tagname = 'D%d' % newrevid
            tags.tag(repo, tagname, ctx.node(), message=None, user=None,
                     date=None, local=True)
        else:
            # Nothing changed. But still set "newrevid" so the next revision
            # could depend on this one.
            newrevid = revid
            action = _('skipped')

        ui.write(_('D%s: %s - %s: %s\n') % (newrevid, action, ctx,
                                            ctx.description().split('\n')[0]))
        lastrevid = newrevid
