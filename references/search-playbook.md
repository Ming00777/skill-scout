# 检索与评分手册

## 检源优先级

1. **GitHub 代码搜索**（主源）—— 直接命中 `filename:SKILL.md`，精准度远高于搜仓库名
2. **官方精选目录** —— `github.com/openai/skills` 的 `skills/.curated`，质量最高
3. **SkillHub** —— 语义搜索，支持中文，已打包可装
4. **Vercel Skills / ClawHub** —— 最后兜底

## GitHub 代码搜索写法

代码搜索**必须认证**，优先用已登录的 `gh`；没登录则退回匿名仓库搜索（精准度下降一个量级）。

```bash
# 主检索式：文件名 + 关键词（gh，需登录）
gh api "search/code?q=filename:SKILL.md+ui+design&per_page=20" \
  --jq '.items[] | {repo:.repository.full_name, path:.path, url:.html_url}'

# 加语言/路径限定，进一步去噪
gh api "search/code?q=filename:SKILL.md+frontend+path:skills&per_page=20"

# 退回：匿名仓库搜索（无需 token，结果较粗）
curl -s "https://api.github.com/search/repositories?q=SKILL.md+agent+skill+ui&sort=stars&per_page=10"
```

`scripts/search_github.py` 已封装上述逻辑，直接调用即可：

```bash
python3 {SKILL_DIR}/scripts/search_github.py "ui design frontend" --limit 15 --fetch-content
```

## 检索式构造

**中英双语都要跑**。中文 Skill 生态和英文生态几乎不重叠，只搜一边漏一半。

| 用户痛点 | 中文检索词 | 英文检索词 |
|---|---|---|
| UI 丑 / 界面难看 | 界面美化 前端设计 | ui design, frontend aesthetics, styling |
| 老是报错调不通 | 调试 排错 根因 | debugging, root cause, runtime debug |
| 重复劳动 | 脚手架 模板 生成 | scaffolding, boilerplate, code generation |
| 报告有 AI 味 | 去 AI 味 改写 降重 | humanize writing, rewrite, natural prose |
| 不会写测试 | 测试用例 覆盖率 | test generation, coverage, unit test |
| 代码要评审 | 代码审查 规范 | code review, lint, style check |

关键词控制在 **2-3 个**，多了反而搜不到。搜不到就减词，不要加词。

## 质量红线（命中即淘汰）

- 没有 `SKILL.md` 文件
- `SKILL.md` 缺 YAML frontmatter，或 frontmatter 里没有 `name` / `description`
- 仓库是 `awesome-*` 清单/合集类（它本身不是 Skill）
- 最后一次提交在 2 年以上（除非 star 极高且是公认经典）
- `description` 没写触发条件，Agent 无法自动匹配到它

## 评分权重（满分 100）

| 维度 | 分值 | 说明 |
|---|---|---|
| 意图匹配度 | 35 | frontmatter 的 `description` 命中最高，正文次之，仓库名最低 |
| 活跃度 | 20 | 90 天内有提交满分；1 年内 10 分；2 年 5 分 |
| 来源可信度 | 15 | 官方精选 / 知名组织满分；个人仓库看 star 和文档 |
| 文档完整度 | 15 | 有 When to Use + 分步 Instructions + 示例 |
| 热度 | 15 | star 数对数缩放，不是决定性因素 |

取 Top 3。**第 1 名必须给出"为什么是你的情况选它"的一句话理由。**

## 致命提醒

搜不到就是搜不到。**不许用记忆里的仓库名编一个出来**，不许猜 URL，不许把相似名字当成已验证存在的仓库。

输出前逐条确认：这个仓库我这次真的搜到了吗？链接是检索结果里给的吗？
