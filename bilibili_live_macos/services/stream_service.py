"""开播、下播与推流地址编排。"""

from typing import Any, Dict, Optional

from .. import obs_bridge as bridge
from ..api.live_api import BiliLiveApi


SERVICE_NAME = "Bilibili Live - RTMP | 哔哩哔哩直播 - RTMP"


class StreamService:
    def __init__(self, live_api: BiliLiveApi) -> None:
        self.api = live_api
        self.room_id: Optional[int] = None

    def set_room_id(self, room_id: int) -> None:
        self.room_id = room_id

    def start(self, area_id: str) -> Dict[str, Any]:
        if not self.room_id:
            return {"ok": False, "message": "直播间状态尚未就绪"}
        if not area_id:
            return {"ok": False, "message": "请先选择直播分区"}
        result = self.api.start_stream(self.room_id, area_id)
        if not result.ok:
            return {
                "ok": False,
                "message": result.message,
                "code": result.code,
            }
        data = result.data or {}
        return {
            "ok": True,
            "message": "B 站开播成功",
            "addr": data.get("addr") or "",
            "code": data.get("code") or "",
        }

    def stop(self) -> Dict[str, Any]:
        if not self.room_id:
            return {"ok": False, "message": "直播间状态尚未就绪"}
        result = self.api.stop_stream(self.room_id)
        if not result.ok:
            return {"ok": False, "message": result.message}
        return {"ok": True, "message": "下播请求已提交"}

    def fetch_info(self) -> Dict[str, Any]:
        if not self.room_id:
            return {"ok": False, "message": "直播间状态尚未就绪"}
        result = self.api.fetch_stream_info(self.room_id)
        if not result.ok:
            return {"ok": False, "message": result.message}

        data = result.data or {}
        addr = data.get("addr") or ""
        code = data.get("code") or ""
        return {
            "ok": True,
            "message": "推流信息已获取",
            "addr": addr,
            "code": code,
        }

    def apply_to_obs(self, addr: str, code: str) -> Dict[str, Any]:
        if not addr or not code:
            return {"ok": False, "message": "请先获取推流地址"}

        settings = None
        try:
            service = bridge.get_streaming_service()
            settings = bridge.get_service_settings(service)
            bridge.set_string(settings, "service", SERVICE_NAME)
            bridge.set_string(settings, "server", addr)
            bridge.set_string(settings, "key", code)
            bridge.update_service(service, settings)
            bridge.save_streaming_service()
        except Exception as exc:
            return {"ok": False, "message": f"写入 OBS 推流设置失败：{exc}"}
        finally:
            if settings is not None:
                bridge.release_data(settings)

        return {"ok": True, "message": "已写入 OBS 推流设置"}

    def start_obs(self) -> None:
        bridge.start_streaming()

    def stop_obs(self) -> None:
        bridge.stop_streaming()

    def obs_active(self) -> bool:
        return bridge.streaming_active()
