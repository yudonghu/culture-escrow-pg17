# PG17 Web v1 Online Entry

## 目标
把原本只适合本地 demo 的 `apps/web/index.html` 提升为适合线上访问的前端页面。

## 历史变化
- v1（英文化）：英文化和页面结构整理，默认对接 `https://api.hydenluc.com`
- v2（PR #28，UI 大改版）：
  - Source PDF 上传区域改为全宽布局
  - 自定义文件选择框（替代系统默认样式）
  - Status / 结果区域默认隐藏，填写完成后显示
  - 新增 "How to Use" 步骤说明区块

## 部署方式
- 文件路径：`apps/web/index.html`
- 生产静态路径：`/var/www/pg17-web/index.html`（由 Caddy 服务）
- 自动部署：`deploy_prod.sh` 在每次 push to main 时同步静态文件（PR #29）
- 访问地址：`portal.cultureescrow.com/pg17`

## 当前定位
pg17 前端当前版本，适合面向实际业务使用。非最终产品 UI，后续可进一步迭代。
