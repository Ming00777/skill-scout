#!/usr/bin/env bash
#
# install-to-other-agents.sh
#
# 把 skill-scout 分发到本机其他 Agent 的 skills 目录。
# 因为 SKILL.md 已是通用格式，无需改内容，复制目录即可。
#
# 用法：
#   bash install-to-other-agents.sh              # 只装到本机已存在的 Agent
#   bash install-to-other-agents.sh --all        # 全部目标都创建并安装
#   bash install-to-other-agents.sh --force      # 目标已存在时覆盖（覆盖前自动备份）
#
# 安全说明：本脚本不会静默删除任何目录。目标已存在时默认跳过；
# 只有显式传入 --force 才会先备份再覆盖。
#
set -uo pipefail

SRC="$HOME/.workbuddy/skills/skill-scout"
FORCE_ALL=0
FORCE_OVERWRITE=0

for arg in "$@"; do
  case "$arg" in
    --all)   FORCE_ALL=1 ;;
    --force) FORCE_OVERWRITE=1 ;;
    *)
      echo "未知参数：$arg" >&2
      echo "用法：bash install-to-other-agents.sh [--all] [--force]" >&2
      exit 2
      ;;
  esac
done

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "找不到源目录：$SRC" >&2
  exit 1
fi

# 目标目录 | 需要存在的前置目录（判断用户是否真的装了这个 Agent）| 显示名
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
failed=0

for entry in "${TARGETS[@]}"; do
  IFS='|' read -r dest prereq label <<< "$entry"

  if [ ! -d "$prereq" ] && [ "$FORCE_ALL" -eq 0 ]; then
    echo "跳过 $label（未检测到 $prereq）"
    skipped=$((skipped + 1))
    continue
  fi

  mkdir -p "$dest"

  # 目标已存在：默认跳过，绝不静默删除
  if [ -e "$dest/skill-scout" ]; then
    if [ "$FORCE_OVERWRITE" -eq 0 ]; then
      echo "已存在，跳过 $label（要覆盖请加 --force，会先备份）"
      skipped=$((skipped + 1))
      continue
    fi
    backup="$dest/skill-scout.bak.$(date +%Y%m%d%H%M%S)"
    mv "$dest/skill-scout" "$backup"
    echo "已备份原目录 -> $backup"
  fi

  if cp -R "$SRC" "$dest/skill-scout" && [ -f "$dest/skill-scout/SKILL.md" ]; then
    echo "已安装 -> $label : $dest/skill-scout"
    installed=$((installed + 1))
  else
    echo "安装失败 -> $label" >&2
    failed=$((failed + 1))
  fi
done

echo ""
echo "完成：安装 $installed 处，跳过 $skipped 处，失败 $failed 处。"
echo "提示：新装的 Skill 需要重启对应 Agent 的会话才会加载。"
[ "$failed" -gt 0 ] && exit 1
exit 0
