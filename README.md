# Verified Security Sweep: the directory edition

This branch holds the edition of the plugin that the Claude plugin directory serves: the
`plugin/` folder of `main` without the skill's `scripts/` folder, and nothing else. The
directory accepts script files only from verified organizations, so this edition has none;
Claude does every check by hand, following `references/without-scripts.md`.

The branch is generated, never edited: each commit is the output of
`.github/scripts/build_directory_edition.py` on a commit of `main`, named in the commit
message. The source, the full edition with its scripts, the tests, the evaluations and the
changelog are on [`main`](https://github.com/SecPlusDev/verified-security-sweep).
