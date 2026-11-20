"""Build the edition of the plugin that the Claude plugin directory accepts, and check it.

The directory accepts script files only from verified organizations. From an organization that
is not one, a version is refused unless every file of the plugin folder is Markdown, text, JSON,
YAML or a PNG, JPEG, GIF, WebP or ICO image (a license, a readme and a .gitignore may stay as
UTF-8 text). This script copies the plugin folder without the skill's scripts/ folder and then
verifies the copy against that rule, so main can always produce an edition the directory takes.

    python3 .github/scripts/build_directory_edition.py --out dist/directory   # build and check
    python3 .github/scripts/build_directory_edition.py --check                # check only

The rule checked, from the directory's own refusal text (2026-11-06):
    allowed: .md .txt .json .yaml .yml, .png .jpg .jpeg .gif .webp .ico, and the files named
        LICENSE, README and .gitignore (any case, with or without an allowed extension);
    refused: any other file; a file that starts with `#!`; a package manager's configuration or
        package list (requirements.txt, package.json, package-lock.json, pnpm-workspace.yaml and
        the like); a `.claude/skills` folder; a `.claude-plugin` folder other than the plugin's
        own, and in the plugin's own anything but plugin.json, marketplace.json and images;
        hooks.json, .lsp.json, monitors.json, .mcp.json; an output-styles/ folder; a text file
        that is not UTF-8 or holds a NUL byte; an image that holds a zip archive.

Exit codes: 0 the edition is built (or would be) and meets the rule; 1 a file breaks the rule;
2 setup error (plugin folder missing, output folder not empty).
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

TEXT_EXT = {".md", ".txt", ".json", ".yaml", ".yml"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}
NAMED_TEXT = {"license", "readme", ".gitignore"}
PACKAGE_FILES = {
    "requirements.txt", "package.json", "package-lock.json", "npm-shrinkwrap.json", "pnpm-workspace.yaml",
    "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb", "pyproject.toml", "uv.lock", "poetry.lock",
    "pipfile", "pipfile.lock", "gemfile", "gemfile.lock", "go.mod", "go.sum", "cargo.toml", "cargo.lock",
    "composer.json", "composer.lock", ".npmrc", "bunfig.toml", "uv.toml",
}
REFUSED_NAMES = {"hooks.json", ".lsp.json", "monitors.json", ".mcp.json"}
# Left out of the copy: the scripts the directory refuses, and caches no edition should carry.
DROPPED_DIRS = {"scripts", "__pycache__"}


def is_dropped(rel: Path) -> bool:
    """True for a path under a skill's scripts/ folder or under any cache folder."""
    parts = rel.parts
    if "__pycache__" in parts:
        return True
    return len(parts) >= 3 and parts[0] == "skills" and parts[2] == "scripts"


def build(plugin: Path, out: Path) -> list[Path]:
    copied = []
    for src in sorted(p for p in plugin.rglob("*") if p.is_file()):
        rel = src.relative_to(plugin)
        if is_dropped(rel):
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied.append(rel)
    return copied


def problems_in(root: Path) -> list[str]:
    out = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root)
        name = path.name.lower()
        ext = path.suffix.lower()
        stem_name = name if not ext or name.startswith(".") else name[: -len(ext)]
        parts = [p.lower() for p in rel.parts]

        if name in PACKAGE_FILES:
            out.append(f"{rel}: a package manager's file")
            continue
        if name in REFUSED_NAMES:
            out.append(f"{rel}: {path.name} is not accepted")
            continue
        if "output-styles" in parts[:-1]:
            out.append(f"{rel}: under output-styles/")
            continue
        if ".claude" in parts[:-1] and "skills" in parts[:-1]:
            out.append(f"{rel}: under a .claude/skills folder")
            continue
        if ".claude-plugin" in parts[:-1]:
            if parts[0] != ".claude-plugin":
                out.append(f"{rel}: a .claude-plugin folder other than the plugin's own")
                continue
            if name not in {"plugin.json", "marketplace.json"} and ext not in IMAGE_EXT:
                out.append(f"{rel}: only plugin.json, marketplace.json and images belong in .claude-plugin")
                continue

        named = name in NAMED_TEXT or stem_name in NAMED_TEXT
        if ext in IMAGE_EXT:
            if b"PK\x03\x04" in path.read_bytes():
                out.append(f"{rel}: an image that holds a zip archive")
            continue
        if ext not in TEXT_EXT and not named:
            out.append(f"{rel}: not Markdown, text, JSON, YAML or an allowed image")
            continue
        data = path.read_bytes()
        if b"\0" in data:
            out.append(f"{rel}: holds a NUL byte")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            out.append(f"{rel}: not UTF-8")
            continue
        if text.startswith("#!"):
            out.append(f"{rel}: starts with #!")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--plugin", default="plugin", help="the plugin folder (default: plugin)")
    ap.add_argument("--out", help="folder to write the edition to; it must not exist or must be empty")
    ap.add_argument("--check", action="store_true", help="build in a temporary folder, check, and keep nothing")
    args = ap.parse_args()

    plugin = Path(args.plugin)
    if not (plugin / ".claude-plugin" / "plugin.json").is_file():
        print(f"not a plugin folder (no .claude-plugin/plugin.json): {plugin}", file=sys.stderr)
        return 2
    if not args.out and not args.check:
        print("give --out DIR or --check", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        if args.out:
            out = Path(args.out)
            if out.exists() and any(out.iterdir()):
                print(f"output folder is not empty: {out}", file=sys.stderr)
                return 2
            out.mkdir(parents=True, exist_ok=True)
        else:
            out = Path(tmp) / "plugin"
            out.mkdir()
        copied = build(plugin, out)
        problems = problems_in(out)
        if not any(len(r.parts) >= 3 and r.parts[0] == "skills" and r.name == "SKILL.md" for r in copied):
            problems.append("no skills/<name>/SKILL.md in the edition")
        for rel in copied:
            print(rel.as_posix())
        for p in problems:
            print(f"REFUSED  {p}")
        print(f"{len(copied)} file(s) in the directory edition, {len(problems)} problem(s)")
        return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
