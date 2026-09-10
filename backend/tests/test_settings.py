from pytest import MonkeyPatch

from app.core.config import Settings


def test_settings_load_from_prefixed_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("RELAY_ENVIRONMENT", "test")
    monkeypatch.setenv("RELAY_CORS_ORIGINS", '["https://relay.example"]')

    settings = Settings()

    assert settings.environment == "test"
    assert settings.cors_origins == ["https://relay.example"]
