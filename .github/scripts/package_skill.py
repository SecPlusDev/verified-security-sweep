#!/usr/bin/env python3
"""Package the skill into a `.skill` archive (a zip rooted at `<name>/`). Standard library only.

    python3 .github/scripts/package_skill.py --out dist

The skill lives in the plugin folder (plugin/skills/verified-security-sweep); the archive is for
manual installation in claude.ai. The archive name and the root folder inside it come from `name`
in the SKILL.md frontmatter. Contents: SKILL.md, references/, scripts/ and the license (LICENSE in
the skill folder, or --license, by default the repository's LICENSE). Caches, compiled files,
tests, evals and build notes are never packaged. File order and timestamps are fixed, so the
same tree always produces a byte-identical archive and its hash can be compared across builds.

Exit codes: 0 archive written and verified, 1 packaging error.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

INCLUDE_DIRS = ("references", "scripts")
INCLUDE_FILES = ("SKILL.md", "LICENSE")
DEFAULT_ROOT = "plugin/skills/verified-security-sweep"
EXCLUDE_DIR_NAMES = {"__pycache__", ".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
# Images belong to the plugin's directory listing (plugin/.claude-plugin/icon.png), not to the
# skill archive for claude.ai; none is packaged even if one lands in the skill folder.
EXCLUDE_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def skill_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    m = re.search(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError(f"{skill_md}: no frontmatter block")
    name_m = re.search(r"^name:\s*(\S+)\s*$", m.group(1), re.M)
    if not name_m:
        raise ValueError(f"{skill_md}: no name in frontmatter")
    return name_m.group(1)


def collect(root: Path, license_file: Path | None = None) -> list[tuple[str, Path]]:
    """(path inside the skill folder, file on disk), sorted by the path inside the archive."""
    files: list[Path] = []
    for fname in INCLUDE_FILES:
        p = root / fname
        if p.is_file():
            files.append(p)
    for dname in INCLUDE_DIRS:
        d = root / dname
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            if EXCLUDE_DIR_NAMES & set(p.relative_to(root).parts) or p.suffix.lower() in EXCLUDE_SUFFIXES | EXCLUDE_IMAGE_SUFFIXES:
                continue
            files.append(p)
    entries = {p.relative_to(root).as_posix(): p for p in files}
    if "LICENSE" not in entries and license_file is not None and license_file.is_file():
        entries["LICENSE"] = license_file
    return sorted(entries.items())


def write_archive(root: Path, name: str, out_dir: Path, license_file: Path | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{name}.skill"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, p in collect(root, license_file):
            arcname = f"{name}/{rel}"
            info = zipfile.ZipInfo(arcname, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            # Every entry is a plain file without the execute bit: the scripts carry no shebang
            # and run as `python3 scripts/<name>.py`.
            info.external_attr = 0o644 << 16
            zf.writestr(info, p.read_bytes())
            print(f"  added {arcname}")
    return archive


def verify(archive: Path, name: str) -> None:
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad:
            raise ValueError(f"corrupt member {bad}")
        names = zf.namelist()
    if f"{name}/SKILL.md" not in names:
        raise ValueError(f"{name}/SKILL.md missing from archive")
    outside = [n for n in names if not n.startswith(f"{name}/")]
    if outside:
        raise ValueError(f"members outside {name}/: {outside}")
    images = [n for n in names if Path(n).suffix.lower() in EXCLUDE_IMAGE_SUFFIXES or ".claude-plugin" in n]
    if images:
        raise ValueError(f"plugin listing files in the skill archive: {images}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=DEFAULT_ROOT, help=f"skill root, the folder holding SKILL.md (default: {DEFAULT_ROOT})")
    ap.add_argument("--license", default="LICENSE", help="license file packaged as <name>/LICENSE when the skill folder has none (default: LICENSE)")
    ap.add_argument("--out", default="dist", help="output folder (default: dist)")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    license_path = Path(a.license)
    if not license_path.is_absolute() and not license_path.exists():
        # resolve a relative default against the repository root, not the current directory
        license_path = Path(__file__).resolve().parents[2] / license_path
    try:
        if not license_path.is_file():
            raise ValueError(f"license file not found: {license_path}")
        name = skill_name(root / "SKILL.md")
        archive = write_archive(root, name, Path(a.out), license_path.resolve())
        verify(archive, name)
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print(f"packaging failed: {e}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"\n{archive} ({archive.stat().st_size} bytes)\nsha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
