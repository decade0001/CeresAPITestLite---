# CeresAPITestLite

轻量级接口自动化测试工具，面向 CERESHOP 商城系统接口练习场景。工具使用 Python 标准库实现，无需安装第三方依赖。

## 功能

- 使用 JSON 文件维护接口测试用例。
- 支持 GET / POST / PUT / DELETE 请求。
- 支持 query 参数、JSON 请求体、Header、Cookie/Token 等字段。
- 支持变量提取与复用，例如从登录接口响应中提取 token。
- 支持状态码、响应字段、字段值、包含文本、响应时间断言。
- 自动生成 HTML 测试报告和 JSON 摘要。
- 提供 mock_server.py，未启动 CERESHOP 项目时也能演示工具效果。
- 提供 Dockerfile 和 GitHub Actions 示例，便于包装为自动化测试项目。

## 目录

```text
CeresAPITestLite/
  run_tests.py              # 接口自动化测试运行器
  mock_server.py            # 本地模拟接口服务
  cases/
    demo_cases.json         # 可直接配合 mock_server.py 运行的演示用例
    cereshop_cases.json     # CERESHOP 项目接口用例模板
  reports/                  # 运行后生成报告
  Dockerfile
  .github/workflows/api-test.yml
```

## 快速演示

先启动 mock 服务：

```bash
python mock_server.py
```

再打开另一个终端运行：

```bash
python run_tests.py --case cases/demo_cases.json --report-dir reports
```

运行完成后查看 `reports/` 目录下的 HTML 报告。

## 对接 CERESHOP

CERESHOP app 服务默认端口在源码配置中为 `9007`，business 服务默认端口为 `9004`，admin 服务默认端口为 `9003`。如果你本地启动了 CERESHOP app 服务，可以运行：

```bash
python run_tests.py --case cases/cereshop_cases.json --base-url http://127.0.0.1:9007
```

`cases/cereshop_cases.json` 中的接口来自源码 Controller，包括：

- `/app/login`
- `/product/getProducts`
- `/product/getById`
- `/shop/getShops`
- `/cart/getCart`
- `/order/getAll`

其中部分接口可能需要登录 token 或数据库测试数据。实际使用时需要根据本地环境调整账号、密码、商品 ID、token 字段路径和期望返回码。

## 简历表述建议

可以写成：

> 基于 Python 标准库实现轻量级接口自动化测试工具，采用 JSON 管理测试用例，支持 GET/POST 请求、Header/Token、变量提取、状态码/响应字段/响应时间断言，并生成 HTML 测试报告；结合 CERESHOP 商城项目对登录、商品查询、店铺查询、购物车、订单等接口设计用例模板，提升接口回归验证效率。

