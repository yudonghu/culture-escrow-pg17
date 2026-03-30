# Engine Runtime (PR13)

## 目标
让 pg17 服务端不再依赖开发机本地绝对路径，能够在 EC2 / 其他主机独立运行。

## 新机制
通过环境变量指定引擎入口：
- `PG17_ENGINE_PYTHON`
- `PG17_ENGINE_SCRIPT`

未配置时，默认使用仓库内置的 fallback stub：
- `tools/pg17-engine/fill_page17_stub.py`

## 当前状态
- 这次先完成“部署解耦”
- fallback stub 仅用于验证服务链路与部署可用性
- 后续可再替换为真正的 page17 fill engine 实现

## 建议
- staging/prod 使用仓库内 engine 或明确指定部署路径
- 不再写死 `/Users/wu/...` 这类本机开发路径
