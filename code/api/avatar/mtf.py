import html
from io import BytesIO

import httpx
import rembg
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from wand.color import Color
from wand.drawing import Drawing
from wand.image import Image

session = rembg.new_session()  # models: https://github.com/danielgatis/rembg/releases/tag/v0.0.0
isnet_anime = rembg.new_session("isnet-anime")


def count_transparent_pixels(image: Image, limit: int = 25):
    """
    计算空白像素比例

    Args:
        image (Image): 图片
        limit (int, optional): 空白像素认定界限

    Returns:
        空白像素比例
    """
    width, height = image.size
    total_pixels = width * height
    transparent_pixels = 0

    pixels = image.export_pixels()
    for i in range(0, len(pixels), 4):
        if pixels[i + 3] <= limit:
            transparent_pixels += 1

    return transparent_pixels / total_pixels


def get_removed_image(origin: bytes) -> Image:
    """
    获取移除背景的图片

    Args:
        origin (bytes): 图片字节

    Returns:
        图片
    """
    b = rembg.remove(origin, session=isnet_anime)
    rem = Image(blob=b, format="png")
    rem.alpha_channel = True
    if count_transparent_pixels(rem) <= 0.8:
        return rem
    # 空白比例过高则更换模型重试
    b = rembg.remove(origin, session=session)
    rem = Image(blob=b, format="png")
    rem.alpha_channel = True
    return rem


def generate_mtf_flag(w: int, h: int = 0) -> Image:
    """
    生成 mtf 旗帜

    Args:
        w (int): 宽度
        h (int, optional): 高度，不指定则默认同宽

    Returns:
        旗帜图片
    """
    if h == 0:
        h = w
    flag = Image(width=w, height=h, background=Color("#5BCEFA"))
    with Drawing() as draw:
        draw.fill_color = Color("#F5A9B8")
        draw.rectangle(0, int(h / 5), w, int(4 * h / 5))
        draw.fill_color = Color("#FFFFFF")
        draw.rectangle(0, int(2 * h / 5), w, int(3 * h / 5))
        draw(flag)
    return flag


def set_mtf_background(img: Image, radius: float = 0):
    """
    设置 mtf 背景

    Args:
        img (Image): 去除背景的图片
        radius (float, optional): 高斯模糊

    Returns:
        合并后图片
    """
    a = max(img.width, img.height)
    flag = generate_mtf_flag(a)
    if radius != 0:
        flag.gaussian_blur(radius=radius)
    x = (a - img.width) // 2
    y = (a - img.height) // 2
    flag.composite(img, x, y, operator="over")
    return flag


router = APIRouter()


@router.get("/qq/{qq}")
async def get_qq_mtf_avatar(qq: int, radius: float = Query(0.0), scale: float = Query(1.0), format: str = Query("JPEG")):
    """
    获取 QQ 头像的 mtf 风格化头像

    Args:
        qq (int): qq号
        radius (float, optional): 高斯模糊
        scale (float, optional): 缩放倍数
        format (str, optional): 导出格式

    Returns:
        图片的数据流
    """
    return await get_mtf_avatar(f"https://q1.qlogo.cn/g?b=qq&nk={qq}&s=5", radius, scale, format)


@router.get("/")
async def get_mtf_avatar(url: str = Query(...), radius: float = Query(0.0), scale: float = Query(1.0), format: str = Query("JPEG")):
    """
    获取 mtf 风格化头像

    Args:
        url (str): 原图片链接
        radius (float, optional): 高斯模糊
        scale (float, optional): 缩放倍数
        format (str, optional): 导出格式

    Returns:
        图片的数据流
    """
    async with httpx.AsyncClient() as session:
        resp = await session.get(html.unescape(url), timeout=30)
    img = get_removed_image(resp.content)
    if scale != 1.0:
        img.resize(int(scale * img.width), int(scale * img.height))
    avatar = set_mtf_background(img, radius)
    img_io = BytesIO(avatar.make_blob("png"))
    return StreamingResponse(img_io, media_type=f"image/{format}", headers={"Cache-Control": "max-age=86400"})
