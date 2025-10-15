from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from requests.exceptions import HTTPError, RequestException, Timeout

logger = logging.getLogger(__name__)


class LoveBaliAPIError(Exception):
    """Base exception for errors returned by the Love Bali API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class LoveBaliAPIService:
    """Service for interacting with the Love Bali API."""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        *,
        timeout: int = 30,
    ) -> None:
        normalized_base = base_url.strip()
        if not normalized_base:
            normalized_base = "https://lovebali.baliprov.go.id/api/v2/"
        if not normalized_base.endswith("/"):
            normalized_base = f"{normalized_base}/"

        self.base_url = normalized_base
        self.api_token = api_token.strip()
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        logger.info(
            "Initialized Love Bali API service",
            extra={"base_url": self.base_url},
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        request_kwargs: Dict[str, Any] = {"timeout": self.timeout}
        if payload is not None:
            request_kwargs["json"] = payload

        try:
            logger.debug(
                "Calling Love Bali API",
                extra={"method": method, "url": url, "has_payload": payload is not None},
            )
            response = self.session.request(method, url, **request_kwargs)
            response.raise_for_status()
        except Timeout as exc:
            message = (
                f"Love Bali API request to {url} timed out after {self.timeout} seconds"
            )
            logger.error(
                message,
                extra={"url": url, "method": method},
            )
            raise LoveBaliAPIError(message) from exc
        except HTTPError as exc:
            response_obj = exc.response
            status_code = response_obj.status_code if response_obj is not None else None
            error_body: Optional[Dict[str, Any]] = None
            if response_obj is not None:
                try:
                    error_body = response_obj.json()
                except ValueError:
                    error_body = {"raw_response": response_obj.text}

            message = (
                f"Love Bali API request failed with status {status_code or 'unknown'}"
            )
            logger.error(
                message,
                extra={"url": url, "method": method, "status_code": status_code},
            )
            raise LoveBaliAPIError(
                message,
                status_code=status_code,
                response_data=error_body,
            ) from exc
        except RequestException as exc:
            message = f"Love Bali API request failed: {exc}"
            logger.error(
                message,
                extra={"url": url, "method": method},
            )
            raise LoveBaliAPIError(message) from exc

        try:
            return response.json()
        except ValueError:
            logger.warning(
                "Love Bali API returned non-JSON response",
                extra={"url": url, "method": method},
            )
            return {"raw_response": response.text}

    def single_scan_passport(self, passport_number: str) -> Dict[str, Any]:
        """Submit a passport number to the Love Bali single scan endpoint."""
        payload = {"passport_number": passport_number}
        return self._request("POST", "bpd/single_scan_passport", payload=payload)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()
        logger.debug("Closed Love Bali API session")

    def __enter__(self) -> LoveBaliAPIService:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
