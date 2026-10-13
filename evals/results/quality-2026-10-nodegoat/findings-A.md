# Findings A
## A-1
- Claim: An earlier issue concerning access to the benefits route was handled in a previous audit and is treated as closed.
- Cited: none
- Status: unconfirmed
## A-2
- Claim: An earlier issue concerning the admin-gating middleware was rejected in a previous audit and not reconsidered.
- Cited: none
- Status: unconfirmed
## A-3
- Claim: The allocations route takes the target user id from the URL without comparing it to the session user, so any signed-in user can read another user's allocations and name.
- Cited: app/routes/allocations.js:16, index.js:59, allocations-dao.js:377, allocations-dao.js:401, allocations-dao.js:416-418
- Status: confirmed
## A-4
- Claim: Every signed-in user sees all memos and memos carry no owner, suggesting missing per-user scoping on the memos page.
- Cited: app/data/memos-dao.js:448-468
- Status: unconfirmed
## A-5
- Claim: The memo body can carry stored script that is rendered to other users.
- Cited: none
- Status: unconfirmed
## A-6
- Claim: The threshold query value is concatenated into a server-side JavaScript filter, letting a signed-in user remove the user restriction and read all allocations.
- Cited: allocations-dao.js:396-398
- Status: unconfirmed
## A-7
- Claim: The tutorial pages can be reached without signing in.
- Cited: none
- Status: unconfirmed
## A-8
- Claim: A user could set the admin flag on their account through signup or profile update by supplying extra fields.
- Cited: user-dao.js (addUser), profile-dao.js (updateUser)
- Status: unconfirmed
## A-9
- Claim: Contribution form fields are evaluated as code on the server, allowing an authenticated user to execute code.
- Cited: contributions.js:271-273
- Status: unconfirmed
## A-10
- Claim: A query-supplied URL is used for a redirect without validation.
- Cited: index.js:68
- Status: unconfirmed
## A-11
- Claim: The server fetches a user-supplied URL, enabling server-side requests to arbitrary targets.
- Cited: research.js:14-15
- Status: unconfirmed
## A-12
- Claim: The session identifier is not renewed when a user logs in.
- Cited: session.js:197
- Status: unconfirmed
## A-13
- Claim: User passwords are stored in plaintext.
- Cited: user-dao.js
- Status: unconfirmed
