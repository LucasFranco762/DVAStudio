import functools
import http.server
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import imageio_ffmpeg

from src.dvaStudio.core.downloader import DownloadRequest, DownloadWorker, MediaInfoWorker


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class DownloadWorkerTests(unittest.TestCase):
    def test_original_name_lookup_does_not_download_media_and_sanitizes_filename(self):
        worker = MediaInfoWorker("https://example.com/music")
        names, failures, done = [], [], []
        worker.title_ready.connect(names.append)
        worker.failed.connect(failures.append)
        worker.done.connect(lambda: done.append(True))
        with patch('yt_dlp.YoutubeDL') as ydl_class:
            ydl = ydl_class.return_value.__enter__.return_value
            ydl.extract_info.return_value = {"title": 'Artista: Música / Ao vivo?'}
            worker.run()
            ydl.extract_info.assert_called_once_with(worker.url, download=False)
            self.assertTrue(ydl_class.call_args.args[0]["skip_download"])
        self.assertEqual(failures, [])
        self.assertEqual(len(names), 1)
        self.assertIn("Música", names[0])
        self.assertFalse(any(character in names[0] for character in '<>:"/\\|?*'))
        self.assertEqual(done, [True])

    def test_cancelled_name_lookup_does_not_request_metadata(self):
        worker = MediaInfoWorker("https://example.com/music")
        worker.cancel()
        with patch('yt_dlp.YoutubeDL') as ydl_class:
            worker.run()
            ydl_class.assert_not_called()

    def test_download_and_convert_to_playable_mp3(self):
        """Baixa por HTTP e converte com os binários reais, sem acessar sites."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run(
                [ffmpeg, '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.2',
                 '-y', str(root / 'source.wav')],
                capture_output=True, check=True,
            )
            server = http.server.ThreadingHTTPServer(
                ('127.0.0.1', 0),
                functools.partial(QuietHandler, directory=str(root)),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                request = DownloadRequest(
                    f'http://127.0.0.1:{server.server_port}/source.wav',
                    'audio', root / 'áudio 100%', 'mp3', 'música 50% %(title)s',
                )
                worker = DownloadWorker(request)
                successes, failures = [], []
                worker.finished.connect(lambda path, title: successes.append(path))
                worker.failed.connect(failures.append)
                with patch.dict(os.environ, {'LOCALAPPDATA': str(root)}):
                    worker.run()
                self.assertEqual(failures, [])
                expected = request.output_dir / 'música 50% %(title)s.mp3'
                self.assertEqual(successes, [str(expected)])
                self.assertGreater(expected.stat().st_size, 0)
                subprocess.run(
                    [ffmpeg, '-v', 'error', '-i', str(expected), '-f', 'null', '-'],
                    capture_output=True, check=True,
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_failure_includes_extractor_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker = DownloadWorker(DownloadRequest('https://example.com/video', 'audio', Path(tmp), 'mp3'))
            failures = []
            worker.failed.connect(failures.append)

            def fail(url, download):
                options = ydl_class.call_args.args[0]
                self.assertIn('node', options['js_runtimes'])
                options['logger'].warning('JavaScript runtime unavailable')
                raise RuntimeError('Requested format is not available')

            with patch('src.dvaStudio.core.downloader._get_ffmpeg_dir', return_value=tmp), \
                    patch('yt_dlp.YoutubeDL') as ydl_class:
                ydl_class.return_value.__enter__.return_value.extract_info.side_effect = fail
                worker.run()
            self.assertEqual(len(failures), 1)
            self.assertIn('Requested format is not available', failures[0])
            self.assertIn('JavaScript runtime unavailable', failures[0])


if __name__ == '__main__':
    unittest.main()
