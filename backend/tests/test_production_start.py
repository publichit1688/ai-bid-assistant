import sys


def test_production_start_disables_raw_uvicorn_access_log(monkeypatch):
    from scripts import start_production

    captured = {}
    monkeypatch.setattr(sys, "argv", ["start_production.py"])
    monkeypatch.setattr(
        start_production,
        "prepare_and_validate_runtime",
        lambda: {"checks": {"database": "ok"}},
    )
    monkeypatch.setattr(
        start_production.uvicorn,
        "run",
        lambda *args, **kwargs: captured.update({"args": args, "kwargs": kwargs}),
    )

    assert start_production.main() == 0
    assert captured["kwargs"]["access_log"] is False
    assert captured["kwargs"]["reload"] is False
