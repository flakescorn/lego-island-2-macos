#!/usr/bin/env python3
"""Build the public launcher from open-source files only. Never includes build/li2 or gen/."""
import argparse
import hashlib
import json
import os
import pathlib
import plistlib
import shutil
import subprocess
import sys
import zipfile
from public_files import ROOT, files, fingerprint


def build(output, archive=False):
    if sys.platform != 'darwin' or os.uname().machine != 'arm64':
        raise ValueError('Build the launcher on an Apple Silicon Mac.')
    if output.exists(): raise ValueError('Preserving existing output. Choose a new --output or move it aside: ' + str(output))
    source_files = files()
    resources = output/'Contents/Resources'; resources.mkdir(parents=True)
    binary = output/'Contents/MacOS/IslandLauncher'; binary.parent.mkdir()
    payload = resources/'EngineSource'; payload.mkdir()
    manifest = []
    for source in source_files:
        relative = source.relative_to(ROOT)
        target = payload/relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest.append(dict(path=relative.as_posix(), sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    (resources/'Source.version').write_text(fingerprint()+'\n')
    (resources/'source-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    subprocess.run(['xcrun','swiftc','-swift-version','5','-parse-as-library','-O',
                    '-target','arm64-apple-macos26.0',str(ROOT/'macos/Launcher.swift'),'-o',str(binary)],check=True)
    scratch = ROOT/'work/launcher-build'; scratch.mkdir(parents=True, exist_ok=True)
    icon = scratch/'make-icon'
    subprocess.run(['xcrun','swiftc',str(ROOT/'macos/Icon.swift'),'-o',str(icon)],check=True)
    iconset = scratch/'Launcher.iconset'
    subprocess.run([str(icon),str(iconset)],check=True)
    subprocess.run(['/usr/bin/iconutil','-c','icns',str(iconset),'-o',str(resources/'Launcher.icns')],check=True)
    plist = dict(CFBundleName='LEGO Island 2 for macOS', CFBundleDisplayName='LEGO Island 2 for macOS',
                 CFBundleExecutable='IslandLauncher', CFBundleIdentifier='io.github.flakescorn.lego-island-2-macos',
                 CFBundlePackageType='APPL', CFBundleVersion='2', CFBundleShortVersionString='0.2.0',
                 CFBundleIconFile='Launcher', LSMinimumSystemVersion='26.0', NSHighResolutionCapable=True,
                 NSPrincipalClass='NSApplication', NSHumanReadableCopyright='Unofficial fan project. Based on AntAir267/li2-recompiled; see bundled credits and licenses.')
    with (output/'Contents/Info.plist').open('wb') as f: plistlib.dump(plist, f)
    subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(output)],check=True)
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(output)],check=True)
    subprocess.run([sys.executable,str(ROOT/'tools/macos/audit_public.py'),'--bundle',str(output)],check=True)
    if archive:
        destination = output.parent/'lego-island-2-macos-0.2.0-preview-arm64.zip'
        if destination.exists(): raise ValueError('Preserving existing archive: '+str(destination))
        with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(output.rglob('*')):
                if path.is_file(): zipped.write(path, str(path.relative_to(output.parent)))
        print('Launcher archive:',destination)
    print('Public launcher (no game code/assets):',output)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=pathlib.Path,default=ROOT/'dist/LEGO Island 2 Launcher.app')
    parser.add_argument('--zip',action='store_true')
    args=parser.parse_args()
    try: build(args.output.expanduser().resolve(), args.zip)
    except (ValueError,OSError,subprocess.CalledProcessError) as e: sys.exit(str(e))
