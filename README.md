# skill-scout

你在 Codex 里装过的好用 Skill，换到 WorkBuddy 就用不上了。

skill-scout 的第一步不是去网上搜，而是**先把你本机所有 Agent 已装的 Skill 扫一遍**——你要的东西大概率机器上已经有了。扫完没有，才去 GitHub 找，最后给你一条能直接粘贴的安装命令。

<!-- TODO: 在这里放一张 15-30 秒的终端录屏 GIF -->

**一句话**：别急着搜，先看看你机器上已经有了什么。

## 30 秒装上

```bash
npx skills add Ming00777/skill-scout
```

## 它解决什么

你很难找到适合自己的 Skill——不是因为网上没有，而是三个具体障碍：

1. **不知道该搜什么词**。"UI 好丑"拿去搜 GitHub 搜不出东西。
2. **不知道搜到的东西在自己的 Agent 上能不能跑**。Codex、Claude Code、TRAE 的 Skill 目录各不相同。
3. **你在 A 里装的能力，在 B 里用不上**。多数人装了四五个 Agent，各自的 Skill 互不相通——
   明明 Codex 里就有个官方 `frontend-design`，在 WorkBuddy 里做界面却够不着。

skill-scout 的处理顺序是**先内后外**：

1. 先扫本机**全部** Agent 的目录，找到现成的就直接给搬运命令（本机已有的至少装得上、跑得起来）
2. 本机没有，才去 GitHub 和公开注册表检索
3. 评分后给出 Top 3，并告诉你**能解决到什么程度**、**该装到哪个目录**

## 支持的 Agent

| Agent | Skill 目录 |
|---|---|
| WorkBuddy | `~/.workbuddy/skills/` |
| CodeBuddy | `~/.codebuddy/skills/` |
| Codex CLI | `~/.codex/skills/` |
| Claude Code | `~/.claude/skills/` |
| TRAE 国际版 | `~/.trae/skills/` |
| TRAE 国内版 | `~/.trae-cn/skills/` |
| OpenClaw | `~/.openclaw/skills/` |
| 通用开放位置 | `~/.agents/skills/` |

`SKILL.md` 已是跨 Agent 的事实标准，格式一致，**差异只在放哪个目录**。豆包等纯云端助手不支持本地 Skill；Octo 这类云端协作产品会主动询问你目录，答过一次就记住。

## 安装

**方式一：Skills CLI**

```bash
npx skills add Ming00777/skill-scout
```

**方式二：让 Agent 安装**

把下面这句话直接丢给你的 Agent：

```
安装这个 Skill: https://github.com/Ming00777/skill-scout
```

**方式三：手动 clone 到指定 Agent 目录**

```bash
# WorkBuddy
git clone https://github.com/Ming00777/skill-scout.git ~/.workbuddy/skills/skill-scout

# Codex CLI
git clone https://github.com/Ming00777/skill-scout.git ~/.codex/skills/skill-scout

# Claude Code
git clone https://github.com/Ming00777/skill-scout.git ~/.claude/skills/skill-scout

# TRAE 国内版
git clone https://github.com/Ming00777/skill-scout.git ~/.trae-cn/skills/skill-scout
```

装完**重启 Agent 会话**才会加载。

已经装过一份、想分发到本机其他 Agent：在仓库目录跑 `bash install-to-other-agents.sh`。

该脚本**不会静默删除任何目录**。目标已存在时默认跳过；只有显式加 `--force` 才会覆盖，且覆盖前自动备份原目录。

## 前置要求

- Python 3（脚本零依赖，只用标准库）
- **推荐**：安装并登录 GitHub CLI。登录后能走代码搜索，直接命中 `SKILL.md` 文件，检索精准度比匿名 API 高一个量级。

```bash
brew install gh      # macOS；Windows: winget install GitHub.cli
gh auth login
```

没登录也能用，会自动退回匿名仓库搜索，只是结果粗一些。

## 用法

在任意一个支持的 Agent 里直接说：

> 我在做前端界面，一直觉得很丑，帮我找个适合现在情况的 Skill

它会自己完成：扫本机全部 Agent 找现成的 → 探测 Agent → 分析技术栈 → 翻译意图 → 检索 → 评分 → 安全审计 → 出推荐卡，**然后停下来等你选**。

找不到现成的，会建议你自建一个，并给出建法要点。

## 目录结构

```
skill-scout/
  SKILL.md                         主入口，五步流程
  references/
    agent-registry.md              Agent 检测规则与目录映射
    search-playbook.md             检索式写法、评分权重、质量红线
    security-checklist.md          安装前安全审计清单
  scripts/
    detect_agent.py                探测当前 Agent（零依赖）
    search_github.py               GitHub 检索（gh 优先，匿名兜底）
    list_local_skills.py           扫描本机已装 Skill
    sync_local_skills.py           跨 Agent 能力调度：找本机现成的 + 版本漂移检测
    analyze_codebase.py            确定性提取项目技术栈（纯本地，无网络）
  install-to-other-agents.sh       分发到本机其他 Agent
```

## 隐私与网络请求

本 Skill 会联网，但**只发检索关键词，不发你的项目内容**。完整清单：

| 位置 | 目标 | 发送内容 | 何时触发 |
|---|---|---|---|
| `scripts/search_github.py` | `api.github.com`（或经已认证的 `gh`） | 关键词、仓库名 | 每次检索，必需 |
| `scripts/detect_agent.py` | 无网络请求 | — | 纯本地探测 |
| SKILL.md 兜底源：SkillHub | `lightmake.site`（第三方） | 关键词本身 | 仅 GitHub 结果不足时 |
| SKILL.md 兜底源：`npx` 系列 | npm registry（第三方） | 包名，并执行其中代码 | 仅前两者都不足，**且需你明确同意** |

**永不外发**：文件名、`git log` 提交信息、代码片段、绝对路径、环境变量内容。这些只在本地参与关键词构造。

两条硬规则：

- 任何会下载并执行第三方包的命令（`npx <pkg>`、`curl | bash`），执行前必须告知并取得同意，不许静默执行。
- 本仓库的 `scripts/` 下只有两个 Python 文件，无 shell 管道执行、无凭据读取、无混淆代码。

## 四条设计原则

1. **不编造**——只推荐真实检索到的 Skill，搜不到就明说，绝不用记忆里的仓库名凑数。
2. **推荐后停下**——不自动安装、不自动 clone。
3. **说明能解决到什么程度**——每条推荐都要写局限，不吹牛。
4. **安装前必须安全审计**——Skill 是用你的权限执行的代码，`curl | bash`、读 `~/.ssh` 这类一律拦下。

## License

MIT
