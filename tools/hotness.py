#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 chenhz01 — see LICENSE, LICENSE-SPEC and NOTICE
"""hotness.py — check the hot-ready claims made in this repo's README.

Why this file is shipped inside every repo instead of living in a private
folder: the README says "run `python tools/hotness.py` and check me". A promise
that needs the author's laptop to verify is not a promise, it is a slogan.

What it does NOT promise
------------------------
It does not promise a Trending position. GitHub has never published how
Trending sorts repositories, so any repo selling you a guaranteed ranking is
telling you something it cannot know. This script checks 15 structural
properties that are known to hurt when missing. Passing them is necessary,
never sufficient.

Usage
-----
    python tools/hotness.py              # check the repo this file sits in
    python tools/hotness.py --repo DIR   # check another checkout
    python tools/hotness.py --json       # machine readable
    python tools/hotness.py --min 15     # exit 1 if the score is below N (default 15)
"""
import argparse
import json
import os
import re
import subprocess
import sys

STD = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()


def read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def git(repo, *args):
    try:
        r = subprocess.run(("git", "-C", repo) + args, capture_output=True, text=True, timeout=60)
        return r.stdout
    except Exception:
        return ""


# 自身识别用绝对路径，不用拼字符串 "tools/hotness.py"：
# 这个脚本可能被拷到仓根做临时体检，那时相对路径对不上，
# 它就会把自己数进 .py 总数，把上一秒刚断言过的「one file」变成假话。
_THIS = os.path.abspath(__file__)


def default_repo():
    """这个脚本自己认路。

    安装位是 <repo>/tools/hotness.py，此时仓根在上一级；也可能被临时拷到
    <repo>/ 根目录体检，此时仓根就是脚本所在目录。判据不用「路径里有没有
    tools 这个词」（换个安装位就废），而是看这个目录像不像一个门仓——
    门仓的铁特征是根上有 gate.py。
    """
    here = os.path.dirname(_THIS)
    for cand in (here, os.path.dirname(here)):
        if os.path.isfile(os.path.join(cand, "gate.py")):
            return cand
    return here


def py_files(repo, exclude_self=True):
    """数「这个门自己的代码」有几个 .py。

    排除三类：.git/__pycache__、examples/（示例数据不是源码）、
    以及**本文件自己**（hotness.py 是校验工具，不是门的一部分——
    不排除的话，检查器一落地就把自己刚断言过的「one file」变成假话）。
    """
    out = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in files:
            if not f.endswith(".py"):
                continue
            full = os.path.join(root, f)
            if exclude_self and os.path.abspath(full) == _THIS:
                continue
            out.append(full)
    return out


def imports_of(path):
    src = read(path)
    mods = set()
    # 单行内匹配：\s 会吃换行，把下一行函数名当模块名（曾经一次误报 13 个仓）
    for m in re.finditer(r"^[ \t]*(?:from[ \t]+([\w.]+)[ \t]+import|import[ \t]+([\w., \t]+))", src, re.M):
        for part in (m.group(1) or m.group(2)).split(","):
            name = part.strip().split(" ")[0].split(".")[0]
            if name:
                mods.add(name)
    return mods


def check(repo):
    readme = read(os.path.join(repo, "README.md"))
    gate = os.path.join(repo, "gate.py")
    rows = []

    def add(name, ok, ev):
        rows.append({"check": name, "ok": bool(ok), "evidence": ev})

    # 1 a sentence that names the disease
    m = re.search(r"<b>(.+?)</b>", readme, re.S)
    tag = (m.group(1).strip() if m else "")
    add("one_sentence", 0 < len(tag) <= 96, "%d chars" % len(tag))

    # 2 the command in the README is the command CI runs
    wf = read(os.path.join(repo, ".github", "workflows", "gate.yml")) + \
        read(os.path.join(repo, ".github", "workflows", "index.yml"))
    # 只取「真跑示例」那一条：workflow 里先有 `gate.py --help`，抓第一条会拿到 --help
    mw = re.search(r"python\s+(gate\.py[^\n]*?)\s*>\s*out\.txt", wf)
    mr = re.search(r"python\s+(gate\.py[^\n`]+)", readme)
    a = mw.group(1).strip() if mw else None
    b = mr.group(1).strip() if mr else None
    add("example_matches_run", bool(a) and a == b, "ci=%s | readme=%s" % ((a or "?")[:34], (b or "?")[:34]))

    # 3 the output block is a real run, not a mock
    add("real_output", "Real output" in readme and "```text" in readme, "Real output + text fence")

    # 4 no third-party imports (in-repo modules count as shipped)
    src_py = [p for p in py_files(repo) if os.sep + "examples" + os.sep not in p]
    third = set()
    if os.path.exists(gate):
        for mod in imports_of(gate):
            if mod in STD or mod.startswith("_"):
                continue
            if os.path.exists(os.path.join(repo, mod)) or os.path.exists(os.path.join(repo, mod + ".py")):
                continue
            third.add(mod)
    add("zero_deps", not third, "third-party: %s" % (sorted(third) or "none"))

    # 5 the subtitle's file count is true
    sub = (re.search(r"<sub>(.*?)</sub>", readme, re.S).group(1).strip()
           if re.search(r"<sub>(.*?)</sub>", readme, re.S) else "")
    n = len(py_files(repo))
    words = {1: "one", 2: "two", 3: "three"}
    add("surface_honest", sub.startswith(words.get(n, str(n)) + " file"),
        "subtitle=%r, actual=%d py" % (sub[:20], n))

    # 6 exit-code semantics documented
    add("exit_codes", "## Exit codes" in readme, "## Exit codes")

    # 7 honest limits
    add("honest_limits", "**not** do" in readme, "What it does **not** do")

    # 8 CI can actually fail
    add("ci_can_fail", ('if [ "$code" !=' in wf) or 'exit 1' in wf, "asserts exit code")

    # 9 pinnable version
    # 拿不到 tag 不等于「没有钉版本」：`git clone --depth 1` 和 GitHub 的
    # "Download ZIP" 都拿不到 tag，而这两种正是新读者最常用的方式。
    # 2026-10-20 实测：线上真跑一遍，浅克隆被判 14/15 并打印
    # "A claim on the README page is currently false" —— 检查器在自己的仓上
    # 诬告自己。读者的克隆方式不是作者的 bug，判据必须跟着证据可得性降级。
    tags = [t for t in git(repo, "tag", "--list").split() if t.startswith("v")]
    pin = re.search(r"@(v\d+\.\d+\.\d+)", readme)
    if tags:
        ok = bool(pin) and pin.group(1) in tags and ("@" + sorted(tags)[-1]) in readme
        ev = "tag %s" % sorted(tags)[-1]
        if not ok:
            ev += " (README pins %s)" % (pin.group(1) if pin else "nothing")
    else:
        # 只能判「README 里有没有一个形如 @vX.Y.Z 的钉子」，并明写证据不足的原因
        ok = bool(pin)
        ev = ("pinned %s" % pin.group(1) if pin else "no pin in README") + \
             " (no local tag list: shallow clone, ZIP download, or tags not fetched)"
    add("pinnable", ok, ev)

    # 10 license five-piece + SPDX on every source file
    lic = all(os.path.exists(os.path.join(repo, f)) for f in ("LICENSE", "LICENSE-SPEC", "NOTICE"))
    no_spdx = [os.path.basename(p) for p in src_py if "SPDX-License-Identifier" not in read(p)]
    add("license_complete", lic and not no_spdx, "missing SPDX: %s" % (no_spdx or "none"))

    # 11 shareable: card + topics
    card = os.path.join(repo, "assets", "social-preview.png")
    size = os.path.getsize(card) if os.path.exists(card) else 0
    topics = [t for t in read(os.path.join(repo, "topics.txt")).split() if t]
    add("shareable", size > 20000 and len(topics) >= 5, "card %dKB, %d topics" % (size // 1024, len(topics)))

    # 12 series entry map (symptom tree + full table)
    tree = ("Start here" in readme) or ("Which one do you need" in readme) or ("你现在卡在哪" in readme)
    table = ("## The gates" in readme) or ("## The fourteen gates" in readme) or ("## The 15 gates" in readme)
    add("series_map", tree and table, "tree=%s table=%s" % (tree, table))

    # 13 Chinese brief
    cjk = len(re.findall(r"[\u4e00-\u9fff]", readme))
    add("cn_brief", ("## 中文速览" in readme) or cjk >= 200, "%d CJK chars" % cjk)

    # 14 fixtures committed
    # 没有 git（ZIP 下载解压出来）时 ls-files 恒为空 —— 那不能说「fixture 没提交」，
    # 只能说「这个副本提供不了提交证据」。有 .git 时判据保持严格。
    tracked = [x for x in git(repo, "ls-files", "examples").splitlines() if x.strip()]
    if tracked:
        add("fixture_tracked", True, "%d file(s) tracked" % len(tracked))
    elif not os.path.isdir(os.path.join(repo, ".git")):
        on_disk = []
        for root, dirs, files in os.walk(os.path.join(repo, "examples")):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            on_disk += files
        add("fixture_tracked", len(on_disk) >= 1,
            "%d file(s) in examples/ (no .git here, so 'tracked' cannot be proven)" % len(on_disk))
    else:
        add("fixture_tracked", False, "0 file(s) tracked — examples/ is empty or ignored")

    # 15 byte-stable checkouts
    add("byte_stable", "-text" in read(os.path.join(repo, ".gitattributes")), ".gitattributes * -text")

    passed = sum(1 for r in rows if r["ok"])
    return {"repo": os.path.basename(os.path.abspath(repo)), "passed": passed,
            "total": len(rows), "score": round(100 * passed / len(rows)), "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=default_repo())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min", type=int, default=15)
    a = ap.parse_args()

    r = check(a.repo)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["passed"] >= a.min else 1

    print("repo: %s" % r["repo"])
    for x in r["rows"]:
        print("  [%s] %-20s %s" % ("o" if x["ok"] else "-", x["check"], x["evidence"]))
    print("\n%d/%d  (%d)" % (r["passed"], r["total"], r["score"]))
    if r["passed"] < r["total"]:
        print("A claim on the README page is currently false. That is a bug, not a preference.")
    return 0 if r["passed"] >= a.min else 1


if __name__ == "__main__":
    sys.exit(main())
