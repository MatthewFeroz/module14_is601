# Module 13 Reflection

## Connecting the Front End to the API

The most valuable part of this module was seeing authentication as one complete
browser-to-database workflow rather than as separate HTML, JavaScript, and
FastAPI exercises. The course videos emphasized that Jinja performs the
server-side page composition while JavaScript manipulates the browser's
Document Object Model after it loads. I followed that model with a shared
`layout.html`, separate page templates, and one deferred JavaScript file that
registers its event listeners after `DOMContentLoaded`.

Intercepting each form's submit event with `preventDefault()` made the
registration and login pages behave like API clients. The code builds a JSON
object from the form, sends it with `fetch`, waits for the response, and updates
the existing page instead of allowing a traditional form submission to erase
the user's input. Matching the client-side rules to the Pydantic rules was
important: the browser gives immediate, field-specific feedback, while the API
remains the authoritative validation boundary.

## Authentication and Authorization

The registration flow reinforced why a password should never be recoverable
from the database. The application creates a unique bcrypt salt and hash for
each password and exposes neither the original value nor the stored hash in its
response models. Duplicate checks are case-insensitive, and database uniqueness
constraints remain in place to handle concurrent requests safely.

The login flow clarified the difference between authentication and
authorization. Valid credentials authenticate the user and produce a
short-lived signed JWT. The browser stores that token in `localStorage`, as
demonstrated in the video, and redirects to the dashboard. The dashboard then
uses the token as an HTTP bearer credential when requesting `/auth/me`.
Possessing a dashboard URL is not authorization; the server still verifies the
signature, expiry, access-token type, active account, and database user before
returning any protected data.

## Testing Challenges

Playwright made the boundaries between the layers visible. The positive test
registers through the real form, waits for its success message and redirect,
logs in through the real form, verifies the stored JWT, and confirms that the
protected profile appears. The negative tests prove that a short password is
stopped by browser validation and that a valid request with the wrong password
reaches the server, receives `401 Unauthorized`, and produces a useful UI
message without storing a token.

One visual issue only appeared during screenshot review. The test context
requests reduced motion, but the delayed reveal animation still briefly left
the authenticated identity card transparent. The element existed, so a DOM
assertion passed, yet the screenshot showed a blank column. Removing animation
delays under `prefers-reduced-motion` fixed both accessibility behavior and the
captured evidence. This was a useful reminder that functional assertions and
visual inspection catch different classes of defects.

The Docker Compose smoke test exposed another integration issue: publishing
PostgreSQL on host port 5432 conflicted with an earlier course container.
PostgreSQL only needs to be reachable by the app on the internal Compose
network, so removing the host binding made the project coexist cleanly with
prior modules without weakening the architecture.

## CI/CD and Next Steps

The final pipeline mirrors the local workflow. GitHub Actions starts a clean
PostgreSQL service, installs Chromium, runs all 19 tests, preserves JUnit,
coverage, and screenshot evidence, and only then builds and publishes the
Docker image. Publishing both `latest` and commit-SHA tags keeps the convenient
default tag while retaining an immutable deployment reference.

I intentionally stopped at authentication and a protected identity view. The
existing calculation BREAD ideas belong to Module 14. That separation keeps
this submission aligned with Module 13's learning goal and leaves a clean
authorization foundation for user-owned calculation routes in the next module.
