#!/usr/bin/env python3
"""Validate a user's game without modifying it. Exit 2 means unsupported executable."""
import hashlib, json, pathlib, sys
WANT = '385f223b6aea264b3b0eac7aa08b46cf13ffa675cedd1788e765417fb81e792a'
EN1 = '117c111d8de6ce6179c70b2ff88f74766a3417b9997e83b186e1c56fca873198'
def inspect(folder):
    folder = pathlib.Path(folder).expanduser().resolve()
    if not folder.is_dir(): raise ValueError('Not a game folder: '+str(folder))
    files = {p.name.lower():p for p in folder.iterdir()}
    exe = files.get('lego island 2.exe'); data = files.get('_data')
    if not exe or not exe.is_file(): raise ValueError('Missing LEGO Island 2.exe')
    if not data or not data.is_dir(): raise ValueError('Missing _data folder')
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    missing = [name for name in ('menu.bob','menu.bod','fonts.bob','fonts.bod','genericbits.bob','bricks.bob')
               if name not in {p.name.lower() for p in data.iterdir()}]
    return dict(folder=str(folder),executable=str(exe),sha256=sha,
                version='English Version 2' if sha==WANT else 'English Version 1' if sha==EN1 else 'Unknown/modified',
                build_config='builds/en_v1.py' if sha==EN1 else 'builds/en_v2.py' if sha==WANT else None,
                supported=sha in (WANT,EN1) and not missing,missing_core_assets=missing,
                expected_sha256=EN1 if sha==EN1 else WANT,
                supported_sha256=[EN1,WANT],
                asset_check='Core filenames only; full asset completeness and version compatibility require game testing.')
if __name__=='__main__':
    try: result=inspect(sys.argv[1]); print(json.dumps(result,indent=2)); sys.exit(0 if result['supported'] else 2)
    except (ValueError,OSError,IndexError) as e: sys.exit(str(e)+'\nUsage: check_game.py GAME_FOLDER')
