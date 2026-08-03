import unittest
import tempfile
import os
import json
import hashlib
from pathlib import Path

import anchor_metadata


class TestAnchorMetadataExtra(unittest.TestCase):
    def test_exclude_patterns(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "keep.txt").write_bytes(b"ok")
            (td_path / "secret.txt").write_bytes(b"no")
            sub = td_path / "sub"
            sub.mkdir()
            (sub / "skipme.txt").write_bytes(b"skip")

            manifest = anchor_metadata.generate_ip_manifest(td_path, exclude_globs=["secret.txt", "sub/*"])

            self.assertIn("keep.txt", manifest["assets"])
            self.assertNotIn("secret.txt", manifest["assets"])
            self.assertNotIn("sub/skipme.txt", manifest["assets"])  # excluded by pattern

    def test_skip_hidden_flag(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / ".hiddenfile").write_bytes(b"x")
            manifest_default = anchor_metadata.generate_ip_manifest(td_path)
            self.assertNotIn(".hiddenfile", manifest_default["assets"])  # default skips hidden

            manifest_including_hidden = anchor_metadata.generate_ip_manifest(td_path, skip_hidden=False)
            self.assertIn(".hiddenfile", manifest_including_hidden["assets"])  # included when skip_hidden=False

    def test_nonexistent_target_raises(self):
        nonexist = Path(tempfile.gettempdir()) / "__this_dir_should_not_exist_123456789"
        # Ensure it doesn't exist
        if nonexist.exists():
            # remove if by chance present
            if nonexist.is_dir():
                for p in nonexist.rglob('*'):
                    if p.is_file():
                        p.unlink()
                nonexist.rmdir()
            else:
                nonexist.unlink()
        with self.assertRaises(FileNotFoundError):
            anchor_metadata.generate_ip_manifest(nonexist)

    def test_write_manifest_fallback_when_parent_uncreatable(self):
        # Prepare a manifest and an output path whose parent is a file to force mkdir to fail
        manifest = {"assets": {}, "master_anchor_hash": "deadbeef"}
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            # Create a file where a directory is expected
            parent_file = td_path / "parentfile"
            parent_file.write_bytes(b"I am a file, not a dir")
            output_path = parent_file / "out.json"  # this makes parent_path == parent_file which is a file

            # Change cwd to td so fallback writes into td if mkdir fails
            old_cwd = Path.cwd()
            try:
                os.chdir(td_path)
                out = anchor_metadata.write_manifest(manifest, output_path)
                # Expect the fallback to write to cwd/out.json
                expected = td_path / "out.json"
                self.assertEqual(Path(out).resolve(), expected.resolve())
                self.assertTrue(expected.exists())
                # Cleanup
                expected.unlink()
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
