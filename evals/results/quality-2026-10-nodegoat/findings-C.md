# Findings C
## C-1
- Claim: The benefits route was previously reachable by regular users; the earlier fix restricting both read and write to admins still holds.
- Cited: none
- Status: unconfirmed
## C-2
- Claim: The allocations route takes the target user id from the URL with no ownership check, so any signed-in user can read any user's allocations.
- Cited: app/routes/allocations.js:16-23, app/routes/index.js:59, app/data/allocations-dao.js:57
- Status: confirmed
## C-3
- Claim: The threshold query value is concatenated into a server-side JavaScript filter, letting a signed-in user retrieve every user's allocations in one request.
- Cited: app/data/allocations-dao.js:77-79
- Status: confirmed
## C-4
- Claim: Login reuses the pre-login session identifier instead of regenerating it, enabling session fixation.
- Cited: app/routes/session.js:116, server.js:84, session.js:234
- Status: confirmed
## C-5
- Claim: State-changing routes, including the admin-only benefits update, lack anti-forgery protection and the cookie has no SameSite attribute, so requests can be forged through a victim's browser.
- Cited: server.js:104-113
- Status: confirmed
## C-6
- Claim: The existing benefits guard test exercises only the read request, so removing the admin check from the write path would go undetected.
- Cited: test/e2e/integration/benefits_access_guard_spec.js, app/routes/index.js:56
- Status: confirmed
## C-7
- Claim: A user could grant themselves admin rights by sending the admin flag through profile update or signup.
- Cited: profile.js:42-50, user-dao.js:20-31
- Status: unconfirmed
## C-8
- Claim: A demoted admin could keep admin rights through a stale session.
- Cited: session.js:25
- Status: unconfirmed
## C-9
- Claim: The root route is mounted without any gate.
- Cited: session.js:259-262
- Status: unconfirmed
## C-10
- Claim: The tutorial pages are reachable without signing in.
- Cited: none
- Status: unconfirmed
## C-11
- Claim: Memos have no owner and every signed-in user sees every memo, which could be a cross-user exposure.
- Cited: memos-dao.js:18-21
- Status: unconfirmed
## C-12
- Claim: The admin middleware redirects instead of answering with a forbidden status.
- Cited: none
- Status: unconfirmed
## C-13
- Claim: The learn route performs an open redirect.
- Cited: index.js:66-69
- Status: unconfirmed
## C-14
- Claim: The research route fetches a caller-controlled URL from the server.
- Cited: research.js:14-16
- Status: unconfirmed
## C-15
- Claim: Contribution form fields are evaluated as code on the server.
- Cited: contributions.js:32-34
- Status: unconfirmed
