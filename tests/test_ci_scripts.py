"""Tests for the repository's own CI scripts in .github/scripts/, on synthetic fixtures.

    python -m pytest tests/ -q

leakage_check.py is the gate that keeps the origin project out of this repository; its positive
path (a term found) never runs in CI, because the repository must have zero matches, so it is
exercised here on temporary git repositories. check_skill.py and package_skill.py are checked on
a minimal synthetic skill. Nothing here reads the real pattern list's terms.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".github" / "scripts"
LEAKAGE = SCRIPTS / "leakage_check.py"
LEAKAGE_SH = SCRIPTS / "leakage_grep.sh"
CHECK_SKILL = SCRIPTS / "check_skill.py"
PACKAGE = SCRIPTS / "package_skill.py"
HYGIENE = SCRIPTS / "public_hygiene_check.py"
DIRECTORY_EDITION = SCRIPTS / "build_directory_edition.py"


def run(script: Path, *args: str, cwd=None, env=None) -> subprocess.CompletedProcess:
    cmd = [str(script)] if script.suffix == ".sh" else [sys.executable, str(script)]
    return subprocess.run([*cmd, *args], cwd=cwd, env=env, capture_output=True, text=True)


def git_env(tmp_path: Path) -> dict:
    env = dict(os.environ)
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    })
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def sha(term: str) -> str:
    return hashlib.sha256(term.encode()).hexdigest()


def make_repo(tmp_path: Path, patterns: str, files: dict) -> tuple[Path, dict]:
    repo = tmp_path / "repo"
    (repo / ".github").mkdir(parents=True)
    (repo / ".github" / "leakage-patterns.txt").write_text(patterns, encoding="utf-8")
    for rel, content in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    env = git_env(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=repo, env=env, check=True)
    return repo, env


# The synthetic forbidden terms; none of them is in the real list.
PATTERNS = "\n".join([
    "# synthetic list",
    f"sha256:{sha('zorbleworks')}",        # single token
    f"sha256:{sha('acme' + 'cloud')}",     # two tokens: "Acme Cloud", "acme-cloud", "AcmeCloud"
    f"sha256:{sha('law' + '42' + 'bis')}", # three tokens: "Law 42 bis"
    r"regex:/home/[a-z]+/",
    r"regex:\b([0-9]{1,3}\.){3}[0-9]{1,3}\b",
    "",
])


def test_clean_repository_passes(tmp_path: Path):
    repo, env = make_repo(tmp_path, PATTERNS, {"README.md": "Nothing to see here.\n"})
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 0, r.stderr
    assert "3 hashed terms, 2 shapes" in r.stdout
    assert "no matches" in r.stdout


def test_single_token_term_is_found_case_insensitively(tmp_path: Path):
    repo, env = make_repo(tmp_path, PATTERNS, {"docs/a.md": "Built for ZorbleWorks customers.\n"})
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 1
    assert "docs/a.md:1:zorbleworks" in r.stdout


@pytest.mark.parametrize("text", ["Acme Cloud", "acme-cloud", "AcmeCloud", "acme_cloud", "Acme (cloud)"])
def test_two_token_term_is_found_across_separators(tmp_path: Path, text: str):
    repo, env = make_repo(tmp_path, PATTERNS, {"n.md": f"deployed on {text} last year\n"})
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 1, text
    assert "n.md:1:acmecloud" in r.stdout


@pytest.mark.parametrize("text", ["Law 42 bis", "law-42-bis", "LAW42BIS"])
def test_three_token_term_is_found_as_a_contiguous_run(tmp_path: Path, text: str):
    repo, env = make_repo(tmp_path, PATTERNS, {"n.md": f"see {text}\n"})
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 1, text
    assert "law42bis" in r.stdout


def test_unrelated_words_do_not_match(tmp_path: Path):
    repo, env = make_repo(tmp_path, PATTERNS, {"n.md": "acme makes clouds; the law of 42 is bis repetita\n"})
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 0, r.stdout


def test_regex_shapes_are_reported_with_the_matched_text(tmp_path: Path):
    # built at run time so this file does not itself contain the shapes the real list forbids
    home = "/" + "home/alice/"
    ip = ".".join(["10", "0", "0", "7"])
    repo, env = make_repo(tmp_path, PATTERNS, {"n.md": f"cd {home}work and ping {ip}\n"})
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 1
    assert f"n.md:1:{home}" in r.stdout
    assert f"n.md:1:{ip}" in r.stdout


def test_binary_files_are_skipped_and_ignored_files_are_not_scanned(tmp_path: Path):
    repo, env = make_repo(tmp_path, PATTERNS, {
        "img.bin": b"\x89PNG\x00zorbleworks\x00",
        "ignored.md": "zorbleworks\n",
        ".gitignore": "ignored.md\n",
    })
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 0, r.stdout
    assert "no matches" in r.stdout


def test_pattern_list_itself_is_not_scanned(tmp_path: Path):
    # a comment in the list naming a term must not trip the check
    repo, env = make_repo(tmp_path, PATTERNS + "# zorbleworks is listed above\n", {"n.md": "clean\n"})
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 0, r.stdout


def test_malformed_entry_is_a_setup_error(tmp_path: Path):
    repo, env = make_repo(tmp_path, "zorbleworks\n", {"n.md": "clean\n"})
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 2
    assert "bad entry" in r.stderr


def test_hash_option_prints_a_list_entry_and_refuses_long_terms():
    r = run(LEAKAGE, "--hash", "Acme Cloud")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == f"sha256:{sha('acmecloud')}"
    r = run(LEAKAGE, "--hash", "one two three four")
    assert r.returncode == 2
    assert "at most three tokens" in r.stderr


def test_outside_a_repository_is_a_setup_error(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    r = run(LEAKAGE, cwd=plain, env=git_env(tmp_path))
    assert r.returncode == 2
    assert "not inside a git repository" in r.stderr


def test_shell_wrapper_delegates_to_the_python_check(tmp_path: Path):
    repo, env = make_repo(tmp_path, PATTERNS, {"n.md": "ZorbleWorks\n"})
    r = run(LEAKAGE_SH, cwd=repo, env=env)
    assert r.returncode == 1
    assert "zorbleworks" in r.stdout


def test_real_pattern_list_holds_shapes_only():
    """The public list carries generic shapes only: no hashed term (a hashed short name is
    recovered by guessing) and no owner-specific regex."""
    for raw in (ROOT / ".github" / "leakage-patterns.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, _, value = line.partition(":")
        assert kind == "regex", raw
        assert "secplusdev" not in value.lower(), raw


def test_private_terms_file_is_applied(tmp_path: Path):
    """Terms come from LEAKAGE_TERMS_FILE; the public list alone runs the shapes and says so."""
    repo, env = make_repo(tmp_path, "regex:/home/[a-z]+/\n", {"a.md": "the zorbleworks launch\n"})
    r = run(LEAKAGE, cwd=repo, env=env)
    assert r.returncode == 0 and "shapes only" in r.stdout
    terms = tmp_path / "terms.txt"
    terms.write_text(f"sha256:{sha('zorbleworks')}\n", encoding="utf-8")
    r = run(LEAKAGE, cwd=repo, env={**env, "LEAKAGE_TERMS_FILE": str(terms)})
    assert r.returncode == 1 and "a.md:1:zorbleworks" in r.stdout
    r = run(LEAKAGE, cwd=repo, env={**env, "LEAKAGE_TERMS_FILE": str(tmp_path / "missing.txt")})
    assert r.returncode == 2


# --------------------------------------------------------------------------------------
# check_skill.py and package_skill.py on a minimal synthetic skill
# --------------------------------------------------------------------------------------

SKILL_MD = """---
name: tiny-skill
description: A minimal skill used by the repository's own tests.
---

# Tiny skill

Read `references/one.md` when asked.
"""


@pytest.fixture
def skill(tmp_path: Path) -> Path:
    root = tmp_path / "tiny-skill"
    (root / "references").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    (root / "references" / "one.md").write_text("# One\n\nPlain text.\n", encoding="utf-8")
    (root / "scripts" / "tool.py").write_text("print('x')\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
    return root


def test_check_skill_passes_on_the_minimal_skill(skill: Path):
    r = run(CHECK_SKILL, str(skill))
    assert r.returncode == 0, r.stdout
    assert "all checks passed" in r.stdout


def test_check_skill_fails_on_an_em_dash(skill: Path):
    (skill / "references" / "one.md").write_text("# One\n\nA " + chr(0x2014) + " dash.\n", encoding="utf-8")
    r = run(CHECK_SKILL, str(skill))
    assert r.returncode == 1
    assert "em dash" in r.stdout.lower()


def test_check_skill_fails_on_a_broken_frontmatter(skill: Path):
    (skill / "SKILL.md").write_text("---\nname: tiny-skill\n\n# no closing fence\n", encoding="utf-8")
    r = run(CHECK_SKILL, str(skill))
    assert r.returncode == 1
    assert "FAIL frontmatter block present and closed" in r.stdout


def test_check_skill_fails_when_name_is_not_kebab_case(skill: Path):
    (skill / "SKILL.md").write_text(SKILL_MD.replace("name: tiny-skill", "name: Tiny_Skill"), encoding="utf-8")
    r = run(CHECK_SKILL, str(skill))
    assert r.returncode == 1
    assert "FAIL name is kebab-case" in r.stdout


def test_check_skill_exits_2_without_a_skill_md(tmp_path: Path):
    r = run(CHECK_SKILL, str(tmp_path))
    assert r.returncode == 2
    assert "cannot read" in r.stderr


def test_package_skill_is_reproducible_and_contains_only_the_skill(skill: Path, tmp_path: Path):
    out1, out2 = tmp_path / "d1", tmp_path / "d2"
    for out in (out1, out2):
        r = run(PACKAGE, "--root", str(skill), "--license", str(tmp_path / "LICENSE"), "--out", str(out))
        assert r.returncode == 0, r.stderr
    a, b = out1 / "tiny-skill.skill", out2 / "tiny-skill.skill"
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as z:
        names = sorted(z.namelist())
        assert all(n.startswith("tiny-skill/") for n in names)
        assert "tiny-skill/SKILL.md" in names and "tiny-skill/LICENSE" in names
        stamps = {i.date_time for i in z.infolist()}
        assert len(stamps) == 1  # fixed timestamp on every member


def test_package_skill_fails_without_a_license_file(skill: Path, tmp_path: Path):
    r = run(PACKAGE, "--root", str(skill), "--license", str(tmp_path / "missing-LICENSE"), "--out", str(tmp_path / "d"))
    assert r.returncode == 1
    assert "license file not found" in r.stderr


# --------------------------------------------------------------------------------------
# public_hygiene_check.py
# --------------------------------------------------------------------------------------

# Planted values are assembled at run time so this file does not contain them literally;
# the hygiene check scans this file too.
GH = "https://" + "github.com/"
EVIL = "https://" + "evil.example/"
HEX = "a1b2c3" + "d4e"
DOT = "."

HYGIENE_ALLOW = "\n".join([
    "# synthetic allowlist",
    "email:*@example.invalid",
    "host:github.com",
    "github-owner:friend",
    "hex-file:pins/",
    "lang-file:evals/multilingual.json",
    "identifier:okName",
    "date:2026-01-15",
    "",
])


def make_hygiene_repo(tmp_path: Path, files: dict) -> tuple[Path, dict]:
    repo = tmp_path / "hrepo"
    (repo / ".github").mkdir(parents=True)
    (repo / ".github" / "hygiene-allowlist.txt").write_text(HYGIENE_ALLOW, encoding="utf-8")
    for rel, content in files.items():
        q = repo / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(content, encoding="utf-8")
    env = git_env(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=repo, env=env, check=True)
    return repo, env


def test_hygiene_clean_repository_passes(tmp_path: Path):
    repo, env = make_hygiene_repo(tmp_path, {
        "README.md": "Contact fixture@example.invalid, see " + GH + "friend/tool, name okName.\n",
        "pins/setup.sh": "git checkout " + HEX + "5f\n",
        "evals/multilingual.json": '{"q": "text cu diacritice " + "\u021b" + "}\n',
        "plugin/x.md": "run 2026-01-15\n",
    })
    r = run(HYGIENE, cwd=repo, env=env)
    assert r.returncode == 0, r.stdout
    assert "no findings" in r.stdout


def test_hygiene_reports_each_kind(tmp_path: Path):
    ip = ".".join(["10", "1", "2", "3"])
    repo, env = make_hygiene_repo(tmp_path, {
        "n.md": f"mail bob@corp{DOT}example host {ip} commit {HEX} url {EVIL}x "
                "and " + GH + "stranger/repo, word " + chr(0x21B) + " ident fooBarBaz\n",
        "plugin/y.md": "last run 2026-03-03\n",
    })
    r = run(HYGIENE, cwd=repo, env=env)
    assert r.returncode == 1
    kinds = {line.split(":")[2] for line in r.stdout.splitlines() if line.startswith(("n.md", "plugin/"))}
    assert kinds == {"email", "ip", "hex", "url", "text", "identifier", "date"}
    assert "n.md:1:url:" + GH + "stranger/repo\n" in r.stdout  # trailing comma stripped


def test_hygiene_flags_romanian_typed_without_diacritics(tmp_path: Path):
    # Reproduces the gap: Romanian prose with no diacritics passed the text check.
    line = "userId din URL " + "f" + "ara verificare; " + "lini" + "ile citate nu exista\n"
    repo, env = make_hygiene_repo(tmp_path, {"results/grading.json": line})
    r = run(HYGIENE, cwd=repo, env=env)
    assert r.returncode == 1, r.stdout
    assert "results/grading.json:1:text:" in r.stdout


def test_hygiene_ignores_digests_action_pins_and_code_files(tmp_path: Path):
    digest = "0" * 63 + "a"
    repo, env = make_hygiene_repo(tmp_path, {
        "n.md": f"digest {digest}\n",
        "ci.yml": "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1\nrun: curl -fsSL\n",
        "tool.py": "someCamelCase = 1\n",
    })
    r = run(HYGIENE, cwd=repo, env=env)
    assert r.returncode == 0, r.stdout


def test_hygiene_bad_allowlist_entry_is_a_setup_error(tmp_path: Path):
    repo, env = make_hygiene_repo(tmp_path, {"n.md": "clean\n"})
    (repo / ".github" / "hygiene-allowlist.txt").write_text("nonsense\n", encoding="utf-8")
    r = run(HYGIENE, cwd=repo, env=env)
    assert r.returncode == 2
    assert "bad allowlist entry" in r.stderr


def test_hygiene_outside_a_repository_is_a_setup_error(tmp_path: Path):
    plain = tmp_path / "plain2"
    plain.mkdir()
    r = run(HYGIENE, cwd=plain, env=git_env(tmp_path))
    assert r.returncode == 2


# --------------------------------------------------------------------------------------
# build_directory_edition.py: the edition the Claude plugin directory accepts
# --------------------------------------------------------------------------------------

def make_plugin(root: Path) -> Path:
    plugin = root / "plugin"
    skill = plugin / "skills" / "sample-skill"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (skill / "references").mkdir(parents=True)
    (skill / "scripts" / "__pycache__").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "sample", "version": "1.0.0"}\n', encoding="utf-8")
    (plugin / ".claude-plugin" / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    (plugin / "README.md").write_text("# Sample\n", encoding="utf-8")
    (plugin / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (skill / "SKILL.md").write_text("---\nname: sample-skill\ndescription: a sample\n---\n# Sample\n", encoding="utf-8")
    (skill / "references" / "notes.md").write_text("notes\n", encoding="utf-8")
    (skill / "scripts" / "check.py").write_text("print('ok')\n", encoding="utf-8")
    (skill / "scripts" / "shapes.json").write_text("{}\n", encoding="utf-8")
    (skill / "scripts" / "__pycache__" / "check.cpython-313.pyc").write_bytes(b"\0\0")
    return plugin


def test_directory_edition_drops_the_scripts_and_passes(tmp_path: Path):
    # The directory refuses script files from an organization that is not verified (2026-11-06);
    # the edition is the plugin folder without the skill's scripts/ folder, nothing else changed
    plugin = make_plugin(tmp_path)
    out = tmp_path / "edition"
    r = run(DIRECTORY_EDITION, "--plugin", str(plugin), "--out", str(out))
    assert r.returncode == 0, r.stdout + r.stderr
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert files == [".claude-plugin/icon.png", ".claude-plugin/plugin.json", "LICENSE", "README.md",
                     "skills/sample-skill/SKILL.md", "skills/sample-skill/references/notes.md"]
    assert "6 file(s) in the directory edition, 0 problem(s)" in r.stdout
    # the source folder is untouched
    assert (plugin / "skills" / "sample-skill" / "scripts" / "check.py").is_file()
    # a second build into the same folder is a setup error, not a silent merge
    assert run(DIRECTORY_EDITION, "--plugin", str(plugin), "--out", str(out)).returncode == 2


@pytest.mark.parametrize("rel, content, why", [
    ("skills/sample-skill/helper.sh", b"echo hi\n", "not Markdown, text, JSON, YAML or an allowed image"),
    ("skills/sample-skill/references/run.md", b"#!/bin/sh\necho hi\n", "starts with #!"),
    ("requirements.txt", b"requests==2.0\n", "a package manager's file"),
    ("hooks/hooks.json", b"{}\n", "hooks.json is not accepted"),
    (".claude-plugin/extra.md", b"x\n", "only plugin.json, marketplace.json and images"),
    ("skills/sample-skill/references/latin1.md", b"caf\xe9\n", "not UTF-8"),
    ("skills/sample-skill/references/diagram.svg", b"<svg/>\n", "not Markdown, text, JSON, YAML or an allowed image"),
    ("skills/sample-skill/references/picture.png", b"\x89PNG\r\n\x1a\nPK\x03\x04", "an image that holds a zip archive"),
])
def test_directory_edition_refuses_what_the_directory_refuses(tmp_path: Path, rel: str, content: bytes, why: str):
    plugin = make_plugin(tmp_path)
    target = plugin / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    r = run(DIRECTORY_EDITION, "--plugin", str(plugin), "--check")
    assert r.returncode == 1, r.stdout
    assert f"REFUSED  {rel}: {why}" in r.stdout


def test_the_real_plugin_builds_a_directory_edition_with_every_reference():
    r = run(DIRECTORY_EDITION, "--plugin", str(ROOT / "plugin"), "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "skills/verified-security-sweep/references/without-scripts.md" in r.stdout
    assert "scripts/" not in r.stdout
