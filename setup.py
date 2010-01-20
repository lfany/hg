#!/usr/bin/env python
#
# This is the mercurial setup script.
#
# 'python setup.py install', or
# 'python setup.py --help' for more options

import sys
if not hasattr(sys, 'version_info') or sys.version_info < (2, 4, 0, 'final'):
    raise SystemExit("Mercurial requires Python 2.4 or later.")

# Solaris Python packaging brain damage
try:
    import hashlib
    sha = hashlib.sha1()
except:
    try:
        import sha
    except:
        raise SystemExit(
            "Couldn't import standard hashlib (incomplete Python install).")

try:
    import zlib
except:
    raise SystemExit(
        "Couldn't import standard zlib (incomplete Python install).")

import os, subprocess, time
import shutil
import tempfile
from distutils.core import setup, Extension
from distutils.dist import Distribution
from distutils.command.install_data import install_data
from distutils.command.build import build
from distutils.command.build_py import build_py
from distutils.spawn import spawn, find_executable
from distutils.ccompiler import new_compiler

extra = {}
scripts = ['hg']
if os.name == 'nt':
    scripts.append('contrib/win32/hg.bat')

# simplified version of distutils.ccompiler.CCompiler.has_function
# that actually removes its temporary files.
def has_function(cc, funcname):
    tmpdir = tempfile.mkdtemp(prefix='hg-install-')
    devnull = oldstderr = None
    try:
        try:
            fname = os.path.join(tmpdir, 'funcname.c')
            f = open(fname, 'w')
            f.write('int main(void) {\n')
            f.write('    %s();\n' % funcname)
            f.write('}\n')
            f.close()
            # Redirect stderr to /dev/null to hide any error messages
            # from the compiler.
            # This will have to be changed if we ever have to check
            # for a function on Windows.
            devnull = open('/dev/null', 'w')
            oldstderr = os.dup(sys.stderr.fileno())
            os.dup2(devnull.fileno(), sys.stderr.fileno())
            objects = cc.compile([fname], output_dir=tmpdir)
            cc.link_executable(objects, os.path.join(tmpdir, "a.out"))
        except:
            return False
        return True
    finally:
        if oldstderr is not None:
            os.dup2(oldstderr, sys.stderr.fileno())
        if devnull is not None:
            devnull.close()
        shutil.rmtree(tmpdir)

# py2exe needs to be installed to work
try:
    import py2exe

    # Help py2exe to find win32com.shell
    try:
        import modulefinder
        import win32com
        for p in win32com.__path__[1:]: # Take the path to win32comext
            modulefinder.AddPackagePath("win32com", p)
        pn = "win32com.shell"
        __import__(pn)
        m = sys.modules[pn]
        for p in m.__path__[1:]:
            modulefinder.AddPackagePath(pn, p)
    except ImportError:
        pass

    extra['console'] = ['hg']

except ImportError:
    pass

def runcmd(cmd, env):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=env)
    out, err = p.communicate()
    # If root is executing setup.py, but the repository is owned by
    # another user (as in "sudo python setup.py install") we will get
    # trust warnings since the .hg/hgrc file is untrusted. That is
    # fine, we don't want to load it anyway.  Python may warn about
    # a missing __init__.py in mercurial/locale, we also ignore that.
    err = [e for e in err.splitlines()
           if not e.startswith('Not trusting file') \
              and not e.startswith('warning: Not importing')]
    if err:
        return ''
    return out

version = ''

if os.path.isdir('.hg'):
    # Execute hg out of this directory with a custom environment which
    # includes the pure Python modules in mercurial/pure. We also take
    # care to not use any hgrc files and do no localization.
    pypath = ['mercurial', os.path.join('mercurial', 'pure')]
    env = {'PYTHONPATH': os.pathsep.join(pypath),
           'HGRCPATH': '',
           'LANGUAGE': 'C'}
    if 'LD_LIBRARY_PATH' in os.environ:
        env['LD_LIBRARY_PATH'] = os.environ['LD_LIBRARY_PATH']
    if 'SystemRoot' in os.environ:
        # Copy SystemRoot into the custom environment for Python 2.6
        # under Windows. Otherwise, the subprocess will fail with
        # error 0xc0150004. See: http://bugs.python.org/issue3440
        env['SystemRoot'] = os.environ['SystemRoot']
    cmd = [sys.executable, 'hg', 'id', '-i', '-t']
    l = runcmd(cmd, env).split()
    while len(l) > 1 and l[-1][0].isalpha(): # remove non-numbered tags
        l.pop()
    if len(l) > 1: # tag found
        version = l[-1]
        if l[0].endswith('+'): # propagate the dirty status to the tag
            version += '+'
    elif len(l) == 1: # no tag found
        cmd = [sys.executable, 'hg', 'parents', '--template',
               '{latesttag}+{latesttagdistance}-']
        version = runcmd(cmd, env) + l[0]
    if version.endswith('+'):
        version += time.strftime('%Y%m%d')
elif os.path.exists('.hg_archival.txt'):
    kw = dict([[t.strip() for t in l.split(':', 1)]
               for l in open('.hg_archival.txt')])
    if 'tag' in kw:
        version =  kw['tag']
    elif 'latesttag' in kw:
        version = '%(latesttag)s+%(latesttagdistance)s-%(node).12s' % kw
    else:
        version = kw.get('node', '')[:12]

if version:
    f = open("mercurial/__version__.py", "w")
    f.write('# this file is autogenerated by setup.py\n')
    f.write('version = "%s"\n' % version)
    f.close()


try:
    from mercurial import __version__
    version = __version__.version
except ImportError:
    version = 'unknown'

class install_package_data(install_data):
    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('install_lib', 'install_dir'))
        install_data.finalize_options(self)

class build_mo(build):

    description = "build translations (.mo files)"

    def run(self):
        if not find_executable('msgfmt'):
            self.warn("could not find msgfmt executable, no translations "
                     "will be built")
            return

        podir = 'i18n'
        if not os.path.isdir(podir):
            self.warn("could not find %s/ directory" % podir)
            return

        join = os.path.join
        for po in os.listdir(podir):
            if not po.endswith('.po'):
                continue
            pofile = join(podir, po)
            modir = join('locale', po[:-3], 'LC_MESSAGES')
            mofile = join(modir, 'hg.mo')
            cmd = ['msgfmt', '-v', '-o', mofile, pofile]
            if sys.platform != 'sunos5':
                # msgfmt on Solaris does not know about -c
                cmd.append('-c')
            self.mkpath(modir)
            self.make_file([pofile], mofile, spawn, (cmd,))
            self.distribution.data_files.append((join('mercurial', modir),
                                                 [mofile]))

build.sub_commands.append(('build_mo', None))

Distribution.pure = 0
Distribution.global_options.append(('pure', None, "use pure (slow) Python "
                                    "code instead of C extensions"))

class hg_build_py(build_py):

    def finalize_options(self):
        build_py.finalize_options(self)

        if self.distribution.pure:
            if self.py_modules is None:
                self.py_modules = []
            for ext in self.distribution.ext_modules:
                if ext.name.startswith("mercurial."):
                    self.py_modules.append("mercurial.pure.%s" % ext.name[10:])
            self.distribution.ext_modules = []

    def find_modules(self):
        modules = build_py.find_modules(self)
        for module in modules:
            if module[0] == "mercurial.pure":
                if module[1] != "__init__":
                    yield ("mercurial", module[1], module[2])
            else:
                yield module

cmdclass = {'install_data': install_package_data,
            'build_mo': build_mo,
            'build_py': hg_build_py}

ext_modules=[
    Extension('mercurial.base85', ['mercurial/base85.c']),
    Extension('mercurial.bdiff', ['mercurial/bdiff.c']),
    Extension('mercurial.diffhelpers', ['mercurial/diffhelpers.c']),
    Extension('mercurial.mpatch', ['mercurial/mpatch.c']),
    Extension('mercurial.parsers', ['mercurial/parsers.c']),
    Extension('mercurial.osutil', ['mercurial/osutil.c']),
    ]

packages = ['mercurial', 'mercurial.hgweb', 'hgext', 'hgext.convert',
            'hgext.highlight', 'hgext.zeroconf', ]

if sys.platform == 'linux2' and os.uname()[2] > '2.6':
    # The inotify extension is only usable with Linux 2.6 kernels.
    # You also need a reasonably recent C library.
    cc = new_compiler()
    if has_function(cc, 'inotify_add_watch'):
        ext_modules.append(Extension('hgext.inotify.linux._inotify',
                                     ['hgext/inotify/linux/_inotify.c']))
        packages.extend(['hgext.inotify', 'hgext.inotify.linux'])

datafiles = []
for root in ('templates', 'i18n', 'help'):
    for dir, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith('.')]
        files = [x for x in files if not x.startswith('.')]
        datafiles.append((os.path.join('mercurial', dir),
                          [os.path.join(dir, file_) for file_ in files]))

setup(name='mercurial',
      version=version,
      author='Matt Mackall',
      author_email='mpm@selenic.com',
      url='http://mercurial.selenic.com/',
      description='Scalable distributed SCM',
      license='GNU GPLv2+',
      scripts=scripts,
      packages=packages,
      ext_modules=ext_modules,
      data_files=datafiles,
      cmdclass=cmdclass,
      options=dict(py2exe=dict(packages=['hgext', 'email']),
                   bdist_mpkg=dict(zipdist=True,
                                   license='COPYING',
                                   readme='contrib/macosx/Readme.html',
                                   welcome='contrib/macosx/Welcome.html')),
      **extra)
