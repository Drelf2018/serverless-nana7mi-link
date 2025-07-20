import base64
import ctypes
import json
import struct
from pathlib import Path

import httpx
import sseclient
from fastapi import APIRouter, Header
from pydantic import BaseModel
from wasmtime import Linker, Module, Store

store = Store()
module = Module.from_file(store.engine, Path(__file__).parent / "sha3_wasm_bg.7b9ca65ddd.wasm")
exports = Linker(store.engine).instantiate(store, module).exports(store)
memory = exports["memory"]
wasm_solve = exports["wasm_solve"]
alloc = exports["__wbindgen_export_0"]
add_to_stack = exports["__wbindgen_add_to_stack_pointer"]


def read_memory(offset: int, size: int) -> bytes:
    base_addr = ctypes.cast(memory.data_ptr(store), ctypes.c_void_p).value
    return ctypes.string_at(base_addr + offset, size)


def encode_string(text: str):
    data = text.encode("utf-8")
    length = len(data)
    ptr = alloc(store, length, 1)
    base_addr = ctypes.cast(memory.data_ptr(store), ctypes.c_void_p).value
    ctypes.memmove(base_addr + ptr, data, length)
    return ptr, length


router = APIRouter()


@router.get("/compute_pow_answer")
async def compute_pow_answer(challenge: str, salt: str, difficulty: int, expire_at: int) -> dict:
    """
    使用 WASM 模块计算 DeepSeekHash 答案

    Args:
        challenge (str): 挑战字符串
        salt (str): 加盐
        difficulty (int): 挑战难度
        expire_at (int): 过期时间

    Returns:
        结果
    """
    # 申请 16 字节栈空间
    retptr = add_to_stack(store, -16)
    # 编码 challenge 与 prefix 到 wasm 内存中
    ptr_challenge, len_challenge = encode_string(challenge)
    ptr_prefix, len_prefix = encode_string(f"{salt}_{expire_at}_")
    # 调用 wasm_solve
    wasm_solve(store, retptr, ptr_challenge, len_challenge, ptr_prefix, len_prefix, float(difficulty))
    # 从 retptr 处读取 4 字节状态和 8 字节求解结果
    status_bytes = read_memory(retptr, 4)
    if len(status_bytes) != 4:
        add_to_stack(store, 16)
        return {"code": 1, "msg": "读取状态字节失败"}
    status = struct.unpack("<i", status_bytes)[0]
    value_bytes = read_memory(retptr + 8, 8)
    if len(value_bytes) != 8:
        add_to_stack(store, 16)
        return {"code": 2, "msg": "读取结果字节失败"}
    value = struct.unpack("<d", value_bytes)[0]
    # 恢复栈指针
    add_to_stack(store, 16)
    if status == 0:
        return {"code": 3, "msg": "状态为空"}
    return {"code": 0, "msg": "成功", "data": int(value)}


@router.get("/create_pow_challenge")
async def create_pow_challenge(authorization: str = Header(..., alias="Authorization")) -> dict:
    """
    通过 Authorization 请求头获取挑战结果

    Args:
        authorization (str, optional): 鉴权请求头

    Returns:
        挑战结果
    """
    async with httpx.AsyncClient() as session:
        r = await session.post(
            "https://chat.deepseek.com/api/v0/chat/create_pow_challenge",
            json={"target_path": "/api/v0/chat/completion"},
            headers={"Authorization": authorization},
        )
        data = r.json()
        if data["code"] != 0:
            return data
        challenge = data["data"]["biz_data"]["challenge"]
        result = await compute_pow_answer(challenge["challenge"], challenge["salt"], challenge["difficulty"], challenge["expire_at"])
        if result["code"] == 0:
            result["data"] = {
                "algorithm": challenge["algorithm"],
                "challenge": challenge["challenge"],
                "salt": challenge["salt"],
                "answer": result["data"],
                "signature": challenge["signature"],
                "target_path": challenge["target_path"],
            }
            result["msg"] = base64.b64encode(json.dumps(result["data"]).encode("utf-8")).decode("utf-8")
        return result


class CompletionOptions(BaseModel):
    prompt: str
    search_enabled: bool = True
    thinking_enabled: bool = True


@router.post("/completion")
async def completion(o: CompletionOptions, authorization: str = Header(..., alias="Authorization")) -> dict:
    """
    与网页版 DeepSeek 对话

    Args:
        o (CompletionOptions): 对话参数
        authorization (str, optional): 鉴权请求头

    Returns:
        对话结果
    """
    pow = await create_pow_challenge(authorization)
    if pow["code"] != 0:
        return pow

    async with httpx.AsyncClient() as session:
        r = await session.post(
            "https://chat.deepseek.com/api/v0/chat_session/create",
            headers={"Authorization": authorization},
        )
        data = r.json()
        if data["code"] != 0:
            return data

    def with_httpx():
        with httpx.stream(
            "POST",
            "https://chat.deepseek.com/api/v0/chat/completion",
            json={
                "chat_session_id": data["data"]["biz_data"]["id"],
                "parent_message_id": None,
                "prompt": o.prompt,
                "ref_file_ids": [],
                "search_enabled": o.search_enabled,
                "thinking_enabled": o.thinking_enabled,
            },
            headers={"Authorization": authorization, "X-Ds-Pow-Response": pow["msg"]},
        ) as s:
            yield from s.iter_bytes()

    content = []
    append_content = False
    thinking_content = []
    append_thinking_content = False

    client = sseclient.SSEClient(with_httpx())
    for event in client.events():
        data: dict = json.loads(event.data)
        p: str = data.get("p", "")
        if p == "response/content":
            append_content = True
        elif p == "response":
            append_content = False
        elif p == "response/thinking_content":
            append_thinking_content = True
        elif p == "response/thinking_elapsed_secs":
            append_thinking_content = False

        if append_content:
            content.append(data["v"])
        elif append_thinking_content:
            thinking_content.append(data["v"])

    return {"code": 0, "thinking_content": "".join(thinking_content), "content": "".join(content)}
