# Security policy

## Scope

In scope:

- The plugin folder `plugin/`, which is all that users install: its manifest, its README and the
  skill in `plugin/skills/verified-security-sweep/`.
- The skill's `SKILL.md` and `references/`: instructions that could lead Claude to act outside the
  boundaries this policy describes (writing outside `docs/audits/` and test folders, leaving
  processes running, sending data elsewhere).
- The skill's `scripts/sweep_status.py` and `scripts/fresh_code.py`.
- The evaluation harness in `evals/`, including `evals/fixtures/setup.sh` and the planted patches.
- CI and release: `.github/workflows/ci.yml` and the scripts in `.github/scripts/`.

Out of scope: findings the skill produces about other people's code. A defect the skill reports
in your repository, or in a repository you reviewed with it, is a vulnerability of that project,
not of this one. Report it to that project's maintainers.

## What this skill does on your machine

- It reads the code of the repository you point it at.
- It writes only under `docs/audits/` and in the project's test folders (new reproduction tests
  and guards). Every other change, including fixes and a pointer from your rules file, is written
  as a proposal in the report, not applied.
- It may start the application and its database to reproduce a finding, under a name or port
  specific to the run, and it stops only what it started, by PID or container name.
- It does not send data anywhere outside the Claude session it runs in. What the session itself
  sends to the model provider is governed by your Claude Code configuration.

Run it on a clone or a disposable checkout, not on the working tree you deploy from. Reproduction
starts services and writes test files, and a run interrupted by a limit can leave them behind.

## Reporting a vulnerability

Report privately, through either of these:

1. **GitHub private vulnerability reporting**: the "Report a vulnerability" button on the
   Security tab of this repository (Advisories).
2. **Email**: unittest072@gmail.com. Use it if you cannot use GitHub.

Do not describe a vulnerability in a public pull request or anywhere else public.

The maintainer confirms receipt within 5 working days. Please do not disclose the issue publicly
until a fixed version is released; a disclosure date is agreed with you once the fix is ready.

## Supported versions

Only the latest minor release receives security fixes. Older versions are not patched; upgrade to
the latest release.

## Supply chain

- Every GitHub Action in CI is pinned to a full commit SHA, and the runner image is pinned
  (`ubuntu-24.04`).
- The workflow token is `contents: read`. The release job is the only job with `contents: write`,
  and it runs only on `v*` tags.
- The skill scripts and the CI helpers use the Python standard library only; there are no runtime
  dependencies to install.
- The only third-party code in this repository's pipeline is pytest, installed hash-checked from
  `requirements-ci.txt` on the CI runner; Dependabot alerts on it are fixed, not dismissed.
- The `.skill` archive is reproducible byte for byte: fixed file order and timestamps, so the same
  commit always yields the same file. The release job rebuilds it from the tagged commit, and the
  release page shows its SHA-256 digest. To check a download, rebuild and compare:

  ```bash
  git checkout v1.4.0
  python3 .github/scripts/package_skill.py --out dist
  sha256sum dist/verified-security-sweep.skill
  ```

## Known limitations

- The skill runs with the permissions of the Claude Code session that loads it. If that session
  may run shell commands, edit files or reach the network, so may the skill.
- It has no sandbox of its own. The boundaries above are instructions to the model, not technical
  controls; review the session's permission settings before running it on sensitive code.
- Evaluations that use nested `claude -p` sessions inherit the parent's permissions and current
  directory. Run them only as described in `README.md` and `docs/BUILD.md`: from an empty
  directory, with `Bash`, `Write` and `Edit` denied, and without the skill synced to the account.
