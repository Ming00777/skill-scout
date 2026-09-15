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

## 工作流程

> 以下命令均以**本 Skill 所在目录**为工作目录，路径用相对写法，任何 Agent 里都能直接跑。

### 第一步：读处境

先跑探测脚本，拿到当前 Agent 身份：

```bash
python3 scripts/detect_agent.py
```

脚本输出 JSON：`agent`（识别到的客户端）、`skill_dir`（该装到哪）、`confidence`、`candidates`（其他可能）。

脚本识别不出来时（豆包、Octo 这类云端客户端本机不留痕），**直接问用户一句**，不要猜。问完把答案记进 `references/agent-registry.md` 的自定义区，下次就不用再问。

同时读取项目处境作为推断依据：
- 当前工作目录的项目类型（看 `package.json` / `requirements.txt` / `Cargo.toml` 等）
- 最近改动的文件（`git log --oneline -10`、`git status --short`）
- 用户刚说的话里的情绪词和痛点词（"好丑"、"老是报错"、"太慢"、"每次都要"）

**边界要诚实**：读不到用户在别的 Agent 里的历史会话。处境推断只作为补充，**用户显式说出来的痛点永远优先于推断**。推断与用户表述冲突时，以用户为准。

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

GitHub 结果不足或质量差时，按顺序走兜底源：

```bash
curl -s "https://lightmake.site/api/v1/search?q=<关键词>&limit=10"   # SkillHub
npx skills find <关键词>                                              # Vercel Skills
npx clawhub search <关键词>                                            # ClawHub
```

官方精选源（质量最高，优先看）：`openai/skills` 仓库的 `skills/.curated` 目录。

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

**搜不到就直说**：

```
在 GitHub、SkillHub、ClawHub 都没找到匹配的。
我可以现在直接帮你做这件事，或者帮你写一个自定义 Skill——你说哪种。
```

绝对不要用记忆里的仓库名编一个出来。

## 用户确认后

用户选定才安装。安装时：

1. 按 `agent-registry.md` 的路径放到对应目录
2. 目标目录已存在同名 Skill 时，明确告知并让用户选：跳过 / 覆盖 / 改名
3. 装完验证：`ls <skill_dir>/<name>/SKILL.md`
4. 提醒用户重启会话才能加载新 Skill

## 参考文件

- `references/agent-registry.md` — 各 Agent 检测规则与 Skill 目录映射
- `references/search-playbook.md` — 检索式写法、评分权重、质量红线
- `references/security-checklist.md` — 安装前安全审计清单
