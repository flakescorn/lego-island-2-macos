#!/usr/bin/env python3
"""Fail closed on private inputs/generated game outputs in source or a launcher bundle."""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from public_files import ROOT, allowed, files, fingerprint


def check_source(name, data):
    if not allowed(name): raise ValueError('Not in the public source allowlist: '+name)
    if data.startswith((b'MZ', b'RIFF', b'PK\x03\x04', b'\x89PNG', b'\xff\xd8\xff')) or b'\x00' in data:
        raise ValueError('Unexpected binary/asset in public source: '+name)
    if data.startswith(b'/* Generated from the user\'s game files'):
        raise ValueError('Translated proprietary game code: '+name)
    if b'/' + b'Users/' in data or b'/' + b'home/jouke' in data:
        raise ValueError('Private absolute home path: '+name)
    if re.search(rb'gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', data):
        raise ValueError('Possible credential/private key: '+name)


def audit_bundle(bundle):
    resources = bundle/'Contents/Resources'
    entries = json.loads((resources/'source-manifest.json').read_text())
    manifest = {e['path']:e['sha256'] for e in entries}
    if len(manifest) != len(entries): raise ValueError('Duplicate source manifest entry')
    payload = resources/'EngineSource'
    actual = {p.relative_to(payload).as_posix():p for p in payload.rglob('*') if p.is_file()}
    if set(actual) != set(manifest): raise ValueError('Launcher source manifest does not match its payload')
    for name,path in actual.items():
        if path.is_symlink(): raise ValueError('Unexpected source symlink: '+name)
        data=path.read_bytes();check_source(name,data)
        if hashlib.sha256(data).hexdigest()!=manifest[name]: raise ValueError('Source checksum mismatch: '+name)
    permitted={'Contents/Info.plist','Contents/MacOS/IslandLauncher','Contents/_CodeSignature/CodeResources',
               'Contents/Resources/Launcher.icns','Contents/Resources/Source.version','Contents/Resources/source-manifest.json'}
    for path in bundle.rglob('*'):
        if path.is_symlink(): raise ValueError('Unexpected bundle symlink: '+str(path))
        if not path.is_file(): continue
        name=path.relative_to(bundle).as_posix()
        if name not in permitted and not name.startswith('Contents/Resources/EngineSource/'):
            raise ValueError('Unexpected launcher content: '+name)
    exe=bundle/'Contents/MacOS/IslandLauncher'
    if not exe.is_file(): raise ValueError('Missing launcher executable')
    if (resources/'Source.version').read_text().strip() != fingerprint(payload):
        raise ValueError('Engine source fingerprint does not match the payload')
    if b'/' + b'Users/' in exe.read_bytes():
        raise ValueError('Unexpected absolute home path in launcher executable')
    if b'117c111d8de6ce6179c70b2ff88f74766a3417b9997e83b186e1c56fca873198' in exe.read_bytes():
        raise ValueError('The launcher executable unexpectedly contains the compiled game hash')
    print('PASS: launcher allowlist and %d source checksums; no original game files or translated game output'%len(actual))


def audit_source(history=False):
    paths=files()
    for path in paths:check_source(path.relative_to(ROOT).as_posix(),path.read_bytes())
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=str(ROOT)).decode().split('\0')
    for name in filter(None,tracked):
        if not allowed(name):raise ValueError('Unexpected tracked file: '+name)
    print('PASS: %d public source files; tracked paths are allowlisted'%len(paths))
    if history:
        objects=subprocess.check_output(['git','rev-list','--objects','--all'],cwd=str(ROOT),text=True)
        blobs=0
        for row in objects.splitlines():
            if ' ' not in row:continue
            sha,name=row.split(' ',1)
            kind=subprocess.check_output(['git','cat-file','-t',sha],cwd=str(ROOT),text=True).strip()
            if kind!='blob':continue
            check_source(name,subprocess.check_output(['git','cat-file','blob',sha],cwd=str(ROOT)))
            blobs+=1
        print('PASS: %d historical blobs scanned; original upstream history retained'%blobs)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=pathlib.Path);p.add_argument('--history',action='store_true')
    a=p.parse_args()
    try:
        if a.bundle:audit_bundle(a.bundle)
        else:audit_source(a.history)
    except (ValueError,OSError,subprocess.CalledProcessError) as e:sys.exit('PUBLICATION AUDIT FAILED: '+str(e))
