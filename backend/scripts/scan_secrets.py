import argparse
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = (
    "backend/app",
    "backend/scripts",
    "backend/tests",
    "frontend/src",
    "deploy",
    "docs",
)
ROOT_FILES = (
    "VERSION",
    ".env.example",
    "AGENTS.md",
    "CHANGELOG.md",
    "ROADMAP.md",
    "SECURITY.md",
    "TASKS.md",
    "TESTING.md",
    "backend/requirements-audit.txt",
    "backend/requirements.txt",
    "frontend/eslint.config.js",
    "frontend/index.html",
    "frontend/package.json",
    "frontend/public/favicon.svg",
    "frontend/README.md",
    "frontend/vite.config.js",
)
TEXT_SUFFIXES = {
    ".conf",
    ".css",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".ps1",
    ".py",
    ".service",
    ".toml",
    ".xml",
    ".yaml",
    ".yml",
}
IGNORED_NAMES = {"package-lock.json"}
PLACEHOLDER_WORDS = {
    "change-me",
    "example",
    "placeholder",
    "redacted",
    "sample",
    "test",
    "your-",
}
RULES = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b")),
    ("google-api-key", re.compile(r"\bAIza[A-Za-z0-9_-]{30,}\b")),
    (
        "credential-assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|password)\b"
            r"\s*[:=]\s*['\"]([^'\"\r\n]{16,})['\"]"
        ),
    ),
)


def is_placeholder(value):
    lowered = value.lower()
    return any(word in lowered for word in PLACEHOLDER_WORDS) or len(set(value)) <= 3


def iter_scan_files(project_root):
    for relative in ROOT_FILES:
        path = project_root / relative
        if path.is_file() and not path.is_symlink():
            yield path
    for relative in SCAN_ROOTS:
        root = project_root / relative
        if not root.is_dir() or root.is_symlink():
            continue
        for path in root.rglob("*"):
            if (
                path.is_file()
                and not path.is_symlink()
                and path.name not in IGNORED_NAMES
                and path.suffix.lower() in TEXT_SUFFIXES
            ):
                yield path


def scan_file(path, project_root):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []
    findings = []
    relative = path.relative_to(project_root).as_posix()
    for line_number, line in enumerate(lines, start=1):
        for rule_name, pattern in RULES:
            for match in pattern.finditer(line):
                value = match.group(1) if match.lastindex else match.group(0)
                if is_placeholder(value):
                    continue
                findings.append((relative, line_number, rule_name))
    return findings


def scan_project(project_root=PROJECT_ROOT):
    project_root = Path(project_root).resolve()
    findings = []
    for path in sorted(set(iter_scan_files(project_root))):
        findings.extend(scan_file(path, project_root))
    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Scan source and configuration without printing matched secret values."
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()
    findings = scan_project(args.project_root)
    if findings:
        print(f"秘密扫描失败：发现 {len(findings)} 个疑似凭据位置。")
        for relative, line_number, rule_name in findings:
            print(f"{relative}:{line_number} [{rule_name}]")
        return 1
    print("秘密扫描通过：未在受控源码与配置范围发现高置信度凭据。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
