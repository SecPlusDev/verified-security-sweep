# Install test (criterion B6)

Checks the plugin the way a user gets it: loaded from its plugin folder, not read from this
repository by an evaluation harness. Two steps; the first costs a few thousand tokens, the second
a full run.

## 0. Clean state

```bash
ls -R ~/.claude/skills ~/.claude/plugins 2>/dev/null | grep -i -E 'sweep|audit'   # nothing of this skill
cd <work>/repo && git checkout main && git pull
python3 -c "import json; print(json.load(open('plugin/.claude-plugin/plugin.json'))['version'])"
mkdir -p <work>/install-test && rm -rf <work>/install-test/hc
cp -a <work>/round-v1.2.2/claude-opus-5-5/base/healthchecks-defects <work>/install-test/hc
cd <work>/install-test/hc && git log -1 --format=%h        # 7a07141
```

## 1. Smoke: the plugin loads and its scripts run from where it is installed

```bash
claude --model claude-opus-5-5 --plugin-dir <work>/repo/plugin \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}'
```

Prompt:

```
Use the verified-security-sweep skill. Do not review anything yet: run each of its six scripts
with --help, from the skill's own scripts folder, and tell me the full path you ran them from.
```

Pass: the session loads the skill, the six scripts answer `--help`, and the path is under
`.../repo/plugin/skills/verified-security-sweep/scripts/`.

## 2. Full run: a natural request triggers it and every step works from the installed copy

Same command, new session, the prompt of eval 5 in `evals/evals.json` with `<repo>` replaced by
`.`. Pass:
- the first tool call loads the skill (no reading of the repository before it);
- `docs/audits/` is created with the report, registry, categories and `findings.jsonl`;
- `check_citations.py` and `findings.py check` exit 0 when run again by hand from the plugin path;
- nothing outside `docs/audits/` and the test folders changed (`git status --short`).

`--plugin-dir` loads the plugin for that session only; nothing stays installed. Record the result,
the model, the date and the token use in `evals/results/`.

## 3. From the directory: the installed copy is the release

Once a version is listed, check what the directory delivers. Use a configuration directory
created for the check, so the account's own configuration and plugins stay out of it:

```bash
mkdir -p <work>/cfg-directory-test
export CLAUDE_CONFIG_DIR=<work>/cfg-directory-test
claude plugin install verified-security-sweep@anthropic-plugin-directory
claude plugin list        # verified-security-sweep@anthropic-plugin-directory, Version: <version>-<commit>
```

The installed copy is under `$CLAUDE_CONFIG_DIR/plugins/cache/anthropic-plugin-directory/verified-security-sweep/<version>-<commit>/`.
Compare it with the tagged release, then rebuild the archive from it:

```bash
git -C <work>/repo archive v<version> plugin | tar -x -C <work>/install-test/tag
git -C <work>/repo show v<version>:LICENSE > <work>/install-test/tag/LICENSE
diff -r --brief <work>/install-test/tag/plugin <installed copy>
python3 <work>/repo/.github/scripts/package_skill.py --root <installed copy>/skills/verified-security-sweep \
  --license <work>/install-test/tag/LICENSE --out <work>/install-test/dist-directory
```

Pass: `claude plugin list` names the tagged commit; the diff reports no differing file (an
`.in_use/` folder is Claude Code's marker for a running session, not plugin content); the digest
equals the version's row in `docs/BUILD.md` section 6. Running the scripts with `python3 -I`
during the check writes `__pycache__` into the installed copy, because `-I` ignores
`PYTHONDONTWRITEBYTECODE`; use plain `python3`. Then step 2 can run on the installed copy, from a
session started with the same `CLAUDE_CONFIG_DIR`. Afterwards:

```bash
claude plugin uninstall verified-security-sweep@anthropic-plugin-directory
```

Result: `evals/results/install-directory-2026-10-16.md`.
