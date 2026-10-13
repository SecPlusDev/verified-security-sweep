# Sweep registry: what exists, what ran, what it is worth

Proposals for sweeps are written here, not in conversation. The `Last run` column is derived
from report filenames by the skill's `scripts/sweep_status.py`; the other columns are written by
hand. Yield = confirmed / verified candidates.

## Candidates

| Zone | Argument | Last run | Yield |
|---|---|---|---|
| `api-key-scope` | Management API under `hc/api`: which API key (read-write, read-only, hashed or legacy plain) can read or change which checks. Two decorators and per-view project checks, no table-driven guard. | 2026-10-09 | 3/14 |

## Proposed, not yet run

| Zone | Argument | Premise to re-verify before starting |
|---|---|---|
| `unauthenticated-callbacks` | `notification_status`, `bounces`, `ping`, `ping_by_slug` (auto-provision with `?create=1`) accept requests without an API key. | Each still has no API key decorator in `hc/api/views.py`. |
| `metrics-and-prometheus` | `metrics` compares `X-Metrics-Key` with `!=`; `hc/integrations/prometheus/views.py` uses read-only keys via `for_api_key`. | Both views still exist and are routed. |
| `web-project-access` | Session-authenticated project and check views in `hc/front` and team roles in `hc/accounts`. | Not read by any sweep yet. |

## Candidates verified and refused

See the "Refused or unconfirmed candidates" section of each report; the 2026-10-09 report lists
eleven for `api-key-scope`.
