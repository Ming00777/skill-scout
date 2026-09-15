#!/usr/bin/env bash
#
# install-to-other-agents.sh
#
# 把 skill-scout 分发到本机其他 Agent 的 skills 目录。
# 因为 SKILL.md 已是通用格式，无需改内容，复制目录即可。
#
# 用法：
#   bash install-to-other-agents.sh          # 只装到本机已存在的 Agent
#   bash install-to-other-agents.sh --all    # 全部目标都创建并安装
#
set -uo pipefail

SRC="$HOME/.workbuddy/skills/skill-scout"
FORCE_ALL=0
[ "${1:-}" = "--all" ] && FORCE_ALL=1

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "找不到源目录：$SRC" >&2
  exit 1
fi

# 目标目录 -> 需要存在的前置目录（用来判断用户是否真的装了这个 Agent）
TARGETS=(
  "$HOME/.claude/skills|$HOME/.claude|Claude Code"
  "$HOME/.codex/skills|$HOME/.codex|Codex CLI"
  "$HOME/.trae/skills|$HOME/.trae|TRAE 国际版"
  "$HOME/.trae-cn/skills|$HOME/.trae-cn|TRAE 国内版"
  "$HOME/.openclaw/skills|$HOME/.openclaw|OpenClaw"
  "$HOME/.agents/skills|$HOME/.agents|通用开放位置"
)

installed=0
skipped=0

for entry in "${TARGETS[@]}"; do
  IFS='|' read -r dest prereq label <<< "$entry"

  if [ ! -d "$prereq" ] && [ "$FORCE_ALL" -eq 0 ]; then
    echo "跳过 $label（未检测到 $prereq）"
    skipped=$((skipped + 1))
    continue
  fi

  mkdir -p "$dest"
  rm -rf "$dest/skill-scout"
  cp -R "$SRC" "$dest/skill-scout"

  if [ -f "$dest/skill-scout/SKILL.md" ]; then
    echo "已安装 -> $label : $dest/skill-scout"
    installed=$((installed + 1))
  else
    echo "安装失败 -> $label" >&2
  fi
done

echo ""
echo "完成：安装 $installed 处，跳过 $skipped 处。"
echo "提示：新装的 Skill 需要重启对应 Agent 的会话才会加载。"
