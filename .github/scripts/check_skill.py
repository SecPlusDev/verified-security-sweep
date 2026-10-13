#!/usr/bin/env python3
"""Structural lint for the skill folder and the plugin folder. Standard library only.

    python3 .github/scripts/check_skill.py plugin/skills/verified-security-sweep \
        --markdown-root . --plugin-root plugin             # repository, as CI runs it
    python3 .github/scripts/check_skill.py path/to/unpacked  # an unpacked .skill archive

Checks
  - SKILL.md opens with a `---` frontmatter block that is closed
  - `name` is present, kebab-case, at most 64 characters
  - `description` is present, non-empty, at most 1024 characters once folded
    (both limits come from the Agent Skills frontmatter specification)
  - SKILL.md has fewer than --max-lines lines
  - references/ holds at most --max-references files, each with fewer than
    --max-reference-lines lines
  - no Markdown file anywhere under --markdown-root (default: the skill folder) contains an
    em dash (U+2014)
  - with --plugin-root, the directory checks that block or hold a plugin submission:
    .claude-plugin/plugin.json parses and sets name, version, description, author and license;
    README.md has at least 40 words outside code blocks; the listing icon exists at
    .claude-plugin/icon.png, the path the directory reads without an icon field (Claude Code
    ignores that field); LICENSE exists and, when the markdown
    root has one, is identical to it; at most 512 files, each either a text file under 256 KiB or
    a complete PNG, JPEG, GIF or WebP image (or an SVG, or a font) under 5 MiB, with no symbolic
    links and no system files (.DS_Store, Thumbs.db, desktop.ini, __MACOSX); and the
    manifest version equals the newest version in the markdown root's CHANGELOG.md, if present;
    every directory listing URL (documentationUrl, supportUrl, privacyPolicyUrl, ...) is https,
    and one of the form github.com/<owner>/<repo>/blob/main/<path> names a file that exists
    under the markdown root.
    Inside a git work tree only tracked and untracked-but-not-ignored files count, which is what
    the directory reads from the repository.

Exit codes: 0 all checks pass, 1 at least one check fails, 2 SKILL.md unreadable.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(.*)$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
EM_DASH = "\u2014"
SKIP_DIRS = {".git", "dist", "__pycache__", ".pytest_cache", "node_modules"}


def split_frontmatter(text: str) -> tuple[str, str] | None:
    """Return (frontmatter, body) or None when the file has no closed frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])
    return None


def parse_keys(frontmatter: str) -> dict[str, str]:
    """Top-level `key: value` pairs; indented continuation lines are folded into the value.

    Block scalar indicators (`>`, `>-`, `|`, `|-`) are dropped and the continuation lines
    are joined with single spaces, which is what a folded scalar means for a one-paragraph
    description. This is not a YAML parser; it is enough to lint the two required keys.
    """
    keys: dict[str, str] = {}
    current = None
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        m = KEY_RE.match(line)
        if m and not line[0].isspace():
            current = m.group(1)
            value = m.group(2).strip()
            if value in (">", ">-", "|", "|-", ">+", "|+"):
                value = ""
            keys[current] = value
        elif current is not None:
            keys[current] = (keys[current] + " " + line.strip()).strip()
    return keys


def line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def markdown_files(root: Path) -> list[Path]:
    """Every .md under root, skipping build folders and nested git repositories (for example
    the evaluation fixtures cloned under evals/fixtures/, whose content is not ours to lint)."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        dirnames[:] = sorted(
            n for n in dirnames
            if n not in SKIP_DIRS and not (d / n / ".git").exists()
        )
        out.extend(d / f for f in filenames if f.endswith(".md"))
    return sorted(out)


SYSTEM_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
FONT_SUFFIXES = {".ttf", ".otf", ".woff", ".woff2"}
FONT_MAGIC = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"wOFF", b"wOF2")
PLUGIN_FILE_MAX = 256 * 1024
PLUGIN_MEDIA_MAX = 5 * 1024 * 1024
PLUGIN_ICON = Path(".claude-plugin") / "icon.png"
LISTING_URL_FIELDS = ("homepage", "documentationUrl", "supportUrl", "privacyPolicyUrl", "termsOfServiceUrl")
BLOB_MAIN_RE = re.compile(r"^https://github\.com/[^/]+/[^/]+/blob/main/(.+)$")
PLUGIN_FILES_MAX = 512
README_MIN_WORDS = 40
CHANGELOG_VERSION_RE = re.compile(r"^##\s+v?(\d+\.\d+\.\d+)", re.M)


def plugin_files(plugin: Path) -> list[Path]:
    """Files the directory would read: git-tracked or untracked-but-not-ignored inside a work
    tree, every file otherwise (for example in an unpacked archive)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(plugin), "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."],
            capture_output=True, check=True,
        ).stdout.decode("utf-8")
        return sorted(plugin / f for f in out.split("\0") if f and (plugin / f).exists())
    except (OSError, subprocess.CalledProcessError):
        return sorted(p for p in plugin.rglob("*") if p.is_file() or p.is_symlink())


def media_problem(raw: bytes, suffix: str) -> str | None:
    """None when raw is a complete image or font of the kind its suffix names, else the reason.
    The directory accepts complete PNG, JPEG, GIF and WebP images, SVG, and font files."""
    if suffix == ".png":
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            return "not a PNG signature"
        i = 8
        while i + 12 <= len(raw):
            length = struct.unpack(">I", raw[i:i + 4])[0]
            ctype, data = raw[i + 4:i + 8], raw[i + 8:i + 8 + length]
            if i + 12 + length > len(raw):
                return "truncated chunk"
            crc = struct.unpack(">I", raw[i + 8 + length:i + 12 + length])[0]
            if zlib.crc32(ctype + data) & 0xFFFFFFFF != crc:
                return f"bad CRC in chunk {ctype!r}"
            i += 12 + length
            if ctype == b"IEND":
                return None if i == len(raw) else "data after IEND"
        return "no IEND chunk"
    if suffix in (".jpg", ".jpeg"):
        return None if raw[:3] == b"\xff\xd8\xff" and raw.rstrip(b"\x00")[-2:] == b"\xff\xd9" else "not a complete JPEG"
    if suffix == ".gif":
        return None if raw[:6] in (b"GIF87a", b"GIF89a") and raw[-1:] == b";" else "not a complete GIF"
    if suffix == ".webp":
        ok = raw[:4] == b"RIFF" and raw[8:12] == b"WEBP" and struct.unpack("<I", raw[4:8])[0] + 8 == len(raw)
        return None if ok else "not a complete WebP"
    if suffix == ".svg":
        try:
            return None if "<svg" in raw.decode("utf-8") else "SVG without an <svg> element"
        except UnicodeDecodeError:
            return "SVG is not UTF-8 text"
    if suffix in FONT_SUFFIXES:
        return None if raw[:4] in FONT_MAGIC else "not a recognized font file"
    return "not an image or font"


def readme_words(text: str) -> int:
    outside = re.sub(r"```.*?```", "", text, flags=re.S)
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", outside))


def check_plugin(plugin: Path, markdown_root: Path, check) -> None:
    manifest = plugin / ".claude-plugin" / "plugin.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        check(False, "plugin.json present and valid JSON", str(e))
        data = {}
    else:
        check(isinstance(data, dict), "plugin.json present and valid JSON")
    for key in ("name", "version", "description", "author", "license"):
        check(bool(data.get(key)), f"plugin.json sets {key}")
    check(bool(NAME_RE.match(str(data.get("name", "")))), "plugin name is kebab-case", repr(data.get("name")))

    readme = plugin / "README.md"
    words = readme_words(readme.read_text(encoding="utf-8")) if readme.is_file() else 0
    check(words >= README_MIN_WORDS, f"plugin README.md has at least {README_MIN_WORDS} words outside code blocks", f"{words} words")

    icon = plugin / PLUGIN_ICON
    check(icon.is_file(), f"plugin icon present at {PLUGIN_ICON.as_posix()}")

    lic = plugin / "LICENSE"
    check(lic.is_file(), "plugin LICENSE present")
    root_lic = markdown_root / "LICENSE"
    if lic.is_file() and root_lic.is_file() and root_lic.resolve() != lic.resolve():
        check(lic.read_bytes() == root_lic.read_bytes(), "plugin LICENSE identical to the repository LICENSE")

    files = plugin_files(plugin)
    check(len(files) <= PLUGIN_FILES_MAX, f"plugin holds at most {PLUGIN_FILES_MAX} files", f"{len(files)} files")
    links = [p for p in files if p.is_symlink()]
    check(not links, "no symbolic links in the plugin", ", ".join(str(p.relative_to(plugin)) for p in links))
    system = [p for p in files if p.name in SYSTEM_FILES or "__MACOSX" in p.parts]
    check(not system, "no system files in the plugin", ", ".join(str(p.relative_to(plugin)) for p in system))
    big, binary, media = [], [], []
    for p in files:
        if p.is_symlink():
            continue
        raw, suffix, name = p.read_bytes(), p.suffix.lower(), str(p.relative_to(plugin))
        if suffix in IMAGE_SUFFIXES or suffix in FONT_SUFFIXES:
            problem = media_problem(raw, suffix)
            if problem:
                binary.append(f"{name} ({problem})")
            elif len(raw) >= PLUGIN_MEDIA_MAX:
                big.append(f"{name} ({len(raw)} bytes, images and fonts must be under 5 MiB)")
            else:
                media.append(name)
            continue
        if len(raw) >= PLUGIN_FILE_MAX:
            big.append(f"{name} ({len(raw)} bytes)")
        try:
            raw.decode("utf-8")
            if b"\0" in raw:
                raise ValueError
        except ValueError:
            binary.append(name)
    check(not big, "every plugin file within its size limit (text under 256 KiB, images and fonts under 5 MiB)", ", ".join(big))
    check(not binary, "plugin holds text files, complete images and fonts only",
          ", ".join(binary) if binary else (f"images and fonts accepted: {', '.join(media)}" if media else ""))

    for key in LISTING_URL_FIELDS:
        url = data.get(key)
        if not url:
            continue
        check(str(url).startswith("https://"), f"plugin.json {key} is an https URL", str(url))
        m = BLOB_MAIN_RE.match(str(url))
        if m:
            check((markdown_root / m.group(1)).is_file(), f"plugin.json {key} points to an existing file", m.group(1))

    changelog = markdown_root / "CHANGELOG.md"
    if changelog.is_file():
        m = CHANGELOG_VERSION_RE.search(changelog.read_text(encoding="utf-8"))
        newest = m.group(1) if m else None
        check(newest == data.get("version"), "plugin.json version equals the newest CHANGELOG.md version",
              f"plugin.json {data.get('version')!r}, CHANGELOG.md {newest!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default="plugin/skills/verified-security-sweep",
                    help="skill folder holding SKILL.md (default: plugin/skills/verified-security-sweep)")
    ap.add_argument("--markdown-root", default=None, help="folder whose Markdown files are checked for em dashes (default: the skill folder)")
    ap.add_argument("--plugin-root", default=None, help="plugin folder holding .claude-plugin/plugin.json; enables the plugin checks")
    ap.add_argument("--max-lines", type=int, default=500, help="SKILL.md must have fewer lines than this (default 500)")
    ap.add_argument("--max-references", type=int, default=6, help="at most this many files in references/ (default 6)")
    ap.add_argument("--max-reference-lines", type=int, default=300, help="each reference must have fewer lines than this (default 300)")
    a = ap.parse_args()

    root = Path(a.root)
    skill_md = root / "SKILL.md"
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError as e:
        print(f"cannot read {skill_md}: {e}", file=sys.stderr)
        return 2

    failures: list[str] = []

    def check(ok: bool, label: str, detail: str = "") -> None:
        print(f"{'OK  ' if ok else 'FAIL'} {label}" + (f": {detail}" if detail else ""))
        if not ok:
            failures.append(label)

    def rel(p: Path) -> str:
        return p.relative_to(root).as_posix()

    # SKILL.md: size and frontmatter
    check(line_count(text) < a.max_lines, f"SKILL.md under {a.max_lines} lines", f"{line_count(text)} lines")
    fm = split_frontmatter(text)
    check(fm is not None, "frontmatter block present and closed")
    if fm is not None:
        keys = parse_keys(fm[0])
        name = keys.get("name", "")
        check(bool(name), "frontmatter has name", repr(name))
        check(bool(NAME_RE.match(name)), "name is kebab-case (a-z, 0-9, single hyphens)", repr(name))
        check(len(name) <= NAME_MAX, f"name at most {NAME_MAX} characters", f"{len(name)}")
        description = keys.get("description", "")
        check(bool(description), "frontmatter has description", f"{len(description)} characters")
        check(len(description) <= DESCRIPTION_MAX, f"description at most {DESCRIPTION_MAX} characters", f"{len(description)}")
        check(bool(fm[1].strip()), "body after frontmatter is not empty")

    # references/: count and size
    refs_dir = root / "references"
    refs = sorted(p for p in refs_dir.rglob("*") if p.is_file()) if refs_dir.is_dir() else []
    check(len(refs) <= a.max_references, f"references/ holds at most {a.max_references} files", f"{len(refs)} files")
    for p in refs:
        n = line_count(p.read_text(encoding="utf-8", errors="replace"))
        check(n < a.max_reference_lines, f"{rel(p)} under {a.max_reference_lines} lines", f"{n} lines")

    # every Markdown file: no em dash
    md_root = Path(a.markdown_root) if a.markdown_root else root
    md_files = markdown_files(md_root)
    hits = []
    for p in md_files:
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if EM_DASH in line:
                hits.append(f"{p.relative_to(md_root).as_posix()}:{i}")
    check(not hits, f"no em dash in {len(md_files)} Markdown files", ", ".join(hits) if hits else "")

    # plugin folder: the directory's blocking and hold checks
    if a.plugin_root:
        check_plugin(Path(a.plugin_root), md_root, check)

    if failures:
        sys.stdout.flush()
        print(f"\n{len(failures)} check(s) failed: " + "; ".join(failures), file=sys.stderr)
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
