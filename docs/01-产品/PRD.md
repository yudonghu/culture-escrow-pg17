# PRD（V0）- culture-escrow-pg17

## 1. 目标
将 pg17（Escrow Holder Acknowledgment）从手工填充流程，产品化为可复用的客户端+服务端能力。

## 2. 核心价值
- 降低人工重复操作
- 保证填充一致性
- 保留可追溯结果（输入、输出、摘要）

## 3. MVP 范围（Demo）
- 上传 source PDF
- 输入 5 个变量：
  - deposit_amount
  - seller_agent_name
  - escrow_number
  - acceptance_date
  - second_date
- 返回 done.pdf + run summary

## 4. 非目标（MVP 不做）
- 批量任务队列
- 多组织权限体系
- 复杂审批流

## 5. 验收标准
- 样本文件可稳定导出 done.pdf
- 缺失字段能明确回报
- 输出页仅影响 page 17
