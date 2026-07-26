"""Playwright journeys for the JWT-secured calculation interface."""

from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e


@pytest.fixture
def base_url(live_server: str) -> str:
    return live_server.rstrip("/")


def register_and_login_through_ui(page: Page, base_url: str) -> str:
    unique = uuid4().hex[:10]
    username = f"browser_{unique}"
    password = "SecurePass123!"

    page.goto(f"{base_url}/register")
    page.locator("#firstName").fill("Browser")
    page.locator("#lastName").fill("Tester")
    page.locator("#registerEmail").fill(f"{username}@example.com")
    page.locator("#registerUsername").fill(username)
    page.locator("#registerPassword").fill(password)
    page.locator("#confirmPassword").fill(password)
    page.get_by_role("button", name="Create secure account").click()
    page.wait_for_url("**/login")

    page.locator("#loginIdentifier").fill(username)
    page.locator("#loginPassword").fill(password)
    page.get_by_role("button", name="Sign in securely").click()
    page.wait_for_url("**/dashboard")
    expect(page.locator("[data-workspace-user]")).to_have_text(username)
    return username


def test_unauthenticated_dashboard_redirects_to_login(
    page: Page,
    base_url: str,
):
    page.goto(f"{base_url}/dashboard")

    page.wait_for_url("**/login")
    expect(page.get_by_role("heading", name="Welcome back.")).to_be_visible()


def test_invalid_token_is_rejected_by_secured_api(
    page: Page,
    base_url: str,
):
    page.goto(base_url)
    page.evaluate(
        "() => localStorage.setItem('access_token', 'invalid.jwt.token')"
    )

    page.goto(f"{base_url}/dashboard")

    page.wait_for_url("**/login")
    expect(page.locator("#loginForm")).to_be_visible()


def test_complete_bread_journey_and_insights_feature(
    page: Page,
    base_url: str,
):
    register_and_login_through_ui(page, base_url)

    expect(page.locator('[data-testid="insight-total"]')).to_have_text("0")

    # Negative client-side scenarios must not send or save malformed values.
    page.locator("#calcInputs").fill("5, not-a-number")
    page.get_by_role("button", name="Calculate + save").click()
    expect(page.locator("#formAlert")).to_have_text(
        "Every input must be a valid number."
    )
    expect(page.locator('[data-testid="insight-total"]')).to_have_text("0")

    page.locator("#calcType").select_option("division")
    page.locator("#calcInputs").fill("10, 0")
    page.get_by_role("button", name="Calculate + save").click()
    expect(page.locator("#formAlert")).to_have_text(
        "Division by zero is not allowed."
    )

    # Add and browse.
    page.locator("#calcType").select_option("multiplication")
    page.locator("#calcInputs").fill("3, 4")
    page.get_by_role("button", name="Calculate + save").click()
    expect(page.locator("#formAlert")).to_contain_text(
        "Calculation saved. Result: 12."
    )
    row = page.locator('[data-testid="calculation-row"]')
    expect(row).to_have_count(1)
    expect(row).to_contain_text("3 × 4")
    expect(page.locator('[data-testid="insight-total"]')).to_have_text("1")
    expect(page.locator('[data-testid="insight-average"]')).to_have_text("12")
    expect(page.locator('[data-testid="insight-highest"]')).to_have_text("12")
    expect(
        page.locator('[data-operation-count="multiplication"]')
    ).to_have_text("1")

    # Read.
    row.get_by_role("link", name="Read").click()
    page.wait_for_url("**/dashboard/view/*")
    expect(page.locator('[data-testid="detail-result"]')).to_have_text("12")
    expect(page.locator("[data-detail-expression]")).to_have_text("3 × 4")

    # Edit.
    page.get_by_role("link", name="Edit inputs").click()
    page.wait_for_url("**/dashboard/edit/*")
    expect(page.locator("#editInputs")).to_have_value("3, 4")
    page.locator("#editInputs").fill("5, 6")
    expect(page.locator("[data-edit-preview]")).to_contain_text("= 30")
    page.get_by_role("button", name="Save revised record").click()
    page.wait_for_url("**/dashboard/view/*")
    expect(page.locator('[data-testid="detail-result"]')).to_have_text("30")

    # Delete and confirm the aggregate feature updates with the ledger.
    page.get_by_role("link", name="Back to ledger").click()
    page.wait_for_url("**/dashboard")
    expect(page.locator('[data-testid="insight-average"]')).to_have_text("30")
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator('[data-testid="calculation-row"]').get_by_role(
        "button", name="Delete"
    ).click()
    expect(page.locator("#formAlert")).to_have_text("Calculation deleted.")
    expect(page.locator('[data-testid="calculation-row"]')).to_have_count(0)
    expect(page.locator('[data-testid="insight-total"]')).to_have_text("0")
