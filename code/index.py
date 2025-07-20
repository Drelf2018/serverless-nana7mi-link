import json
import os
import sys
from importlib import import_module
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

__dir__ = Path(__file__).parent
exclude: List[str] = json.loads(os.environ.get("EXCLUDE", "[]"))


def get_router(path: str) -> Optional[APIRouter]:
    """
    从模块中获取 API 路由

    Args:
        path (str): 模块名

    Returns:
        API 路由
    """
    if not path.startswith("_"):
        router = getattr(import_module(path), "router", None)
        if router is not None and isinstance(router, APIRouter):
            return router


def auto_include_router(app: FastAPI, folder: str):
    """
    自动导入路由组

    Args:
        app (FastAPI): 应用
        folder (str): 要导入的文件夹
    """
    for dirpath, dirnames, filenames in os.walk(__dir__ / folder):
        relative = str(Path(dirpath).relative_to(__dir__)).replace("\\", "/")
        if relative in exclude:
            continue
        sys.path.append(dirpath)
        for file in filenames:
            if file.endswith(".py"):
                file = file.removesuffix(".py")
                router = get_router(file)
                if router is not None:
                    app.include_router(router, prefix=f"/{relative}/{file}")
        for dir in dirnames:
            if not dir.startswith("."):
                router = get_router(dir)
                if router is not None:
                    app.include_router(router, prefix=f"/{relative}/{dir}")


app = FastAPI()


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("favicon.ico")


if __name__ == "__main__":
    auto_include_router(app, "api")
    app.mount("/", StaticFiles(directory=__dir__ / "web", html=True))
    uvicorn.run(app, host="0.0.0.0", port=9000)
