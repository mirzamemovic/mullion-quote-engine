# Privacy

What personal data the PVC Quote Engine keeps, why, and for how long (PLAN.md section 9). Kosovo's Law No. 06/L-082 on the Protection of Personal Data applies.

## Who is responsible

Each workshop that uses the app is the controller of its own clients' data; the operator of the server processes it for them. Every workshop's data is kept apart: each row carries its workshop and every query is filtered by it. The data is on a server rented from Oracle Cloud, in the account's home region (to be stated here once the server exists).

## What is kept

| Data | Why | Kept for |
|---|---|---|
| Client name, phone number, place | To prepare, send and follow up a quote | Accepted jobs: 10 years. Rejected or expired quotes: erased after 12 months. |
| Window sizes, prices, quote totals, payments | The quote itself | 10 years; these stay when a client's name and phone are erased |
| User accounts (owners and staff): email, password hash, and a TOTP secret for people who turned two-step login on | Logging in | While the account exists |
| Invite links: a hash of the token, the role, who created it, times | Letting a new person join a workshop | Until used or 7 days, then kept as a used or expired record |
| Sessions: a hash of the session token, browser name, times | Keeping users logged in, letting them log out other devices | Up to 30 days |
| "Try it" sandbox requests: IP address and time | Limiting sandboxes to 3 per address per day | 1 day |
| Login attempts: username, IP address, time, success | Stopping password guessing | Not decided yet (PLAN.md does not say) |
| Audit log: who changed what, without personal data | Tracing changes to prices and quotes | Not decided yet (PLAN.md does not say) |

No data is sold or shared. Suppliers receive price requests that list materials only, never client details.

## Where else data goes

| Service | What | Why |
|---|---|---|
| Oracle Cloud | The server and its disk | Hosting |
| OCI Object Storage and Cloudflare R2 | Encrypted database backups | Recovery; the encryption key is not stored with them |
| Sentry (after M6) | Error reports with names and phones removed | Fixing faults |

## Rights

A client can ask the workshop for a copy of their data (export) or for it to be erased. Erasing blanks the name and phone number and records when; the quote totals stay so the workshop's books remain complete. Backups roll over within 8 weeks, so erased data disappears from them by then.

## "Try it" sandboxes

A visitor who clicks "Try it" gets a private workshop filled with invented sample data, with no account to create and no email asked. It is deleted with everything typed into it 24 hours later (an hourly job, and again whenever a new sandbox starts). Visitors are told not to type real client data into a sandbox.

## Status

The export, erase and retention jobs are built with the database in M6. This page is the plan they follow.
