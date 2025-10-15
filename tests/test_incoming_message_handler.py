import logging
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from kommo_command.models.session import SessionUpdateRequest


def _ensure_firebase_stubs() -> None:
    if "firebase_admin" in sys.modules:
        return

    firebase_admin_stub = ModuleType("firebase_admin")
    credentials_stub = ModuleType("credentials")
    db_stub = ModuleType("db")
    google_stub = ModuleType("google")
    cloud_stub = ModuleType("cloud")
    firestore_stub = ModuleType("firestore")
    oauth2_stub = ModuleType("oauth2")
    service_account_stub = ModuleType("service_account")

    # Minimal credential certificate factory
    credentials_stub.Certificate = lambda path: object()

    # Minimal Realtime Database reference stub
    class _DummyRef:
        def get(self):
            return {}

        def set(self, _data):
            return None

        def delete(self):
            return None

        def child(self, _name):
            return self

        def push(self, _data):
            class _DummyPush:
                key = "dummy"

            return _DummyPush()

        def listen(self, _callback):
            class _DummyListener:
                def close(self):
                    pass

            return _DummyListener()

    db_stub.reference = lambda *_args, **_kwargs: _DummyRef()

    firebase_admin_stub.credentials = credentials_stub
    firebase_admin_stub.db = db_stub
    firebase_admin_stub.get_app = lambda name=None: None
    firebase_admin_stub.delete_app = lambda app: None
    firebase_admin_stub.initialize_app = lambda cred, options, name=None: object()

    class _DummyFirestoreClient:
        def __init__(self, *args, **kwargs):
            pass

        def collection(self, *_args, **_kwargs):
            return self

        def document(self, *_args, **_kwargs):
            return self

        def set(self, *_args, **_kwargs):
            return None

        def stream(self, *_args, **_kwargs):
            return iter(())

        def where(self, *_args, **_kwargs):
            return self

    firestore_stub.Client = _DummyFirestoreClient

    class _DummyFieldFilter:
        def __init__(self, *_args, **_kwargs):
            pass

    firestore_stub.FieldFilter = _DummyFieldFilter
    cloud_stub.firestore = firestore_stub
    google_stub.cloud = cloud_stub

    service_account_stub.Credentials = type(
        "_DummyCredentials", (), {"from_service_account_file": staticmethod(lambda *_a, **_k: object())}
    )
    oauth2_stub.service_account = service_account_stub
    google_stub.oauth2 = oauth2_stub

    if "pydantic" not in sys.modules:
        pydantic_stub = ModuleType("pydantic")

        class _DummyBaseModel:
            def __init__(self, **data):
                for key, value in data.items():
                    setattr(self, key, value)

            def model_dump(self):
                return {
                    key: value
                    for key, value in self.__dict__.items()
                    if not key.startswith("__")
                }

        def Field(*_args, **kwargs):
            if "default_factory" in kwargs and callable(kwargs["default_factory"]):
                return kwargs["default_factory"]()
            return kwargs.get("default")

        pydantic_stub.BaseModel = _DummyBaseModel
        pydantic_stub.Field = Field
        sys.modules["pydantic"] = pydantic_stub

    sys.modules["firebase_admin"] = firebase_admin_stub
    sys.modules["firebase_admin.credentials"] = credentials_stub
    sys.modules["firebase_admin.db"] = db_stub
    sys.modules["google"] = google_stub
    sys.modules["google.cloud"] = cloud_stub
    sys.modules["google.cloud.firestore"] = firestore_stub
    sys.modules["google.oauth2"] = oauth2_stub
    sys.modules["google.oauth2.service_account"] = service_account_stub


_ensure_firebase_stubs()

from kommo_command.handlers.incoming_message_handler import IncomingMessageHandler


@pytest.fixture
def handler():
    firestore = MagicMock()
    realtime = MagicMock()
    kommo = MagicMock()
    instance = IncomingMessageHandler(
        firestore_service=firestore,
        realtime_listener=realtime,
        kommo_service=kommo,
    )
    return instance


def test_can_handle_dict_message(handler):
    event_data = {"message": "Hello"}
    assert handler.can_handle("/messages/123", event_data)


def test_can_handle_string(handler):
    assert handler.can_handle("/messages/123", "Hi there")


def test_can_handle_rejects_empty(handler):
    assert not handler.can_handle("/messages/123", " ")
    assert not handler.can_handle("/messages/123", {})


def test_handle_logs_and_prints_message(handler, caplog, capsys):
    caplog.set_level(logging.INFO)

    session = SimpleNamespace(session_id="sess-1", language="EN", metadata={})
    handler.firestore_service.get_session.return_value = session
    handler.firestore_service.update_session.return_value = session

    handler.handle("/messages/sess-1", {"message": "Hello there", "session_id": "sess-1"})

    assert "Incoming message received" in caplog.text

    records = [record for record in caplog.records if record.getMessage() == "Incoming message received"]
    assert records, "Expected a log record for the incoming message"
    assert getattr(records[0], "payload_message", None) == "Hello there"

    captured = capsys.readouterr()
    assert "Step 1" in captured.out
    assert "Hello there" in captured.out
    assert "Step 2" in captured.out
    assert "Step 3" in captured.out

    # Ensure the localized prompt was sent and state persisted
    assert handler.realtime_listener.write_data.call_count == 2
    call_args_list = handler.realtime_listener.write_data.call_args_list

    prompt_args = call_args_list[0].args
    prompt_kwargs = call_args_list[0].kwargs
    state_args = call_args_list[1].args
    state_kwargs = call_args_list[1].kwargs

    assert prompt_args[0]["message"] == "Enter passport number"
    assert prompt_args[0]["language"] == "EN"
    assert prompt_kwargs["path"].endswith("/responses/sess-1")

    assert state_args[0] == handler.WAITING_FOR_PASSPORT_STATE
    assert state_kwargs["path"].endswith("/sessions/sess-1/state")

    update_call = handler.firestore_service.update_session.call_args
    assert update_call is not None
    _, update_request = update_call[0]
    assert isinstance(update_request, SessionUpdateRequest)
    assert update_request.metadata == {"state": handler.WAITING_FOR_PASSPORT_STATE}


def test_handle_without_message(handler, caplog):
    caplog.set_level(logging.DEBUG)

    handler.handle("/messages/abc", {"other": "value"})

    assert "Incoming message received" not in caplog.text
    handler.realtime_listener.write_data.assert_not_called()
    handler.firestore_service.update_session.assert_not_called()


def test_handle_uses_session_language_when_payload_missing(handler):
    session = SimpleNamespace(session_id="sess-99", language="ID", metadata={})
    handler.firestore_service.get_session.return_value = session
    handler.firestore_service.update_session.return_value = session

    handler.handle("/messages/sess-99", {"message": "Halo"})

    prompt_args = handler.realtime_listener.write_data.call_args_list[0].args
    assert prompt_args[0]["message"] == "Masukkan nomor paspor"
    assert prompt_args[0]["language"] == "ID"


def test_handle_skips_when_session_unknown(handler, capsys):
    handler.firestore_service.get_session.return_value = None
    handler.firestore_service.update_session.return_value = None

    handler.handle("/messages/abc", {"message": "Hi"})

    captured = capsys.readouterr()
    assert "Step 2" in captured.out
    assert "Skipped session state update" in captured.out

    # Only the prompt write should occur because session state update fails early
    handler.realtime_listener.write_data.assert_called_once()
    prompt_args = handler.realtime_listener.write_data.call_args.args
    assert prompt_args[0]["message"] == "Enter passport number"

    handler.firestore_service.update_session.assert_called_once()
