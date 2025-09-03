from kommo_command.config import Settings


def test_settings_from_env_path_normalization(monkeypatch):
    monkeypatch.setenv("FIREBASE_DATABASE_URL", "https://example.firebaseio.com/")
    monkeypatch.setenv("FIREBASE_PATH", "messages")
    s = Settings.from_env()
    assert s.firebase_database_url == "https://example.firebaseio.com"
    assert s.firebase_path == "/messages"


def test_auth_mode(monkeypatch):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("FIREBASE_DATABASE_URL", "https://example.firebaseio.com")

    s = Settings.from_env()
    assert s.auth_mode() == "unauthenticated"

    monkeypatch.setenv("GOOGLE_ACCESS_TOKEN", "token")
    s = Settings.from_env()
    assert s.auth_mode() == "access_token"

    monkeypatch.delenv("GOOGLE_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", "/tmp/sa.json")
    s = Settings.from_env()
    assert s.auth_mode() == "service_account"
