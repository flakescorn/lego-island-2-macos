#!/usr/bin/env python3
"""Validate, translate and build the user's supported executable. Never patches an input."""
import os,pathlib,subprocess,sys
from check_game import inspect
root=pathlib.Path(__file__).resolve().parents[2];os.chdir(root)
if len(sys.argv)!=2:sys.exit('Usage: python3 tools/macos/build.py GAME_FOLDER')
if sys.platform!='darwin' or os.uname().machine!='arm64':sys.exit('Use an ARM64 Mac.')
result=inspect(sys.argv[1])
if not result['supported']:sys.exit('Unsupported/incomplete game: '+result['version']+'\nSHA-256 '+result['sha256']+'\nUse an original English Version 1 or Version 2 executable; see MACOS.md.')
py=root/'.venv/bin/python'
if not py.exists():sys.exit('Run tools/macos/bootstrap.py first.')
if result['build_config']=='builds/en_v1.py':
    subprocess.run([str(py),'tools/macos/audit_v1.py',result['folder']],check=True)
# Always translate explicitly: switching game folders must never reuse stale generated files.
subprocess.run([str(py),'tools/recomp.py',result['folder'],result['build_config'],'gen'],check=True)
subprocess.run(['make','JOBS=4','GAME='+result['folder'],'BUILD_CFG='+result['build_config']],check=True)
print('Built build/li2. Test with --game before making a private local app; see MACOS.md.')
