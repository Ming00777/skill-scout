#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_local_skills.py — 跨 Agent 能力调度：先在本机找现成的，找不到再去网上搜。

别的所有 Skill 推荐工具都是单一 Agent 视角（只扫自己那一个目录）。
本脚本因为掌握全部 Agent 的目录，能回答一个别人回答不了的问题：

    "你要的能力，你在另一个 Agent 里其实已经装过了。"

零依赖，只用标准库。**纯本地运行，无网络请求。**

用法：
    python3 scripts/sync_local_skills.py
    python3 scripts/sync_local_skills.py --match "ui design"
    python3 scripts/sync_local_skills.py --to "Claude Code"

输出三类结果：
    owned    当前 Agent 已经有了（别再推荐）
    gaps     其他 Agent 有、当前没有（优先推荐搬过来，附命令）
    drifts   同名 Skill 在多个 Agent 里内容不一致（版本漂移）
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from detect_agent import detect_by_env, detect_installed, expand  # noqa: E402

PROJECT_ROOT = Path.cwd()

# 项目级目录也纳入视野（优先级低于用户级）
PROJECT_DIRS = [
    ("项目级", PROJECT_ROOT / ".agents/skills"),
    ("项目级", PROJECT_ROOT / ".claude/skills"),
    ("项目级", PROJECT_ROOT / ".codex/skills"),
    ("项目级", PROJECT_ROOT / ".workbuddy/skills"),
]


def parse_frontmatter(text):
    """提取 SKILL.md 开头的 YAML frontmatter（轻量实现，同其他脚本）。"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None
    fm = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line[:1] in (" ", "\t") or not line.strip():
            i += 1
            continue
        if ":" not in line or line.strip().startswith("#"):
            i += 1
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v in (">", "|", ">-", "|-", ">+", "|+"):
            block = []
            i += 1
            while i < len(lines) and (lines[i][:1] in (" ", "\t") or not lines[i].strip()):
                if lines[i].strip():
                    block.append(lines[i].strip())
                i += 1
            fm[k] = " ".join(block)
            continue
        fm[k] = v.strip("\"'")
        i += 1
    return fm


def file_sha(path, length=12):
    """文件指纹，用于检测同名 Skill 的版本漂移。"""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:length]
    except OSError:
        return "unknown"


def scan_all():
    """扫描所有已知 Agent 目录，返回 {name: [ {agent, dir, path, hash, description} ]}"""
    targets = [(i["agent"], Path(i["skill_dir"])) for i in detect_installed()]
    targets += [(label, d) for label, d in PROJECT_DIRS]

    found = defaultdict(list)
    for agent, root in targets:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.name.startswith("."):
                continue
            skill_md = child / "SKILL.md"
            if not skill_md.is_file():
                continue
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm = parse_frontmatter(text) or {}
            name = fm.get("name") or child.name
            found[name].append({
                "agent": agent,
                "skill_dir": root / child.name,
                "path": str(skill_md),
                "hash": file_sha(skill_md),
                "description": (fm.get("description") or "")[:300],
            })
    return found


def resolve_current(args_to):
    """确定当前 Agent 及其 Skill 目录。"""
    if args_to:
        for item in detect_installed():
            if args_to.lower() in item["agent"].lower():
                return item["agent"], item["skill_dir"]
        # 当成目录用
        return args_to, args_to

    env = detect_by_env()
    if env:
        return env["agent"], env["skill_dir"]
    installed = detect_installed()
    if installed:
        return installed[0]["agent"], installed[0]["skill_dir"]
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", help="只保留与关键词相关的 Skill（空格分隔，任一命中即保留）")
    ap.add_argument("--to", help="目标 Agent 名或目录，默认自动探测当前 Agent")
    args = ap.parse_args()

    current_agent, current_dir = resolve_current(args.to)
    found = scan_all()

    if args.match:
        terms = [t.lower() for t in args.match.split() if t]
        found = {
            k: v for k, v in found.items()
            if any(t in (k + " " + v[0]["description"]).lower() for t in terms)
        }

    owned, gaps, drifts = [], [], []

    for name, locs in sorted(found.items()):
        here = [l for l in locs if current_agent and l["agent"] == current_agent]

        if here:
            owned.append({
                "name": name,
                "path": here[0]["path"],
                "description": locs[0]["description"],
            })
        else:
            src = locs[0]
            dest = current_dir or "<当前 Agent 的 skills 目录>"
            gaps.append({
                "name": name,
                "available_in": [l["agent"] for l in locs],
                "source": str(src["skill_dir"]),
                "description": src["description"],
                "suggested_command": "cp -R {} {}".format(src["skill_dir"], dest + "/"),
                "alt_command": "ln -s {} {}/{}".format(src["skill_dir"], dest, name),
            })

        hashes = {l["hash"] for l in locs}
        if len(locs) > 1 and len(hashes) > 1:
            drifts.append({
                "name": name,
                "versions": [{"agent": l["agent"], "hash": l["hash"], "path": l["path"]} for l in locs],
            })

    hint = ""
    if gaps:
        hint = ("本机已有 {} 个现成能力不在当前 Agent 里。**优先推荐搬过来**，"
                "别去网上搜一个没验证过的。命令给用户，别自动执行。").format(len(gaps))
    elif owned:
        hint = "当前 Agent 已有所需能力，直接告诉用户路径，不用再找。"
    else:
        hint = "本机没有现成的，去网上搜（第二步）。"

    print(json.dumps({
        "current_agent": current_agent,
        "current_skill_dir": current_dir,
        "owned_count": len(owned),
        "gap_count": len(gaps),
        "owned": owned,
        "gaps": gaps,
        "drifts": drifts,
        "hint": hint,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
