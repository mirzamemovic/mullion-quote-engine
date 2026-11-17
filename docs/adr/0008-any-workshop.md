# 0008. Any window workshop runs its own quote engine

- Status: proposed, for Mirza's review
- Date: 2026-11-17

## Context

The app was built for one family-run PVC workshop in Kosovo. Mirza decided on 17 November 2026 that it should be a product any window workshop can set up for itself: its own profile systems and their deductions, its own prices, its own team. The product is renamed **Mullion**.

The database was multi-tenant from the start (every table carries `workshop_id`, `db/repository.py: Scoped` filters every query, another workshop's row is "not found"). What was missing was everything around it: how a workshop gets in, who inside it may do what, and how a stranger can try it without an account.

## Decisions

1. **Two roles per workshop: `owner` and `staff`.** The owner manages everything inside their own workshop (catalogue, prices, settings, team) and staff make quotes. The former technical `admin` role is folded into `owner` (migration 0003): the person maintaining a workshop's catalogue is that workshop's owner, not a platform developer. A workshop always keeps at least one active owner.
2. **No web super-admin.** Creating a workshop is a command-line job for the operator (`manage.py create-workshop`). A web page that can see every workshop is the most valuable target in a multi-tenant app, and there is no need for one at this size.
3. **People join through one-time invite links**, never with a password someone else chose. The token is 32 random bytes, only its SHA-256 hash is stored, it works once and for 7 days. There is no email service: the owner copies the link and sends it the way they already talk (Viber, WhatsApp). The operator's `create-workshop` prints the first owner's link.
4. **Two-step login (TOTP) is optional for everyone**, instead of being forced on one role. Turning it on proves a code from the new secret before saving it; turning it on or off needs a fresh password check. Forcing it on a workshop owner whose comfort is Viber-level would push them to share one login with staff, which is worse.
5. **"Try it" is a private sandbox workshop per visitor**, seeded with the sample data and deleted after 24 hours, instead of one shared demo login. Visitors cannot see or break each other's changes, and recruiters get a working app in one click. The endpoint is public, so it is limited: a JSON body (no cross-site form), 3 per IP address per day, 200 at once, no invites (a sandbox never becomes a real account). The IP address is kept for one day, only for that limit.
6. **Each workshop picks its currency** from EUR, BAM, RSD, ALL and MKD, the region's currencies. All of them have two minor digits, so the engine's integer cents need no change. The currency is locked once the workshop has a quote, because every amount already quoted is in it.
7. **English is the default language**, Bosnian stays as the second. A workshop sets its default; each person can switch.

## Consequences

- Every new tenant table gets a tenant-isolation test (the parametrised test over `WORKSHOP_SCOPED`); `invites` is the first.
- The database tests for all of this are written but have not run on the development machine yet (no PostgreSQL).
- Phases 3 and 4 add what a workshop needs to set itself up: a readiness checklist, draft and published price lists and sheets, CSV import, and the admin screens.
