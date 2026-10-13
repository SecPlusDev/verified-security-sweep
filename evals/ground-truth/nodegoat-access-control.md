# Access control in NodeGoat: list of defects

Zone: Express routes, the `isLoggedIn`/`isAdmin` middleware, the handlers and DAOs behind them, the session.
Sources read: `app/routes/*.js`, `app/data/*.js`, `server.js`, `config/env/all.js`, `app/views/layout.html`, `app/views/tutorial/a2.html`, `a4.html`, `a7.html` (plus a grep through the rest of the tutorial) and `docs/audits/2026-10-03-access-control.md`.
Method: static analysis only. The application was not started and nothing was modified.

This list was written and committed before any evaluation report was read. It was written in Romanian; this file is its English translation. The only change of content is the correction at the end, made after grading.

## Route map (who can reach what)

| Route | Middleware | Who can reach it | Identity comes from |
|---|---|---|---|
| `GET /`, `GET/POST /login`, `GET/POST /signup`, `GET /logout` | none | anyone | n/a (`/` checks the session in the handler, `session.js:259-262`) |
| `GET /dashboard` | isLoggedIn | any signed-in user | session |
| `GET/POST /profile` | isLoggedIn | any signed-in user | session (`profile.js:14-16`, `:78-80`) |
| `GET/POST /contributions` | isLoggedIn | any signed-in user | session (`contributions.js:13-15`, `:42-44`) |
| `GET/POST /benefits` | isLoggedIn, isAdmin | admin only (after AC-1) | `req.body.userId` (intended, an admin function) |
| `GET /allocations/:userId` | isLoggedIn | any signed-in user | **the URL parameter** |
| `GET/POST /memos` | isLoggedIn | any signed-in user | memos have no owner |
| `GET /learn` | isLoggedIn | any signed-in user | n/a |
| `GET /research` | isLoggedIn | any signed-in user | n/a |
| `GET /tutorial/*` | none | anyone (public by design) | n/a |

## Main list: access-control defects

| ID | Status | file:line | Mechanism | Source |
|---|---|---|---|---|
| GT-1 | OPEN | `app/routes/allocations.js:16-18` (`const { userId } = req.params`), used at `app/routes/allocations.js:23`. The route is mounted with `isLoggedIn` only at `app/routes/index.js:59`, and the DAO filters by that id at `app/data/allocations-dao.js:58` and `:81-83`. | IDOR: the handler takes `userId` from the URL instead of `req.session.userId` and checks no ownership, so any signed-in user reads the allocations (and the name) of any other user by changing `/allocations/<id>`. Ids are sequential integers, and the user's own id appears in the menu (`app/views/layout.html:56`). | both (tutorial `a4.html`; in the code, the commented fix at `allocations.js:12-15`) |
| GT-2 | OPEN | `app/routes/session.js:116` (`req.session.userId = user._id;` without `req.session.regenerate`), helped by `server.js:84` (`saveUninitialized: true`). | Session fixation: at login, the user's privileges (admin included) are attached to the pre-existing session id, already issued to the anonymous visitor. Whoever fixes or learns that id before login takes over the victim's session after login and reaches their data (or the admin functions). | both (tutorial `a2.html`, section "Session hijacking", CWE-384; the code comment at `session.js:104-115`) |
| AC-1 | CLOSED (fix applied, guard `test/e2e/integration/benefits_access_guard_spec.js`) | `app/routes/index.js:55-56` (before the fix, `isLoggedIn` only). The flow reaches `app/routes/benefits.js:35` and `app/data/benefits-dao.js:23`. | Function-level access control was missing: any signed-in user reached `/benefits` and, through `userId` in the body, changed the benefits start date of other employees. `isAdmin` is now wired on both routes. | both (tutorial `a7.html`; the 2026-10-03 report) |
| AC-2 | CLOSED (OVER-RATED, informational) | `app/routes/session.js:28` and `:32` | `isAdminUserMiddleware` answers a non-admin with a redirect to `/login` instead of 403. Nothing relevant is disclosed, because the route list is public. | code (the 2026-10-03 report) |

Checks not listed as defects:
- `isAdminUserMiddleware` (`session.js:25-34`) fails closed if `getUserById` errors: `user` is undefined, so it redirects.
- The role is read from the database on every request, not from the session.
- There is no mass assignment to `isAdmin`: `addUser` builds the document field by field (`user-dao.js:20-31`), and `updateUser` sets only listed fields (`profile-dao.js:45-75`).
- `/profile` and `/contributions` take the identity from the session only.

## Candidates examined and not included

- **Memos without an owner.** The insert without an owner is at `app/data/memos-dao.js:18-21`, the global read at `app/data/memos-dao.js:28`, and `app/routes/memos.js:13` writes without a user. Any signed-in user reads all memos and writes anonymously to the same list. Considered a shared message board by design: no per-user data is exposed, and the tutorial does not treat it as an access-control defect. Its real risk (stored XSS) is listed under adjacent.
- **`/tutorial/*` public** (`app/routes/index.js:75`): static training content, public on purpose.

## Adjacent to the zone (not in the main list)

| ID | file:line | Mechanism | Source | Link to access control |
|---|---|---|---|---|
| ADJ-1 | `app/data/allocations-dao.js:77-79` | NoSQL injection: `threshold` is concatenated into a `$where` (for example `1'; return 1 == '1`). | both (tutorial `a1.html`; the comment at `allocations-dao.js:63-76`) | Bypasses the `this.userId == ...` filter and returns every user's allocations, so it amplifies GT-1 (it stays open even after a GT-1 fix that takes the id from the session). |
| ADJ-2 | `server.js:104-113` (csurf commented out). Targets: `POST /profile`, `/contributions`, `/memos`, `/benefits` (`app/routes/index.js:48,52,56,63`). | CSRF: no state-changing request carries a token. | both (tutorial `a8.html`; code) | An attacker makes a signed-in admin change other users' benefits, or a user change their own profile or bank details. |
| ADJ-3 | `server.js:78-102` (no `httpOnly`, `secure`, `maxAge`, with the default name `connect.sid`) and `config/env/all.js:8` (hardcoded `cookieSecret`) | Session cookie configuration: readable from JS, sent over HTTP, no expiry. See the correction below. | both (tutorial `a2.html`, `a5.html`; the comments in `server.js`) | Makes session theft easier, that is, taking over another user's account. |
| ADJ-4 | `server.js:145` (`http.createServer`) | Unencrypted transport (HTTPS is commented out at `server.js:149-155`). | both (tutorial `a6.html`) | The session id can be intercepted (MITM), which leads to session hijacking. |
| ADJ-5 | `server.js:135-142` (`autoescape: false`). Example output points: memos (`app/routes/memos.js:13`), profile (`app/routes/profile.js:28`). | Stored and reflected XSS. | both (tutorial `a3.html`) | Together with ADJ-3, leads to theft of other users' session cookies, the admin's included. |
| ADJ-6 | `app/routes/index.js:66-69` (line 68, `res.redirect(req.query.url)`) | Open redirect on `/learn`. | both (tutorial `a10.html`; the code comment) | Credential phishing. |
| ADJ-7 | `app/routes/research.js:15-16` | SSRF: the URL the server fetches is user-controlled (`req.query.url + req.query.symbol`). | both (tutorial `ssrf.html`) | Access to internal resources through the server. |
| ADJ-8 | `app/routes/contributions.js:32-34` | SSJS injection through `eval(req.body.*)`. | both (tutorial `a1.html`) | RCE, so a complete bypass of any access control. |
| ADJ-9 | `app/routes/session.js:85` and `:94` (distinct messages), `app/routes/session.js:144` (weak `PASS_RE`), `app/data/user-dao.js:25` and `:61` (plaintext password) | Weak authentication: user enumeration, weak passwords, passwords stored and compared in plaintext. | both (tutorial `a2.html`) | Makes compromising other users' accounts easier. |

## Correction after grading

ADJ-3 is wrong on one point. `server.js:78-102` sets no cookie options, so the `express-session`
default applies, and for the declared `^1.13.0` (`package.json:14`) that default is
`httpOnly: true`: the session cookie is not readable from JS. The tutorial's commented fix sets
`httpOnly` explicitly, which is where the error came from. The rest of ADJ-3 stands (no `secure`,
no `maxAge`, default cookie name, hardcoded `cookieSecret`), and the "together with ADJ-3" chain
in ADJ-5 does not lead to cookie theft through `document.cookie`. The grading found this
independently (B-12, D-9). ADJ-3 is outside the zone, so no metric changes.
