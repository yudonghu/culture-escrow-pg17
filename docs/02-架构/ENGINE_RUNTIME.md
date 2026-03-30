# Engine Runtime (PR14)

## 当前策略
- 默认优先使用仓库内真实引擎：`tools/pg17-engine/fill_page17_real.py`
- 若真实引擎不存在，则回退到：`tools/pg17-engine/fill_page17_stub.py`
- 也可用环境变量覆盖：
  - `PG17_ENGINE_PYTHON`
  - `PG17_ENGINE_SCRIPT`

## 目标
让部署机默认跑真实 page17 fill engine，而不是开发机私有路径或 stub。

## 结果
- EC2 / 其他部署主机可直接随 repo 部署真实引擎
- 不再依赖 `/Users/wu/...` 这类本机绝对路径
