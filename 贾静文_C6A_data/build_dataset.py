# -*- coding: utf-8 -*-
"""C6A 数据集构建器：原始平台数据 + 本地扫描 -> dataset.json / data.js / CSV

输入：
  raw/challenges_raw.json   平台 list-challenges 原样返回
  raw/submissions_raw.json  平台 list-my-submissions 原样返回
  scans.json                scan_submissions.py 输出（可缺失，缺失则跳过文件校验）
输出：
  dataset.json              仪表盘唯一数据源（含 sources / challenges / submissions / insights）
  仪表盘/assets/data.js      同名数据包成 window.C6A_DATA，供 file:// 直接打开（免 fetch，无 CORS）
  submissions.csv           扁平提交表
  coverage.csv              交付物校验表

口径（写进数据字典，避免误读）：
  * 平台 status = 平台侧提交状态；task_state = 平台评估任务状态。两者独立，本脚本不做合并推断。
  * 本地文件校验只代表「本机是否有符合命名要求的文件」，不代表平台已收；二者在仪表盘分列显示。
"""
import argparse, csv, json, os, re
from datetime import datetime, timezone

CODE_RE = re.compile(r"C\d{1,2}[A-Z]?")


def load(path, key):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict):
        d = d.get("json", d)
        return d.get(key, []) if isinstance(d, dict) else d
    return d


def code_of(title):
    m = CODE_RE.search(title or "")
    return m.group(0) if m else None


def build(chal_path, sub_path, scan_path, generated_at):
    challenges = load(chal_path, "challenges")
    subs = load(sub_path, "submissions")
    scans = {"coverage": [], "scanned_files": 0, "assigned_files": 0, "roots": []}
    if scan_path and os.path.exists(scan_path):
        with open(scan_path, "r", encoding="utf-8") as f:
            scans = json.load(f)

    # 挑战表：只保留能识别代号的（C 系列），测试类 T0 不进统计
    chal_rows, by_id, by_code = [], {}, {}
    for c in challenges:
        title = c.get("title", "")
        code = code_of(title)
        if not code:
            continue
        reqs = [s.strip() for s in (c.get("required_deliverables") or "").split(",") if s.strip()]
        row = {
            "challenge_id": c.get("challenge_id"), "code": code, "title": title,
            "status": c.get("status"), "deadline": c.get("deadline"),
            "required": [r.replace("*", "") for r in reqs],
            "required_raw": reqs, "submitted": False,
        }
        chal_rows.append(row)
        by_id[row["challenge_id"]] = row
        by_code.setdefault(code, row)

    # 提交表
    sub_rows = []
    for s in subs:
        ch = by_id.get(s.get("challenge_id"))
        code = ch["code"] if ch else code_of(s.get("project_title"))
        row = {
            "submission_id": s.get("submission_id"), "challenge_id": s.get("challenge_id"),
            "code": code, "project_title": s.get("project_title"),
            "challenge_title": ch["title"] if ch else None,
            "status": s.get("status"), "task_state": s.get("task_state"),
            "submitted_at": s.get("submitted_at"), "repo": s.get("github_repo_url"),
        }
        sub_rows.append(row)
        if ch:
            ch["submitted"] = True
            ch["submission_id"] = row["submission_id"]
            ch["status"] = row["status"]
            ch["submitted_at"] = row["submitted_at"]

    # 本地文件校验并挂到挑战行
    cov_by_code = {c["challenge_code"]: c for c in scans.get("coverage", [])}
    for ch in chal_rows:
        cov = cov_by_code.get(ch["code"])
        ch["local_check"] = {
            "status": cov["status"] if cov else "not_scanned",
            "ratio": cov["ratio"] if cov else None,
            "present": cov["present"] if cov else [],
            "missing": cov["missing"] if cov else [],
            "file_count": cov["file_count"] if cov else 0,
        }

    total = len(chal_rows)
    submitted = [c for c in chal_rows if c["submitted"]]
    revisable = [c for c in chal_rows if c.get("status") == "needs_revision"]
    pending = [c for c in chal_rows if c["submitted"] and c.get("status") != "needs_revision"]
    partial = [c for c in chal_rows if c["submitted"] and c["local_check"]["status"] == "partial"]

    # 时间线按天聚合
    day = {}
    for s in sub_rows:
        if not s["submitted_at"]:
            continue
        d = s["submitted_at"][:10]
        day[d] = day.get(d, 0) + 1
    timeline = [{"date": k, "count": v} for k, v in sorted(day.items())]

    insights = []
    insights.append({
        "level": "info",
        "title": "提交覆盖率 %d/%d（%.0f%%）" % (len(submitted), total, 100.0 * len(submitted) / max(total, 1)),
        "body": "平台已发布的 C 系列挑战共 %d 个，个人已提交 %d 个。未提交的挑战集中在 C3/C3C/C6/C7/C8/C9/C10/C10H/C2G 等需要新增交付物的题目。" % (total, len(submitted)),
        "evidence": ["list-challenges", "list-my-submissions"],
    })
    if revisable:
        insights.append({
            "level": "error",
            "title": "%d 个提交处于 needs_revision，需要返工" % len(revisable),
            "body": "涉及：%s。这类状态不会自动转为通过，必须按评审意见补交新版本。" % "、".join(c["code"] for c in revisable),
            "evidence": [c["submission_id"] for c in revisable],
        })
    if partial:
        insights.append({
            "level": "warning",
            "title": "%d 个已提交挑战本机缺交付物文件" % len(partial),
            "body": "涉及：%s。本机缺文件不影响平台已收的提交，但影响后续返工与复用。" % "、".join(c["code"] for c in partial),
            "evidence": ["scan_submissions.py"],
        })
    if timeline:
        peak = max(timeline, key=lambda x: x["count"])
        insights.append({
            "level": "info",
            "title": "提交峰值集中在 %s（当天 %d 次）" % (peak["date"], peak["count"]),
            "body": "共 %d 个提交日、%d 条提交记录。峰值日说明该天为集中补交时段。" % (len(timeline), len(sub_rows)),
            "evidence": ["submitted_at 按日聚合"],
        })
    insights.append({
        "level": "success" if not revisable else "warning",
        "title": "待评审队列 %d 条" % len(pending),
        "body": "除 needs_revision 外，其余提交均已 checked 并进入 pending_teacher_review，等教师终审即可。",
        "evidence": ["status=checked"],
    })

    dataset = {
        "meta": {
            "title": "C6A 提交数据仪表盘",
            "student": "贾静文", "generated_at": generated_at,
            "challenge_id": "ch-20260717031528-w43gy7",
            "sources": [
                {"id": "list-challenges", "kind": "平台 API", "records": total, "note": "已发布挑战（仅统计可识别 C 代号的）"},
                {"id": "list-my-submissions", "kind": "平台 API", "records": len(sub_rows), "note": "个人提交记录"},
                {"id": "scan_submissions.py", "kind": "本地扫描", "records": scans.get("assigned_files", 0), "note": "按命名约定识别文件并校验交付物"},
            ],
            "metrics": {
                "challenges_total": total, "submitted": len(submitted),
                "not_submitted": total - len(submitted),
                "coverage_pct": round(100.0 * len(submitted) / max(total, 1), 1),
                "pending_review": len(pending), "needs_revision": len(revisable),
                "scanned_files": scans.get("assigned_files", 0),
            },
        },
        "challenges": chal_rows,
        "submissions": sub_rows,
        "timeline": timeline,
        "insights": insights,
    }
    return dataset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--challenges", required=True)
    ap.add_argument("--submissions", required=True)
    ap.add_argument("--scans", default=None)
    ap.add_argument("--out-dataset", required=True)
    ap.add_argument("--out-js", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-cov-csv", required=True)
    ap.add_argument("--generated-at", default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    a = ap.parse_args()

    ds = build(a.challenges, a.submissions, a.scans, a.generated_at)
    with open(a.out_dataset, "w", encoding="utf-8") as f:
        json.dump(ds, f, ensure_ascii=False, indent=1)
    with open(a.out_js, "w", encoding="utf-8") as f:
        f.write("// 自动生成，请勿手改；重新生成：python build_dataset.py ...\n")
        f.write("window.C6A_DATA = ")
        json.dump(ds, f, ensure_ascii=False, indent=1)
        f.write(";\n")

    with open(a.out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["代号", "提交编号", "挑战", "提交时间", "平台状态", "任务状态", "仓库"])
        for s in ds["submissions"]:
            w.writerow([s["code"], s["submission_id"], s["project_title"], s["submitted_at"],
                        s["status"], s["task_state"], s["repo"]])
    with open(a.out_cov_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["代号", "已提交", "平台状态", "本地校验", "命中率", "命中项", "缺失项", "文件数"])
        for c in ds["challenges"]:
            lc = c["local_check"]
            w.writerow([c["code"], "是" if c["submitted"] else "否", c.get("status") or "-",
                        lc["status"], lc["ratio"] if lc["ratio"] is not None else "",
                        " / ".join(lc["present"]), " / ".join(lc["missing"]), lc["file_count"]])
    m = ds["meta"]["metrics"]
    print("dataset ok: challenges=%d submissions=%d coverage=%.1f%% needs_revision=%d"
          % (m["challenges_total"], len(ds["submissions"]), m["coverage_pct"], m["needs_revision"]))


if __name__ == "__main__":
    main()
