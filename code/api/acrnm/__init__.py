from typing import List, Optional

import cloudscraper
from fastapi import APIRouter, Path
from lxml import etree
from pydantic import BaseModel


class Variant(BaseModel):
    """
    商品变体
    """

    color: str
    size: str


class Product(BaseModel):
    """
    商品属性
    """

    name: str  # 展示名
    href: str  # 实际名
    price: str
    variants: Optional[List[Variant]] = None


router = APIRouter()
scraper = cloudscraper.create_scraper()


@router.get("/")
async def get_acrnm_products() -> List[Product]:
    """
    获取 ACRNM 上架的商品列表

    Returns:
        商品列表
    """
    # 获取网页
    resp = scraper.get("https://acrnm.com?sort=default&filter=txt")
    root: etree._Element = etree.HTML(resp.text)
    table: List[etree._Element] = root.cssselect(".m-product-table__row")
    # 解析数据
    products = []
    for tr in table:
        price = tr.xpath("./td[4]/span/text()")
        if len(price) == 0:
            continue
        product = Product(
            name=tr.xpath("./td[1]/a/span/text()")[0],
            href=tr.xpath("./td[1]/a/@href")[0],
            price=price[0],
            variants=[],
        )
        # 去掉难绷前缀
        product.href = product.href.removeprefix("/")
        variants: List[etree._Element] = tr.xpath("./td[3]/div/span")
        for var in variants:
            color = ", ".join(var.xpath("./div/span/text()"))
            size = ", ".join(var.xpath("./span/text()"))
            product.variants.append(Variant(color=color, size=size))
        products.append(product)
    return products


@router.get("/{href}")
async def get_product_appearance(href: str = Path(..., description="商品实际名称", example="J1W-GTV_SS25")) -> List[str]:
    """
    获取商品外观

    Args:
        href (str): 商品实际名称

    Returns:
        外观链接列表
    """
    resp = scraper.get(f"https://acrnm.com/{href}")
    root: etree._Element = etree.HTML(resp.text)
    return root.xpath("//div[contains(@class, 'product-image')]//img/@src")
