# 架构设计（V0）

## 1. 分层
- Client：上传/参数输入/结果下载
- API：请求校验、任务编排、结果返回
- Engine：pg17 填充核心逻辑

## 2. 模块边界
- `apps/web`：前端页面
- `apps/api`：服务端接口
- `packages/pg17-fill-engine`：可复用填充模块
- `packages/shared-types`：统一 schema

## 3. 流程
1) 客户端上传 PDF + 参数
2) API 校验参数
3) 调用 pg17 engine
4) 返回 done.pdf 与 run summary

## 4. 设计原则
- 引擎逻辑与接口层解耦
- 同输入同输出（可重复）
- 错误信息可读、可定位
