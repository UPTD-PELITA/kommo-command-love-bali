from importlib import util
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import requests

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "kommo_command" / "services" / "love_bali_service.py"
spec = util.spec_from_file_location("love_bali_service", MODULE_PATH)
assert spec and spec.loader
love_bali_service = util.module_from_spec(spec)
spec.loader.exec_module(love_bali_service)

LoveBaliAPIService = love_bali_service.LoveBaliAPIService
LoveBaliAPIError = love_bali_service.LoveBaliAPIError


class DummyResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers: dict[str, str] = {}
        self.url = "https://lovebali.baliprov.go.id/api/v2/bpd/single_scan_passport"

    def json(self) -> Dict[str, Any]:
        if self._json_data is None:
            raise ValueError("No JSON data available")
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)


class FakeSession:
    def __init__(self, response: DummyResponse) -> None:
        self._response = response
        self.headers: dict[str, str] = {}
        self.last_request: Optional[Dict[str, Any]] = None
        self.closed = False

    def request(self, method: str, url: str, **kwargs) -> DummyResponse:
        self.last_request = {
            "method": method,
            "url": url,
            "json": kwargs.get("json"),
            "timeout": kwargs.get("timeout"),
        }
        return self._response

    def close(self) -> None:
        self.closed = True


def test_single_scan_passport_success(monkeypatch):
    response_payload = {"status": "ok", "data": {"passport": "M63782727"}}
    fake_response = DummyResponse(json_data=response_payload)
    fake_session = FakeSession(fake_response)

    monkeypatch.setattr(requests, "Session", lambda: fake_session)

    service = LoveBaliAPIService(
        base_url="https://lovebali.baliprov.go.id/api/v2/",
        api_token="test-token",
        timeout=10,
    )

    result = service.single_scan_passport("M63782727")

    assert result == response_payload
    assert fake_session.last_request is not None
    assert fake_session.last_request["method"] == "POST"
    assert fake_session.last_request["json"] == {"passport_number": "M63782727"}
    assert fake_session.headers["Authorization"] == "Bearer test-token"

    service.close()
    assert fake_session.closed is True


def test_single_scan_passport_http_error(monkeypatch):
    error_payload = {"detail": "Unauthorized"}
    fake_response = DummyResponse(status_code=401, json_data=error_payload, text="Unauthorized")
    fake_session = FakeSession(fake_response)

    monkeypatch.setattr(requests, "Session", lambda: fake_session)

    service = LoveBaliAPIService(
        base_url="https://lovebali.baliprov.go.id/api/v2/",
        api_token="invalid",
    )

    with pytest.raises(LoveBaliAPIError) as exc_info:
        service.single_scan_passport("M00000000")

    exc = exc_info.value
    assert exc.status_code == 401
    assert exc.response_data == error_payload
