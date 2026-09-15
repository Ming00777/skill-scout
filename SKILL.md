---
name: skill-scout
description: 上下文感知的 Skill 推荐器。读取当前 Agent 身份与项目处境，理解用户卡点，去 GitHub 和公开注册表检索可用 Skill，评分排序后推荐 Top 3 并说明能解决到什么程度。当用户说"帮我找个 skill"、"装个能做 X 的技能"、"有没有解决 X 的 skill"、"UI 好丑有没有 skill"、"这种情况该装什么 skill"，或描述一个反复卡住的痛点并希望有现成能力包时使用。只推荐，不自动安装。
description_zh: "读懂你现在的处境，从全网找合适的 Skill 并推荐"
description_en: "Context-aware skill discovery and recommendation"
---

# Skill Scout

用户很难找到适合自己的 Skill——不是因为网上没有，而是因为**他不知道该搜什么词**，以及**搜到的东西在他的 Agent 上能不能跑**。本 Skill 解决这两件事。

## 核心原则（违反即失败）

1. **不许编造。** 只能推荐真实检索到的 Skill。搜不到就明说"没找到"，不要用记忆里的名字凑数，不要猜仓库地址。
2. **推荐完必须停下。** 输出卡片后等用户选择，不自动安装、不自动 clone、不自动改文件。
3. **必须说明"能解决到什么程度"。** 每条推荐都要写清楚预期效果和局限，禁止吹牛。
4. **必须先过安全审计。** 凡是带 `scripts/` 的、或内容里出现网络请求/文件读写的，安装前一律扫描并报告风险。
5. **处境数据不出本机。** 从 `git log`、文件内容、目录结构推断出的处境，**只在本地用来拼关键词**。发往任何外部接口的，只有你自己拼出来的那两三个关键词，绝不包含文件名、提交信息、代码片段、绝对路径。
6. **执行远程代码前必须问。** 任何会下载并执行第三方包的命令（`npx <pkg>`、`pip install`、`curl | bash`），执行前必须先告诉用户"这一步会下载并执行第三方包"，得到同意再跑。不许静默执行。

## 工作流程

> 以下命令均以**本 Skill 所在目录**为工作目录，路径用相对写法，任何 Agent 里都能直接跑。

### 第一步：读处境

按顺序做完这三件事，别跳步。

**1.1 先在本机找现成的**（最容易出彩，也最容易漏）

```bash
python3 scripts/sync_local_skills.py --match "<痛点关键词>"
```

它扫的是**全部** Agent 的目录，不只当前这个，返回三类结果：

| 结果 | 含义 | 动作 |
|---|---|---|
| `owned` | 当前 Agent 已经有 | 直接告诉用户"你已经装了 X，在 `<路径>`"，结束 |
| `gaps` | **别的 Agent 有、当前没有** | **优先推荐搬过来**，把 `suggested_command` 给用户 |
| `drifts` | 同名 Skill 在多个 Agent 里内容不一致 | 提示版本漂移，让用户决定以哪份为准 |

**先内后外**：本机已有的至少装得上、跑得起来，网上搜来的没验证过。只要 `gaps` 非空，
就先给搬运方案，用户不满意再去网上搜。

命令只给用户，**不要自动执行**。

**1.2 探测当前 Agent 身份**

```bash
python3 scripts/detect_agent.py
```

输出 `agent`（识别到的客户端）、`skill_dir`（该装到哪）、`confidence`、`installed`（本机装了哪些）。

识别不出来时（豆包、Octo 这类云端客户端本机不留痕），**直接问用户一句**，不要猜。问完把答案记进 `references/agent-registry.md` 的自定义区，下次就不用再问。

**1.3 分析项目技术栈**（用脚本确定性提取，别靠自由发挥）

```bash
python3 scripts/analyze_codebase.py
```

用它的 `summary` 和 `frameworks` 字段构造检索关键词。**只发这两项，别把文件名、路径、git 提交信息发出去。**

补充参考（不必每次都跑）：最近改动 `git log --oneline -10`、用户话里的情绪词（"好丑"、"老是报错"、"太慢"、"每次都要"）。

**边界要诚实**：读不到用户在别的 Agent 里的历史会话。处境推断只作为补充，**用户显式说出来的痛点永远优先于推断**。冲突时以用户为准。

### 第二步：翻译意图

用户说的话通常不能直接拿去搜。"UI 好丑"要扩成可检索的意图：

| 用户说法 | 扩成的检索意图 |
|---|---|
| UI 好丑 / 界面难看 | UI design, frontend aesthetics, styling, 界面美化 |
| 老是报错 / 调不通 | debugging, error diagnosis, root cause, 运行时调试 |
| 每次都要重写一遍 | scaffolding, code generation, template, 脚手架 |
| 报告一股 AI 味 | humanize writing, 去 AI 味, 改写 |
| 不知道怎么测 | test generation, coverage, 测试用例生成 |

**中英双语都要搜**，中文 Skill 生态和英文生态几乎不重叠，只搜一边会漏掉一半。

### 第三步：多源检索

```bash
python3 scripts/search_github.py "ui design frontend" --limit 15 --fetch-content
```

主源是 GitHub 代码搜索（直接命中 `filename:SKILL.md`，精准度远高于搜仓库名）。脚本优先用已登录的 `gh`，没有则退回匿名 API。

官方精选源（质量最高，优先看）：`openai/skills` 仓库的 `skills/.curated` 目录，直接用已认证的 `gh` 拉取，不外发数据。

GitHub 结果不足或质量差时，**才**走下面的兜底源。它们全都是第三方，用之前先跟用户说清楚：

```bash
# SkillHub — 第三方服务（lightmake.site）。只发送关键词本身，不发送任何项目内容。
curl -s "https://lightmake.site/api/v1/search?q=<关键词>&limit=10"

# 下面两条会从 npm 下载并执行第三方包
npx skills find <关键词>        # Vercel Skills
npx clawhub search <关键词>     # ClawHub
```

**跑 `npx` 之前必须先问用户**："这一步会从 npm 下载并执行第三方包，是否继续？"得到明确同意才执行。用户拒绝就用 GitHub 源的结果，或直接说明没找到。

详细检索与评分策略见 `references/search-playbook.md`。

### 第四步：评估与适配

对每个候选：

1. **过滤掉不能装的**：没有 SKILL.md、没有 YAML frontmatter（缺 `name`/`description`）、纯清单/合集类仓库、两年以上没更新。
2. **打分**：关键词匹配度 + star 数 + 更新时间 + 有无示例 + 文档完整度。具体权重见 playbook。
3. **安全审计**：按 `references/security-checklist.md` 逐项检查。
4. **适配判断**：告诉用户这个 Skill 在他的 Agent 上要放到哪个目录。因为 SKILL.md 已是通用格式，**绝大多数情况只需换目录，不用改内容**——直接把 `references/agent-registry.md` 里对应的路径给用户。

### 第五步：输出推荐卡

只给 **Top 3**，每张卡固定五栏：

```
1. [名称]（来源：owner/repo · ⭐ 1.2k · 更新于 2026-08）

   解决什么：一句话说清它干什么
   能解决到什么程度：能做到 X；但 Y 它管不了，Z 需要你自己补
   装上放哪：~/.codex/skills/xxx/（你的 Agent 是 Codex）
   安全提示：无脚本 / 含 1 个 Python 脚本，已扫描无外发请求
   安装命令：git clone https://github.com/... ~/.codex/skills/xxx
```

排序第一的那个，明确说一句"你的情况选第 1 个，因为……"。

**搜不到就直说，然后给两条路**：

```
在 GitHub、SkillHub、ClawHub 都没找到匹配的。

两条路：
1. 我直接帮你把这件事做了（适合一次性的任务）
2. 我帮你写个自定义 Skill（适合以后还会反复遇到的）

你说哪种？
```

用户选 2，就按 `references/authoring-checklist.md` 建。核心只有一条：**description 里必须写触发条件**，否则以后永远不会被自动触发，等于白写。

绝对不要用记忆里的仓库名编一个出来。

## 用户确认后

用户选定才安装。安装时：

1. 按 `agent-registry.md` 的路径放到对应目录
2. 目标目录已存在同名 Skill 时，明确告知并让用户选：跳过 / 覆盖 / 改名
3. 装完验证：`ls <skill_dir>/<name>/SKILL.md`
4. 提醒用户重启会话才能加载新 Skill

## 本 Skill 的对外请求清单

给自己也做一份审计，让用户和审计工具一眼看清哪里会联网：

| 位置 | 目标 | 发送内容 | 何时触发 |
|---|---|---|---|
| `scripts/search_github.py` | `api.github.com`（或经已认证的 `gh`） | 关键词、仓库名 | 每次检索，必需 |
| `scripts/detect_agent.py` | 无网络请求 | — | 纯本地探测 |
| 第三步兜底源：SkillHub | `lightmake.site`（**第三方**） | 关键词本身 | 仅 GitHub 结果不足时 |
| 第三步兜底源：`npx` 系列 | npm registry（**第三方**） | 包名，并执行其中代码 | 仅前两者都不足，**且需用户明确同意** |

**永不外发**：文件名、`git log` 提交信息、代码片段、绝对路径、环境变量内容。这些只在本地参与关键词构造。

## 参考文件

- `references/agent-registry.md` — 各 Agent 检测规则与 Skill 目录映射
- `references/search-playbook.md` — 检索式写法、评分权重、质量红线
- `references/security-checklist.md` — 安装前安全审计清单
- `references/authoring-checklist.md` — 找不到现成 Skill 时，自建的实操要点
