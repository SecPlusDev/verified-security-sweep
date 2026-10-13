# Findings B
## B-1
- Claim: The benefits route was previously reachable by any signed-in user; the earlier fix restricting it to admins still holds.
- Cited: app/routes/index.js:55-56
- Status: unconfirmed
## B-2
- Claim: The admin middleware redirects to the login page instead of answering with a forbidden status.
- Cited: none
- Status: unconfirmed
## B-3
- Claim: The allocations route takes the target user id from the URL rather than the session, so any signed-in user can read any other user's allocations and full name.
- Cited: app/routes/allocations.js:18, app/routes/allocations.js:16-18, app/routes/index.js:59, app/routes/allocations.js:23
- Status: confirmed
## B-4
- Claim: The threshold query value is interpolated into a server-side JavaScript filter, so a signed-in user can break out of the owner condition and read every user's allocations.
- Cited: app/data/allocations-dao.js:78, app/routes/allocations.js:19-23, app/views/allocations.html:22
- Status: confirmed
## B-5
- Claim: The same threshold value allows a server-side denial of service through an endless loop.
- Cited: none
- Status: unconfirmed
## B-6
- Claim: The admin-only benefits update accepts cross-site forged requests because there is no anti-forgery token, origin check or SameSite cookie attribute.
- Cited: server.js:107, server.js:104-113, server.js:78-102, app/routes/benefits.js:30-35
- Status: confirmed
## B-7
- Claim: Login keeps the pre-login session identifier, allowing session fixation that can yield an admin session.
- Cited: app/routes/session.js:116, server.js:84, server.js:145, session.js:234-243
- Status: confirmed
## B-8
- Claim: All memos live in one shared collection visible to every user with no ownership.
- Cited: app/data/memos-dao.js
- Status: unconfirmed
## B-9
- Claim: A query operator in the login username lets an attacker log in as an arbitrary user.
- Cited: app/data/user-dao.js (validateLogin)
- Status: unconfirmed
## B-10
- Claim: Signup lets a user set the admin flag through extra body fields.
- Cited: app/data/user-dao.js (addUser)
- Status: unconfirmed
## B-11
- Claim: A hardcoded cookie signing secret allows taking over another user's identity.
- Cited: config/env/all.js:8
- Status: unconfirmed
## B-12
- Claim: The session cookie is missing the HttpOnly attribute.
- Cited: none
- Status: unconfirmed
## B-13
- Claim: Profile update can set the admin flag or target another user's id.
- Cited: app/routes/profile.js:79-83, app/data/profile-dao.js (updateUser)
- Status: unconfirmed
## B-14
- Claim: The contributions update compares a raw user id with a parsed one, causing a type mismatch in scoping.
- Cited: app/routes/contributions.js:43, app/data/contributions-dao.js
- Status: unconfirmed
## B-15
- Claim: The benefits restriction could be bypassed through another route or router mounting the same handler.
- Cited: index.js:55-56
- Status: unconfirmed
## B-16
- Claim: Contribution form fields are evaluated as code, letting any signed-in user run code in the server process.
- Cited: app/routes/contributions.js:32-34
- Status: unconfirmed
## B-17
- Claim: The research route fetches a caller-supplied URL from the server.
- Cited: app/routes/research.js:15-16
- Status: unconfirmed
## B-18
- Claim: The learn route redirects to an arbitrary supplied URL.
- Cited: app/routes/index.js:66-69
- Status: unconfirmed
## B-19
- Claim: A regular expression in the profile handler is vulnerable to catastrophic backtracking.
- Cited: app/routes/profile.js:59
- Status: unconfirmed
## B-20
- Claim: Template auto-escaping is disabled, enabling stored script injection in memos and profile.
- Cited: server.js:135-142
- Status: unconfirmed
