import uuid
from io import BytesIO

import puremagic
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

FILE_STORAGE = {}

router = APIRouter()


@router.post("")
async def upload(file: UploadFile = File(...)) -> str:
    """
    接收文件上传，返回 UUID
    """
    file_uuid = uuid.uuid4().hex.upper()
    file_info = {
        "content": await file.read(),
        "filename": file.filename,
    }
    try:
        result = puremagic.magic_string(file_info["content"])  # 推测 MIME
        file_info["mime"] = result[0][3] if result else "application/octet-stream"
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"推测 MIME 出错: {e}")
    FILE_STORAGE[file_uuid] = file_info
    return file_uuid


@router.get("/{file_uuid}")
async def download(file_uuid: str):
    """
    根据 UUID 从内存读取文件，并返回对应具体MIME类型的文件流
    """
    if file_uuid not in FILE_STORAGE:
        raise HTTPException(status_code=404, detail="未找到该 UUID 对应的文件")
    file_info = FILE_STORAGE[file_uuid]
    file_stream = BytesIO(file_info["content"])
    file_stream.seek(0)
    return StreamingResponse(
        file_stream,
        headers={"Content-Disposition": 'inline; filename="%s"' % file_info["filename"]},
        media_type=file_info["mime"],
    )
