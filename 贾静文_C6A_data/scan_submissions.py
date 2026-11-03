# -*- coding: utf-8 -*-
"""C6A 提交扫描器（自动扫描 + 校验引擎）

用途：扫描一个或多个目录，识别「谁 / 哪个挑战 / 交了哪些文件」，
并按 challenges.json 里的 required_deliverables 判定每项是否命中。

命名约定（两种都支持，实测本机两种都存在）：
  A) 带前缀：贾静文_C5_AI日志.md   -> 学生=贾静文 挑战=C5
  B) 不带前缀，靠所在目录定身份：c5a-package/仓库分析.md
     目录名可含 C5A 代号 + 学生名（贾静文_C5A_GitHub入门与仓库理解）

用法：
  python scan_submissions.py --challenges challenges.json --out scans.json \
      --root "D:\\...\\c5-package" --root "C:\\...\\贾静文_C5A_GitHub入门与仓库理解"

输出 scans.json：
  {"roots":[...], "files":[{"rel","dir","name","size","student","challenge_code"}],
   "coverage":[{student,challenge_code,present:[...],missing:[...],ratio,file_count}],
   "unassigned":[...]}
"""
import argparse, json, os, re, sys

# 从挑战标题里抽代号：C1 / C2A / C4D / C10H ...
CODE_RE = re.compile(r"C\d{1,2}[A-Z]?")
# 学生名：本课程当前只有本人的提交可核验，支持少量分隔写法
STUDENT_RE = re.compile(r"^([\u4e00-\u9fa5]{2,4})(?=_|$)")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "neoskills-clone"}


def norm(text):
    """匹配用归一化：小写、去空白。"""
    return re.sub(r"\s+", "", str(text)).lower()


def load_challenges(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 兼容平台原始返回 {rc,stderr,json:{...}} 与已解包的 {challenges:[...]}
    if isinstance(data, dict) and isinstance(data.get("json"), (dict, list)):
        data = data["json"]
    chs = data["challenges"] if isinstance(data, dict) and "challenges" in data else data
    if isinstance(chs, dict):
        chs = []
    out = []
    for c in chs:
        title = c.get("title", "")
        codes = list(dict.fromkeys(CODE_RE.findall(title)))
        # T0 之类的测试挑战不参与覆盖率统计
        if not codes:
            continue
        raw = c.get("required_deliverables") or ""
        items = [s.strip() for s in raw.split(",") if s.strip()]
        reqs = []
        for it in items:
            literal = it.replace("*", "")
            reqs.append({"pattern": it, "label": literal, "required": True})
        out.append({
            "challenge_id": c.get("challenge_id"),
            "codes": codes,
            "title": title,
            "deadline": c.get("deadline"),
            "required": reqs,
        })
    return out


def pick_code(text, codes_by_len):
    """从一段文本里识别挑战代号，最长优先（C10H / C5A / C4D 不被 C1/C5/C4 抢走）。"""
    t = str(text).upper()
    for code in codes_by_len:
        if re.search(r"(?<![A-Z0-9])" + re.escape(code) + r"(?![A-Z0-9])", t):
            return code
    return None


def pick_student(text):
    m = STUDENT_RE.match(str(text))
    return m.group(1) if m else None


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--challenges", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", action="append", required=True)
    ap.add_argument("--default-student", default="贾静文")
    args = ap.parse_args()

    chals = load_challenges(args.challenges)
    code2chal = {}
    for c in chals:
        for code in c["codes"]:
            code2chal[code] = c
    codes_by_len = sorted(code2chal.keys(), key=len, reverse=True)

    files, unassigned = [], []
    for root in args.root:
        if not os.path.isdir(root):
            unassigned.append({"root": root, "reason": "目录不存在"})
            continue
        for path in walk(root):
            rel = os.path.relpath(path, root)
            name = os.path.basename(path)
            parent = os.path.basename(os.path.dirname(path))
            # 身份推断顺序：文件名前缀 > 直接父目录名 > 根目录名
            student = pick_student(name) or pick_student(parent) or pick_student(os.path.basename(root)) or args.default_student
            code = (pick_code(name, codes_by_len) or pick_code(rel, codes_by_len)
                    or pick_code(parent, codes_by_len) or pick_code(os.path.basename(root), codes_by_len))
            rec = {
                "root": root, "rel": rel.replace("\\", "/"), "name": name,
                "dir": parent, "size": os.path.getsize(path),
                "mtime": os.path.getmtime(path),
                "student": student, "challenge_code": code,
            }
            (files if code else unassigned).append(rec if code else {"rel": rec["rel"], "root": root, "reason": "无法识别挑战代号"})

    # 校验引擎：按挑战 requirements 判定命中/缺失
    buckets = {}
    for fr in files:
        buckets.setdefault((fr["student"], fr["challenge_code"]), []).append(fr)
    coverage = []
    for (student, code), frs in sorted(buckets.items()):
        chal = code2chal[code]
        names = [norm(f["name"]) for f in frs]
        present, missing = [], []
        for req in chal["required"]:
            target = norm(req["label"])
            hit = any(target in n for n in names)
            (present if hit else missing).append(req)
        total = len(chal["required"]) or 1
        coverage.append({
            "student": student, "challenge_code": code,
            "challenge_title": chal["title"], "challenge_id": chal["challenge_id"],
            "file_count": len(frs),
            "present": [r["label"] for r in present],
            "present_patterns": [r["pattern"] for r in present],
            "missing": [r["label"] for r in missing],
            "missing_patterns": [r["pattern"] for r in missing],
            "ratio": round(len(present) / total, 3),
            "status": "complete" if not missing else ("partial" if present else "empty"),
            "files": [f["rel"] for f in frs],
        })

    out = {
        "roots": args.root,
        "scanned_files": len(files) + len(unassigned),
        "assigned_files": len(files),
        "coverage": coverage,
        "unassigned": [u for u in unassigned if "rel" in u][:50],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("scanned=%d assigned=%d buckets=%d" % (out["scanned_files"], out["assigned_files"], len(coverage)))
    for cv in coverage:
        print("  %-6s %-5s ratio=%.2f missing=%s" % (cv["student"], cv["challenge_code"], cv["ratio"], cv["missing"] or "-"))


if __name__ == "__main__":
    main()
