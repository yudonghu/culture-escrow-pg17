# 运维手册

## 服务信息
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
