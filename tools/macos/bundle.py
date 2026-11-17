#!/usr/bin/env python3
"""Package a locally translated ARM64 game. Includes no original exe, assets, DLS or movies.
This local app still contains code generated from the user's exe and must not be distributed.
"""
import argparse,json,os,pathlib,plistlib,shutil,subprocess,sys
from check_game import inspect
root=pathlib.Path(__file__).resolve().parents[2];os.chdir(root)
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('game');p.add_argument('--output',type=pathlib.Path)
p.add_argument('--no-record-location',action='store_true')
args=p.parse_args()
result=inspect(args.game)
if not result['supported']:sys.exit('App packaging requires a supported original English executable and complete assets.')
exe=root/'build/li2'
if not exe.is_file():sys.exit('Build and test build/li2 first; see MACOS.md.')
if result['sha256'].encode() not in exe.read_bytes():sys.exit('The compiled binary belongs to a different game version; rebuild with this game folder first.')
subprocess.run(['/usr/bin/lipo',str(exe),'-verify_arch','arm64'],check=True)
app=args.output.expanduser().resolve() if args.output else root/'build/LEGO Island 2.app'
if app.exists():sys.exit('App already exists; preserving it. Move it aside before creating a new bundle.')
contents=app/'Contents';mac=contents/'MacOS';fw=contents/'Frameworks';res=contents/'Resources'
for d in [mac,fw,res]:d.mkdir(parents=True,exist_ok=True)
shutil.copy2(exe,mac/'li2')
for source,name in [(root/'third_party/sdl3/lib/libSDL3.0.dylib','libSDL3.0.dylib'),
                    (root/'third_party/MoltenVK/MoltenVK/dynamic/dylib/macOS/libMoltenVK.dylib','libMoltenVK.dylib')]:
    shutil.copy2(source,fw/name)
# Keep only bundle-relative runtime search paths; no dependency on this checkout at launch.
load=subprocess.check_output(['/usr/bin/otool','-l',str(mac/'li2')],text=True).splitlines()
rpaths=[]
for i,line in enumerate(load):
    if 'cmd LC_RPATH' in line:rpaths.append(load[i+2].strip().split('path ',1)[1].split(' (offset',1)[0])
for path in rpaths:subprocess.run(['/usr/bin/install_name_tool','-delete_rpath',path,str(mac/'li2')],check=True)
subprocess.run(['/usr/bin/install_name_tool','-add_rpath','@executable_path/../Frameworks',str(mac/'li2')],check=True)
plist=dict(CFBundleName='LEGO Island 2',CFBundleDisplayName='LEGO Island 2',CFBundleExecutable='li2',
           CFBundleIdentifier='local.li2-native.game',CFBundlePackageType='APPL',CFBundleVersion='0.1',
           CFBundleShortVersionString='0.1-experimental',LSMinimumSystemVersion='26.0',
           NSHighResolutionCapable=True,NSPrincipalClass='NSApplication')
with (contents/'Info.plist').open('wb') as f:plistlib.dump(plist,f)
licenses=res/'Licenses';licenses.mkdir()
for source,name in [(root/'LICENSE','Runtime.txt'),(root/'third_party/sdl3/share/licenses/SDL3/LICENSE.txt','SDL3.txt'),
                    (root/'third_party/MoltenVK/LICENSE','MoltenVK.txt'),(root/'third_party/simde-0.8.2/COPYING','SIMDe.txt'),
                    (root/'third_party/dmusic/LICENSE.md','dmusic.txt'),(root/'licenses/DejaVu.txt','DejaVu.txt'),
                    (root/'THIRD_PARTY_NOTICES.md','THIRD_PARTY_NOTICES.md')]:shutil.copy2(source,licenses/name)
# Preserve full in-header license notices for the vendored single-header libraries.
for source,name,marker in [('third_party/dr_libs/dr_mp3.h','dr_mp3.txt',None),
                           ('third_party/pl_mpeg/pl_mpeg.h','pl_mpeg.txt',None),
                           ('third_party/dmusic/vendor/TinySoundFont/tsf.h','TinySoundFont.txt',None)]:
    shutil.copy2(root/source,licenses/name)
(res/'LOCAL-USE-ONLY.txt').write_text('Private local build incorporating code translated from your game. Do not distribute. Original game files live outside this app.\n')
for binary in list(fw.iterdir())+[mac/'li2']:
    subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(binary)],check=True)
subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(app)],check=True)
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True)
if not args.no_record_location:
    user=pathlib.Path.home()/'Library/Application Support/li2-native';user.mkdir(parents=True,exist_ok=True)
    location=user/'game-location.txt'
    if location.exists() and location.read_text().strip()!=result['folder']:
        sys.exit('App created, but existing game-location.txt was preserved. Launch with --game or edit that path yourself.')
    location.write_text(result['folder']+'\n')
print('Private local app: '+str(app))
