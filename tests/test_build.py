import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import Gerar_executavel as builder
from src.dvaStudio.core.downloader import _get_ffmpeg_dir, _get_js_runtimes


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for name, value in (("ROOT", self.root), ("BUILD", self.root / "build"),
                            ("DIST", self.root / "dist")):
            patcher = patch.object(builder, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        builder.BUILD.mkdir()

    def test_replaces_previous_distribution_and_preserves_config_bytes(self):
        builder.DIST.mkdir()
        (builder.DIST / "old.exe").write_bytes(b"old")
        original = b'{"download_dir": "D:/Musicas", "quality": 192}\n'
        (builder.DIST / "config.json").write_bytes(original)
        (self.root / "config.json").write_text('{"quality": 128}')
        new = builder.BUILD / "staging"
        new.mkdir()
        (new / "DVAStudio.exe").write_bytes(b"new")
        builder._preserve_config(new)
        builder._replace_dist(new)
        self.assertFalse((builder.DIST / "old.exe").exists())
        self.assertEqual((builder.DIST / "DVAStudio.exe").read_bytes(), b"new")
        self.assertEqual((builder.DIST / "config.json").read_bytes(), original)
        self.assertEqual(list(builder.BUILD.iterdir()), [])

    def test_restores_previous_distribution_if_publish_fails(self):
        builder.DIST.mkdir()
        (builder.DIST / "old.exe").write_bytes(b"old")
        new = builder.BUILD / "staging"
        new.mkdir()
        rename = Path.rename

        def fail_new(path, target):
            if path == new:
                raise PermissionError("file in use")
            return rename(path, target)

        with patch.object(Path, "rename", fail_new):
            with self.assertRaises(PermissionError):
                builder._replace_dist(new)
        self.assertEqual((builder.DIST / "old.exe").read_bytes(), b"old")

    def test_refuses_operations_outside_project(self):
        for path in (self.root, self.root.parent / "other", self.root / ".." / "other"):
            with self.assertRaises(RuntimeError):
                builder._remove(path)

    def test_frozen_runtime_uses_only_bundled_executables(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        (runtime / "ffmpeg.exe").touch()
        (runtime / "node.exe").touch()
        with patch("sys.frozen", True, create=True), patch("sys._MEIPASS", str(self.root), create=True):
            self.assertEqual(_get_ffmpeg_dir(), str(runtime))
            self.assertEqual(_get_js_runtimes(), {"node": {"path": str(runtime / "node.exe")}})


if __name__ == "__main__":
    unittest.main()
