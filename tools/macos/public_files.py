"""Explicit source boundary shared by launcher packaging and publication checks."""
import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOP = {'.gitignore', '.recomp.json', 'Makefile', 'LICENSE', 'README.md',
       'MACOS.md', 'BUILDING.md', 'CREDITS.md', 'DESIGN.md', 'CONTRIBUTING.md',
       'THIRD_PARTY_NOTICES.md', 'SECURITY.md'}
TREES = ('runtime/', 'tools/', 'builds/', 'tests/', 'macos/', 'docs/', '.github/',
         'licenses/', 'third_party/dmusic/', 'third_party/dr_libs/', 'third_party/pl_mpeg/')
SUFFIXES = {'.c', '.h', '.py', '.md', '.txt', '.json', '.swift', '.sh', '.inc',
            '.yml', '.yaml', '.vert', '.frag', '.glsl', '.plist', '.rc', '.manifest'}


def allowed(name):
    p = pathlib.PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '__pycache__' in p.parts:
        return False
    if any(part.lower() in ('_data', 'gen', 'work', 'build', 'captures') or
           part.lower().endswith('.app') for part in p.parts):
        return False
    return (name in TOP or name == 'third_party/README.md' or
            (name.startswith(TREES) and p.suffix in SUFFIXES))


def files(root=ROOT):
    # Only traverse permitted source trees, never the game/dependency/build directories.
    found = [root / n for n in TOP if (root / n).is_file()]
    found += [root / 'third_party/README.md'] if (root / 'third_party/README.md').is_file() else []
    for tree in TREES:
        base = root / tree
        if base.exists():
            found.extend(p for p in base.rglob('*') if p.is_file() and allowed(p.relative_to(root).as_posix()))
    result = sorted(set(found))
    for p in result:
        if p.is_symlink():
            raise ValueError('Source symlinks are not permitted: ' + str(p))
    return result


def fingerprint(root=ROOT):
    h = hashlib.sha256()
    for p in files(root):
        name = p.relative_to(root).as_posix()
        # UI/documentation edits do not invalidate a user's compiled game.
        if name != 'Makefile' and not name.startswith(('runtime/', 'builds/', 'tools/',
                'third_party/dmusic/', 'third_party/dr_libs/', 'third_party/pl_mpeg/')):
            continue
        if name in ('tools/macos/build_launcher.py', 'tools/macos/audit_public.py', 'tools/macos/verify.py'):
            continue
        h.update(name.encode() + b'\0')
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()
