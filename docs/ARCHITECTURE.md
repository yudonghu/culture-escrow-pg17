# 架构设计（当前生产版）

## 1. 分层
- Client：上传/参数输入/结果下载（`apps/web/index.html`，由 Caddy 静态服务）
- HTTP 层：请求路由、认证、速率限制（`apps/api/main.py`，FastAPI）
- 业务逻辑层：任务编排、幂等、审计、引擎调用（`apps/api/pg17_service.py`，PG17Service 类）
- Engine：pg17 填充核心逻辑（子进程调用）

## 2. 模块边界
- `apps/web/index.html`：前端单页应用，由 Caddy 从 `/var/www/pg17-web/` 静态服务
- `apps/api/main.py`：HTTP 层（FastAPI，路由、认证、速率限制 20次/分钟/IP）
- `apps/api/pg17_service.py`：业务逻辑层（PG17Service 类，PR #25 从 main.py 抽出）
- `packages/pg17-fill-engine/pg17_engine.py`：引擎子进程调用包装
- `packages/pg17-fill-engine/fill_page17_real.py`：真实填写脚本（OCR + reportlab，生产使用）
- `packages/pg17-fill-engine/fill_page17_stub.py`：本地测试桩（测试/开发使用）

## 3. 流程
1) 客户端上传 PDF + 参数（multipart/form-data）
2) `main.py` 校验认证（Bearer token）、速率限制
3) 交由 `PG17Service` 处理业务逻辑（幂等检查、审计日志）
4) 调用 pg17 engine 子进程填充
5) 返回 done.pdf 与 run summary（含 timings_ms）

## 4. 设计原则
- 引擎逻辑与接口层解耦（engine 独立子进程）
- HTTP 层与业务层分离（main.py 不含业务逻辑）
- 同输入同输出（幂等性，基于 x-idempotency-key）
- 错误信息可读、可定位（error_code + request_id）

## 5. 关键中间件
- Bearer token 认证（`PG17_API_TOKEN` 非空时启用）
- 速率限制：20次/分钟/IP（内存滑动窗口）
- 幂等存储：文件级 JSON store（`PG17_IDEMPOTENCY_STORE`）
- 审计日志：JSONL 格式（`PG17_AUDIT_LOG_PATH`），敏感字段脱敏

---

## 6. Engine Runtime

### 当前策略
- 生产环境使用真实引擎：`packages/pg17-fill-engine/fill_page17_real.py`（OCR + reportlab）
- 本地测试使用 stub：`packages/pg17-fill-engine/fill_page17_stub.py`
- 通过环境变量控制：
  - `PG17_ENGINE_PYTHON`：Python 解释器路径（生产默认 `python3`）
  - `PG17_ENGINE_SCRIPT`：引擎脚本路径（生产为 `packages/pg17-fill-engine/fill_page17_real.py`）

### 调用方式
引擎以子进程方式调用，通过 `packages/pg17-fill-engine/pg17_engine.py` 封装：
- stdout 读取 JSON 结果
- 非零退出码视为引擎异常

### 生产依赖（版本锁定，与 EC2 一致）
- `pypdf`
- `pymupdf`
- `pillow`
- `pytesseract`
- `reportlab`
- 系统依赖：`tesseract-ocr`

### 本地测试
测试套件（tests/）使用 stub engine，无需配置 `PG17_ENGINE_SCRIPT` 等生产变量。
