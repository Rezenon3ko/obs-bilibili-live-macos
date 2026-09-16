"""直播间数据编排。"""

from typing import Any, Dict, List, Optional

from ..api.live_api import BiliLiveApi


class RoomService:
    """读取当前房间并保存标题、分区等设置。"""

    def __init__(self, live_api: BiliLiveApi) -> None:
        self.api = live_api
        self.room_id: Optional[int] = None
        self.room_info: Dict[str, Any] = {}
        self.area_tree: List[Dict[str, Any]] = []

    def refresh(self) -> Dict[str, Any]:
        result = self.api.fetch_room_id()
        if not result.ok:
            return {"ok": False, "message": result.message}

        room_id = int(result.data or 0)
        self.room_id = room_id
        if not room_id:
            return {"ok": True, "has_room": False, "message": "当前账号还没有开通直播间"}

        info_result = self.api.fetch_room_info(room_id)
        if not info_result.ok:
            return {"ok": False, "message": info_result.message}

        self.room_info = info_result.data or {}
        area_result = self.api.fetch_area_tree()
        if area_result.ok:
            self.area_tree = area_result.data or []
        else:
            self.area_tree = []

        title = self.room_info.get("title") or ""
        area_name = self.room_info.get("area_name") or ""
        parent_name = self.room_info.get("parent_area_name") or ""
        area_text = f"{parent_name} / {area_name}" if area_name else ""
        live_status = int(self.room_info.get("live_status") or 0)
        live_text = {0: "未开播", 1: "直播中", 2: "轮播中"}.get(live_status, "未知状态")
        return {
            "ok": True,
            "has_room": True,
            "message": (
                f"房间 {room_id}｜{self.room_info.get('uname') or ''}｜"
                f"{live_text}｜分区：{area_text or '未知'}"
            ),
            "title": title,
            "area_id": self.room_info.get("area_id"),
            "live_status": live_status,
        }

    def save_title(self, title: str) -> Dict[str, Any]:
        if not self.room_id:
            return {"ok": False, "message": "直播间状态尚未就绪"}
        title = title.strip()
        if not title:
            return {"ok": False, "message": "直播标题不能为空"}
        result = self.api.update_title(self.room_id, title)
        if not result.ok:
            return {"ok": False, "message": result.message}
        self.room_info["title"] = title
        return {"ok": True, "message": "标题已保存"}

    def save_area(self, area_id: str) -> Dict[str, Any]:
        if not self.room_id:
            return {"ok": False, "message": "直播间状态尚未就绪"}
        area_id = str(area_id)
        if not area_id:
            return {"ok": False, "message": "请选择直播分区"}
        result = self.api.update_area(self.room_id, area_id)
        if not result.ok:
            return {"ok": False, "message": result.message}
        self.room_info["area_id"] = area_id
        return {"ok": True, "message": "分区已保存"}

    def area_options(self) -> List[Dict[str, str]]:
        options: List[Dict[str, str]] = []
        for parent in self.area_tree:
            parent_name = parent.get("name") or ""
            for child in parent.get("children") or []:
                label = f"{parent_name} / {child.get('name') or ''}"
                options.append({"label": label, "value": str(child.get("id") or "")})
        return options
