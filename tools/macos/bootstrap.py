#!/usr/bin/env python3
"""Build pinned dependencies inside this checkout; no Homebrew installs or game downloads."""
import hashlib, json, os, pathlib, subprocess, sys, tarfile, urllib.request
root = pathlib.Path(__file__).resolve().parents[2]
os.chdir(root)
if sys.platform != 'darwin': sys.exit('This bootstrap targets macOS.')
if os.uname().machine != 'arm64': sys.exit('This experimental port currently targets native ARM64 only.')
work = root/'work'; work.mkdir(exist_ok=True)
venv = root/'.venv'
if not (venv/'bin/python').exists(): subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
subprocess.run([str(venv/'bin/python'),'-m','pip','install','-r','tools/macos/requirements.txt'],check=True)
env = dict(os.environ, PATH=str(venv/'bin')+os.pathsep+os.environ['PATH'])
for dep in json.loads((root/'tools/macos/dependencies.lock.json').read_text()):
    path = work/dep['url'].rsplit('/',1)[1]
    if not path.exists(): urllib.request.urlretrieve(dep['url'],path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != dep['sha256']:
        sys.exit('Checksum mismatch: '+str(path)+'; remove that local download and retry.')
    marker=root/'third_party'/dep['directory']
    if not marker.exists():
        with tarfile.open(path) as archive:
            # Hash-pinned upstream archives; still reject path traversal.
            base=(root/'third_party').resolve()
            for member in archive.getmembers():
                target=(base/member.name).resolve()
                if os.path.commonpath([str(base),str(target)]) != str(base): sys.exit('Unsafe archive member')
            archive.extractall(base)
cmake=str(venv/'bin/cmake')
def build(source,builddir,prefix,extra):
    subprocess.run([cmake,'-S',source,'-B',builddir,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_OSX_ARCHITECTURES=arm64','-DCMAKE_INSTALL_PREFIX='+str(root/prefix)]+extra,check=True,env=env)
    subprocess.run([cmake,'--build',builddir,'-j4'],check=True,env=env)
    subprocess.run([cmake,'--install',builddir],check=True,env=env)
build('third_party/SDL3-3.4.18','work/SDL3-build','third_party/sdl3',
      ['-DSDL_SHARED=ON','-DSDL_STATIC=OFF','-DSDL_TESTS=OFF','-DSDL_TEST_LIBRARY=OFF'])
build('third_party/unshield-1.6.2','work/unshield-build','third_party/unshield',
      ['-DBUILD_TESTING=OFF','-DUSE_OUR_OWN_MD5=ON'])
print('Dependencies ready. See MACOS.md for game validation and build instructions.')
