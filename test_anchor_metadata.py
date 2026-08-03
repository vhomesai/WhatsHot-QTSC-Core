import unittest
import tempfile
import os
import json
import hashlib
from pathlib import Path

import anchor_metadata


class TestAnchorMetadata(unittest.TestCase):
    def test_hash_file(self):
        # Create a temporary file with known content
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"hello world")
            tf.flush()
            tf_path = Path(tf.name)
        try:
            expected = hashlib.sha256(b"hello world").hexdigest()
            got = anchor_metadata.hash_file(tf_path)
            self.assertEqual(expected, got)
        finally:
            tf_path.unlink()

    def test_generate_ip_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            # Create files in an order that would exercise sorting
            (td_path / "b.txt").write_bytes(b"b")
            (td_path / "a.txt").write_bytes(b"a")
            # Hidden file should be skipped by default
            (td_path / ".hidden").write_bytes(b"x")

            sub = td_path / "dir1"
            sub.mkdir()
            (sub / "c.txt").write_bytes(b"c")

            manifest = anchor_metadata.generate_ip_manifest(td_path)

            # Hidden file should not be present
            self.assertNotIn(".hidden", manifest["assets"], msg="Hidden files should be skipped by default")

            # Assets should include created files
            self.assertIn("a.txt", manifest["assets"])
            self.assertIn("b.txt", manifest["assets"])
            self.assertIn("dir1/c.txt", manifest["assets"])  # relative posix path

            # Asset keys should be sorted deterministically
            keys = list(manifest["assets"].keys())
            self.assertEqual(keys, sorted(keys), msg="Asset keys must be sorted deterministically")

            # Size checks
            self.assertEqual(manifest["assets"]["a.txt"]["size_bytes"], 1)
            self.assertEqual(manifest["assets"]["b.txt"]["size_bytes"], 1)

            # Recompute master hash using the same canonicalization as the implementation
            manifest_copy = dict(manifest)
            # remove master_anchor_hash before recomputing
            manifest_copy.pop("master_anchor_hash", None)
            manifest_bytes = json.dumps(manifest_copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
            expected_master = hashlib.sha256(manifest_bytes).hexdigest()
            self.assertEqual(manifest["master_anchor_hash"], expected_master)


if __name__ == "__main__":
    unittest.main()
