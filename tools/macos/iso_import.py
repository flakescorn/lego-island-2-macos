"""Extract a user-owned disc locally; never run the Windows installer.

System libarchive reads ISO/CAB members; libunshield reads InstallShield Game files.
All output paths are validated, links/devices are rejected, and files are exclusive.
"""
import ctypes as C
import os
import pathlib
import shutil


def safe_relative(name):
    name = name.replace('\\', '/')
    p = pathlib.PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or ':' in name or '\x00' in name:
        raise ValueError('Unsafe archive path: ' + repr(name))
    return p


def archive_files(source, destination, accept):
    """Stream accepted regular members; do not trust archive-provided paths or links."""
    lib = C.CDLL('/usr/lib/libarchive.2.dylib')
    for name in ('archive_read_new', 'archive_error_string'):
        getattr(lib, name).restype = C.c_void_p if name.endswith('_new') else C.c_char_p
    for name in ('archive_read_support_filter_all', 'archive_read_support_format_all',
                 'archive_read_free', 'archive_read_data_skip'):
        getattr(lib, name).argtypes = [C.c_void_p]
    lib.archive_error_string.argtypes = [C.c_void_p]
    lib.archive_read_open_filename.argtypes = [C.c_void_p, C.c_char_p, C.c_size_t]
    lib.archive_read_next_header.argtypes = [C.c_void_p, C.POINTER(C.c_void_p)]
    lib.archive_read_data.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t]
    lib.archive_read_data.restype = C.c_ssize_t
    for name in ('archive_entry_pathname', 'archive_entry_symlink', 'archive_entry_hardlink'):
        getattr(lib, name).argtypes = [C.c_void_p]
        getattr(lib, name).restype = C.c_char_p
    lib.archive_entry_filetype.argtypes = [C.c_void_p]
    lib.archive_entry_filetype.restype = C.c_uint
    lib.archive_entry_size.argtypes = [C.c_void_p]
    lib.archive_entry_size.restype = C.c_int64
    a = lib.archive_read_new()
    destination = pathlib.Path(destination)
    output = []
    total = 0
    try:
        lib.archive_read_support_filter_all(a)
        lib.archive_read_support_format_all(a)
        if lib.archive_read_open_filename(a, os.fsencode(source), 10240) != 0:
            raise ValueError('Cannot read disc/archive: ' + str(lib.archive_error_string(a)))
        entry = C.c_void_p()
        while True:
            status = lib.archive_read_next_header(a, C.byref(entry))
            if status == 1: break
            if status < 0: raise ValueError('Damaged archive: ' + str(lib.archive_error_string(a)))
            raw = lib.archive_entry_pathname(entry)
            if not raw: raise ValueError('Archive member has no name')
            rel = safe_relative(os.fsdecode(raw))
            chosen = accept(rel)
            if chosen is None:
                lib.archive_read_data_skip(a)
                continue
            rel = safe_relative(str(chosen))
            if lib.archive_entry_symlink(entry) or lib.archive_entry_hardlink(entry):
                raise ValueError('Archive links are not supported: ' + str(rel))
            kind = lib.archive_entry_filetype(entry)
            path = destination.joinpath(*rel.parts)
            if kind == 0o040000:
                path.mkdir(parents=True, exist_ok=True)
                continue
            if kind != 0o100000: raise ValueError('Unsupported archive member: ' + str(rel))
            size = lib.archive_entry_size(entry)
            total += max(0, size)
            if size < 0 or total > 8 * 1024**3: raise ValueError('Archive exceeds the 8 GB import limit')
            path.parent.mkdir(parents=True, exist_ok=True)
            if size > shutil.disk_usage(destination).free - 256 * 1024**2:
                raise ValueError('Not enough free disk space to extract the game')
            with path.open('xb') as f:
                buf = C.create_string_buffer(1024 * 1024)
                while True:
                    n = lib.archive_read_data(a, buf, len(buf))
                    if n < 0: raise ValueError('Cannot extract member: ' + str(rel))
                    if not n: break
                    f.write(buf.raw[:n])
            output.append(path)
    finally:
        lib.archive_read_free(a)
    return output


def extract_game(cab, game, unshield_prefix):
    lib = C.CDLL(str(pathlib.Path(unshield_prefix) / 'lib/libunshield.1.dylib'))
    lib.unshield_set_log_level.argtypes = [C.c_int]
    lib.unshield_set_log_level(0)
    class Group(C.Structure):
        _fields_ = [('name', C.c_char_p), ('first', C.c_uint), ('last', C.c_uint)]
    lib.unshield_open.argtypes = [C.c_char_p]; lib.unshield_open.restype = C.c_void_p
    lib.unshield_close.argtypes = [C.c_void_p]
    lib.unshield_file_group_find.argtypes = [C.c_void_p, C.c_char_p]
    lib.unshield_file_group_find.restype = C.POINTER(Group)
    for name in ('unshield_file_count', 'unshield_directory_count'):
        getattr(lib, name).argtypes = [C.c_void_p]
    for name in ('unshield_file_name', 'unshield_directory_name'):
        getattr(lib, name).argtypes = [C.c_void_p, C.c_int]; getattr(lib, name).restype = C.c_char_p
    for name in ('unshield_file_directory', 'unshield_file_is_valid', 'unshield_file_size'):
        getattr(lib, name).argtypes = [C.c_void_p, C.c_int]
    lib.unshield_file_is_valid.restype = C.c_bool
    lib.unshield_file_size.restype = C.c_size_t
    lib.unshield_file_save.argtypes = [C.c_void_p, C.c_int, C.c_char_p]
    lib.unshield_file_save.restype = C.c_bool
    u = lib.unshield_open(os.fsencode(cab))
    if not u: raise ValueError('Cannot open the disc InstallShield cabinet')
    game = pathlib.Path(game)
    game.mkdir(parents=True, exist_ok=False)
    count = 0
    try:
        group = lib.unshield_file_group_find(u, b'Game')
        if not group: raise ValueError('This disc has no supported InstallShield Game group')
        group = group.contents
        if group.first > group.last or group.last >= lib.unshield_file_count(u):
            raise ValueError('Invalid InstallShield file group')
        total = 0
        for i in range(group.first, group.last + 1):
            if not lib.unshield_file_is_valid(u, i): continue
            name = lib.unshield_file_name(u, i)
            if not name: raise ValueError('Cabinet member has no filename')
            folder_index = lib.unshield_file_directory(u, i)
            folder = b''
            if folder_index >= 0:
                if folder_index >= lib.unshield_directory_count(u): raise ValueError('Invalid cabinet directory')
                folder = lib.unshield_directory_name(u, folder_index) or b''
            relative = safe_relative(os.fsdecode(folder) + '/' + os.fsdecode(name)) if folder else safe_relative(os.fsdecode(name))
            target = game.joinpath(*relative.parts)
            total += lib.unshield_file_size(u, i)
            if total > 8 * 1024**3: raise ValueError('Installed game exceeds the 8 GB import limit')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists(): raise ValueError('Duplicate cabinet filename: ' + str(relative))
            if lib.unshield_file_size(u, i) > shutil.disk_usage(game).free - 256 * 1024**2:
                raise ValueError('Not enough free disk space to install the game')
            if not lib.unshield_file_save(u, i, os.fsencode(target)):
                raise ValueError('Cannot extract game file: ' + str(relative))
            count += 1
    finally:
        lib.unshield_close(u)
    return count


def import_disc(iso, destination, unshield_prefix, progress=print):
    destination = pathlib.Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    cd = destination / 'Disc'
    cd.mkdir()
    def disc_member(p):
        parts = p.parts
        if parts and parts[0].lower() == 'lego island 2':
            return pathlib.PurePosixPath('LEGO Island 2', *parts[1:])
        if p.as_posix().lower() == 'directx8/directx.cab':
            return pathlib.PurePosixPath('directx8/directx.cab')
        return None
    progress('Reading your disc image…')
    archive_files(iso, cd, disc_member)
    folder = cd / 'LEGO Island 2'
    cabinets = [p for p in folder.iterdir() if p.name.lower() == 'data1.cab'] if folder.exists() else []
    if len(cabinets) != 1: raise ValueError('Unsupported disc layout: expected LEGO Island 2/data1.cab')
    game = destination / 'Game'
    progress('Extracting the original game files…')
    n = extract_game(cabinets[0], game, unshield_prefix)
    movies = next((p for p in folder.iterdir() if p.name.lower() == 'movies' and p.is_dir()), None)
    if movies: (game / 'Movies').symlink_to(movies, target_is_directory=True)
    cab = cd / 'directx8/directx.cab'
    if cab.exists():
        archive_files(cab, game, lambda p: pathlib.PurePosixPath(p.name.lower())
                      if p.name.lower() in ('gm16.dls', 'gmreadme.txt') else None)
    progress('Extracted %d game files locally.' % n)
    return game
