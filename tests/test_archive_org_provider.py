import unittest
from unittest.mock import patch

from visuals import providers
from visuals.license import License


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


class ArchiveOrgProviderTests(unittest.TestCase):
    def test_search_expands_beyond_two_collections_and_keeps_strict_license_filter(self):
        docs = [
            {"identifier": "pd-film", "title": "Public domain", "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/"},
            {"identifier": "cc0-film", "title": "CC0", "licenseurl": "https://creativecommons.org/publicdomain/zero/1.0/"},
            {"identifier": "cc-by-film", "title": "CC BY", "licenseurl": "https://creativecommons.org/licenses/by/4.0/"},
            {"identifier": "unknown-film", "title": "Unknown", "licenseurl": ""},
        ]
        metadata = {
            "result": [
                {"format": "512kb MPEG4", "name": "video.mp4", "width": 1280, "height": 720, "length": "30"}
            ]
        }
        responses = [_Response({"response": {"docs": docs}}), _Response(metadata), _Response(metadata)]

        with patch.object(providers._session, "get", side_effect=responses) as get:
            results = providers.search_archive_org("moon landing", per_page=8)

        self.assertEqual({item.id for item in results}, {"ia_pd-film", "ia_cc0-film"})
        self.assertTrue(all(item.license.license in (License.PUBLIC_DOMAIN, License.CC0) for item in results))
        query = get.call_args_list[0].kwargs["params"]["q"]
        self.assertIn("mediatype:movies", query)
        self.assertNotIn("collection:", query)
        self.assertEqual(get.call_count, 3)


if __name__ == "__main__":
    unittest.main()
