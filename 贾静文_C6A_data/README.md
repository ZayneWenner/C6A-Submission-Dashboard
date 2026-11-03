# 贾静文_C6A_data｜提交数据管道说明

C6A 的全部数据都由三个脚本生成，**不手工填任何一个数字**。换一个人、换一天，只要按顺序重跑就能得到同样的结果。

## 目录里有什么

| 文件 | 类型 | 说明 |
|------|------|------|
| `scan_submissions.py` | 脚本 | 扫描本地提交目录，按平台 `required_deliverables` 校验交付物是否命中 |
| `build_dataset.py` | 脚本 | 拉取平台挑战与提交记录，合并扫描结果，产出 `dataset.json` + CSV |
| `build_excel.py` | 脚本 | 把 `dataset.json` 渲染成 6 Sheet 的 Excel 总表 |
| `raw/challenges_raw.json` | 原始数据 | 平台 `list-challenges` 原样返回，未加工 |
| `raw/submissions_raw.json` | 原始数据 | 平台 `list-my-submissions` 原样返回，未加工 |
| `dataset.json` | 中间产物 | 前端仪表盘与 Excel 共用的唯一数据源 |
| `submissions.csv` / `coverage.csv` | 中间产物 | 便于用 Excel / pandas 直接查看 |
| `scans.json` | 中间产物 | 本地扫描明细，含每个挑战的缺失项 |
| `贾静文_C6A_数据_提交总表.xlsx` | 交付物 | Level 2 的多 Sheet 工作簿 |

## 运行顺序

三个脚本有先后依赖，顺序不能颠倒：

```bash
# 1) 扫描本地交付物（离线，不需要网络）
python scan_submissions.py

# 2) 拉平台数据 + 合并扫描结果，生成 dataset.json
python build_dataset.py

# 3) 渲染 Excel（依赖 dataset.json）
python build_excel.py
```

`build_dataset.py` 需要平台可达（校园网）。`scan_submissions.py` 和 `build_excel.py` 都是纯本地离线运行。

## 数据口径

- **挑战总数 = 20**：平台 `list-challenges` 返回 21 条，其中 `ch-20260904104535-14aac163`（T0 发布流程测试，标题明示"请忽略"）被排除，故分母为 21 − 1 = 20。
- **完成率 = 已提交挑战数 ÷ 20**：当前 10 ÷ 20 = 50.0%。
- **已提交 / 未提交** 以平台 `list-my-submissions` 为准，本地有文件但平台无记录**不算已提交**。
- **待评审 / 需返工** 按 `status` 字段区分：`checked` 进待评审，`needs_revision` 单列且不计入通过。
- 时间均为 UTC，与北京时间相差 8 小时。

## 已知边界

1. 平台只返回**本人**提交记录，无法统计同班其他学生，因此仪表盘是个人视角，不是班级口径。
2. 本地扫描依赖**文件名匹配** `required_deliverables` 的模式，文件改名会被判为缺失；此时以平台状态为准。
3. 平台「挑战详情」接口对部分挑战返回"挑战不存在"（已知平台缺陷），脚本改为回退到 `list-challenges` 的完整列表，不影响结果。

## 换一个人复用要改哪里

只有两处：

- `scan_submissions.py` 顶部的 `ROOT_DIRS`：改成自己的提交包所在目录列表。
- `build_dataset.py` 顶部的输出路径与作者名。

其余逻辑与口径无需改动。
