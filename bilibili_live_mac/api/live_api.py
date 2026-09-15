"""B 站直播房间相关接口。"""

import hashlib
import time
from typing import Any, Dict, List, Optional

import requests


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://link.bilibili.com/p/center/index",
}


class LiveApiResult:
    def __init__(
        self,
        ok: bool,
        message: str = "",
        data: Any = None,
        code: Optional[int] = None,
    ) -> None:
        self.ok = ok
        self.message = message
        self.data = data
        self.code = code


class BiliLiveApi:
    """依赖已登录 Session 的直播房间 API。"""

    def __init__(self, session: requests.Session) -> None:
        self.session = session

    def fetch_room_id(self) -> LiveApiResult:
        url = "https://api.live.bilibili.com/xlive/app-blink/v1/highlight/getRoomHighlightState"
        result = self._get_json(url)
        if not result.ok:
            return result
        room_id = int((result.data or {}).get("room_id") or 0)
        return LiveApiResult(True, data=room_id)

    def fetch_room_info(self, room_id: int) -> LiveApiResult:
        url = "https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo"
        result = self._get_json(
            url,
            params={"req_biz": "web_room_componet", "room_ids": str(room_id)},
        )
        if not result.ok:
            return result

        by_room = (result.data or {}).get("by_room_ids") or {}
        info = by_room.get(str(room_id)) or by_room.get(room_id)
        if not info:
            return LiveApiResult(False, "没有找到直播间信息")

        return LiveApiResult(
            True,
            data={
                "room_id": info.get("room_id"),
                "uid": info.get("uid"),
                "uname": info.get("uname"),
                "title": info.get("title") or "",
                "area_id": info.get("area_id"),
                "parent_area_id": info.get("parent_area_id"),
                "area_name": info.get("area_name") or "",
                "parent_area_name": info.get("parent_area_name") or "",
                "live_status": info.get("live_status"),
                "live_time": info.get("live_time") or "",
                "online": info.get("online"),
                "cover": info.get("cover") or "",
            },
        )

    def fetch_area_tree(self) -> LiveApiResult:
        url = "https://api.live.bilibili.com/room/v1/Area/getList"
        result = self._get_json(url)
        if not result.ok:
            return result

        parents = []
        for parent in result.data or []:
            children = [
                {
                    "id": child.get("id"),
                    "name": child.get("name") or "",
                    "parent_id": child.get("parent_id"),
                    "parent_name": child.get("parent_name") or parent.get("name") or "",
                }
                for child in parent.get("list") or []
            ]
            parents.append(
                {
                    "id": parent.get("id"),
                    "name": parent.get("name") or "",
                    "children": children,
                }
            )
        return LiveApiResult(True, data=parents)

    def update_title(self, room_id: int, title: str) -> LiveApiResult:
        url = "https://api.live.bilibili.com/room/v1/Room/update"
        csrf = self._csrf()
        if not csrf:
            return LiveApiResult(False, "登录 Cookie 缺少 bili_jct，无法保存标题")
        return self._post_form(
            url,
            data={
                "room_id": str(room_id),
                "title": title,
                "csrf_token": csrf,
                "csrf": csrf,
            },
        )

    def update_area(self, room_id: int, area_id: str) -> LiveApiResult:
        url = "https://api.live.bilibili.com/xlive/app-blink/v2/room/AnchorChangeRoomArea"
        csrf = self._csrf()
        if not csrf:
            return LiveApiResult(False, "登录 Cookie 缺少 bili_jct，无法保存分区")
        return self._post_form(
            url,
            params={
                "platform": "pc",
                "room_id": str(room_id),
                "area_id": str(area_id),
                "csrf_token": csrf,
                "csrf": csrf,
            },
        )

    def start_stream(self, room_id: int, area_id: str) -> LiveApiResult:
        url = "https://api.live.bilibili.com/room/v1/Room/startLive"
        csrf = self._csrf()
        if not csrf:
            return LiveApiResult(False, "登录 Cookie 缺少 bili_jct，无法开播")

        params = {
            "access_key": "",
            "appkey": "aae92bc66f3edfab",
            "platform": "pc_link",
            "room_id": str(room_id),
            "area_v2": str(area_id),
            "build": "9343",
            "backup_stream": "0",
            "csrf": csrf,
            "csrf_token": csrf,
            "ts": str(int(time.time())),
        }
        params["sign"] = self._start_live_sign(params)
        result = self._post_form(url, params=params)
        if not result.ok:
            return result

        rtmp = (result.data or {}).get("rtmp") or {}
        result.data = {
            "addr": rtmp.get("addr") or "",
            "code": rtmp.get("code") or "",
        }
        return result

    def stop_stream(self, room_id: int) -> LiveApiResult:
        url = "https://api.live.bilibili.com/room/v1/Room/stopLive"
        csrf = self._csrf()
        if not csrf:
            return LiveApiResult(False, "登录 Cookie 缺少 bili_jct，无法下播")
        return self._post_form(
            url,
            params={
                "platform": "pc_link",
                "room_id": str(room_id),
                "csrf": csrf,
                "csrf_token": csrf,
            },
        )

    def fetch_stream_info(self, room_id: int) -> LiveApiResult:
        url = "https://api.live.bilibili.com/live_stream/v1/StreamList/get_stream_by_roomId"
        result = self._get_json(url, params={"room_id": str(room_id)})
        if not result.ok:
            return result

        rtmp = (result.data or {}).get("rtmp") or {}
        return LiveApiResult(
            True,
            data={
                "addr": rtmp.get("addr") or "",
                "code": rtmp.get("code") or "",
                "lines": (result.data or {}).get("stream_line") or [],
            },
        )

    def _get_json(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> LiveApiResult:
        try:
            response = self.session.get(
                url,
                params=params,
                headers=_HEADERS,
                timeout=10,
            )
            payload = response.json()
        except requests.RequestException as exc:
            return LiveApiResult(False, f"网络请求失败：{exc}")
        except ValueError:
            return LiveApiResult(False, "接口返回了无效 JSON")
        return self._parse_payload(payload)

    def _post_form(
        self,
        url: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> LiveApiResult:
        try:
            response = self.session.post(
                url,
                data=data,
                params=params,
                headers=_HEADERS,
                timeout=10,
            )
            payload = response.json()
        except requests.RequestException as exc:
            return LiveApiResult(False, f"网络请求失败：{exc}")
        except ValueError:
            return LiveApiResult(False, "接口返回了无效 JSON")
        return self._parse_payload(payload)

    @staticmethod
    def _parse_payload(payload: Any) -> LiveApiResult:
        if not isinstance(payload, dict):
            return LiveApiResult(False, "接口返回结构异常")
        code = int(payload.get("code") or 0)
        if code != 0:
            return LiveApiResult(
                False,
                str(payload.get("message") or payload.get("msg") or f"接口返回错误（{code}）"),
                data=payload.get("data"),
                code=code,
            )
        return LiveApiResult(True, data=payload.get("data"), code=code)

    def _csrf(self) -> str:
        return self.session.cookies.get("bili_jct") or ""

    @staticmethod
    def _start_live_sign(params: Dict[str, str]) -> str:
        query = "&".join(f"{key}={params[key]}" for key in sorted(params))
        raw = query + "af125a0d5279fd576c1b4418a3e8276d"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()
