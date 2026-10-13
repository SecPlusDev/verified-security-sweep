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
Use the verified-security-sweep skill. Do not review anything yet: run each of its five scripts
with --help, from the skill's own scripts folder, and tell me the full path you ran them from.
```

Pass: the session loads the skill, the five scripts answer `--help`, and the path is under
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
