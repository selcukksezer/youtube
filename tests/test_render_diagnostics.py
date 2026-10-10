from visuals.fetch import (
    _record_provider_search,
    get_job_provider_diagnostics,
    reset_job_manifest,
)


def test_provider_search_diagnostics_aggregate_latency_and_results():
    reset_job_manifest()
    _record_provider_search("pexels", 0, 0, 125.36, 3)
    _record_provider_search("pexels", 1, 1, 240.24, 0)
    _record_provider_search("pixabay", 0, 0, 70.05, 0, error="TimeoutError")

    report = get_job_provider_diagnostics()

    assert report["searches"] == 3
    assert report["providers"]["pexels"] == {
        "searches": 2,
        "total_ms": 365.6,
        "max_ms": 240.2,
        "results": 3,
        "empty_searches": 1,
        "errors": 0,
        "avg_ms": 182.8,
    }
    assert report["providers"]["pixabay"]["errors"] == 1
    assert report["slowest_searches"][0]["scene"] == 2
    assert "query" not in report["slowest_searches"][0]


def test_reset_clears_provider_search_diagnostics():
    _record_provider_search("pexels", 0, 0, 12, 1)
    reset_job_manifest()

    assert get_job_provider_diagnostics() == {
        "searches": 0,
        "providers": {},
        "slowest_searches": [],
    }
