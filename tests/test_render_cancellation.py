"""Cancellation tests for interruptible stock-video downloads."""
import os
import tempfile
import unittest
from unittest.mock import patch

from video_fetcher import _download


class FakeResponse:
    def raise_for_status(self):
        return None

    def iter_content(self, _chunk_size):
        yield b"first-chunk"
        yield b"second-chunk"


class TestRenderCancellation(unittest.TestCase):
    @patch("video_fetcher.requests.get", return_value=FakeResponse())
    def test_download_removes_partial_file_when_cancelled(self, _get):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "partial.mp4")
            self.assertFalse(_download("https://example.invalid/video", path, cancel_check=lambda: True))
            self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()