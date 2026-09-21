"""Index HTML serves mtime-based static asset versions."""

import re
import unittest

from fastapi.testclient import TestClient

import server


class IndexCacheBustTest(unittest.TestCase):
    def test_index_injects_static_mtime_versions(self):
        client = TestClient(server.app)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-cache", response.headers.get("cache-control", "").lower())

        html = response.text
        app_mtime = str(int(server._static_mtime_version("app.js")))
        self.assertIn(f"/static/app.js?v={app_mtime}", html)
        self.assertIsNone(re.search(r"/static/app\.js\?v=5\.\d+", html))


if __name__ == "__main__":
    unittest.main()
