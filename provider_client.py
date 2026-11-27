"""PanelFollows v2 reseller API client. Keep API keys server-side only."""
from __future__ import annotations
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PANELFOLLOWS_API_URL = "https://panelfollows.com/api/v2"

class ProviderAPIError(RuntimeError):
    pass

class PanelFollowsClient:
    def __init__(self, api_key: str, timeout: int = 20):
        if not api_key or not api_key.strip():
            raise ValueError("مفتاح PanelFollows غير مضبوط")
        self.api_key = api_key.strip()
        self.timeout = timeout

    def _post(self, action: str, **params: Any) -> Any:
        payload = {"key": self.api_key, "action": action, **params}
        request = Request(
            PANELFOLLOWS_API_URL,
            data=urlencode(payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Accept": "application/json", "User-Agent": "HAMO-STORE-SMM/1.0"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise ProviderAPIError(f"PanelFollows HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise ProviderAPIError("تعذر الاتصال بـ PanelFollows") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderAPIError("استجابة PanelFollows غير مفهومة") from exc
        if isinstance(data, dict) and data.get("error"):
            raise ProviderAPIError(str(data["error"]))
        return data

    def balance(self) -> dict[str, Any]:
        data = self._post("balance")
        if not isinstance(data, dict) or "balance" not in data:
            raise ProviderAPIError("استجابة الرصيد غير صحيحة")
        return data

    def services(self) -> list[dict[str, Any]]:
        data = self._post("services")
        if not isinstance(data, list):
            raise ProviderAPIError("استجابة قائمة الخدمات غير صحيحة")
        return data

    def add_order(self, service_id: str, link: str, quantity: int) -> dict[str, Any]:
        data = self._post("add", service=str(service_id), link=link, quantity=int(quantity))
        if not isinstance(data, dict) or not data.get("order"):
            raise ProviderAPIError("المورد لم يرجع رقم طلب صالحًا")
        return data

    def status(self, order_id: str) -> dict[str, Any]:
        data = self._post("status", order=str(order_id))
        if not isinstance(data, dict):
            raise ProviderAPIError("استجابة حالة الطلب غير صحيحة")
        return data

    def cancel(self, order_ids: list[str]) -> Any:
        return self._post("cancel", orders=",".join(map(str, order_ids)))

    def refill(self, order_id: str) -> Any:
        return self._post("refill", order=str(order_id))

    def refill_status(self, refill_id: str) -> Any:
        return self._post("refill_status", refill=str(refill_id))
