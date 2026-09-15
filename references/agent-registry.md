# Agent 检测与 Skill 目录映射

## 关键事实：SKILL.md 已是事实标准

Codex、Claude Code、TRAE、OpenClaw、WorkBuddy 用的都是同一个格式：

```
skill-name/
  SKILL.md          # 必需，YAML frontmatter: name + description
  scripts/          # 可选
  references/       # 可选
  assets/           # 可选
```

**差异基本只在"放哪个目录"**，不做格式转换。所以推荐时的适配工作 = 给用户正确的目标路径。

## 官方精选源

| 来源 | 地址 | 说明 |
|---|---|---|
| OpenAI 官方目录 | `github.com/openai/skills` | `skills/.curated` 是精选，`skills/.experimental` 是实验。质量最高，优先看这里 |
| Codex 内置安装器 | `$skill-installer` | Codex 里可直接按名安装官方目录里的 skill |

## 检测规则（按优先级匹配）

| Agent | 检测信号 | 全局 Skill 目录 | 项目级目录 | 调用方式 |
|---|---|---|---|---|
| WorkBuddy | `$__CFBundleIdentifier` 含 `workbuddy`，或 `~/.workbuddy` 存在 | `~/.workbuddy/skills/` | `.workbuddy/skills/` | 自动匹配 / 显式调用 |
| CodeBuddy | `$__CFBundleIdentifier` 含 `codebuddy` | `~/.codebuddy/skills/` | `.codebuddy/skills/` | 同上 |
| Codex CLI | `~/.codex` 存在 | `~/.codex/skills/` | `.codex/skills/` | `$skill-name` 或 `/skills` 浏览 |
| Claude Code | `~/.claude` 存在，或 `$CLAUDECODE` 非空 | `~/.claude/skills/` | `.claude/skills/` | `/skill-name` |
| TRAE（国际版） | `~/.trae` 存在 | `~/.trae/skills/` | `.trae/skills/{name}/SKILL.md` | 对话中显式引用 |
| TRAE（国内版） | `~/.trae-cn` 存在 | `~/.trae-cn/skills/` | `.trae/skills/{name}/SKILL.md` | 同上 |
| Cursor | `~/.cursor` 存在 | `~/.cursor/skills/` | `.cursor/rules/*.mdc` | 自动 / `@` 引用 |
| OpenClaw | `~/.openclaw` 存在 | `~/.openclaw/skills/` | `.openclaw/skills/` | 同 Claude |
| 通用开放位置 | — | `~/.agents/skills/` | `.agents/skills/` | TRAE、Cursor 等均已支持这个开放标准位置 |

## 本机不留痕的客户端（必须问用户）

以下客户端在本机没有可探测的痕迹，自动识别会失败，**不要猜，直接问**：

| 客户端 | 情况 | 处理 |
|---|---|---|
| 豆包（通用 AI 助手） | App/Web 形态，不支持本地 Skill 文件 | 告知用户不适用；若他指的是 TRAE SOLO 或 MarsCode，走 TRAE 规则 |
| Octo / OctoBody（明略科技） | 云端人机协作产品，Skill 是云端沉淀资产，无本机标准目录 | 问用户："你的 Skill 放在哪个目录？"拿到后记入下方自定义区 |
| 其他云端 Agent | 同上 | 同上 |

## 多 Agent 共存

一个人机器上往往同时装了好几个 Agent。检测到多个时：

1. 取**当前运行时**那个（环境变量命中优先于目录存在）
2. 都是目录命中的话，按上表顺序取第一个
3. 仍然不确定就问用户："检测到你装了 X 和 Y，这次要装给哪个？"

## 一次安装，多处可用

`.agents/skills/` 是跨 Agent 开放标准位置。如果目标 Agent 支持，可以只装一份再软链：

```bash
ln -s ~/.agents/skills/<name> ~/.codex/skills/<name>
ln -s ~/.agents/skills/<name> ~/.claude/skills/<name>
```

---

## 自定义区（用户补充，探测到就写这里）

<!-- 用户手动指定的 Agent 与目录，格式：
| Agent 名 | 检测信号 | Skill 目录 |
-->

| Octo（明略） | 待用户确认 | 待用户确认 |
