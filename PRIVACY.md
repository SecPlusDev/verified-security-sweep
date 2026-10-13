# Privacy policy

Last updated: 2026-10-05

This policy covers the `verified-security-sweep` plugin and skill. The maintainer runs no service for
it: there is no server, no account and no telemetry.

## What the plugin reads

- The source code of the repository you point it at, its rules file, and any previous reports in
  its `docs/audits/` folder.
- The repository's git history, through `scripts/fresh_code.py`. That includes commit authors'
  names: the script counts the distinct authors per changed file and prints only the count. It
  does not display, write or keep the names, and they are gone when the script exits.

## What the plugin writes

Only files in the target repository: reports and the registry under `docs/audits/`, and
reproduction tests in the repository's test folders. It writes nothing anywhere else.

## What the plugin sends

Nothing to the maintainer or to any service the maintainer runs. The plugin has no network code.

Your Claude session sends its content, including the code the plugin reads, to the model
provider your account uses: Anthropic, or the cloud provider your Claude Code is configured for.
Your account settings govern that, not this plugin. When a sweep starts the target application
to reproduce a finding, that application's own tooling may contact package or container
registries, as it would when you run it yourself.

## Retention

None. The maintainer has no service, so there is nothing to retain or delete. Files the plugin
writes stay in your repository until you remove them.

## Contact

unittest072@gmail.com, the same address as in [`SECURITY.md`](SECURITY.md).
