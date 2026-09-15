#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_codebase.py — 确定性分析当前项目的技术栈。

作用：把「读处境」从"让 Agent 自由看"变成脚本提取，结果稳定、可复现。

零依赖，只用标准库。**纯本地运行，无任何网络请求。**

用法：
    python3 scripts/analyze_codebase.py
    python3 scripts/analyze_codebase.py /path/to/project

输出 JSON：语言分布、配置文件、检测到的框架、是否有测试/CI/Docker。
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

# 扫描时跳过的目录（避免扫进依赖目录导致巨慢）
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", "target", "vendor", ".idea", ".vscode",
    "site-packages", ".gradle", ".mypy_cache", ".pytest_cache", "coverage",
    ".terraform", "Pods", "DerivedData",
}

MAX_FILES = 8000  # 大仓库保护

EXT_LANG = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript/React", ".jsx": "JavaScript/React", ".java": "Java",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".cs": "C#",
    ".c": "C", ".cpp": "C++", ".swift": "Swift", ".kt": "Kotlin",
    ".scala": "Scala", ".sh": "Shell", ".html": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".vue": "Vue", ".svelte": "Svelte", ".sql": "SQL",
    ".lua": "Lua", ".r": "R", ".m": "Objective-C", ".dart": "Dart",
}

# 配置文件 -> 生态
CONFIG_SIGNALS = {
    "package.json": "Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Pipfile": "Python",
    "setup.py": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java/Maven",
    "build.gradle": "Java/Gradle",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "Package.swift": "Swift",
    "Podfile": "iOS",
}

# 依赖名 -> 框架/工具（用于从依赖表推断技术栈）
FRAMEWORK_HINTS = {
    "react": "React", "react-dom": "React", "next": "Next.js",
    "vue": "Vue", "nuxt": "Nuxt", "svelte": "Svelte", "sveltekit": "SvelteKit",
    "angular": "Angular", "express": "Express", "koa": "Koa",
    "tailwindcss": "Tailwind CSS", "sass": "Sass", "vite": "Vite",
    "webpack": "Webpack", "typescript": "TypeScript",
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
    "pandas": "pandas", "numpy": "numpy", "scipy": "SciPy",
    "torch": "PyTorch", "tensorflow": "TensorFlow", "sklearn": "scikit-learn",
    "requests": "requests", "sqlalchemy": "SQLAlchemy",
    "pytest": "pytest", "jest": "Jest", "vitest": "Vitest",
    "playwright": "Playwright", "cypress": "Cypress", "selenium": "Selenium",
    "opencv-python": "OpenCV", "pillow": "Pillow",
    "spring-boot": "Spring Boot", "redux": "Redux", "pinia": "Pinia",
    "electron": "Electron", "tauri": "Tauri", "react-native": "React Native",
}


def read_json_safe(path):
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def extract_deps(root):
    """从常见依赖清单里提取依赖名。"""
    deps = set()

    pkg = root / "package.json"
    if pkg.is_file():
        data = read_json_safe(pkg)
        if isinstance(data, dict):
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                for name in (data.get(key) or {}):
                    deps.add(str(name).lower())

    req = root / "requirements.txt"
    if req.is_file():
        try:
            for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.split("#")[0].strip()
                if not line or line.startswith("-"):
                    continue
                name = re.split(r"[=<>!~\[; ]", line)[0].strip()
                if name:
                    deps.add(name.lower())
        except OSError:
            pass

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'^\s*"([A-Za-z0-9_.\-]+)', text, re.M):
                deps.add(m.group(1).lower().split(">=")[0].split("==")[0])
        except OSError:
            pass

    return deps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=".", help="要分析的项目路径，默认当前目录")
    args = ap.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(json.dumps({"error": "不是有效目录: {}".format(root)}, ensure_ascii=False))
        return 1

    ext_counter = Counter()
    file_count = 0
    truncated = False

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if file_count >= MAX_FILES:
                truncated = True
                break
            file_count += 1
            ext = Path(fn).suffix.lower()
            if ext:
                ext_counter[ext] += 1
        if truncated:
            break

    top_ext = [[ext, n] for ext, n in ext_counter.most_common(8)]
    languages = []
    for ext, _ in top_ext:
        lang = EXT_LANG.get(ext)
        if lang and lang not in languages:
            languages.append(lang)

    configs = [name for name in CONFIG_SIGNALS if (root / name).is_file()]
    ecosystems = sorted({CONFIG_SIGNALS[c] for c in configs})

    deps = extract_deps(root)
    frameworks = sorted({FRAMEWORK_HINTS[d] for d in deps if d in FRAMEWORK_HINTS})

    has_tests = any(
        (root / d).is_dir() for d in ("tests", "test", "__tests__", "spec")
    ) or bool(re.search(r"test", " ".join(deps)))
    has_ci = (root / ".github/workflows").is_dir() or (root / ".gitlab-ci.yml").is_file()
    has_docker = (root / "Dockerfile").is_file() or (root / "docker-compose.yml").is_file()

    parts = []
    if ecosystems:
        parts.append("、".join(ecosystems[:3]))
    if frameworks:
        parts.append("、".join(frameworks[:4]))
    if languages:
        parts.append("主要语言 " + "、".join(languages[:3]))
    summary = "；".join(parts) if parts else "未能识别出明确技术栈"

    print(json.dumps({
        "path": str(root),
        "file_count": file_count,
        "truncated": truncated,
        "top_extensions": top_ext,
        "languages": languages[:5],
        "configs_found": configs,
        "ecosystems": ecosystems,
        "frameworks": frameworks,
        "has_tests": has_tests,
        "has_ci": has_ci,
        "has_docker": has_docker,
        "summary": summary,
        "hint": "把 summary 和 frameworks 转成检索关键词，别把文件名和路径发出去。",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
