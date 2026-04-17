# 运维手册

## 生产服务信息
- EC2 IP: 50.18.170.151，用户: ubuntu
- 部署路径: `/opt/services/culture-escrow-pg17/`
- systemd 服务: `pg17`（端口 8787）
- 前端 URL: `portal.cultureescrow.com/pg17`
- API URL: `api.hydenluc.com`
- Web 静态文件: `/var/www/pg17-web/index.html`

## SSH 登录
```bash
ssh -i ~/Downloads/CultureEscrow-EC2.pem ubuntu@50.18.170.151
```

---

## 日常检查

```bash
# 健康检查
curl http://127.0.0.1:8787/health

# 查看服务状态
systemctl status pg17

# 查看最近日志
journalctl -u pg17 -n 50

# 查看审计日志
tail -f /var/log/pg17/prod-audit.log.jsonl
```

## 手动触发文件清理

```bash
curl -X POST https://api.hydenluc.com/v1/admin/cleanup \
  -H "Authorization: Bearer $PG17_API_TOKEN"
```

## 故障处理

1. 记录 `request_id` / `job_id`（来自 API 响应或审计日志）
2. 收集错误码和 error_code
3. 判断根因：
   - 参数问题（400/422）：检查请求参数
   - 认证失败（401）：检查 `PG17_API_TOKEN`
   - 速率限制（429）：等待或提高 `PG17_RATE_LIMIT_PER_MINUTE`
   - 引擎异常（500）：查看 `journalctl -u pg17 -n 100`
   - 模板漂移（422）：检查源 PDF 锚点
4. 重启服务：`systemctl restart pg17`
5. 查看重启后健康状态：`curl http://127.0.0.1:8787/health`

## 部署回滚（手动）

```bash
ssh -i ~/Downloads/CultureEscrow-EC2.pem ubuntu@50.18.170.151
cd /opt/services/culture-escrow-pg17
git log --oneline -10        # 确认目标 commit
git checkout <commit-sha>
systemctl restart pg17
curl http://127.0.0.1:8787/health
```

---

## 本地开发运行

### Prerequisites
- macOS with Homebrew
- Python 3.11.x

### 1. Verify Python
```bash
python3.11 --version
```

### 2. Setup venv
```bash
cd ~/Developer/ClaudeCodeSpace/culture-escrow-pg17
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
python -V
```

### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r apps/api/requirements.txt
```

### 4. Configure env
```bash
cp .env.example .env
# 填入 PG17_API_TOKEN（本地随便填一个字符串即可）
```

### 5. Start API (Terminal A)
```bash
cd ~/Developer/ClaudeCodeSpace/culture-escrow-pg17
source .venv/bin/activate
./deploy/scripts/run_api.sh
```

### 6. Open Web UI (Terminal B)
```bash
cd ~/Developer/ClaudeCodeSpace/culture-escrow-pg17
python3 -m http.server 8788 --directory apps/web
```
访问：http://127.0.0.1:8788

### 7. Run tests
```bash
source .venv/bin/activate
python -m pytest tests/ -v
```
本地测试使用 stub engine，无需配置生产环境变量（`PG17_ESCROW_COMPANY` 等）。

### Troubleshooting
- 如果 `pydantic-core` build 失败：确认使用 Python 3.11，而不是 3.14
- 如果浏览器一直显示"处理中..."：确认 API 正在运行且 CORS 已启用

---

## Web UI

- 文件路径：`apps/web/index.html`
- 生产静态路径：`/var/www/pg17-web/index.html`（由 Caddy 服务）
- 自动部署：`deploy_prod.sh` 在每次 push to main 时同步静态文件
- 访问地址：`portal.cultureescrow.com/pg17`

### UI 变更历史
- v1：英文化 + 页面结构整理，默认对接 `https://api.hydenluc.com`
- v2（PR #28）：Source PDF 上传区域改为全宽布局，自定义文件选择框，Status 区域默认隐藏，新增 "How to Use" 步骤说明
