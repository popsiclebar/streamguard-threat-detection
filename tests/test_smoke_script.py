"""Tests for StreamGuard's local streaming smoke-test helpers."""

from scripts.smoke_test import run_python_module


def test_run_python_module_uses_current_python_executable(monkeypatch) -> None:
    """Smoke-test module execution should call Python with `-m module`."""
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        calls.append(command)
        assert check is True

    monkeypatch.setattr("scripts.smoke_test.run", fake_run)

    run_python_module("apps.producer.main", ["--input", "events.jsonl"])

    assert calls
    assert calls[0][1:] == ["-m", "apps.producer.main", "--input", "events.jsonl"]
