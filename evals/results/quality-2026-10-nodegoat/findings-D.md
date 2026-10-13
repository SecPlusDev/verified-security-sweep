# Findings D
## D-1
- Claim: The benefits route was previously open to non-admin users and has since been fixed.
- Cited: none
- Status: unconfirmed
## D-2
- Claim: The admin middleware redirects instead of refusing with a forbidden status.
- Cited: none
- Status: unconfirmed
## D-3
- Claim: Signup could let a user promote themselves to admin by supplying the admin flag.
- Cited: none
- Status: unconfirmed
## D-4
- Claim: A stale session could retain admin rights after the user loses them.
- Cited: none
- Status: unconfirmed
## D-5
- Claim: The allocations route reads the target user id from the URL instead of the session, so any signed-in user can read other users' allocations and names.
- Cited: app/routes/index.js:59, app/routes/allocations.js:11-30, app/data/allocations-dao.js:57-100
- Status: confirmed
## D-6
- Claim: The threshold query value is interpolated into a server-side JavaScript filter, allowing a user to escape per-user scoping and read all allocations.
- Cited: app/data/allocations-dao.js:~63-82
- Status: confirmed
## D-7
- Claim: The same injection can hang the server with an endless loop.
- Cited: none
- Status: unconfirmed
## D-8
- Claim: Memos form a single shared list without an author, so there is no per-user ownership.
- Cited: none
- Status: unconfirmed
## D-9
- Claim: With template auto-escaping off and a session cookie described as not HttpOnly, a posted memo could run script in other users' browsers and steal an admin session.
- Cited: server.js
- Status: unconfirmed
## D-10
- Claim: Profile and contributions could accept a body-supplied user id or extra fields allowing changes to other users or privileges.
- Cited: none
- Status: unconfirmed
## D-11
- Claim: No POST route, including the admin benefits update, has protection against cross-site request forgery.
- Cited: none
- Status: unconfirmed
## D-12
- Claim: The session identifier is not regenerated at login, enabling fixation.
- Cited: none
- Status: unconfirmed
## D-13
- Claim: Passwords are stored and compared in plaintext.
- Cited: user-dao.js
- Status: unconfirmed
## D-14
- Claim: Contribution fields are evaluated as code on the server.
- Cited: none
- Status: unconfirmed
## D-15
- Claim: The learn route performs an open redirect.
- Cited: none
- Status: unconfirmed
## D-16
- Claim: The research route fetches a caller-controlled URL from the server.
- Cited: none
- Status: unconfirmed
