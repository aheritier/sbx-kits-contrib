import os
from pathlib import Path
import subprocess
import unittest


class VolumePathsTest(unittest.TestCase):
    def test_refuses_missing_unmounted_and_symlink_paths(self):
        self.assertTrue(Path("/.dockerenv").exists())
        self.assertFalse(os.path.lexists("/data"))
        for kind in ("missing", "directory", "symlink", "file"):
            with self.subTest(kind=kind):
                if kind == "directory":
                    os.mkdir("/data")
                elif kind == "symlink":
                    os.rmdir("/data")
                    os.symlink("/tmp", "/data")
                elif kind == "file":
                    os.unlink("/data")
                    Path("/data").write_text("keep")
                result = subprocess.run(
                    ["python3", "/kit/hermes-volume-init.py"],
                    env={**os.environ, "HERMES_INIT_VOLUME": "1", "HERMES_HOME": "/data"},
                    capture_output=True, text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Hermes volume initialization failed", result.stderr)
                self.assertEqual(Path("/tmp").stat().st_uid, 0)
                if kind == "file":
                    self.assertEqual(Path("/data").read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
