import pytest

pytest.importorskip("fastapi")


def test_import_runtime_api_mission_control():
    from runtime.api.mission_control import app  # noqa: F401
