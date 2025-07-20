# acrnm-api

这是一个现代、快速、高性能的基于 FastAPI 编写的将网站页面解析为接口的后端。

## 介绍

被解析网站 [acrnm.com/index](https://acrnm.com/index?sort=default&filter=txt)

该项目部署在阿里云 [Serverless 应用](https://serverless.nana7mi.link/api/acrnm)

目前提供了两个接口：`/` 与 `/{href}`

### 接口 `/`

获取 ACRNM 上架的商品列表

响应示例：

```json
[
    {
        "name": "J123A-GT",
        "href": "/J123A-GT_SS24",
        "price": "1,458.00 EUR",
        "variants": [
            {
                "color": "black",
                "size": "XS/S"
            },
            {
                "color": "alpha_green",
                "size": "XS/S/M"
            }
        ]
    },
    ...
]
```

### 接口 `/{href}`

获取商品外观链接列表

使用路径参数传入该商品的 `href`

调用示例：

```
GET /J118-WS_SS24
```

响应示例：

```json
[
    "https://acrnm.com/rails/active_storage/representations/proxy/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBNWJrQVE9PSIsImV4cCI6bnVsbCwicHVyIjoiYmxvYl9pZCJ9fQ==--40b550a0eb67cefb443dfbd7e639d2d4bfbb490f/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaDdDRG9MWm05eWJXRjBPZ2wzWldKd09oUnlaWE5wZW1WZmRHOWZiR2x0YVhSYkIya0NZQWxwQW1BSk9neGpiMjUyWlhKME93WT0iLCJleHAiOm51bGwsInB1ciI6InZhcmlhdGlvbiJ9fQ==--3d0ae92aa09fe6f90cb74abd0968f1648b3acb0e/J118-DS_1216.jpg",
    ...
]
```