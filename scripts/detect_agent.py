#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
detect_agent.py — 探测当前正在运行的 Agent，以及它的 Skill 安装目录。

零依赖，只用标准库。

用法：
    python3 detect_agent.py
    python3 detect_agent.py --json

输出 JSON：
    agent       识别到的 Agent 名（None 表示没识别出来）
    skill_dir   该 Agent 的全局 Skill 目录（绝对路径）
    confidence  high=环境变量命中（确凿） / medium=目录命中 / unknown=没识别出来
    reason      为什么这么判断
    installed   本机实际装了哪些 Agent
"""

import argparse
import json
import os
import sys
from pathlib import Path

HOME = Path.home()

# 环境变量命中 = 当前确实在这个 Agent 的运行时里，置信度最高
ENV_SIGNALS = [
    # (环境变量名, 命中值包含, Agent 名, Skill 目录)
    ("__CFBundleIdentifier", "codebuddy", "CodeBuddy", "~/.codebuddy/skills"),
    ("__CFBundleIdentifier", "workbuddy", "WorkBuddy", "~/.workbuddy/skills"),
    ("CLAUDECODE", "1", "Claude Code", "~/.claude/skills"),
    ("CLAUDE_CODE", "1", "Claude Code", "~/.claude/skills"),
    ("CODEX_SKILLS_DIR", None, "Codex CLI", "~/.codex/skills"),
    ("CODEX_CLI", "1", "Codex CLI", "~/.codex/skills"),
    ("CURSOR_TRACE_ID", None, "Cursor", "~/.cursor/skills"),
    ("TRAE_SKILLS_DIR", None, "TRAE", "~/.trae/skills"),
]

# 目录命中 = 本机装了，但不确定现在是不是在用它
DIR_SIGNALS = [
    ("~/.workbuddy", "WorkBuddy", "~/.workbuddy/skills"),
    ("~/.codebuddy", "CodeBuddy", "~/.codebuddy/skills"),
    ("~/.claude", "Claude Code", "~/.claude/skills"),
    ("~/.codex", "Codex CLI", "~/.codex/skills"),
    ("~/.trae-cn", "TRAE（国内版）", "~/.trae-cn/skills"),
    ("~/.trae", "TRAE（国际版）", "~/.trae/skills"),
    ("~/.cursor", "Cursor", "~/.cursor/skills"),
    ("~/.openclaw", "OpenClaw", "~/.openclaw/skills"),
    ("~/.agents", "通用开放位置", "~/.agents/skills"),
]


def expand(p):
    return str(HOME / p.replace("~/", "", 1)) if p.startswith("~/") else p


def detect_by_env():
    """环境变量优先——能命中说明当前确实运行在这个 Agent 里。"""
    for var, contains, agent, skill_dir in ENV_SIGNALS:
        val = os.environ.get(var)
        if not val:
            continue
        if contains is None or contains.lower() in val.lower():
            return {
                "agent": agent,
                "skill_dir": expand(skill_dir),
                "confidence": "high",
                "reason": "环境变量 {} 命中（{}）".format(var, val[:60]),
            }
    return None


def detect_installed():
    """列出本机装了哪些 Agent（只看目录是否存在）。"""
    found = []
    for d, agent, skill_dir in DIR_SIGNALS:
        if Path(expand(d)).exists():
            found.append({"agent": agent, "skill_dir": expand(skill_dir)})
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="输出纯 JSON（默认已为 JSON）")
    args = ap.parse_args()

    result = detect_by_env()
    installed = detect_installed()

    if result:
        result["installed"] = installed
        result["hint"] = "已确认当前 Agent，直接用 skill_dir 作为安装目标。"
    elif installed:
        # 没拿到运行时信号，就按目录命中的第一个猜，但标明置信度低
        top = installed[0]
        result = {
            "agent": top["agent"],
            "skill_dir": top["skill_dir"],
            "confidence": "medium",
            "reason": "未捕获运行时环境变量，按已安装目录猜测",
            "installed": installed,
            "hint": ("检测到本机装了多个 Agent：{}。向用户确认这次要装给哪一个，"
                     "不要直接假定。").format("、".join(i["agent"] for i in installed)),
        }
    else:
        result = {
            "agent": None,
            "skill_dir": None,
            "confidence": "unknown",
            "reason": "无环境变量命中，也无已知目录",
            "installed": [],
            "hint": ("识别不出当前 Agent（豆包、Octo 这类云端客户端本机不留痕）。"
                     "直接问用户：你用的是哪个 Agent？Skill 放哪个目录？"
                     "拿到答案后写入 references/agent-registry.md 的自定义区。"),
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["confidence"] != "unknown" else 2


if __name__ == "__main__":
    sys.exit(main())
