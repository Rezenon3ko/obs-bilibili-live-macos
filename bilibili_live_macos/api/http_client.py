"""统一 HTTP 请求封装。"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class ApiResult:
    ok: bool
    code: Optional[int] = None
    message: str = ""
    data: Any = None
    status_code: Optional[int] = None

    @classmethod
    def failure(cls, message: str, status_code: Optional[int] = None) -> "ApiResult":
        return cls(ok=False, message=message, status_code=status_code)


class BiliHttpClient:
    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    def get_json(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ApiResult:
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            return ApiResult.failure(str(exc))

        try:
            payload = response.json()
        except ValueError:
            return ApiResult.failure(
                "响应不是有效 JSON",
                status_code=response.status_code,
            )

        if not isinstance(payload, dict):
            return ApiResult.failure(
                "响应结构不是对象",
                status_code=response.status_code,
            )

        api_code = payload.get("code")
        if api_code is not None and int(api_code) != 0:
            return ApiResult(
                ok=False,
                code=int(api_code),
                message=str(payload.get("message") or payload.get("msg") or "请求失败"),
                data=payload.get("data"),
                status_code=response.status_code,
            )

        return ApiResult(
            ok=True,
            code=int(api_code) if api_code is not None else None,
            message=str(payload.get("message") or payload.get("msg") or ""),
            data=payload.get("data"),
            status_code=response.status_code,
        )

    def get_bytes(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
    ) -> ApiResult:
        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return ApiResult.failure(str(exc))
        return ApiResult(ok=True, data=response.content, status_code=response.status_code)
