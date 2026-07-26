# Module 14 Development Reflection

## Continuing the Module 13 application

Module 14 now directly continues my Module 13 JWT project rather than treating
authentication and calculations as unrelated applications. The existing user,
bcrypt, token, database, and Pydantic code remains the security foundation.
Calculation persistence and BREAD routes were added around that foundation.

This continuity made the purpose of JWT authentication clearer. Login is not
only a feature by itself; the verified token supplies the user identity used by
every calculation query.

## Completing the BREAD workflow

Browse, Read, Edit, Add, and Delete are more than five API routes. Each
operation also requires an authenticated request, ownership filtering,
database persistence, JSON serialization, and a matching front-end state
change.

The most important security decision was deriving the calculation owner from
the verified JWT. The server never accepts a user ID from the calculation form
as proof of ownership. Read, edit, and delete queries filter by both the
calculation ID and authenticated user ID. An unowned record therefore returns
`404`, which prevents users from learning whether another user's record
exists.

## Validation and error handling

Validation exists at multiple boundaries. JavaScript provides immediate
feedback for missing values, nonnumeric operands, and division by zero.
Pydantic and calculation-domain functions repeat the important rules because
browser code can be bypassed.

Invalid updates are calculated before the valid stored values are replaced.
If an update fails, the transaction is rolled back and the original record
remains unchanged. Integration tests verify that behavior directly.

## Testing lessons

The project demonstrates why different test levels are complementary:

- Unit tests verify arithmetic, Pydantic, JWT, bcrypt, and insight rules.
- Integration tests verify authentication, persistence, ownership isolation,
  controlled errors, and complete BREAD behavior.
- Bun tests verify reusable client-side parsing and preview functions.
- Playwright uses a real Chromium browser to verify registration, login,
  validation, creation, browsing, reading, editing, deletion, redirects, and
  the Insights display.

The complete browser journey is valuable because request-only tests cannot
prove that scripts loaded, selectors remained connected to the templates, or
the visible ledger changed after an API response.

## CI/CD and containerization

The GitHub Actions workflow treats deployment as a sequence of gates. Python
and JavaScript tests run first. The production image is built and scanned for
fixed high and critical vulnerabilities only after tests pass. Docker Hub
publication occurs only after the security scan succeeds.

The container runs as a non-root user and installs only production
dependencies. Publishing `latest` plus the Git commit SHA provides both a
convenient tag and an immutable connection between deployed code and source.

## Final takeaway

A feature is not complete merely because its route works once. A professional
feature includes validation, authorization, persistence, useful errors,
automated tests at several boundaries, documentation, a reproducible
container, and a gated delivery pipeline. Module 14 connected those practices
to the authentication work completed in Module 13.
