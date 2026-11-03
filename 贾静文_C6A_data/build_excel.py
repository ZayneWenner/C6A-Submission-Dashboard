# -*- coding: utf-8 -*-
"""C6A Level 2：把 dataset.json 渲染为多 Sheet Excel 工作簿。

输入：同目录 dataset.json
输出：贾静文_C6A_数据_提交总表.xlsx
用法：python build_excel.py
"""
import json
import os
from datetime import datetime, timezone, timedelta

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "dataset.json")
OUT = os.path.join(HERE, "贾静文_C6A_数据_提交总表.xlsx")
CST = timezone(timedelta(hours=8))

NAVY = "1F2A44"
ACCENT = "4F46E5"
LIGHT = "EEF2FF"
GREY = "F1F5F9"
OK = "DCFCE7"
WARN = "FEF3C7"
ERR = "FEE2E2"

thin = Side(style="thin", color="D5DBE3")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)


def style_header(ws, row, ncol, fill=NAVY):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor=fill)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[row].height = 26


def style_body(ws, r1, r2, ncol):
    for r in range(r1, r2 + 1):
        for c in range(1, ncol + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = BORDER
            cell.font = Font(size=10)
            cell.alignment = Alignment(vertical="center", wrap_text=(c <= 2))


def widths(ws, mapping):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


def title_block(ws, text, sub, ncol):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    c = ws.cell(row=1, column=1, value=text)
    c.font = Font(bold=True, size=14, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 30

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncol)
    c = ws.cell(row=2, column=1, value=sub)
    c.font = Font(size=9, color="475569")
    c.fill = PatternFill("solid", fgColor=LIGHT)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 22


def status_cn(s):
    return {"checked": "已审核", "needs_revision": "需返工", "pending": "待处理"}.get(s, s or "—")


def local_cn(s):
    return {"complete": "齐全", "partial": "缺失", "empty": "零命中", "not_scanned": "未扫描"}.get(s, s)


def main():
    with open(SRC, encoding="utf-8") as f:
        d = json.load(f)

    meta = d["meta"]
    m = meta["metrics"]
    chal = d["challenges"]
    subs = d["submissions"]
    tl = d.get("timeline", [])
    ins = d.get("insights", [])

    wb = Workbook()

    # ---------------- Sheet 1: 总览 ----------------
    ws = wb.active
    ws.title = "1-总览"
    title_block(
        ws,
        "C6A 提交数据仪表盘 · 总览",
        "数据源：EduSeed 平台 list-challenges / list-my-submissions + 本地目录扫描　|　生成时间：%s" % meta["generated_at"],
        6,
    )

    ws["A4"] = "核心指标"
    ws["A4"].font = Font(bold=True, size=11, color=NAVY)

    kpis = [
        ("挑战总数", m["challenges_total"], "平台已发布、可解析出 C 代号的挑战"),
        ("已提交", m["submitted"], "提交记录中出现的不同挑战数"),
        ("未提交", m["not_submitted"], "仍需新增交付物"),
        ("完成率", "%.1f%%" % m["coverage_pct"], "已提交 / 挑战总数"),
        ("待评审", m["pending_review"], "平台 status=checked，等待教师终审"),
        ("需返工", m["needs_revision"], "平台 status=needs_revision，不计入通过"),
        ("扫描文件", m["scanned_files"], "本地扫描命中的交付物文件数"),
        ("提交记录", len(subs), "list-my-submissions 返回条数"),
    ]
    r = 5
    ws.cell(row=r, column=1, value="指标")
    ws.cell(row=r, column=2, value="数值")
    ws.cell(row=r, column=3, value="口径")
    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=6)
    style_header(ws, r, 6)
    for name, val, note in kpis:
        r += 1
        ws.cell(row=r, column=1, value=name).font = Font(bold=True, size=10)
        ws.cell(row=r, column=2, value=val).alignment = Alignment(horizontal="center")
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=6)
        ws.cell(row=r, column=3, value=note).font = Font(size=9, color="475569")
    style_body(ws, 5, r, 6)
    for rr in range(6, r + 1):
        ws.cell(row=rr, column=1).fill = PatternFill("solid", fgColor=GREY)

    r += 2
    ws.cell(row=r, column=1, value="口径与边界（必读）").font = Font(bold=True, size=11, color=NAVY)
    notes = [
        "1. 本表只统计本人账号 GET /submissions/my 返回的 %d 条记录，不含全班数据；" % len(subs),
        "   挑战总数 %d 来自平台 list-challenges（已剔除无法解析 C 代号的条目）。" % meta.get("challenges_total", len(chal)),
        "2. 「平台状态 status」与「任务状态 task_state」是两套独立字段，本表不合并、不推断；task_state 为空即原样留空。",
        "3. 「本地校验」只表示“本机目录里存在同名文件”，不等同于平台已收件或已通过评审。",
        "4. needs_revision 视为未通过，不因存在提交记录而算完成。",
        "5. 交付物命中去重、忽略大小写与空白：先按 required_deliverables 的通配规则匹配文件名，再回退到父目录名。",
    ]
    for n in notes:
        r += 1
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        c = ws.cell(row=r, column=1, value=n)
        c.font = Font(size=9, color="334155")
        c.alignment = Alignment(vertical="center", indent=1)

    widths(ws, {"A": 18, "B": 10, "C": 22, "D": 18, "E": 16, "F": 20})

    # ---------------- Sheet 2: 挑战清单 ----------------
    ws2 = wb.create_sheet("2-挑战清单")
    title_block(ws2, "挑战提交清单", "按 C 代号升序；本地校验 = 本机文件对照 required_deliverables 的结果", 9)
    head2 = ["代号", "挑战名称", "截止时间", "已提交", "提交编号", "平台状态", "本地校验", "命中率", "缺失项"]
    for i, h in enumerate(head2, 1):
        ws2.cell(row=4, column=i, value=h)
    style_header(ws2, 4, len(head2))

    row = 4
    for c in sorted(chal, key=lambda x: x["code"]):
        row += 1
        lc = c["local_check"]
        vals = [
            c["code"], c["title"], (c.get("deadline") or "—"),
            "是" if c["submitted"] else "否",
            c.get("submission_id") or "—",
            status_cn(c.get("status")),
            local_cn(lc["status"]),
            ("%.0f%%" % (lc["ratio"] * 100)) if lc["ratio"] is not None else "—",
            " / ".join(lc["missing"]) if lc["missing"] else "无",
        ]
        for i, v in enumerate(vals, 1):
            ws2.cell(row=row, column=i, value=v)
        # 上色
        st = lc["status"]
        if st == "complete":
            ws2.cell(row=row, column=7).fill = PatternFill("solid", fgColor=OK)
        elif st == "partial":
            ws2.cell(row=row, column=7).fill = PatternFill("solid", fgColor=WARN)
        elif st == "empty":
            ws2.cell(row=row, column=7).fill = PatternFill("solid", fgColor=ERR)
        if c.get("status") == "needs_revision":
            ws2.cell(row=row, column=6).fill = PatternFill("solid", fgColor=ERR)
        elif c.get("status") == "checked":
            ws2.cell(row=row, column=6).fill = PatternFill("solid", fgColor=OK)
        elif c["submitted"]:
            ws2.cell(row=row, column=6).fill = PatternFill("solid", fgColor=WARN)
    style_body(ws2, 4, row, len(head2))
    style_header(ws2, 4, len(head2))
    ws2.freeze_panes = "A5"
    ws2.auto_filter.ref = "A4:%s%d" % (get_column_letter(len(head2)), row)
    widths(ws2, {"A": 9, "B": 30, "C": 12, "D": 8, "E": 26, "F": 11, "G": 10, "H": 9, "I": 18})

    # ---------------- Sheet 3: 提交记录 ----------------
    ws3 = wb.create_sheet("3-提交记录")
    title_block(ws3, "我的提交记录", "按提交时间倒序；task_state 为平台任务状态，空值原样保留不推断", 6)
    head3 = ["提交时间(UTC)", "代号", "项目标题", "平台状态", "任务状态", "仓库地址"]
    for i, h in enumerate(head3, 1):
        ws3.cell(row=4, column=i, value=h)
    style_header(ws3, 4, len(head3))
    row = 4
    for s in sorted(subs, key=lambda x: str(x.get("submitted_at") or ""), reverse=True):
        row += 1
        ts = str(s.get("submitted_at") or "—")
        if ts != "—":
            try:
                dt = datetime.strptime(ts.replace("Z", "+0000").replace(".000", ""), "%Y-%m-%dT%H:%M:%S%z")
                ts = dt.astimezone(CST).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts = ts.replace("T", " ")
        vals = [ts, s.get("code") or "—", s.get("project_title") or "—",
                status_cn(s.get("status")), s.get("task_state") or "（空）", s.get("repo") or "—"]
        for i, v in enumerate(vals, 1):
            ws3.cell(row=row, column=i, value=v)
        if s.get("status") == "needs_revision":
            ws3.cell(row=row, column=4).fill = PatternFill("solid", fgColor=ERR)
        elif s.get("status") == "checked":
            ws3.cell(row=row, column=4).fill = PatternFill("solid", fgColor=OK)
        else:
            ws3.cell(row=row, column=4).fill = PatternFill("solid", fgColor=WARN)
    style_body(ws3, 4, row, len(head3))
    style_header(ws3, 4, len(head3))
    ws3.freeze_panes = "A5"
    widths(ws3, {"A": 22, "B": 9, "C": 46, "D": 11, "E": 11, "F": 52})

    # ---------------- Sheet 4: 时间线 ----------------
    ws4 = wb.create_sheet("4-时间线")
    title_block(ws4, "提交时间线", "按北京时间自然日汇总提交次数，用于观察提交节奏", 4)
    head4 = ["日期(北京)", "提交次数", "涉及挑战", "备注"]
    for i, h in enumerate(head4, 1):
        ws4.cell(row=4, column=i, value=h)
    style_header(ws4, 4, len(head4))
    row = 4
    for t in tl:
        row += 1
        ws4.cell(row=row, column=1, value=t["date"])
        ws4.cell(row=row, column=2, value=t["count"])
        ws4.cell(row=row, column=3, value=t.get("codes") and " / ".join(t["codes"]) or "—")
        ws4.cell(row=row, column=4, value="集中提交" if t["count"] >= 3 else "")
    style_body(ws4, 4, row, len(head4))
    style_header(ws4, 4, len(head4))
    if row > 4:
        ch = None
        try:
            from openpyxl.chart import BarChart, Reference
            ch = BarChart()
            ch.title = "每日提交次数"
            ch.y_axis.title = "次数"
            ch.x_axis.title = "日期"
            data = Reference(ws4, min_col=2, min_row=4, max_row=row)
            cats = Reference(ws4, min_col=1, min_row=5, max_row=row)
            ch.add_data(data, titles_from_data=True)
            ch.set_categories(cats)
            ch.height, ch.width = 7, 14
            ws4.add_chart(ch, "F4")
        except Exception as e:
            print("chart skipped:", e)
    widths(ws4, {"A": 14, "B": 11, "C": 28, "D": 12})

    # ---------------- Sheet 5: 交付物校验 ----------------
    ws5 = wb.create_sheet("5-交付物校验")
    title_block(ws5, "交付物校验明细", "要求项来自平台 required_deliverables；命中/缺失由本机扫描结果得出", 5)
    head5 = ["代号", "要求项", "本地命中", "本地缺失", "文件数"]
    for i, h in enumerate(head5, 1):
        ws5.cell(row=4, column=i, value=h)
    style_header(ws5, 4, len(head5))
    row = 4
    for c in sorted(chal, key=lambda x: x["code"]):
        lc = c["local_check"]
        if lc["status"] == "not_scanned" and not c["submitted"]:
            continue
        row += 1
        ws5.cell(row=row, column=1, value=c["code"])
        ws5.cell(row=row, column=2, value=" / ".join(c.get("required") or []) or "（平台未定义）")
        ws5.cell(row=row, column=3, value=" / ".join(lc["present"]) or "—")
        ws5.cell(row=row, column=4, value=" / ".join(lc["missing"]) or "无")
        ws5.cell(row=row, column=5, value=lc["file_count"])
        ws5.cell(row=row, column=4).fill = PatternFill(
            "solid", fgColor=OK if not lc["missing"] else ERR)
    style_body(ws5, 4, row, len(head5))
    style_header(ws5, 4, len(head5))
    ws5.freeze_panes = "A5"
    widths(ws5, {"A": 9, "B": 46, "C": 30, "D": 26, "E": 9})

    # ---------------- Sheet 6: 洞察与建议 ----------------
    ws6 = wb.create_sheet("6-洞察与建议")
    title_block(ws6, "数据洞察与行动建议", "由 build_dataset.py 依据数据自动生成，供复盘与后续排期使用", 4)
    ws6.cell(row=4, column=1, value="级别")
    ws6.cell(row=4, column=2, value="结论")
    ws6.cell(row=4, column=3, value="依据")
    ws6.merge_cells(start_row=4, start_column=3, end_row=4, end_column=4)
    style_header(ws6, 4, 4)
    row = 4
    for i in ins:
        row += 1
        ws6.cell(row=row, column=1, value={"risk": "风险", "warn": "注意", "ok": "正常", "info": "观察"}.get(i["level"], i["level"]))
        ws6.cell(row=row, column=2, value=i["title"])
        ws6.merge_cells(start_row=row, start_column=3, end_row=row, end_column=4)
        ws6.cell(row=row, column=3, value=i["body"])
        fill = {"risk": ERR, "warn": WARN, "ok": OK}.get(i["level"])
        if fill:
            ws6.cell(row=row, column=1).fill = PatternFill("solid", fgColor=fill)
    style_body(ws6, 4, row, 4)
    style_header(ws6, 4, 4)
    widths(ws6, {"A": 9, "B": 30, "C": 42, "D": 22})

    wb.save(OUT)
    total = sum(1 for _ in chal)
    print("saved:", OUT)
    print("sheets:", wb.sheetnames)
    print("challenge rows:", total, "submission rows:", len(subs), "insights:", len(ins))


if __name__ == "__main__":
    main()
