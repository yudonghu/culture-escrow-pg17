# Engine Runtime

## 当前策略（PR #24 锁定依赖版本）
- 生产环境使用真实引擎：`tools/pg17-engine/fill_page17_real.py`（OCR + reportlab）
- 本地测试使用 stub：`tools/pg17-engine/fill_page17_stub.py`
- 通过环境变量控制：
  - `PG17_ENGINE_PYTHON`：Python 解释器路径（生产默认 `python3`）
  - `PG17_ENGINE_SCRIPT`：引擎脚本路径（生产为 `tools/pg17-engine/fill_page17_real.py`）

## 调用方式
引擎以子进程方式调用，通过 `packages/pg17-fill-engine/pg17_engine.py` 封装：
- stdin 传入 JSON 参数
- stdout 读取结果
- 非零退出码视为引擎异常

## 生产依赖（PR #24 锁定版本，与 EC2 一致）
- `pypdf`
- `pymupdf`
- `pillow`
- `pytesseract`
- `reportlab`
- 系统依赖：`tesseract-ocr`

## 本地测试
测试套件（tests/）使用 stub engine，无需配置 `PG17_ENGINE_SCRIPT` 等生产变量。

## 历史
- 原设计（PR14）：默认优先真实引擎，不存在则回退 stub
- PR #24：锁定 engine 依赖版本，确保本地与生产一致
- PR #27：修复生产启动崩溃的 sys.path 问题，确保 engine 包可正确导入
