"""Generic SMM Panel API client.

Credentials are supplied at runtime and must never be committed to Git.
This adapter follows the common SMM Panel API v2 form protocol:
key=<API key>, action=services|add|status|refill|cancel.
Provider-specific differences should be handled by a dedicated adapter before
enabling automatic order placement.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ProviderAPIError(RuntimeError):
    pass


class SMMPanelClient:
    def __init__(self, api_url: str, api_key: str, timeout: int = 20):
        self.api_url = api_url.strip()
        self.api_key = api_key
        self.timeout = timeout
        if not self.api_url.startswith(("https://", "http://")):
            raise ValueError("عنوان API غير صحيح")

    def _post(self, payload: dict[str, Any]) -> Any:
        data = urlencode({"key": self.api_key, **payload}).encode("utf-8")
        request = Request(
            self.api_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "HAMO-STORE-SMM/1.0"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise ProviderAPIError(f"HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise ProviderAPIError(f"تعذر الاتصال بالمورد: {exc}") from exc
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderAPIError("المورد أعاد استجابة غير مفهومة") from exc
        if isinstance(result, dict) and result.get("error"):
            raise ProviderAPIError(str(result["error"]))
        return result

    def get_services(self) -> list[dict[str, Any]]:
        result = self._post({"action": "services"})
        if not isinstance(result, list):
            raise ProviderAPIError("استجابة قائمة الخدمات ليست بالشكل المتوقع")
        return result

    def add_order(self, service_id: str, link: str, quantity: int) -> dict[str, Any]:
        result = self._post({
            "action": "add",
            "service": str(service_id),
            "link": link,
            "quantity": int(quantity),
        })
        if not isinstance(result, dict) or not result.get("order"):
            raise ProviderAPIError("لم يرجع المورد رقم طلب صالحًا")
        return result

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        result = self._post({"action": "status", "order": str(order_id)})
        if not isinstance(result, dict):
            raise ProviderAPIError("استجابة حالة الطلب غير صحيحة")
        return result
