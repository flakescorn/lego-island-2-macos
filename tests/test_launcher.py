"""Asset-free checks of import boundaries, validation, and source packaging."""
import io
import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools/macos'))
from audit_public import check_source
from check_game import inspect
from iso_import import archive_files, safe_relative
from launcher_backend import atomic_json, run
from public_files import allowed, fingerprint


class SourceBoundaryTests(unittest.TestCase):
    def test_document_edits_keep_the_prepared_game_but_engine_edits_invalidate_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);(root/'runtime').mkdir()
            (root/'runtime/test.c').write_text('/* engine */')
            before=fingerprint(root)
            (root/'README.md').write_text('Updated instructions')
            self.assertEqual(fingerprint(root),before)
            (root/'runtime/test.c').write_text('/* changed engine */')
            self.assertNotEqual(fingerprint(root),before)

    def test_private_outputs_cannot_enter_source_payload(self):
        for name in ['gen/code_000.c', 'work/Game/LEGO Island 2.exe', 'build/li2',
                     'dist/Launcher.app/Contents/MacOS/IslandLauncher', 'runtime/_data/menu.bob',
                     'runtime/secret.dls', 'tools/macos/game.iso', '/runtime/test.c',
                     'tools/../private.c', 'runtime/__pycache__/test.py']:
            self.assertFalse(allowed(name), name)
        self.assertTrue(allowed('runtime/shaders/draw.frag.spv.h'))

    def test_generated_code_and_binary_disguised_as_source_are_rejected(self):
        for data in [b'MZnot-source', b'RIFFnot-source', b'abc\0def',
                     b"/* Generated from the user's game files by tools/recomp.py. */"]:
            with self.assertRaises(ValueError): check_source('runtime/test.c', data)

    def test_wrong_executable_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            d=pathlib.Path(temp); (d/'_data').mkdir()
            (d/'LEGO Island 2.exe').write_bytes(b'own test data, not game code')
            result=inspect(d)
            self.assertFalse(result['supported'])
            self.assertEqual(result['version'], 'Unknown/modified')


class ImportTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'darwin', 'macOS preparation worker')
    def test_invalid_iso_preserves_ready_record_and_saves_without_bootstrapping(self):
        with tempfile.TemporaryDirectory() as temp:
            d=pathlib.Path(temp);library=d/'Library';library.mkdir()
            record=library/'prepared.json';record.write_text('{"existing":"game"}')
            saves=library/'Profiles/en-v1';saves.mkdir(parents=True)
            (saves/'own-test-save').write_text('existing progress')
            bad=d/'wrong.iso'
            with tarfile.open(bad,'w'):pass
            result=subprocess.run([sys.executable,str(ROOT/'tools/macos/launcher_backend.py'),
                '--input',str(bad),'--library',str(library)],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,1)
            events=[json.loads(line) for line in result.stdout.splitlines()]
            self.assertIn('Unsupported disc layout',events[-1]['message'])
            self.assertEqual(record.read_text(),'{"existing":"game"}')
            self.assertEqual((saves/'own-test-save').read_text(),'existing progress')
            self.assertFalse((library/'Engines').exists())

    def test_windows_and_unix_traversal_are_rejected(self):
        for name in ['../escape', 'a/../../escape', '/absolute', 'C:\\Windows\\file', 'a\\..\\escape']:
            with self.assertRaises(ValueError):safe_relative(name)
        self.assertEqual(safe_relative('_Data\\sounds\\test.wav').as_posix(), '_Data/sounds/test.wav')

    @unittest.skipUnless(sys.platform == 'darwin', 'Uses the macOS libarchive')
    def test_archive_link_cannot_escape_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            d=pathlib.Path(temp); archive=d/'fixture.tar'; output=d/'output';output.mkdir()
            with tarfile.open(archive,'w') as t:
                item=tarfile.TarInfo('escape');item.type=tarfile.SYMTYPE;item.linkname='../outside';t.addfile(item)
            with self.assertRaises(ValueError):archive_files(archive,output,lambda p:p)
            self.assertEqual(list(output.iterdir()), [])

    @unittest.skipUnless(sys.platform == 'darwin', 'Uses the macOS libarchive')
    def test_archive_extracts_only_selected_files_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            d=pathlib.Path(temp); archive=d/'fixture.tar'; output=d/'output';output.mkdir()
            with tarfile.open(archive,'w') as t:
                for name,data in [('keep.txt',b'keep'),('ignore.txt',b'ignore')]:
                    item=tarfile.TarInfo(name);item.size=len(data);t.addfile(item,io.BytesIO(data))
            archive_files(archive,output,lambda p:p if p.name=='keep.txt' else None)
            self.assertEqual((output/'keep.txt').read_bytes(), b'keep')
            self.assertFalse((output/'ignore.txt').exists())
            with self.assertRaises(FileExistsError):archive_files(archive,output,lambda p:p)

    def test_worker_timeout_stops_a_stuck_child(self):
        with tempfile.TemporaryDirectory() as temp:
            with (pathlib.Path(temp)/'log.txt').open('w') as log:
                with self.assertRaises(RuntimeError):
                    run([sys.executable,'-c','import time; time.sleep(30)'],temp,log,timeout=0.1)


if __name__=='__main__':unittest.main()
