"""Tests for the four helper scripts in plugin/skills/verified-security-sweep/scripts/, on synthetic fixtures only.

    python -m pytest tests/ -q

Nothing here touches a real audits folder or the repository's own git history: the
sweep_status tests build a five-report audits folder with one planted divergence, the
fresh_code tests build a three-commit git repository in a temporary directory.

The scripts must run on Python 3.9+; the suite itself runs on 3.10+ (pytest 9), and a separate CI
job checks the scripts under 3.9 without pytest.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import sysconfig
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugin" / "skills" / "verified-security-sweep" / "scripts"
SWEEP_STATUS = SCRIPTS / "sweep_status.py"
FRESH_CODE = SCRIPTS / "fresh_code.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


sweep_status = _load(SWEEP_STATUS)
fresh_code = _load(FRESH_CODE)


def run_script(script: Path, *args: str, cwd=None, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


# --------------------------------------------------------------------------------------
# sweep_status.py
# --------------------------------------------------------------------------------------

TODAY = date.today()


def days_ago(n: int) -> str:
    return (TODAY - timedelta(days=n)).isoformat()


# Five dated reports. `money` was run twice; the latest run is the one that counts.
REPORTS = [
    (days_ago(120), "money"),
    (days_ago(50), "money"),
    (days_ago(44), "unaudited-zones"),
    (days_ago(32), "auth"),
    (days_ago(19), "operator"),
]

# Planted divergence: the registry says the unaudited-zones sweep ran ten days before the
# report filename says it did. Everything else agrees. `superadmin` has no report at all.
REGISTRY_DIVERGENT = f"""# Sweep registry

Zone and argument are written by hand. The last-run date is derived from report filenames.

## Candidate zones

| Zone | Argument | Last run | Yield |
|---|---|---|---|
| `money` | Billing, quotas, crons | {days_ago(50)} | 3/5 |
| `auth` | Login, sessions, second factor | {days_ago(32)} | 1/4 |
| `unaudited-zones` | Modules with no registry row yet | {days_ago(54)} | 0/2 |
| `operator` | Operator console | {days_ago(19)} | 2/2 |
| `superadmin` | Platform-level admin paths | planned | - |

## Proposed zones

This table must be ignored by the script.

| Zone | Argument | Last run | Yield |
|---|---|---|---|
| `reports` | Document generation | never | - |
"""

REGISTRY_ALIGNED = REGISTRY_DIVERGENT.replace(days_ago(54), days_ago(44))


@pytest.fixture
def audits(tmp_path: Path) -> Path:
    folder = tmp_path / "docs" / "audits"
    folder.mkdir(parents=True)
    for day, slug in REPORTS:
        (folder / f"{day}-{slug}.md").write_text(f"# {slug} sweep on {day}\n", encoding="utf-8")
    # Files that must not be counted as reports.
    (folder / "categories.md").write_text("# Categories\n", encoding="utf-8")
    (folder / "2025-roadmap.md").write_text("not a dated report\n", encoding="utf-8")
    return folder


@pytest.fixture
def registry_divergent(tmp_path: Path) -> Path:
    path = tmp_path / "registry-divergent.md"
    path.write_text(REGISTRY_DIVERGENT, encoding="utf-8")
    return path


@pytest.fixture
def registry_aligned(tmp_path: Path) -> Path:
    path = tmp_path / "registry-aligned.md"
    path.write_text(REGISTRY_ALIGNED, encoding="utf-8")
    return path


def test_reports_parses_dated_filenames_only(audits: Path):
    reps = sweep_status.reports(audits)
    assert len(reps) == 5
    assert reps == sorted(reps)
    assert [slug for _, slug in reps] == ["money", "money", "unaudited-zones", "auth", "operator"]
    assert all(isinstance(d, date) for d, _ in reps)


def test_registry_rows_reads_only_the_candidate_table(registry_divergent: Path):
    rows = sweep_status.registry_rows(registry_divergent)
    assert [r["zone"] for r in rows] == ["money", "auth", "unaudited-zones", "operator", "superadmin"]
    assert "reports" not in {r["zone"] for r in rows}
    by_zone = {r["zone"]: r for r in rows}
    assert by_zone["money"]["declared"] == days_ago(50)
    assert by_zone["unaudited-zones"]["declared"] == days_ago(54)
    assert by_zone["superadmin"]["declared"] is None
    assert by_zone["operator"]["argument"] == "Operator console"


def test_registry_rows_without_backticked_slugs_is_empty(tmp_path: Path):
    path = tmp_path / "registry.md"
    path.write_text("## Candidate zones\n\n| Zone | Argument | Last run |\n|---|---|---|\n| money | x | 2026-01-01 |\n", encoding="utf-8")
    assert sweep_status.registry_rows(path) == []


def test_last_run_matches_hyphen_token_runs_in_either_direction(audits: Path):
    reps = sweep_status.reports(audits)
    assert sweep_status.last_run("money", reps).isoformat() == days_ago(50)
    assert sweep_status.last_run("zones", reps).isoformat() == days_ago(44)
    assert sweep_status.last_run("unaudited-zones-and-more", reps).isoformat() == days_ago(44)
    assert sweep_status.last_run("superadmin", reps) is None


def test_last_run_does_not_match_on_substrings_inside_tokens():
    reps = [(date(2026, 1, 15), "oauth-callbacks"), (date(2026, 1, 16), "author-pages")]
    # `auth` is a substring of both slugs but a token of neither
    assert sweep_status.last_run("auth", reps) is None
    assert sweep_status.slug_matches("oauth", "oauth-callbacks")
    assert not sweep_status.slug_matches("auth", "oauth")
    assert not sweep_status.slug_matches("", "oauth")


def test_registry_rows_ignores_refused_table_when_candidates_table_is_empty(tmp_path: Path):
    path = tmp_path / "registry.md"
    path.write_text(
        "# Sweep registry\n\n## Candidates\n\n(none yet)\n\n"
        "## Candidates verified and refused\n\n| Zone | Argument | Last run | Yield |\n|---|---|---|---|\n"
        "| `refused-one` | not worth it | 2026-01-01 | - |\n",
        encoding="utf-8",
    )
    assert sweep_status.registry_rows(path) == []
    assert sweep_status.is_candidates_heading("## Candidate zones")
    assert sweep_status.is_candidates_heading("## Candidates")
    assert not sweep_status.is_candidates_heading("## Candidates verified and refused")
    assert not sweep_status.is_candidates_heading("## Proposed candidates")


def test_declared_date_without_any_report_is_a_divergence(audits: Path, tmp_path: Path):
    path = tmp_path / "registry-ghost.md"
    path.write_text(
        REGISTRY_ALIGNED.replace("| `superadmin` | Platform-level admin paths | planned | - |",
                                 f"| `superadmin` | Platform-level admin paths | {days_ago(10)} | 1/1 |"),
        encoding="utf-8",
    )
    r = run_script(SWEEP_STATUS, "--check", "--audits", str(audits), "--registry", str(path))
    assert r.returncode == 1, r.stderr
    assert "superadmin" in r.stderr
    assert "registry declares a run but no report matches slug" in r.stdout


def test_invalid_calendar_date_in_filename_is_skipped(audits: Path, registry_aligned: Path):
    (audits / "2026-13-01-money.md").write_text("bad month\n", encoding="utf-8")
    r = run_script(SWEEP_STATUS, "--check", "--audits", str(audits), "--registry", str(registry_aligned))
    assert r.returncode == 0, r.stderr
    assert "skipping 2026-13-01-money.md" in r.stderr
    assert "5 dated reports" in r.stdout


def test_check_exits_1_on_planted_divergence(audits: Path, registry_divergent: Path):
    r = run_script(SWEEP_STATUS, "--check", "--audits", str(audits), "--registry", str(registry_divergent))
    assert r.returncode == 1, r.stderr
    assert "unaudited-zones" in r.stderr
    assert "1 divergent" in r.stdout
    assert "registry text differs from reports" in r.stdout
    assert "no report matches slug" in r.stdout  # superadmin: noted, not a divergence


def test_check_exits_0_once_registry_matches_reports(audits: Path, registry_aligned: Path):
    r = run_script(SWEEP_STATUS, "--check", "--audits", str(audits), "--registry", str(registry_aligned))
    assert r.returncode == 0, r.stderr
    assert "0 divergent" in r.stdout
    assert "5 zones, 5 dated reports" in r.stdout


def test_without_check_divergence_is_printed_but_exit_is_0(audits: Path, registry_divergent: Path):
    r = run_script(SWEEP_STATUS, "--audits", str(audits), "--registry", str(registry_divergent))
    assert r.returncode == 0, r.stderr
    assert "1 divergent" in r.stdout


def test_stale_zones_are_flagged_without_failing_check(audits: Path, registry_aligned: Path):
    r = run_script(SWEEP_STATUS, "--check", "--stale-days", "40", "--audits", str(audits), "--registry", str(registry_aligned))
    assert r.returncode == 0, r.stderr
    assert "2 stale" in r.stdout  # money (50 days) and unaudited-zones (44 days)
    stale_lines = [line for line in r.stdout.splitlines() if "stale > 40d" in line]
    assert sorted(line.split()[0] for line in stale_lines) == ["money", "unaudited-zones"]


def test_default_registry_path_is_inside_audits(audits: Path):
    (audits / "sweep-registry.md").write_text(REGISTRY_ALIGNED, encoding="utf-8")
    r = run_script(SWEEP_STATUS, "--check", "--audits", str(audits))
    assert r.returncode == 0, r.stderr


def test_exit_2_when_audits_folder_missing(tmp_path: Path, registry_aligned: Path):
    r = run_script(SWEEP_STATUS, "--audits", str(tmp_path / "missing"), "--registry", str(registry_aligned))
    assert r.returncode == 2
    assert "audits folder not found" in r.stderr


def test_exit_2_when_registry_missing(audits: Path, tmp_path: Path):
    r = run_script(SWEEP_STATUS, "--audits", str(audits), "--registry", str(tmp_path / "nope.md"))
    assert r.returncode == 2
    assert "registry not found" in r.stderr


def test_exit_2_when_registry_has_no_candidate_rows(audits: Path, tmp_path: Path):
    path = tmp_path / "empty.md"
    path.write_text("# Sweep registry\n\n## Candidate zones\n\n(none yet)\n", encoding="utf-8")
    r = run_script(SWEEP_STATUS, "--audits", str(audits), "--registry", str(path))
    assert r.returncode == 2
    assert "no candidate rows" in r.stderr


def test_exit_2_when_fewer_reports_than_min(audits: Path, registry_aligned: Path):
    r = run_script(SWEEP_STATUS, "--min-reports", "10", "--audits", str(audits), "--registry", str(registry_aligned))
    assert r.returncode == 2
    assert "extraction looks broken" in r.stderr


def test_first_run_with_no_report_and_no_declared_run_is_not_an_error(tmp_path: Path):
    # Seen on every bootstrap: the registry is written before the first report exists
    audits = tmp_path / "audits"
    audits.mkdir()
    (audits / "sweep-registry.md").write_text(
        "## Candidates\n\n| Zone | Argument | Last run | Yield |\n|---|---|---|---|\n| `money` | billing | | |\n",
        encoding="utf-8",
    )
    r = run_script(SWEEP_STATUS, "--check", "--audits", str(audits))
    assert r.returncode == 0, r.stderr
    assert "no reports yet (first run): 1 zone(s)" in r.stdout
    assert "extraction looks broken" not in r.stderr
    # A declared run with no report is still a problem, not a first run
    (audits / "sweep-registry.md").write_text(
        "## Candidates\n\n| Zone | Argument | Last run | Yield |\n|---|---|---|---|\n| `money` | billing | 2026-01-15 | 1/1 |\n",
        encoding="utf-8",
    )
    r = run_script(SWEEP_STATUS, "--check", "--audits", str(audits))
    assert r.returncode == 2
    assert "extraction looks broken" in r.stderr


# --------------------------------------------------------------------------------------
# fresh_code.py
# --------------------------------------------------------------------------------------


def git_env(tmp_path: Path, author: str) -> dict:
    """Isolated git environment: no user or system config, no discovery above tmp_path."""
    env = dict(os.environ)
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CEILING_DIRECTORIES": str(tmp_path),
            "GIT_AUTHOR_NAME": author,
            "GIT_AUTHOR_EMAIL": f"{author.lower().replace(' ', '.')}@example.invalid",
            "GIT_COMMITTER_NAME": author,
            "GIT_COMMITTER_EMAIL": f"{author.lower().replace(' ', '.')}@example.invalid",
        }
    )
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def git(repo: Path, env: dict, *args: str) -> None:
    subprocess.run(["git", "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", *args], cwd=repo, env=env, check=True, capture_output=True, text=True)


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path):
    """Three commits.

    1. thirty days old, author One: src/legacy.py
    2. now, author One: src/billing.py, src/auth.py, tests/test_billing.py, README.md
    3. now, author Two: src/billing.py changed again

    tests/test_billing.py mentions `billing` and nothing else, so within the default three
    day window billing is "mentioned by a test" and auth is not.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    one = git_env(tmp_path, "Reviewer One")
    two = git_env(tmp_path, "Reviewer Two")
    git(repo, one, "init", "-q")

    old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    aged = dict(one, GIT_AUTHOR_DATE=old, GIT_COMMITTER_DATE=old)
    write(repo, "src/legacy.py", "def legacy():\n    return 1\n")
    git(repo, aged, "add", "-A")
    git(repo, aged, "commit", "-q", "-m", "legacy module")

    write(repo, "src/billing.py", "def charge(amount):\n    return amount\n")
    write(repo, "src/auth.py", "def login(user):\n    return user\n")
    write(repo, "tests/test_billing.py", "from src import billing\n\n\ndef test_charge():\n    assert billing.charge(1) == 1\n")
    write(repo, "README.md", "# demo\n")
    git(repo, one, "add", "-A")
    git(repo, one, "commit", "-q", "-m", "billing and login")

    write(repo, "src/billing.py", "def charge(amount):\n    return amount * 2\n")
    git(repo, two, "add", "-A")
    git(repo, two, "commit", "-q", "-m", "billing follow-up")
    return repo, one


def fresh(repo_and_env, *args: str) -> subprocess.CompletedProcess:
    repo, env = repo_and_env
    return run_script(FRESH_CODE, *args, cwd=repo, env=env)


def fresh_json(repo_and_env, *args: str) -> dict:
    r = fresh(repo_and_env, "--json", *args)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_is_test_and_under_helpers():
    assert fresh_code.is_test("tests/test_billing.py")
    assert fresh_code.is_test("src/__tests__/foo.spec.ts")
    assert fresh_code.is_test("src/guards/tenancy.guard.ts")
    assert not fresh_code.is_test("src/billing.py")
    assert fresh_code.under("src/billing.py", [])
    assert fresh_code.under("src/billing.py", ["src"])
    assert fresh_code.under("src/billing.py", ["src/"])
    assert fresh_code.under("src", ["src"])
    assert not fresh_code.under("lib/billing.py", ["src"])
    assert not fresh_code.under("srcdir/billing.py", ["src"])


def test_ranks_by_commits_and_counts_authors(repo):
    out = fresh_json(repo)
    assert out["days"] == 3
    files = {f["file"]: f for f in out["files"]}
    assert list(files) == ["src/billing.py", "src/auth.py"]
    assert files["src/billing.py"]["commits"] == 2
    assert files["src/billing.py"]["authors"] == 2
    assert files["src/auth.py"]["commits"] == 1
    assert files["src/auth.py"]["authors"] == 1
    assert out["dirs"] == [["src", 3]]


def test_excludes_test_files_and_non_source_extensions(repo):
    names = [f["file"] for f in fresh_json(repo)["files"]]
    assert "tests/test_billing.py" not in names
    assert "README.md" not in names


def test_test_mention_flag_positive_and_negative(repo):
    files = {f["file"]: f for f in fresh_json(repo)["files"]}
    assert files["src/billing.py"]["test_mentions"] is True
    assert files["src/auth.py"]["test_mentions"] is False


def test_test_mention_flag_depends_on_test_roots(repo):
    files = {f["file"]: f for f in fresh_json(repo, "--tests", "nowhere")["files"]}
    assert files["src/billing.py"]["test_mentions"] is False
    assert files["src/auth.py"]["test_mentions"] is False


def test_days_window_excludes_then_includes_the_old_commit(repo):
    assert "src/legacy.py" not in [f["file"] for f in fresh_json(repo, "--days", "3")["files"]]
    wide = {f["file"]: f for f in fresh_json(repo, "--days", "60")["files"]}
    assert wide["src/legacy.py"]["commits"] == 1
    assert wide["src/legacy.py"]["test_mentions"] is False


def test_top_and_src_filters(repo):
    assert [f["file"] for f in fresh_json(repo, "--top", "1")["files"]] == ["src/billing.py"]
    assert len(fresh_json(repo, "--src", "src")["files"]) == 2
    assert fresh_json(repo, "--src", "lib")["files"] == []


def test_text_output_marks_untested_files(repo):
    r = fresh(repo)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    billing = next(line for line in lines if line.endswith("src/billing.py"))
    auth = next(line for line in lines if line.endswith("src/auth.py"))
    assert "yes" in billing
    assert "NO" in auth
    assert "1 changed files not mentioned by any test; read these first." in r.stdout
    assert "churn by directory:" in r.stdout


def test_exit_2_in_a_repository_with_no_commits(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    env = git_env(tmp_path, "Nobody")
    git(empty, env, "init", "-q")
    r = run_script(FRESH_CODE, cwd=empty, env=env)
    assert r.returncode == 2, r.stdout
    assert "git log failed" in r.stderr


def test_test_mention_is_a_whole_word_match(tmp_path: Path):
    repo = tmp_path / "repo2"
    repo.mkdir()
    env = git_env(tmp_path, "Reviewer One")
    git(repo, env, "init", "-q")
    write(repo, "src/app.py", "x = 1\n")
    write(repo, "src/db.py", "y = 2\n")
    write(repo, "tests/test_misc.py", "# the application talks to the db\n")
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "init")
    files = {f["file"]: f for f in fresh_json((repo, env))["files"]}
    assert files["src/app.py"]["test_mentions"] is False  # "application" is not "app"
    assert files["src/db.py"]["test_mentions"] is True


def test_exit_2_outside_a_git_repository(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    r = run_script(FRESH_CODE, cwd=plain, env=git_env(tmp_path, "Nobody"))
    assert r.returncode == 2
    assert "not a git repository" in r.stderr


# --------------------------------------------------------------------------------------
# Both scripts
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("script", [SWEEP_STATUS, FRESH_CODE, SCRIPTS / "check_citations.py", SCRIPTS / "findings.py"], ids=lambda p: p.name)
def test_help_exits_0_and_documents_usage(script: Path):
    r = run_script(script, "--help")
    assert r.returncode == 0, r.stderr
    assert "usage:" in r.stdout
    assert script.name in r.stdout  # the docstring shows invocation examples


def imported_top_level_modules(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("script", [SWEEP_STATUS, FRESH_CODE, SCRIPTS / "check_citations.py", SCRIPTS / "findings.py"], ids=lambda p: p.name)
def test_scripts_use_only_the_standard_library(script: Path):
    stdlib = Path(sysconfig.get_paths()["stdlib"]).resolve()
    siblings = {p.stem for p in SCRIPTS.glob("*.py")}  # the scripts ship together and may import each other
    for name in sorted(imported_top_level_modules(script)):
        if name in siblings:
            continue
        spec = importlib.util.find_spec(name)
        assert spec is not None, f"{script.name} imports {name}, which is not importable here"
        origin = spec.origin or ""
        if origin in ("built-in", "frozen", ""):
            continue
        assert Path(origin).resolve().is_relative_to(stdlib), f"{script.name} imports {name} from {origin}, outside the standard library"


def test_fresh_code_reads_rust_and_explains_an_empty_list(tmp_path: Path):
    # From a field report (2026-10-28): a Rust workspace, single commit; the script listed 0 files
    # and said nothing, and the run blamed the single commit. Two causes, two answers: `.rs` is a
    # listed extension now, and a list emptied by the extension filter says what it filtered.
    repo = tmp_path / "rs"
    repo.mkdir()
    env = git_env(tmp_path, "Reviewer One")
    git(repo, env, "init", "-q")
    write(repo, "core/src/packet.rs", "pub fn parse() {}\n" * 40)
    write(repo, "core/src/lib.rs", "mod packet;\n")
    write(repo, "core/tests/packet_test.rs", "#[test] fn packet() {}\n")
    write(repo, "notes.proto", "message A {}\n")
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "import")
    d = json.loads(run_script(FRESH_CODE, "--json", cwd=repo, env=env).stdout)
    files = [r["file"] for r in d["files"]]
    assert files == ["core/src/lib.rs", "core/src/packet.rs"] or files == ["core/src/packet.rs", "core/src/lib.rs"]
    # every commit inside the window: size ranks, untested first; lib.rs is untested and small,
    # packet.rs is mentioned by the test and large
    assert files[0] == "core/src/lib.rs"
    assert "every commit of the repository (1) is inside the window" in d["note"]
    r = run_script(FRESH_CODE, cwd=repo, env=env)
    assert "ranked by size" in r.stdout and "note:" in r.stdout
    # the same tree with only an unlisted extension changed: the empty list is explained
    d = json.loads(run_script(FRESH_CODE, "--json", "--src", "nowhere", cwd=repo, env=env).stdout)
    assert d["files"] == []
    repo2 = tmp_path / "proto"
    repo2.mkdir()
    git(repo2, env, "init", "-q")
    write(repo2, "schema/a.proto", "message A {}\n")
    git(repo2, env, "add", "-A")
    git(repo2, env, "commit", "-q", "-m", "schema")
    r = run_script(FRESH_CODE, cwd=repo2, env=env)
    assert r.returncode == 0
    assert "filtered out by extension: .proto (1)" in r.stdout
    d = json.loads(run_script(FRESH_CODE, "--json", "--ext", ".proto", cwd=repo2, env=env).stdout)
    assert [x["file"] for x in d["files"]] == ["schema/a.proto"]


# --------------------------------------------------------------------------------------
# check_citations.py
# --------------------------------------------------------------------------------------

CHECK_CITATIONS = SCRIPTS / "check_citations.py"


@pytest.fixture()
def cited_repo(tmp_path: Path) -> Path:
    root = tmp_path / "app"
    (root / "app" / "routes").mkdir(parents=True)
    (root / "app" / "data").mkdir(parents=True)
    (root / "node_modules" / "lib").mkdir(parents=True)
    (root / "app" / "routes" / "allocations.js").write_text(
        "".join(f"// line {i}\n" for i in range(1, 16))
        + "function handler(req, res) {\n"
        + "  const {\n"
        + "    userId\n"
        + "  } = req.params;\n"
        + "}\n",
        encoding="utf-8",
    )
    (root / "app" / "data" / "profile-dao.js").write_text("x\n" * 113, encoding="utf-8")
    (root / "app" / "routes" / "session.js").write_text("s\n" * 40, encoding="utf-8")
    (root / "app" / "data" / "session.js").write_text("d\n" * 40, encoding="utf-8")
    # A dependency with the same name as application code must not make a citation ambiguous
    (root / "node_modules" / "lib" / "allocations.js").write_text("y\n", encoding="utf-8")
    (root / "docs").mkdir()
    return root


def write_report(root: Path, body: str) -> Path:
    report = root / "docs" / "report.md"
    report.write_text(body, encoding="utf-8")
    return report


def test_citations_resolve_and_show_the_cited_text(cited_repo: Path):
    report = write_report(cited_repo, "Location `app/routes/allocations.js:19`, chain `allocations.js:16-19,20`.\n")
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(cited_repo))
    assert r.returncode == 0, r.stdout
    assert "OK            R:1    app/routes/allocations.js:19  | } = req.params;" in r.stdout
    assert "allocations.js:16-19,20 -> app/routes/allocations.js  | function handler(req, res) {" in r.stdout
    assert "2 citation(s), 0 not OK" in r.stdout


def test_line_past_the_end_of_the_file_fails(cited_repo: Path):
    # Reproduces the defect seen in an evaluation run: a range cited in a 113-line file
    report = write_report(cited_repo, "Read and clean: `profile-dao.js:168-189`.\n")
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(cited_repo))
    assert r.returncode == 1
    assert "OUT OF RANGE" in r.stdout and "file has 113 lines" in r.stdout


def test_backwards_range_and_line_zero_fail(cited_repo: Path):
    report = write_report(cited_repo, "`app/routes/allocations.js:19-16` and `app/routes/allocations.js:0`\n")
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(cited_repo), "--quiet")
    assert r.returncode == 1
    assert r.stdout.count("OUT OF RANGE") == 2


def test_shortened_path_matching_several_files_is_ambiguous(cited_repo: Path):
    report = write_report(cited_repo, "See `session.js:12`, then `routes/session.js:12`.\n")
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(cited_repo))
    assert r.returncode == 1
    assert "AMBIGUOUS     R:1    session.js:12" in r.stdout
    assert "routes/session.js:12 -> app/routes/session.js" in r.stdout


def test_missing_file_and_approximate_line_fail(cited_repo: Path):
    report = write_report(cited_repo, "`app/data/memos-dao.js:3` and `app/data/profile-dao.js:~63-82`\n")
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(cited_repo), "--quiet")
    assert r.returncode == 1
    assert "MISSING" in r.stdout and "APPROXIMATE" in r.stdout


def test_urls_addresses_and_times_are_not_citations(cited_repo: Path):
    addr = ".".join(["127", "0", "0", "1"])
    web = "https" + ":"  # assembled so this file does not itself hold a URL
    report = write_report(
        cited_repo,
        f"Started on {addr}:4000 at 10:30; see {web}//example.invalid/app.js:12 and {web}//localhost:3000.\n",
    )
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(cited_repo))
    assert r.returncode == 0, r.stdout
    assert "no file:line citations found" in r.stdout


def test_missing_report_is_a_setup_error(tmp_path: Path):
    r = run_script(CHECK_CITATIONS, str(tmp_path / "nope.md"), "--root", str(tmp_path))
    assert r.returncode == 2
    assert "report not found" in r.stderr


# Credential-like lines: the five shapes seen in an external review run, none of which the
# key-like rule alone catches, plus one key-like token. The values below are invented.
SECRET_VALUES = {
    "dsn_default": "postgresql://app:hunter2pw@db/app",
    "app_password": "abcd efgh ijkl mnop",
    "dotenv_key": "dev-secret-12",
    "dotenv_admin": "apple",
    "keylike": "sk_live_" + "A1b2C3d4" * 4,
}


@pytest.fixture()
def secret_repo(tmp_path: Path) -> Path:
    root = tmp_path / "svc"
    (root / "app" / "seeds").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "app" / "config.py").write_text(
        "import os\n"
        f'DATABASE_URL = os.getenv("DATABASE_URL", "{SECRET_VALUES["dsn_default"]}")\n'
        f'API_KEY = "{SECRET_VALUES["keylike"]}"\n'
        "SECRET_KEY = settings.SECRET_KEY\n",
        encoding="utf-8",
    )
    (root / "app" / "seeds" / "smtp_seed.py").write_text(
        "config = SMTPConfiguration(\n"
        '    username="mailer@example.invalid",\n'
        f'    password="{SECRET_VALUES["app_password"]}",\n'
        ")\n",
        encoding="utf-8",
    )
    (root / "app" / ".env").write_text(
        f"SECRET_KEY={SECRET_VALUES['dotenv_key']}\nADMIN_PASSWORD={SECRET_VALUES['dotenv_admin']}\n",
        encoding="utf-8",
    )
    return root


def test_credential_like_lines_are_printed_masked(secret_repo: Path):
    report = write_report(
        secret_repo,
        "F1 `app/config.py:2`, F2 `app/seeds/smtp_seed.py:3`, F3 `app/.env:1`, F4 `app/.env:2`, "
        "F5 `app/config.py:3`; plain `app/config.py:4` and `app/seeds/smtp_seed.py:2`.\n",
    )
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(secret_repo))
    assert r.returncode == 0, r.stdout
    for value in SECRET_VALUES.values():
        assert value not in r.stdout
    assert r.stdout.count("OK (masked)") == 5
    assert 'DATABASE_URL = os.getenv("DATABASE_URL", "<masked, 33 chars>")' in r.stdout
    assert 'password="<masked, 19 chars>"' in r.stdout
    assert "SECRET_KEY=<masked, 13 chars>" in r.stdout
    assert "ADMIN_PASSWORD=<masked, 5 chars>" in r.stdout
    assert 'API_KEY = "<masked, 40 chars>"' in r.stdout
    # A reference to configuration and a username are printed as they are
    assert "OK            R:1    app/config.py:4  | SECRET_KEY = settings.SECRET_KEY" in r.stdout
    assert 'username="mailer@example.invalid"' in r.stdout
    assert "7 citation(s), 0 not OK" in r.stdout


def test_quiet_hides_masked_rows_too(secret_repo: Path):
    report = write_report(secret_repo, "`app/.env:1` and `app/config.py:99`.\n")
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(secret_repo), "--quiet")
    assert r.returncode == 1
    assert "app/.env:1" not in r.stdout
    assert "OUT OF RANGE" in r.stdout
    for value in SECRET_VALUES.values():
        assert value not in r.stdout


def test_sensitive_predicate_shapes():
    cc = _load(CHECK_CITATIONS)
    assert cc.needs_mask("app/.env", "ADMIN_PASSWORD=apple")
    assert not cc.needs_mask("app/.env", "# ADMIN_PASSWORD is set at deploy time")
    assert cc.needs_mask("settings.yaml", "smtp_password: abcd efgh")
    assert not cc.needs_mask("settings.yaml", "smtp_host: smtp.example.invalid")
    assert cc.needs_mask("app.py", '"password": "abc def"')
    assert not cc.needs_mask("app.py", '"password":')
    assert not cc.needs_mask("app.py", 'password = request.form["password"]')
    assert not cc.needs_mask("app.py", "token = secrets.token_urlsafe(32)")
    assert cc.needs_mask("app.py", "conn = connect('postgresql://user:hunter2@db/app')")
    assert cc.mask("conn = connect('postgresql://user:hunter2@db/app')") == "conn = connect('<masked, 32 chars>')"
    assert cc.mask("DATABASE_URL=postgres://app:pw@db/app", "app/.env") == "DATABASE_URL=<masked, 24 chars>"


# --------------------------------------------------------------------------------------
# findings.py
# --------------------------------------------------------------------------------------

FINDINGS = SCRIPTS / "findings.py"
PY = shlex.quote(sys.executable)


@pytest.fixture()
def findings_repo(tmp_path: Path) -> Path:
    root = tmp_path / "svc"
    audits = root / "docs" / "audits"
    audits.mkdir(parents=True)
    (root / "app.py").write_text(
        "import db\n\n\ndef get_invoice(user, invoice_id):\n    return db.find(id=invoice_id)\n",
        encoding="utf-8",
    )
    # The reproduction fails while the defect is present: no owner filter in app.py
    (root / "t_repro.py").write_text(
        "import sys\nsys.exit(0 if 'owner=' in open('app.py').read() else 1)\n", encoding="utf-8"
    )
    (root / "t_guard.py").write_text(
        "import pathlib, sys\np = pathlib.Path('guard_rc')\nsys.exit(int(p.read_text()) if p.exists() else 0)\n",
        encoding="utf-8",
    )
    (audits / "2026-01-15-money.md").write_text(
        "# Verified security sweep: money, 2026-01-15\n\n## Verification\n"
        "| Finding | Zone | Verdict |\n|---|---|---|\n| F1 invoice read across tenants | money | VERIFIED REAL |\n\n"
        "## Confirmed defects\nF1 at `app.py:5`.\n",
        encoding="utf-8",
    )
    write_index(root, [finding_entry()])
    return root


def finding_entry(**changes) -> dict:
    entry = {
        "id": "2026-01-15-money/F1", "report": "2026-01-15-money.md", "zone": "money",
        "title": "Any user can read another tenant's invoice", "severity": "High",
        "category": "authorization", "cwe": "CWE-639", "location": "app.py:5",
        "snippet": "return db.find(id=invoice_id)",
        "reproduce": f"{PY} t_repro.py", "guard": f"{PY} t_guard.py", "status": "open",
    }
    entry.update(changes)
    return entry


def write_index(root: Path, entries: list) -> None:
    (root / "docs" / "audits" / "findings.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8"
    )


def run_findings(root: Path, *args: str) -> subprocess.CompletedProcess:
    return run_script(FINDINGS, *args, "--root", str(root))


def test_findings_check_accepts_a_valid_entry(findings_repo: Path):
    r = run_findings(findings_repo, "check")
    assert r.returncode == 0, r.stdout
    assert "OK    2026-01-15-money/F1  app.py:5 (working tree)  | return db.find(id=invoice_id)" in r.stdout


def test_findings_check_fails_when_the_cited_line_does_not_hold_the_snippet(findings_repo: Path):
    # The defect seen in evaluation runs: a citation that exists but points at the next line
    write_index(findings_repo, [finding_entry(location="app.py:4")])
    (findings_repo / "docs" / "audits" / "2026-01-15-money.md").write_text(
        "| F1 | money | VERIFIED REAL |\nF1 at `app.py:4`.\n", encoding="utf-8"
    )
    r = run_findings(findings_repo, "check")
    assert r.returncode == 1
    assert "does not hold the snippet; the line reads: def get_invoice(user, invoice_id):" in r.stdout


def test_findings_check_refuses_a_literal_next_to_a_secret_name(findings_repo: Path):
    (findings_repo / "app.py").write_text(
        'import db\n\n\ndef get_invoice(user, invoice_id):\n    return connect("postgresql://app:hunter2pw@db/app")\n',
        encoding="utf-8",
    )
    write_index(findings_repo, [finding_entry(snippet='connect("postgresql://app:hunter2pw@db/app")')])
    r = run_findings(findings_repo, "check")
    assert r.returncode == 1
    assert "hunter2pw" not in r.stdout
    assert "quote the part of the line without it" in r.stdout
    write_index(findings_repo, [finding_entry(snippet='"password": "abc def"', location="app.py:5")])
    r = run_findings(findings_repo, "check")
    assert r.returncode == 1
    assert "literal value next to a listed name" in r.stdout
    assert "abc def" not in r.stdout.split("literal value")[0]


def test_findings_check_accepts_a_secret_name_without_its_value(findings_repo: Path):
    (findings_repo / "app.py").write_text(
        'import db\n\n\ndef get_invoice(user, invoice_id):\n    return {"password": "abc def"}\n', encoding="utf-8"
    )
    write_index(findings_repo, [finding_entry(snippet='"password":')])
    r = run_findings(findings_repo, "check")
    assert r.returncode == 0, r.stdout
    assert "abc def" not in r.stdout


def test_findings_check_masks_the_line_it_reads_when_it_looks_like_a_credential(findings_repo: Path):
    (findings_repo / "app.py").write_text(
        'import db\nPASSWORD = "hunter2pw"\n\ndef get_invoice(user, invoice_id):\n    return db.find(id=invoice_id)\n',
        encoding="utf-8",
    )
    write_index(findings_repo, [finding_entry(location="app.py:2")])
    (findings_repo / "docs" / "audits" / "2026-01-15-money.md").write_text(
        "| F1 | money | VERIFIED REAL |\nF1 at `app.py:2`.\n", encoding="utf-8"
    )
    r = run_findings(findings_repo, "check")
    assert r.returncode == 1
    assert "hunter2pw" not in r.stdout
    assert 'the line reads: PASSWORD = "<masked, 9 chars>"' in r.stdout


def test_findings_check_reports_bad_fields_duplicates_and_count_mismatch(findings_repo: Path):
    write_index(findings_repo, [finding_entry(), finding_entry(severity="Urgent"), {"id": "x"}])
    (findings_repo / "docs" / "audits" / "findings.jsonl").open("a").write("{not json\n")
    r = run_findings(findings_repo, "check")
    assert r.returncode == 1
    assert "severity 'Urgent'" in r.stdout
    assert "duplicate id" in r.stdout
    assert "missing field 'report'" in r.stdout
    assert "not valid JSON" in r.stdout
    assert "1 VERIFIED REAL row(s) in the report, 2 entr(y/ies) in the index" in r.stdout


def test_findings_check_needs_the_report_to_cite_the_location(findings_repo: Path):
    (findings_repo / "docs" / "audits" / "2026-01-15-money.md").write_text("| F1 | money | VERIFIED REAL |\n", encoding="utf-8")
    r = run_findings(findings_repo, "check")
    assert r.returncode == 1
    assert "does not cite app.py:5" in r.stdout


def test_recheck_lists_commands_and_runs_nothing_without_run(findings_repo: Path):
    r = run_findings(findings_repo, "recheck")
    assert r.returncode == 0
    assert "reproduce: " in r.stdout and "nothing was run" in r.stdout
    assert not (findings_repo / "docs" / "audits" / "recheck-log.jsonl").exists()


def test_recheck_open_then_fixed_and_the_log_keeps_both(findings_repo: Path):
    r = run_findings(findings_repo, "recheck", "--run", "--write", "--fail-on-open")
    assert r.returncode == 1, r.stdout
    assert "OPEN" in r.stdout and "reproduction still fails" in r.stdout
    app = findings_repo / "app.py"
    app.write_text(app.read_text().replace("id=invoice_id", "id=invoice_id, owner=user"), encoding="utf-8")
    r = run_findings(findings_repo, "recheck", "--run", "--write", "--fail-on-open")
    assert r.returncode == 0, r.stdout
    assert "FIXED" in r.stdout
    log = (findings_repo / "docs" / "audits" / "recheck-log.jsonl").read_text().splitlines()
    assert [json.loads(x)["result"] for x in log] == ["open", "fixed"]


def test_recheck_failing_guard_is_inconclusive_not_open(findings_repo: Path):
    (findings_repo / "guard_rc").write_text("1", encoding="utf-8")
    r = run_findings(findings_repo, "recheck", "--run", "--fail-on-open")
    assert r.returncode == 0
    assert "INCONCLUSIVE" in r.stdout and "guard failed" in r.stdout


def test_recheck_write_needs_run(findings_repo: Path):
    r = run_findings(findings_repo, "recheck", "--write")
    assert r.returncode == 2


def test_sarif_lists_open_findings_and_drops_fixed_ones(findings_repo: Path):
    r = run_findings(findings_repo, "sarif")
    assert r.returncode == 0
    doc = json.loads(r.stdout)
    assert doc["version"] == "2.1.0"
    (res,) = doc["runs"][0]["results"]
    assert res["level"] == "error" and res["ruleId"] == "authorization"
    assert res["locations"][0]["physicalLocation"]["region"]["startLine"] == 5
    assert doc["runs"][0]["tool"]["driver"]["rules"][0]["properties"]["tags"] == ["external/cwe/cwe-639"]
    (findings_repo / "docs" / "audits" / "recheck-log.jsonl").write_text(
        json.dumps({"id": "2026-01-15-money/F1", "result": "fixed"}) + "\n", encoding="utf-8"
    )
    assert json.loads(run_findings(findings_repo, "sarif").stdout)["runs"][0]["results"] == []
    assert len(json.loads(run_findings(findings_repo, "sarif", "--all").stdout)["runs"][0]["results"]) == 1


def test_findings_without_index_is_a_setup_error(tmp_path: Path):
    (tmp_path / "docs" / "audits").mkdir(parents=True)
    r = run_findings(tmp_path, "check")
    assert r.returncode == 2
    assert "no findings index" in r.stderr


def commit_all(root: Path, env: dict, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=root, env=env, check=True)
    subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", message], cwd=root, env=env, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture()
def pinned_repo(findings_repo: Path, tmp_path: Path) -> tuple[Path, dict, str]:
    env = git_env(tmp_path, "Reviewer")
    subprocess.run(["git", "init", "-q"], cwd=findings_repo, env=env, check=True)
    sha = commit_all(findings_repo, env, "service")
    write_index(findings_repo, [finding_entry(commit=sha)])
    return findings_repo, env, sha


def test_check_holds_after_the_code_moves_because_it_reads_the_entry_commit(pinned_repo):
    root, env, sha = pinned_repo
    app = root / "app.py"
    app.write_text("# header\n# moved two lines down\n" + app.read_text(), encoding="utf-8")
    commit_all(root, env, "unrelated edit above the finding")
    r = run_script(FINDINGS, "check", "--root", str(root), env=env)
    assert r.returncode == 0, r.stdout
    assert f"app.py:5 @{sha[:12]}" in r.stdout
    r = run_script(FINDINGS, "recheck", "--root", str(root), env=env)
    assert "now at app.py:7" in r.stdout


def test_citations_are_checked_at_the_commit_the_report_names(pinned_repo, tmp_path: Path):
    # From a field report (2026-10-28): after the fixes, check_citations.py still returned
    # 55 OK on the sweep report while every cited line showed unrelated code, because it read
    # the working tree. A report that names its commit in Context is checked at that commit.
    root, env, sha = pinned_repo
    app = root / "app.py"
    cited = app.read_text(encoding="utf-8").splitlines()[4].strip()
    report = root / "docs" / "audits" / "2026-01-15-money.md"
    report.write_text(f"# Verified security sweep: money, 2026-01-15\n\n## Context\nCommit: `{sha}`\n\n"
                      f"## Confirmed defects\nF1 at `app.py:5`\n", encoding="utf-8")
    app.write_text("# header\n# moved two lines down\n" + app.read_text(encoding="utf-8"), encoding="utf-8")
    commit_all(root, env, "unrelated edit above the finding")
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(root), env=env)
    assert r.returncode == 0, r.stdout
    assert r.stdout.startswith(f"lines read at {sha[:12]}; the working tree is at ")
    assert f"app.py:5  | {cited}" in r.stdout
    # the working tree, forced, shows the moved line instead
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(root), "--rev", "", env=env)
    assert f"app.py:5  | {cited}" not in r.stdout
    # a commit the clone does not have: warning, working tree
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(root), "--rev", "0" * 40, env=env)
    assert "is not in this clone; lines read from the working tree" in r.stdout
    # the external-review form names the commit too
    report.write_text(report.read_text(encoding="utf-8").replace(f"Commit: `{sha}`", f"External review: yes, at {sha}, permalinks https://github.com/healthchecks/healthchecks/blob/{sha}/"), encoding="utf-8")
    r = run_script(CHECK_CITATIONS, str(report), "--root", str(root), env=env)
    assert f"app.py:5  | {cited}" in r.stdout


def test_recheck_reports_changed_code_once_the_fix_lands(pinned_repo):
    root, env, _ = pinned_repo
    app = root / "app.py"
    app.write_text(app.read_text().replace("id=invoice_id", "id=invoice_id, owner=user"), encoding="utf-8")
    commit_all(root, env, "fix")
    r = run_script(FINDINGS, "recheck", "--run", "--write", "--root", str(root), env=env)
    assert "FIXED" in r.stdout and "the snippet is no longer in app.py" in r.stdout
    log = json.loads((root / "docs" / "audits" / "recheck-log.jsonl").read_text().splitlines()[-1])
    assert log["result"] == "fixed" and log["where"].startswith("the code at app.py:5 changed")
    assert run_script(FINDINGS, "check", "--root", str(root), env=env).returncode == 0  # history stays valid


def test_a_commit_missing_from_the_clone_is_skipped_unless_strict(pinned_repo):
    # Squash merges, rebases and shallow clones remove commits; the entry is not wrong, only
    # unverifiable here.
    root, env, _ = pinned_repo
    write_index(root, [finding_entry(commit="0" * 40)])
    r = run_script(FINDINGS, "check", "--root", str(root), env=env)
    assert r.returncode == 0, r.stdout
    assert "SKIP  2026-01-15-money/F1: commit " + "0" * 40 + " is not in this clone" in r.stdout
    r = run_script(FINDINGS, "check", "--strict", "--root", str(root), env=env)
    assert r.returncode == 1


def test_guard_is_required(findings_repo: Path):
    entry = finding_entry()
    del entry["guard"]
    write_index(findings_repo, [entry])
    r = run_findings(findings_repo, "check")
    assert r.returncode == 1 and "missing field 'guard'" in r.stdout
    r = run_findings(findings_repo, "recheck", "--run")
    assert "INCONCLUSIVE" in r.stdout and "no guard recorded" in r.stdout


@pytest.mark.parametrize("command", [
    "bash t_repro.py", "sh -x t_repro.py", f"{PY} -c print(1)", "node -e 1", "npx -c true",
])
def test_shells_and_inline_code_are_refused(findings_repo: Path, command: str):
    write_index(findings_repo, [finding_entry(reproduce=command)])
    r = run_findings(findings_repo, "check")
    assert r.returncode == 1 and "write the reproduction as a test" in r.stdout
    marker = findings_repo / "ran"
    r = run_findings(findings_repo, "recheck", "--run")
    assert "INCONCLUSIVE" in r.stdout and "not run:" in r.stdout
    assert not marker.exists()


def test_ordinary_runner_commands_are_not_refused():
    findings = _load(FINDINGS)
    for command in ("python3 manage.py test hc.api", "npx vitest run tests/a.test.ts -t 'own invoice'",
                    "pytest -c pytest.ini tests/test_scope.py", "bundle exec rspec spec/scope_spec.rb"):
        assert findings.refused(command) == "", command


def test_keylike_snippet_is_refused(findings_repo: Path):
    key = "sk" + "_live_" + "4eC39HqLyjWDarjtT1zdp7dc"
    (findings_repo / "app.py").write_text(f"import db\n\n\n\nKEY = '{key}'\n", encoding="utf-8")
    write_index(findings_repo, [finding_entry(snippet=key)])
    r = run_findings(findings_repo, "check")
    assert r.returncode == 1 and "holds a long token" in r.stdout


def test_recheck_log_records_uncommitted_changes_to_tracked_files_only(pinned_repo):
    # From a field report (2026-10-28): an untracked log outside the zone marked a run dirty.
    # Dirty is a tracked file that differs from the commit; untracked files change nothing the
    # recorded commands run on. The paths are printed.
    root, env, _ = pinned_repo
    run_script(FINDINGS, "recheck", "--run", "--write", "--root", str(root), env=env)
    (root / "scratch.txt").write_text("local edit\n", encoding="utf-8")
    run_script(FINDINGS, "recheck", "--run", "--write", "--root", str(root), env=env)
    tracked = next(p for p in root.rglob("*.py") if "docs" not in p.parts and "tests" not in p.parts)
    tracked.write_text(tracked.read_text(encoding="utf-8") + "# local edit\n", encoding="utf-8")
    r = run_script(FINDINGS, "recheck", "--run", "--write", "--root", str(root), env=env)
    assert "working tree dirty against" in r.stdout and tracked.name in r.stdout
    log = [json.loads(x) for x in (root / "docs" / "audits" / "recheck-log.jsonl").read_text().splitlines()]
    assert [x["dirty"] for x in log] == [False, False, True]


def test_sarif_points_at_the_current_line_with_a_stable_fingerprint(pinned_repo):
    root, env, _ = pinned_repo
    first = json.loads(run_script(FINDINGS, "sarif", "--root", str(root), env=env).stdout)["runs"][0]["results"][0]
    app = root / "app.py"
    app.write_text("# header\n" + app.read_text(), encoding="utf-8")
    later = json.loads(run_script(FINDINGS, "sarif", "--root", str(root), env=env).stdout)["runs"][0]["results"][0]
    assert first["locations"][0]["physicalLocation"]["region"]["startLine"] == 5
    assert later["locations"][0]["physicalLocation"]["region"]["startLine"] == 6
    assert first["partialFingerprints"] == later["partialFingerprints"]


def test_recheck_says_still_at_when_the_recorded_line_holds_the_snippet(pinned_repo):
    root, env, _ = pinned_repo
    r = run_script(FINDINGS, "recheck", "--root", str(root), env=env)
    assert "still at app.py:5" in r.stdout


# --------------------------------------------------------------------------------------
# check_report.py
# --------------------------------------------------------------------------------------

CHECK_REPORT = SCRIPTS / "check_report.py"

GOOD_REPORT = """# Verified security sweep: exports, 2026-01-15

## Context
Scope: the export download views under `app/exports/`, files `app/exports/views.py` and
`app/exports/urls.py`.

## Delegation
No reviewer; single small zone.

## Verification
| Finding | Zone | Verdict | Claimed | Verified | Reservations | Proof |
|---|---|---|---|---|---|---|
| F1 download is not scoped to the organization | exports | VERIFIED REAL | High | High | - | `test_scope.py`, ran, fails as expected |
| R1 missing rate limit on download | exports | FALSE POSITIVE | Medium | - | lens: existing mitigation | `app/exports/views.py:12` |
| R2 export job id is sequential | exports | NEEDS DEEPER REVIEW | Low | - | - | `app/exports/views.py:30` |

## Confirmed defects

### F1. Download is not scoped to the organization (High)
Location: `app/exports/views.py:57`. Reproduction: `test_scope.py`, ran, fails as expected.

## Refused or unconfirmed candidates
- R1, missing rate limit (`app/exports/views.py:12`): refused, lens existing mitigation. The
  gateway limits downloads.
- R2, sequential job ids (`app/exports/views.py:30`): needs deeper review. Deciding needs the
  deployment's URL exposure.
- R3, stale cron in `app/jobs/cleanup.py:8`: out of zone, proposed sweep of `jobs`.

## Coverage
Files read: `app/exports/views.py`, `app/exports/urls.py`. Skipped: `app/jobs/` (another zone).

## Hand-off
1. Fix F1 at `app/exports/views.py:57`, shipping `test_scope.py` alongside.
2. Proposed sweep of `jobs`: the stale cron at `app/jobs/cleanup.py:8`.
"""


def write_report(tmp_path: Path, text: str) -> Path:
    report = tmp_path / "2026-01-15-exports.md"
    report.write_text(text, encoding="utf-8")
    return report


def test_check_report_accepts_the_template_shape(tmp_path: Path):
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, GOOD_REPORT)))
    assert r.returncode == 0, r.stdout
    assert "3 verification rows (1 VERIFIED REAL), 3 refused entries" in r.stdout


def test_check_report_requires_anchors_on_an_external_review(tmp_path: Path):
    # From the first external run (a third party's repository): the citations of a delivered
    # record resolve only against the commit reviewed and a permalink base, and the run had to
    # decide both on the spot. "External review: yes" now needs them in Context.
    ctx = "## Context\n"
    declared = GOOD_REPORT.replace(ctx, ctx + "External review: yes. Asked by the maintainer; the reviewer is a user of the project.\n")
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, declared)))
    assert r.returncode == 1
    assert "EXTERNAL REVIEW WITHOUT ANCHOR" in r.stdout
    assert "the commit reviewed and the permalink base URL" in r.stdout
    anchored = GOOD_REPORT.replace(
        ctx, ctx + f"- **External review**: yes, at {bytes(range(6)).hex()}, permalinks https://github.com/healthchecks/healthchecks/blob/{bytes(range(6)).hex()}/.\n"
    )
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, anchored)))
    assert r.returncode == 0, r.stdout
    assert "external review, 0 problem(s)" in r.stdout
    # The owner's own repository declares nothing and is not asked for anchors
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, GOOD_REPORT.replace(ctx, ctx + "External review: no.\n"))))
    assert r.returncode == 0, r.stdout
    assert "external review" not in r.stdout


def test_check_report_flags_a_zone_lead_hidden_in_the_handoff(tmp_path: Path):
    text = GOOD_REPORT.replace(
        "2. Proposed sweep of `jobs`",
        "2. Seen, no verdict here: the threshold filter at `app/exports/views.py:78` reads other users' rows.\n"
        "3. Proposed sweep of `jobs`",
    )
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, text)))
    assert r.returncode == 1
    assert "LEAD WITHOUT VERDICT: hand-off cites app/exports/views.py:78" in r.stdout
    assert "app/jobs/cleanup.py:8" not in r.stdout  # another zone, named in Context's scope nowhere


def test_check_report_does_not_accept_a_citation_outside_the_verdict_sections(tmp_path: Path):
    # The loophole a v1.3.3 run used: the flagged line cited in a narrative section instead of
    # getting a verdict or a disposition.
    text = GOOD_REPORT.replace(
        "## Coverage\n",
        "## Recheck of earlier findings\nThe threshold filter at `app/exports/views.py:78` was also read.\n\n## Coverage\n",
    ).replace(
        "2. Proposed sweep of `jobs`",
        "2. Seen, no verdict here: the threshold filter at `app/exports/views.py:78`.\n3. Proposed sweep of `jobs`",
    )
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, text)))
    assert r.returncode == 1
    assert "LEAD WITHOUT VERDICT: hand-off cites app/exports/views.py:78" in r.stdout


def test_check_report_accepts_a_fix_proposal_that_names_its_finding(tmp_path: Path):
    text = GOOD_REPORT.replace(
        "1. Fix F1 at `app/exports/views.py:57`",
        "1. Fix F1: filter by organization at `app/exports/views.py:55` (two lines above the sink)",
    )
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, text)))
    assert r.returncode == 0, r.stdout


def test_check_report_rejects_a_verdict_outside_the_four(tmp_path: Path):
    text = GOOD_REPORT.replace("| NEEDS DEEPER REVIEW |", "| LOW, recorded |")
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, text)))
    assert r.returncode == 1
    assert "NOT A VERDICT: 'LOW, recorded'" in r.stdout


def test_check_report_rejects_an_entry_without_disposition(tmp_path: Path):
    text = GOOD_REPORT.replace(
        "- R3, stale cron in `app/jobs/cleanup.py:8`: out of zone, proposed sweep of `jobs`.",
        "- R3, stale cron in `app/jobs/cleanup.py:8`: seen while reading, left for later.",
    )
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, text)))
    assert r.returncode == 1
    assert "NO DISPOSITION" in r.stdout


def test_check_report_requires_every_section(tmp_path: Path):
    text = GOOD_REPORT.replace("## Refused or unconfirmed candidates\n", "## Notes\n")
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, text)))
    assert r.returncode == 1
    assert "MISSING SECTION: no '## Refused or unconfirmed candidates'" in r.stdout


def test_check_report_scope_is_context_and_cited_files_not_coverage(tmp_path: Path):
    # A file listed only in Coverage (as skipped) is not in scope: a hand-off citation in it passes.
    text = GOOD_REPORT.replace(
        "2. Proposed sweep of `jobs`: the stale cron at `app/jobs/cleanup.py:8`.",
        "2. Proposed sweep of `jobs`: the stale cron at `app/jobs/cleanup.py:8` and `app/jobs/run.py:3`.",
    )
    r = run_script(CHECK_REPORT, str(write_report(tmp_path, text)))
    assert r.returncode == 0, r.stdout


def test_check_report_exit_2_when_missing():
    r = run_script(CHECK_REPORT, "/nonexistent/report.md")
    assert r.returncode == 2


# --------------------------------------------------------------------------------------
# leak_check.py (shapes in the deliverables) and tools/leak_values.py (the repository's values)
# --------------------------------------------------------------------------------------

LEAK_CHECK = SCRIPTS / "leak_check.py"
LEAK_VALUES_TOOL = ROOT / "tools" / "leak_values.py"
LEAK_VALUES = {
    "admin_password": "apple",                      # an ordinary word, 5 characters: WARN territory
    "app_password": "abcd efgh ijkl mnop",           # an app password: four lowercase groups
    "jwt_default": "postgresql://app:hunter2pw@db/app",
    "api_key": "sk_live_" + "Zz9yY8xX" * 4,
}


@pytest.fixture()
def leak_repo(tmp_path: Path) -> Path:
    root = tmp_path / "svc"
    (root / "app" / "seeds").mkdir(parents=True)
    (root / "docs" / "audits").mkdir(parents=True)
    (root / "tests").mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "app" / ".env").write_text(
        f"ADMIN_EMAIL=admin@example.invalid\nADMIN_PASSWORD={LEAK_VALUES['admin_password']}\n", encoding="utf-8"
    )
    (root / "app" / "config.py").write_text(
        f'SECRET_KEY = os.getenv("SECRET_KEY", "{LEAK_VALUES["jwt_default"]}")\n'
        f'API_KEY = "{LEAK_VALUES["api_key"]}"\n',
        encoding="utf-8",
    )
    (root / "app" / "seeds" / "smtp_seed.py").write_text(
        f'config = SMTP(username="mailer@example.invalid", password="{LEAK_VALUES["app_password"]}")\n',
        encoding="utf-8",
    )
    (root / "tests" / "test_existing.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "import"],
        check=True,
    )
    return root


def run_leak(root: Path, *args: str) -> subprocess.CompletedProcess:
    return run_script(LEAK_CHECK, "--root", str(root), *args)


def run_values(root: Path, *args: str) -> subprocess.CompletedProcess:
    return run_script(LEAK_VALUES_TOOL, "--root", str(root), *args)


def assert_no_value(stdout: str) -> None:
    for value in LEAK_VALUES.values():
        assert value not in stdout


def write_audit(root: Path, text: str) -> Path:
    report = root / "docs" / "audits" / "2026-01-15-auth.md"
    report.write_text(text, encoding="utf-8")
    return report


# The same report, the four values each cited as the skill cites a line ("the line reads:")
# and each written in prose without its name. Measured on both checks in the same test, so the
# gap between them is a number in the test file, not a sentence in the docs.
LABELED = (
    f"L1 the line reads: `ADMIN_PASSWORD={LEAK_VALUES['admin_password']}`\n"
    f"L2 the line reads: `password=\"{LEAK_VALUES['app_password']}\"`\n"
    f"L3 the line reads: `SECRET_KEY = os.getenv(\"SECRET_KEY\", \"{LEAK_VALUES['jwt_default']}\")`\n"
    f"L4 the line reads: `API_KEY = \"{LEAK_VALUES['api_key']}\"`\n"
)
UNLABELED = (
    f"U1 the admin logs in with {LEAK_VALUES['admin_password']} on every environment.\n"
    f"U2 the mailer uses {LEAK_VALUES['app_password']} as its app password.\n"
    f"U3 the fallback DSN is {LEAK_VALUES['jwt_default']}.\n"
    f"U4 the key {LEAK_VALUES['api_key']} is committed.\n"
)


def test_leak_check_passes_a_report_that_names_variables_only(leak_repo: Path):
    write_audit(
        leak_repo,
        "F1 `ADMIN_PASSWORD` in `app/.env:2` is a literal; F2 `SECRET_KEY` default at `app/config.py:1`;\n"
        "F3 the SMTP seed at `app/seeds/smtp_seed.py:1` holds an app password (format checked as a boolean).\n"
        f"Recorded at commit {bytes(range(20)).hex()}; id 2026-01-15-auth/F1; token: rotated on login.\n"
        "| secret | `${SECRET_KEY}` | `<your-key>` | ******** | changeme |\n",
    )
    r = run_leak(leak_repo)
    assert r.returncode == 0, r.stdout
    assert "0 FAIL, 0 WARN" in r.stdout
    r = run_values(leak_repo)
    assert r.returncode == 0, r.stdout
    assert "0 FAIL, 0 WARN" in r.stdout
    assert "5 value(s) collected" in r.stdout   # the username on the seed line is not one of them


def test_leak_check_finds_every_labeled_value_and_the_shaped_unlabeled_ones(leak_repo: Path):
    write_audit(leak_repo, LABELED + UNLABELED)
    r = run_leak(leak_repo)
    assert r.returncode == 1
    assert_no_value(r.stdout)
    lines = r.stdout.splitlines()
    assert "5 FAIL, 1 WARN" in lines[-1]
    assert any("auth.md:1 " in ln and "value after `ADMIN_PASSWORD=` (len 5)" in ln and ln.startswith("WARN") for ln in lines)
    assert any("auth.md:2 " in ln and "literal next to `password` (len 19)" in ln for ln in lines)
    assert any("auth.md:3 " in ln and "literal next to `SECRET_KEY` (len 33)" in ln for ln in lines)
    assert any("auth.md:4 " in ln and "literal next to `API_KEY` (len 40)" in ln for ln in lines)
    assert any("auth.md:7 " in ln and "URL userinfo value (len 9)" in ln for ln in lines)
    assert any("auth.md:8 " in ln and "long token (len 40)" in ln for ln in lines)
    assert "<masked, 40 chars>" in r.stdout and "<masked, 19 chars>" in r.stdout
    # The two it does not see: a weak password and an app password in prose, without a name
    assert not any("auth.md:5 " in ln or "auth.md:6 " in ln for ln in lines)
    # The value-side tool sees all eight, the 5-character one as a WARN
    r = run_values(leak_repo)
    assert r.returncode == 1
    assert_no_value(r.stdout)
    assert "6 FAIL, 2 WARN" in r.stdout
    assert "value from app/.env:ADMIN_PASSWORD (len 5)" in r.stdout
    assert "value from app/seeds/smtp_seed.py:1 (len 19)" in r.stdout


def test_leak_check_warns_and_strict_fails(leak_repo: Path):
    write_audit(leak_repo, "the line reads: `ADMIN_PASSWORD=apple`\n")
    r = run_leak(leak_repo)
    assert r.returncode == 0, r.stdout
    assert "0 FAIL, 1 WARN" in r.stdout
    r = run_leak(leak_repo, "--strict")
    assert r.returncode == 1


def test_leak_check_scans_changed_test_files_and_zip_containers(leak_repo: Path, tmp_path: Path):
    (leak_repo / "tests" / "test_sweep_auth.py").write_text(
        f'KEY = "{LEAK_VALUES["api_key"]}"\n', encoding="utf-8"
    )
    book = tmp_path / "report.xlsx"
    with __import__("zipfile").ZipFile(book, "w") as zf:
        zf.writestr("xl/sharedStrings.xml", f"<t>{LEAK_VALUES['jwt_default']}</t>")
    r = run_leak(leak_repo, "--extra", str(book))
    assert r.returncode == 1
    assert_no_value(r.stdout)
    assert "tests/test_sweep_auth.py:1" in r.stdout.replace("\\", "/")
    assert "report.xlsx!xl/sharedStrings.xml:1" in r.stdout
    assert "long token (len 40)" in r.stdout and "URL userinfo value (len 9)" in r.stdout
    assert "2 FAIL, 0 WARN" in r.stdout


def test_leak_check_reads_no_file_outside_the_deliverables(leak_repo: Path, monkeypatch):
    # The plugin's check opens the deliverables only: with the repository's sources and dotenv
    # files unreadable, it still runs and still finds the shaped values
    for rel in ("app/.env", "app/config.py", "app/seeds/smtp_seed.py"):
        (leak_repo / rel).chmod(0)
    try:
        write_audit(leak_repo, LABELED)
        r = run_leak(leak_repo)
    finally:
        for rel in ("app/.env", "app/config.py", "app/seeds/smtp_seed.py"):
            (leak_repo / rel).chmod(0o644)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "3 FAIL, 1 WARN" in r.stdout


def test_leak_check_setup_errors(tmp_path: Path, leak_repo: Path):
    r = run_leak(leak_repo, "--extra", str(tmp_path / "missing.xlsx"))
    assert r.returncode == 2
    r = run_values(leak_repo, "--from-cited", str(tmp_path / "missing.md"))
    assert r.returncode == 2


def test_leak_values_from_cited_limits_the_collection(leak_repo: Path):
    report = write_audit(
        leak_repo, f"Only `app/config.py:1` is cited; the seed password is {LEAK_VALUES['app_password']}.\n"
    )
    r = run_values(leak_repo, "--from-cited", str(report))
    # The seed is not cited, so its value is not collected; the dotenv file always is
    assert "0 FAIL, 0 WARN" in r.stdout
    assert "4 value(s) collected" in r.stdout
    r = run_values(leak_repo)
    assert r.returncode == 1
    assert "1 FAIL, 0 WARN" in r.stdout


def test_keylike_is_a_key_shape_not_an_identifier():
    # Measured on a real record of 13 reports: identifiers with digits, dated file names and API
    # paths made 696 false values and 1850 false FAILs before these rules
    cc = _load(CHECK_CITATIONS)
    assert cc.tokenlike("Zz9yY8xX" * 4)                              # both cases
    assert cc.tokenlike(bytes(range(16)).hex())                       # hex, 32
    assert cc.tokenlike("dGhpcyBpcyBhIHNlY3JldCBrZXk9")               # base64 padding
    assert not cc.tokenlike("test_sweep_case_access_20261017")        # one case, digits
    assert not cc.tokenlike("docs/audits/2026-10-17-reports.md")      # a dated path
    assert not cc.tokenlike("/api/v1/cases/9/members/active")         # an API path
    assert not cc.tokenlike("2026-10-19-authentication")
    # From the shape-side scan of a real record: a finding id with both cases, an assignment
    # with `=` inside; base64 padding is `=` at the end only
    assert not cc.tokenlike("2026-01-15-audit-chain/AC6")
    assert not cc.tokenlike("sensor_case_max_armed=50")
    assert cc.identifier_like("tests/test_sweep_auth.py::test_f1")
    assert not cc.identifier_like("sk_live_" + "Zz9yY8xX" * 4)


def test_name_like_covers_words_that_stand_next_to_secret_names():
    cc = _load(CHECK_CITATIONS)
    for word in ("bearer", "Shodan", "VirusTotal", "clearance_level", "SECRET_KEY", "password", "changeme"):
        assert cc.name_like(word), word
    for value in ("apple", "hunter2pw", "abcd efgh", "dev-secret-12", "Tr0ub4dor&3"):
        assert not cc.name_like(value), value
    # A dict key after a secret-name literal is not a value; a type annotation is not a value
    assert cc.named_literals('"api_key": "x9y8z7w6v5", "shodan": {') == ["x9y8z7w6v5"]
    assert cc.named_literals('KeyedConnector("SHODAN_API_KEY", "Shodan", ("domain", "ip"))') == []
    assert not cc.needs_mask("config.py", "postgres_password_file: str | None = None")
    assert cc.needs_mask("config.py", "postgres_password: str = 'hunter2pw'")


def test_leak_values_never_collects_from_the_deliverables_or_test_fixtures(leak_repo: Path):
    # A report quoting a test name, and a test fixture holding an invented password, are not leaks
    (leak_repo / "tests" / "test_sweep_auth.py").write_text(
        'def test_f1():\n    client.login(password="invented-fixture-pw-2026")\n', encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(leak_repo), "add", "-A"], check=True)
    (leak_repo / "docs" / "audits" / "2026-01-15-auth.md").write_text(
        "Reproduction: `tests/test_sweep_auth.py::test_f1` uses the fixture password invented-fixture-pw-2026.\n",
        encoding="utf-8",
    )
    r = run_values(leak_repo)
    assert r.returncode == 0, r.stdout
    assert "0 FAIL, 0 WARN" in r.stdout
    r = run_leak(leak_repo)
    assert r.returncode == 0, r.stdout


def test_leak_values_skips_sample_dotenv_files_and_tiny_values(leak_repo: Path):
    # From a confirmation run: `---` in docker/.env.example and `pass` from a test URL matched
    # table rules and prose everywhere, 13 WARN on a clean record
    (leak_repo / "docker").mkdir()
    (leak_repo / "docker" / ".env.example").write_text("SECRET_KEY=---\nADMIN_PASSWORD=change-me-now\n", encoding="utf-8")
    (leak_repo / "app" / "hooks.py").write_text('URL = "http://user:pass@example.invalid/hook"\n', encoding="utf-8")
    subprocess.run(["git", "-C", str(leak_repo), "add", "-A"], check=True)
    (leak_repo / "docs" / "audits" / "2026-01-15-auth.md").write_text(
        "| a | b |\n|---|---|\nread handlers are expected to pass readonly; change-me-now is the sample.\n", encoding="utf-8"
    )
    for run in (run_values, run_leak):
        r = run(leak_repo)
        assert r.returncode == 0, r.stdout
        assert "0 FAIL, 0 WARN" in r.stdout
