import logging
import sys
from typing import Any
from types import ModuleType
from unittest.mock import MagicMock

import pytest  # type: ignore[import]


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

from kommo_command.handlers import BaseHandler, HandlerManager
from kommo_command.handlers.incoming_message_handler import IncomingMessageHandler
from kommo_command.types import BotID


@pytest.fixture
def handler():
    firestore_service = MagicMock()
    firestore_service.get_latest_session_by_entity_id.return_value = None

    kommo_service = MagicMock()
    kommo_service.get_entity_type_code.return_value = "2"
    kommo_service.update_lead_custom_fields.return_value = {"updated": True}
    kommo_service.launch_salesbot.return_value = {"status": "ok"}

    return IncomingMessageHandler(
        firestore_service=firestore_service,
        realtime_listener=MagicMock(),
        kommo_service=kommo_service,
    )


def test_can_handle_dict_message(handler):
    event_data = {"message": "Hello", "entity_id": 101}
    assert handler.can_handle("/messages/123", event_data)


def test_can_handle_string(handler):
    assert not handler.can_handle("/messages/123", "Hi there")


def test_can_handle_rejects_empty(handler):
    assert not handler.can_handle("/messages/123", " ")
    assert not handler.can_handle("/messages/123", {"entity_id": 55})


def test_handle_logs_and_prints_message(handler, caplog, capsys):
    caplog.set_level(logging.INFO)

    handler.handle("/messages/abc", {"message": "Hello there", "entity_id": 777})

    assert "Incoming message received" in caplog.text

    records = [record for record in caplog.records if record.getMessage() == "Incoming message received"]
    assert records, "Expected a log record for the incoming message"
    assert getattr(records[0], "payload_message", None) == "Hello there"

    captured = capsys.readouterr()
    assert "Hello there" in captured.out


def test_handle_without_message(handler, caplog):
    caplog.set_level(logging.DEBUG)

    handler.handle("/messages/abc", {"other": "value", "entity_id": 88})

    assert "Incoming message received" not in caplog.text
    handler.kommo_service.update_lead_custom_fields.assert_not_called()


def test_handle_updates_lead_without_session(handler):
    handler.firestore_service.get_latest_session_by_entity_id.return_value = None

    handler.handle(
        "/messages/abc",
        {"message": "Thanks for the help", "entity_id": "12345", "entity_type": "lead"},
    )

    handler.firestore_service.get_latest_session_by_entity_id.assert_called_once_with(12345)
    handler.kommo_service.update_lead_custom_fields.assert_called_once()

    _, custom_fields = handler.kommo_service.update_lead_custom_fields.call_args[0]
    assert custom_fields[0]["values"][0]["value"] == "Thanks for the help"

    handler.kommo_service.launch_salesbot.assert_called_once_with(
        bot_id=BotID.REPLY_CUSTOM_BOT_ID.value,
        entity_id=12345,
        entity_type="2",
    )


def test_handle_session_found_uses_passport_prompt(handler):
    session = MagicMock()
    session.session_id = "sess-1"
    handler.firestore_service.get_latest_session_by_entity_id.return_value = session

    handler.handle(
        "/messages/abc",
        {"message": "Need passport assistance", "entity_id": 456},
    )

    handler.kommo_service.update_lead_custom_fields.assert_called_once()
    _, custom_fields = handler.kommo_service.update_lead_custom_fields.call_args[0]
    assert custom_fields[0]["values"][0]["value"] == "Please enter your passport number"

    handler.kommo_service.launch_salesbot.assert_called_once_with(
        bot_id=BotID.REPLY_CUSTOM_BOT_ID.value,
        entity_id=456,
        entity_type="2",
    )


def test_handler_manager_uses_incoming_message_handler_as_default(handler):
    manager = HandlerManager()

    original_handle = handler.handle
    handler.handle = MagicMock(side_effect=original_handle)

    manager.register_handler(handler, default=True)

    manager.process_event("/unmatched/event", {"entity_id": 24601})

    handler.handle.assert_called_once_with("/unmatched/event", {"entity_id": 24601})


class _DummyHandler(BaseHandler):
    def __init__(self) -> None:
        super().__init__(
            firestore_service=MagicMock(),
            realtime_listener=MagicMock(),
            kommo_service=MagicMock(),
        )

    def can_handle(self, event_path: str, event_data: Any) -> bool:  # type: ignore[override]
        return True

    def handle(self, event_path: str, event_data: Any) -> None:  # type: ignore[override]
        pass


def test_handler_manager_always_calls_default(handler):
    manager = HandlerManager()

    original_default_handle = handler.handle
    handler.handle = MagicMock(side_effect=original_default_handle)
    manager.register_handler(handler, default=True)

    specific_handler = _DummyHandler()
    specific_handler.handle = MagicMock()
    specific_handler.can_handle = MagicMock(return_value=True)
    manager.register_handler(specific_handler)

    event_payload = {"message": "Welcome aboard", "entity_id": 314}

    manager.process_event("/leads/314", event_payload)

    handler.handle.assert_called_once_with("/leads/314", event_payload)
    specific_handler.handle.assert_called_once_with("/leads/314", event_payload)
