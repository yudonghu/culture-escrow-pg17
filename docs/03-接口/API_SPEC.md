# API 规范（V0 草案）

## POST /v1/pg17/fill

### Request（multipart/form-data）
- `source_pdf` (required)
- `deposit_amount` (optional)
- `seller_agent_name` (optional)
- `escrow_number` (optional)
- `acceptance_date` (optional)
- `second_date` (optional)

### Response（200）
```json
{
  "output_file": ".../xxx-done.pdf",
  "summary": {
    "missing_inputs": [],
    "filled_fields": [],
    "left_blank": []
  }
}
```

### Error
- 400: 参数格式错误
- 413: 文件过大
- 422: 模板漂移/锚点无法定位
- 500: 引擎运行失败
