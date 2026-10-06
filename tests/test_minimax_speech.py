"""speech-2.8-hd has no official local weights. Studio must not offer it."""
import unittest

from tts_voices import get_voice_catalog, resolve_voice


def _catalog_ids(catalog):
    ids = []
    for key, value in catalog.items():
        if not isinstance(value, list):
            continue
        for entry in value:
            if isinstance(entry, dict) and entry.get("id"):
                ids.append(entry["id"])
    return ids


class TestSpeech28HdNotOffered(unittest.TestCase):
    def test_catalog_has_no_speech_28_hd(self):
        catalog = get_voice_catalog()
        self.assertNotIn("minimax", catalog)
        self.assertNotIn("minimax_meta", catalog)
        for voice_id in _catalog_ids(catalog):
            self.assertNotIn("speech-2.8-hd", voice_id)
            self.assertFalse(str(voice_id).startswith("minimax:"))

    def test_stale_selection_falls_back_to_edge(self):
        self.assertEqual(resolve_voice("tr", gender="male"), "tr-TR-AhmetNeural")
        self.assertEqual(
            resolve_voice("tr", voice_id="minimax:speech-2.8-hd", gender="male"),
            "tr-TR-AhmetNeural",
        )

    def test_engine_does_not_call_minimax_speech_api(self):
        import tts_engine

        with open(tts_engine.__file__, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("api.minimax.io/v1/t2a_v2", source)
        self.assertNotIn("speech-2.8-hd", source)


if __name__ == "__main__":
    unittest.main()
