"""3.4: a failed five-frame probe does not lead the encoder chain."""
import system_resilience as sr


def _codecs(chain):
    names = []
    for args, _label in chain:
        if "-c:v" in args:
            names.append(args[args.index("-c:v") + 1])
    return names


def test_failed_nvenc_does_not_lead_when_qsv_passes(monkeypatch):
    monkeypatch.setattr(sr, "_ENCODER_PROBE_CACHE", {
        "h264_nvenc": False,
        "h264_qsv": True,
        "h264_amf": False,
        "h264_mf": False,
        "libx264": True,
    })
    monkeypatch.setattr(sr, "probe_hardware_encoders", lambda force=False: dict(sr._ENCODER_PROBE_CACHE))
    chain = sr.get_encoder_fallback_chain(use_gpu=True, gpu_codec="h264_nvenc")
    names = _codecs(chain)
    assert names[0] == "h264_qsv"
    assert "h264_nvenc" not in names
    assert names[-1] == "libx264"


def test_explicit_qsv_stays_first(monkeypatch):
    monkeypatch.setattr(sr, "_ENCODER_PROBE_CACHE", {
        "h264_nvenc": True,
        "h264_qsv": True,
        "h264_amf": False,
        "h264_mf": False,
        "libx264": True,
    })
    monkeypatch.setattr(sr, "probe_hardware_encoders", lambda force=False: dict(sr._ENCODER_PROBE_CACHE))
    names = _codecs(sr.get_encoder_fallback_chain(use_gpu=True, gpu_codec="h264_qsv"))
    assert names[0] == "h264_qsv"
    assert "h264_amf" not in names
    assert names[-1] == "libx264"


def test_cpu_request_is_only_libx264():
    names = _codecs(sr.get_encoder_fallback_chain(use_gpu=False, gpu_codec="libx264"))
    assert names == ["libx264"]
