#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
list_local_skills.py — 扫描本机已安装的 Skill。

作用：推荐之前先跑它，避免推荐一个用户早就装过的东西。

零依赖，只用标准库。

用法：
    python3 scripts/list_local_skills.py
    python3 scripts/list_local_skills.py --match "ui design"   # 只看跟关键词相关的

输出 JSON：每个已装 skill 的 name / description / 所在 Agent / 路径。
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()
CWD = Path.cwd()

# Agent 名 -> 用户级 Skill 目录
USER_DIRS = [
    ("WorkBuddy", HOME / ".workbuddy/skills"),
    ("CodeBuddy", HOME / ".codebuddy/skills"),
    ("Claude Code", HOME / ".claude/skills"),
    ("Codex CLI", HOME / ".codex/skills"),
    ("TRAE 国际版", HOME / ".trae/skills"),
    ("TRAE 国内版", HOME / ".trae-cn/skills"),
    ("Cursor", HOME / ".cursor/skills"),
    ("OpenClaw", HOME / ".openclaw/skills"),
    ("通用开放位置", HOME / ".agents/skills"),
]

# 项目级 Skill 目录
PROJECT_DIRS = [
    ("项目级", CWD / ".agents/skills"),
    ("项目级", CWD / ".claude/skills"),
    ("项目级", CWD / ".codex/skills"),
    ("项目级", CWD / ".workbuddy/skills"),
    ("项目级", CWD / ".trae/skills"),
]


def parse_frontmatter(text):
    """提取 SKILL.md 开头的 YAML frontmatter（同 search_github.py 的轻量实现）。"""
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


def scan_dir(root, agent):
    """扫描一个 skills 目录下的所有 skill。"""
    found = []
    if not root.is_dir():
        return found

    for child in sorted(root.iterdir()):
        if child.name.startswith("."):
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            # 有些仓库把 SKILL.md 直接放在 skills/ 根，跳过即可
            continue
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = parse_frontmatter(text) or {}
        found.append({
            "name": fm.get("name") or child.name,
            "description": (fm.get("description") or "")[:300],
            "agent": agent,
            "path": str(skill_md),
        })
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", help="只保留与关键词相关的 skill（空格分隔，任一命中即保留）")
    args = ap.parse_args()

    skills = []
    scanned = []
    seen = set()

    for label, d in USER_DIRS + PROJECT_DIRS:
        if not d.is_dir():
            continue
        scanned.append(str(d))
        for item in scan_dir(d, label):
            key = (item["name"], item["agent"])
            if key in seen:
                continue
            seen.add(key)
            skills.append(item)

    if args.match:
        terms = [t.lower() for t in args.match.split() if t]
        skills = [
            s for s in skills
            if any(t in (s["name"] + s["description"]).lower() for t in terms)
        ]

    print(json.dumps({
        "count": len(skills),
        "scanned_dirs": scanned,
        "skills": skills,
        "hint": ("推荐新 Skill 前先比对这份清单。命中已有的就别再推荐了，"
                 "直接告诉用户'你已经装了 X'。" if skills else
                 "本机没发现已装的 Skill。"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
