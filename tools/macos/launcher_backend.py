#!/usr/bin/env python3
"""Local-only launcher worker. Stdout is newline-delimited JSON, never a shell script."""
import argparse
import datetime
import fcntl
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import uuid

from check_game import inspect, EN1
from public_files import files, fingerprint
from iso_import import import_disc, archive_files


def emit(kind, **values):
    print(json.dumps(dict(type=kind, **values)), flush=True)


def atomic_json(path, data):
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(path)


def run(args, cwd, log, env=None, timeout=None):
    log.write('\n$ ' + repr([str(x) for x in args]) + '\n'); log.flush()
    # Never evaluate game paths as shell text. Children inherit our cancellable process group.
    with subprocess.Popen([str(x) for x in args], cwd=str(cwd), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors='replace') as p:
        timer = threading.Timer(timeout, p.kill) if timeout else None
        if timer: timer.start()
        try:
            for line in p.stdout:
                log.write(line); log.flush()
                emit('log', text=line.rstrip())
            status = p.wait()
        finally:
            if timer: timer.cancel()
    if status: raise RuntimeError('Preparation step failed (exit %d). Open the preparation log for details.' % status)


def stage(n, title, detail):
    emit('stage', index=n, title=title, detail=detail)


def prepare(source, input_path, library):
    if sys.platform != 'darwin' or os.uname().machine != 'arm64':
        raise ValueError('This preview requires an Apple Silicon Mac running macOS 26 or later.')
    input_path = input_path.expanduser().resolve()
    if not input_path.exists(): raise ValueError('The selected game source no longer exists. Choose it again.')
    library.mkdir(parents=True, exist_ok=True)
    lock = (library / 'prepare.lock').open('a')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: raise ValueError('Another preparation is running. Wait for it to finish.')
    version = fingerprint(source)
    workspace = library / 'Engines' / version[:20]
    logs = library / 'Logs'; logs.mkdir(exist_ok=True)
    log_path = logs / ('prepare-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6] + '.log')
    emit('logfile', path=str(log_path))
    with log_path.open('w', buffering=1) as log:
        stage(0, 'Checking your game', 'Your files stay on this Mac.')
        if input_path.is_dir():
            result = inspect(input_path)
            if not result['supported'] or result['sha256'] != EN1:
                raise ValueError('This preview supports the original English Version 1 executable and its complete _data folder. Selected: ' + result['version'])
            game = input_path
        elif input_path.suffix.lower() != '.iso':
            raise ValueError('Choose a LEGO Island 2 PC ISO, or an installed folder containing the executable and _data.')
        else:
            game = None
            cabinets = []
            def probe(member):
                if member.as_posix().lower() == 'lego island 2/data1.cab':
                    cabinets.append(member)
                return None
            # Validate the layout before downloading/building any dependencies.
            archive_files(input_path, library, probe)
            if len(cabinets) != 1:
                raise ValueError('Unsupported disc layout: expected LEGO Island 2/data1.cab in your PC ISO.')
        stage(1, 'Setting up the engine', 'Downloading and building pinned open-source tools. Internet is required on first setup.')
        if not workspace.exists():
            staging = workspace.with_name(workspace.name + '-' + uuid.uuid4().hex + '.partial')
            staging.mkdir(parents=True)
            for path in files(source):
                target = staging / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            staging.rename(workspace)
        tools = workspace / 'tools/macos'
        run([sys.executable, '-u', tools / 'bootstrap.py'], workspace, log)
        if game is None:
            stage(2, 'Importing your ISO', 'Extracting the game locally. The ISO will not be modified.')
            destination = library / 'Imports' / uuid.uuid4().hex
            game = import_disc(input_path, destination, workspace / 'third_party/unshield',
                               lambda text: emit('log', text=text))
            result = inspect(game)
            if not result['supported'] or result['sha256'] != EN1:
                raise ValueError('The imported disc is not the supported original English Version 1, or required assets are missing. Found: ' + result['version'])
        else:
            stage(2, 'Game files located', 'Using your installed folder without changing its files.')
        stage(3, 'Preparing native gameplay', 'Translating your copy and compiling it for Apple Silicon. This can take several minutes.')
        run([sys.executable, '-u', tools / 'build.py', game], workspace, log)
        stage(4, 'Checking the prepared game', 'Running a local startup check in a separate test profile.')
        env = {k: v for k, v in os.environ.items() if not k.startswith(('LI2_', 'DYLD_', 'SDL_'))}
        env.update(LI2_GPU_OFFSCREEN='1', LI2_TEST_FPS='30', MVK_CONFIG_LOG_LEVEL='1')
        probe_user = library / 'Checks' / uuid.uuid4().hex
        # Full game menu check, not a claim of full-game compatibility.
        run([workspace / 'build/li2', '--test', '--game', game, '--user', probe_user,
             '--frames', '1800', '--logfile', probe_user / 'startup.log'], workspace, log, env, timeout=90)
        stage(5, 'Finishing setup', 'Keeping game code and original assets in your private local library.')
        builds = library / 'Prepared'; builds.mkdir(exist_ok=True)
        bundle = builds / (uuid.uuid4().hex + '.app')
        run([sys.executable, tools / 'bundle.py', game, '--output', bundle, '--no-record-location'], workspace, log)
        profile = library / 'Profiles/en-v1'; profile.mkdir(parents=True, exist_ok=True)
        record = dict(schema=1, source_version=version, game_path=str(game),
                      executable_path=str(bundle / 'Contents/MacOS/li2'),
                      user_dir=str(profile), input_name=input_path.name,
                      game_version='English Version 1', prepared_at=datetime.datetime.now().isoformat(),
                      preparation_log=str(log_path))
        atomic_json(library / 'prepared.json', record)
        emit('ready', **record)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=pathlib.Path)
    p.add_argument('--library', required=True, type=pathlib.Path)
    p.add_argument('--source', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[2])
    a = p.parse_args()
    try:
        try: os.setsid()
        except OSError: pass
        prepare(a.source.resolve(), a.input, a.library.expanduser().resolve())
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as e:
        emit('error', message=str(e))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
