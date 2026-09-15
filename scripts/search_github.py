#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_github.py — 检索 GitHub 上真实存在的 Skill（含 SKILL.md 的仓库）。

零依赖，只用标准库。优先用已登录的 gh（可走代码搜索，精准）；
gh 不可用或未登录时退回匿名 API（只能搜仓库，精准度下降）。

用法：
    python3 search_github.py "ui design frontend"
    python3 search_github.py "调试 排错" --limit 20
    python3 search_github.py "code review" --fetch-content

输出 JSON 到 stdout。错误写到 stderr 并以退出码 1 结束。
"""

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "skill-scout/1.0"}


def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 1, "", str(e)


def gh_ready():
    """gh 是否存在且已登录。"""
    if not shutil.which("gh"):
        return False
    code, _, _ = run(["gh", "auth", "status"], timeout=15)
    return code == 0


def search_code(query, limit):
    """代码搜索：直接命中 SKILL.md 文件。需认证。"""
    q = "filename:SKILL.md {}".format(query)
    url = "search/code?q={}&per_page={}".format(
        urllib.parse.quote(q), min(limit, 100)
    )
    code, out, err = run(["gh", "api", url], timeout=40)
    if code != 0:
        return None, err.strip()
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        return None, "解析失败: {}".format(e)

    results = []
    seen = set()
    for item in data.get("items", []):
        repo = item.get("repository", {})
        full = repo.get("full_name")
        path = item.get("path")
        key = (full, path)
        if not full or key in seen:
            continue
        seen.add(key)
        results.append({
            "full_name": full,
            "path": path,
            "file_url": item.get("html_url"),
            "repo_url": repo.get("html_url"),
            "stars": repo.get("stargazers_count", 0),
            "updated_at": repo.get("updated_at"),
            "repo_description": (repo.get("description") or "")[:200],
            "default_branch": repo.get("default_branch", "main"),
        })
    return results, None


def search_repos(query, limit):
    """仓库搜索：gh 可用则走 gh，否则匿名 API。精准度低于代码搜索。"""
    q = "SKILL.md agent skill {}".format(query)
    url = "https://api.github.com/search/repositories?q={}&sort=stars&per_page={}".format(
        urllib.parse.quote(q), min(limit, 100)
    )

    items, source = None, None
    if shutil.which("gh"):
        code, out, _ = run(["gh", "api", "search/repositories?q={}&sort=stars&per_page={}".format(
            urllib.parse.quote(q), min(limit, 100))], timeout=40)
        if code == 0:
            try:
                items = json.loads(out).get("items", [])
                source = "gh-repo-search"
            except json.JSONDecodeError:
                items = None
    if items is None:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                items = json.loads(r.read().decode()).get("items", [])
            source = "anonymous-repo-search"
        except Exception as e:
            return None, "仓库搜索失败: {}".format(e)

    results = []
    for repo in items:
        results.append({
            "full_name": repo.get("full_name"),
            "path": "SKILL.md",
            "file_url": "{}/blob/{}/SKILL.md".format(
                repo.get("html_url", ""), repo.get("default_branch", "main")),
            "repo_url": repo.get("html_url"),
            "stars": repo.get("stargazers_count", 0),
            "updated_at": repo.get("updated_at"),
            "repo_description": (repo.get("description") or "")[:200],
            "default_branch": repo.get("default_branch", "main"),
        })
    return results, source


def fetch_content(item, max_chars=3000):
    """拉取 SKILL.md 内容，并提取 frontmatter 的 name / description。"""
    endpoint = "repos/{}/contents/{}".format(item["full_name"], item["path"])
    code, out, err = run(["gh", "api", endpoint], timeout=30)
    if code != 0:
        item["content_error"] = err.strip()[:200]
        return item
    try:
        payload = json.loads(out)
        raw = base64.b64decode(payload.get("content", "")).decode("utf-8", "replace")
    except Exception as e:
        item["content_error"] = str(e)[:200]
        return item

    item["content"] = raw[:max_chars]
    fm = parse_frontmatter(raw)
    if fm:
        item["skill_name"] = fm.get("name")
        item["skill_description"] = fm.get("description")
    item["has_frontmatter"] = bool(fm)
    return item


def parse_frontmatter(text):
    """
    提取 SKILL.md 开头的 YAML frontmatter。

    只做轻量解析：支持 `key: value`，以及 `key: >` / `key: |` 折叠块
    （真实仓库里 description 常写成折叠块，不处理会解析出一个孤立的 ">"）。
    嵌套缩进的键（如 metadata.author）直接跳过，本脚本只关心顶层的
    name / description。
    """
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None

    fm = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # 缩进行属于嵌套结构，跳过
        if line[:1] in (" ", "\t") or not line.strip():
            i += 1
            continue
        if ":" not in line or line.strip().startswith("#"):
            i += 1
            continue

        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()

        if v in (">", "|", ">-", "|-", ">+", "|+"):
            # 折叠 / 字面块：收集后续所有缩进行
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


def enrich_repo_info(items, max_n=12):
    """
    补全 star 数与更新时间。

    GitHub 代码搜索返回的 repository 对象是精简版，不含 stargazers_count
    和 updated_at，直接读会得到一堆 0，无法参与评分。这里回查仓库接口补上。
    """
    for item in items[:max_n]:
        if item.get("stars") and item.get("updated_at"):
            continue
        code, out, _ = run(["gh", "api", "repos/{}".format(item["full_name"])], timeout=20)
        if code != 0:
            continue
        try:
            repo = json.loads(out)
        except json.JSONDecodeError:
            continue
        item["stars"] = repo.get("stargazers_count", item.get("stars", 0))
        item["updated_at"] = repo.get("updated_at", item.get("updated_at"))
        item["default_branch"] = repo.get("default_branch", item.get("default_branch", "main"))
        if not item.get("repo_description"):
            item["repo_description"] = (repo.get("description") or "")[:200]
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="检索关键词，2-3 个为宜")
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--fetch-content", action="store_true",
                    help="拉取 SKILL.md 正文与 frontmatter，便于评分和安全审计")
    args = ap.parse_args()

    results, err = None, None
    source = None

    if gh_ready():
        results, err = search_code(args.query, args.limit)
        source = "gh-code-search"

    if not results:
        results, tmp = search_repos(args.query, args.limit)
        if isinstance(tmp, str) and tmp.startswith("仓库搜索失败"):
            print(json.dumps({"error": tmp, "detail": err or ""},
                             ensure_ascii=False, indent=2))
            return 1
        source = tmp or source

    if not results:
        print(json.dumps({
            "query": args.query,
            "source": source,
            "count": 0,
            "results": [],
            "note": "没搜到。不要编造仓库名——如实告诉用户没找到。",
        }, ensure_ascii=False, indent=2))
        return 0

    results = enrich_repo_info(results[:args.limit])
    if args.fetch_content and gh_ready():
        for item in results:
            fetch_content(item)

    print(json.dumps({
        "query": args.query,
        "source": source,
        "count": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
