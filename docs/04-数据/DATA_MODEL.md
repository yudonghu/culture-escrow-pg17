# 数据模型（V0）

## 实体
- FillJob
- SourceFile
- FillInput
- FillSummary
- OutputArtifact

## 字段要求
- 每次任务必须带 `job_id`
- 输入与输出要可追溯
- 错误必须记录 code + message
