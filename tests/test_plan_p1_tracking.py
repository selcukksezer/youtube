"""P1 tracker guardrails: no-face sampling cap and safe capture cleanup."""
import sys

import numpy as np

from visuals import face_reframe


class _NoFaceCascade:
    def __init__(self):
        self.calls = 0

    def detectMultiScale(self, gray, **kwargs):
        self.calls += 1
        return []


class _ReleaseErrorCapture:
    def __init__(self, cv2, raise_on_release=False):
        self._cv2 = cv2
        self.raise_on_release = raise_on_release
        self.read_calls = 0
        self.release_calls = 0

    def isOpened(self):
        return True

    def get(self, prop):
        if prop == self._cv2.CAP_PROP_FPS:
            return 30.0
        if prop == self._cv2.CAP_PROP_FRAME_COUNT:
            return 90000.0
        return 0.0

    def set(self, prop, value):
        return True

    def read(self):
        self.read_calls += 1
        return True, np.zeros((64, 64, 3), dtype=np.uint8)

    def release(self):
        self.release_calls += 1
        if self.raise_on_release:
            raise RuntimeError("synthetic release failure")


class _FakeCV2:
    CAP_PROP_FPS = 5
    CAP_PROP_FRAME_COUNT = 7
    CAP_PROP_POS_FRAMES = 1
    COLOR_BGR2GRAY = 6

    def __init__(self, raise_on_release=False):
        self.raise_on_release = raise_on_release
        self.capture = None

    def VideoCapture(self, path):
        self.capture = _ReleaseErrorCapture(self, self.raise_on_release)
        return self.capture

    def cvtColor(self, frame, code):
        return frame[:, :, 0]


def _install_fake_tracker(tmp_path, monkeypatch, *, raise_on_release):
    source = tmp_path / "no_face.mp4"
    source.touch()
    fake_cv2 = _FakeCV2(raise_on_release=raise_on_release)
    cascade = _NoFaceCascade()
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setattr(face_reframe, "_load_cascade", lambda: cascade)
    return source, fake_cv2, cascade


def test_no_face_sampling_is_capped_at_120(tmp_path, monkeypatch):
    source, fake_cv2, cascade = _install_fake_tracker(
        tmp_path, monkeypatch, raise_on_release=False,
    )

    track = face_reframe.detect_face_track(
        str(source), samples_per_sec=100.0, duration=300.0, max_samples=10_000,
    )

    assert track == []
    assert fake_cv2.capture.read_calls <= 120
    assert cascade.calls == fake_cv2.capture.read_calls
    assert fake_cv2.capture.release_calls == 1


def test_cap_release_error_is_safe(tmp_path, monkeypatch):
    source, fake_cv2, cascade = _install_fake_tracker(
        tmp_path, monkeypatch, raise_on_release=True,
    )

    track = face_reframe.detect_face_track(
        str(source), samples_per_sec=100.0, duration=300.0, max_samples=10_000,
    )

    assert track == []
    assert fake_cv2.capture.read_calls <= 120
    assert cascade.calls == fake_cv2.capture.read_calls
    assert fake_cv2.capture.release_calls == 1
