from typing import Any, List

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RoomInfoResponse(BaseModel):

    class Data(BaseModel):

        class NewPendants(BaseModel):

            class Frame(BaseModel):
                name: str
                value: str
                position: int
                desc: str
                area: int
                area_old: int
                bg_color: str
                bg_pic: str
                use_old_area: bool

            class Badge(BaseModel):
                name: str
                position: int
                value: str
                desc: str

            class MobileFrame(BaseModel):
                name: str
                value: str
                position: int
                desc: str
                area: int
                area_old: int
                bg_color: str
                bg_pic: str
                use_old_area: bool

            frame: Frame
            badge: Badge
            mobile_frame: MobileFrame
            mobile_badge: Any

        class StudioInfo(BaseModel):
            status: int
            master_list: List[Any]

        uid: int
        room_id: int
        short_id: int
        attention: int
        online: int
        is_portrait: bool
        description: str
        live_status: int
        area_id: int
        parent_area_id: int
        parent_area_name: str
        old_area_id: int
        background: str
        title: str
        user_cover: str
        keyframe: str
        is_strict_room: bool
        live_time: str
        tags: str
        is_anchor: int
        room_silent_type: str
        room_silent_level: int
        room_silent_second: int
        area_name: str
        pendants: str
        area_pendants: str
        hot_words: List[str]
        hot_words_status: int
        verify: str
        new_pendants: NewPendants
        up_session: str
        pk_status: int
        pk_id: int
        battle_id: int
        allow_change_area_time: int
        allow_upload_cover_time: int
        studio_info: StudioInfo

    code: int
    message: str
    msg: str
    data: Data


@router.get("/{roomid}")
async def get_room_info(roomid: int):
    """
    获取房间直播状态
    """
    async with httpx.AsyncClient() as session:
        try:
            resp = await session.get(
                url="https://api.live.bilibili.com/room/v1/Room/get_info",
                params={"room_id": roomid},
                headers={
                    "Referer": "https://www.bilibili.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.54",
                },
            )
            try:
                r = RoomInfoResponse.model_validate_json(resp.text)
                if r.code != 0:
                    return {"code": 3, "message": r.message}
                if r.data.live_status != 1:
                    return {"code": 4, "message": "未开播"}
                return {
                    "code": 0,
                    "message": f"【{r.data.area_name}】{r.data.title}\n{r.data.live_time}",
                    "uid": r.data.uid,
                    "roomid": r.data.room_id,
                    "area": r.data.area_name,
                    "title": r.data.title,
                    "time": r.data.live_time,
                    "cover": r.data.user_cover,
                }
            except Exception as e:
                msg = type(e).__name__
                if str(e) != "":
                    msg += f": {str(e)}"
                return {"code": 2, "message": msg, "response": resp.text}
        except Exception as e:
            msg = type(e).__name__
            if str(e) != "":
                msg += f": {str(e)}"
            return {"code": 1, "message": msg}
