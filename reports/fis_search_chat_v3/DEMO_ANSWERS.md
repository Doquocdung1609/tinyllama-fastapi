# Actual demo questions and complete API answers

These are copied from real localhost Chat responses, not authored expected answers. Native source details and full claim graphs remain in SEMANTIC_FINAL_CASES.json and FINAL_ACCEPTANCE.json.

## Apple Greater China

**Question**

Trong FY2025, khu vực kinh doanh nào của Apple giảm doanh thu so với FY2024 dù tổng doanh thu tăng? Nêu cả hai giá trị, mức giảm tuyệt đối, tỷ lệ và giải thích từ báo cáo.

**Full answer**

Khu vực kinh doanh giảm doanh thu là Greater China.

FY2025 Greater China — doanh thu: 64.377 triệu USD [1]; FY2024: 66.952 triệu USD [2]. Mức thay đổi là -2.575 triệu USD, tương đương -3,85 %.

FY2025 doanh thu thuần: 416.161 triệu USD [3]; FY2024: 391.035 triệu USD [4]. Mức thay đổi là 25.126 triệu USD, tương đương 6,43 %.

Báo cáo giải thích (nguyên văn): Greater China net sales decreased during 2025 compared to 2024 primarily due to lower net sales of iPhone, partially offset by higher net sales of Mac. [5]

**Citations**

- [1] Greater China — physical PDF25; `cellv2_10a5b7cfe338a19ae9310c1f7274`; SHA`3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de`.
- [2] Greater China — physical PDF25; `cellv2_6b73b70dbb458cd5f74adeda25ea`; SHA`3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de`.
- [3] Total net sales — physical PDF32; `cellv2_cc16f54065bce239f5e0fad95209`; SHA`3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de`.
- [4] Total net sales — physical PDF32; `cellv2_7f1fcea611bce77e0db246ae826f`; SHA`3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de`.
- [5] Paragraph — physical PDF25; `paragraph_b83be0eb225f57f53675f71c7631`; SHA`3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de`.

## BIDV adjustment difference

**Question**

Mức điều chỉnh của riêng ngân hàng và hợp nhất khác nhau bao nhiêu? Giải thích cách tính.

**Full answer**

FY2024, mức điều chỉnh hợp nhất cao hơn riêng ngân hàng 1.114 triệu đồng. [1][2]

Điều chỉnh hợp nhất: 72.012; riêng: 70.898 triệu đồng.

**Source operands and steps**

```json
[
  {
    "calculation_id": "q1_calculation_1",
    "title": "consolidated adjustment − separate adjustment",
    "operation": "SCOPE_DIFFERENCE",
    "formula": "consolidated adjustment − separate adjustment",
    "substitution": [
      {
        "value": "72,012",
        "period": "2024",
        "scope": "CONSOLIDATED",
        "basis": "ADJUSTMENT",
        "unit": "TRIEU_VND",
        "citation": "[1]"
      },
      {
        "value": "70,898",
        "period": "2024",
        "scope": "SEPARATE",
        "basis": "ADJUSTMENT",
        "unit": "TRIEU_VND",
        "citation": "[2]"
      }
    ],
    "result": "1114",
    "unit": "TRIEU_VND",
    "rounding": "ROUND_HALF_UP; 2 decimal places for percentages/percentage points; exact Decimal for amounts"
  }
]
```
