"""Capture reproducible Module 14 submission screenshots with Playwright.

Run this script while the Docker Compose application is available on port 8000.
It creates a disposable user and real calculation records, then captures each
BREAD state plus the public CI/CD evidence pages.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "images"
BASE_URL = "http://127.0.0.1:8000"
GITHUB_RUN_URL = (
    "https://github.com/MatthewFeroz/module14_is601/actions/runs/30215387918"
)
DOCKER_HUB_URL = "https://hub.docker.com/r/matthewferoz/module14_is601/tags"


def capture(page: Page, filename: str, *, full_page: bool = True) -> None:
    """Save a readable JPEG screenshot without browser chrome or credentials."""
    page.screenshot(
        path=OUTPUT / filename,
        full_page=full_page,
        type="jpeg",
        quality=88,
    )


def dismiss_cookie_banner(page: Page) -> None:
    """Dismiss common public-site cookie banners when one is present."""
    reject_button = page.locator("#onetrust-reject-all-handler")
    if reject_button.count() and reject_button.first.is_visible():
        reject_button.first.click()
        page.wait_for_timeout(500)
        return

    for label in ("Accept all", "Accept All", "Accept all cookies"):
        button = page.get_by_role("button", name=label, exact=True)
        if button.count() and button.first.is_visible():
            button.first.click()
            page.wait_for_timeout(500)
            break


def capture_public_delivery_evidence(page: Page) -> None:
    page.goto(GITHUB_RUN_URL, wait_until="domcontentloaded", timeout=90_000)
    page.wait_for_timeout(6_000)
    dismiss_cookie_banner(page)
    page.get_by_text("Prepare the independent Module 14 submission").first.wait_for(
        state="visible",
        timeout=30_000,
    )
    capture(page, "github-actions-success.jpg", full_page=False)

    page.goto(DOCKER_HUB_URL, wait_until="domcontentloaded", timeout=90_000)
    page.wait_for_timeout(8_000)
    dismiss_cookie_banner(page)
    page.get_by_text("latest", exact=True).first.wait_for(
        state="visible",
        timeout=30_000,
    )
    capture(page, "docker-hub-tags.jpg", full_page=False)


def register_and_login(page: Page) -> str:
    unique = uuid4().hex[:10]
    username = f"submission_{unique}"
    password = "SubmissionPass123!"

    page.goto(f"{BASE_URL}/register", wait_until="networkidle")
    page.locator("#firstName").fill("Module")
    page.locator("#lastName").fill("Fourteen")
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
    page.locator("[data-workspace-user]").wait_for(state="visible")
    return username


def add_calculation(page: Page, operation: str, inputs: str) -> None:
    page.locator("#calcType").select_option(operation)
    page.locator("#calcInputs").fill(inputs)
    page.get_by_role("button", name="Calculate + save").click()
    page.locator("#formAlert").wait_for(state="visible")


def capture_bread_evidence(page: Page) -> None:
    register_and_login(page)

    add_calculation(page, "addition", "5, 7")
    add_calculation(page, "multiplication", "6, 5")
    page.locator('[data-testid="calculation-row"]').nth(1).wait_for(
        state="visible"
    )
    capture(page, "bread-add-browse.jpg")

    rows = page.locator('[data-testid="calculation-row"]')
    rows.filter(has_text="6 × 5").get_by_role("link", name="Read").click()
    page.wait_for_url("**/dashboard/view/*")
    page.locator('[data-testid="detail-result"]').wait_for(state="visible")
    page.wait_for_timeout(1_200)
    capture(page, "bread-read.jpg")

    page.get_by_role("link", name="Edit inputs").click()
    page.wait_for_url("**/dashboard/edit/*")
    page.locator("#editInputs").fill("10, 3")
    page.locator("[data-edit-preview]").get_by_text("= 30").wait_for(
        state="visible"
    )
    page.wait_for_timeout(1_200)
    capture(page, "bread-edit.jpg")

    page.get_by_role("button", name="Save revised record").click()
    page.wait_for_url("**/dashboard/view/*")
    page.locator("[data-detail-expression]").get_by_text("10 × 3").wait_for(
        state="visible"
    )

    page.get_by_role("link", name="Back to ledger").click()
    page.wait_for_url("**/dashboard")
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator('[data-testid="calculation-row"]').filter(
        has_text="10 × 3"
    ).get_by_role("button", name="Delete").click()
    page.locator("#formAlert").get_by_text("Calculation deleted.").wait_for(
        state="visible"
    )
    page.wait_for_timeout(1_200)
    page.locator(".skip-link").evaluate(
        "(element) => element.style.setProperty('display', 'none', 'important')"
    )
    capture(page, "bread-delete.jpg")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1200},
            device_scale_factor=1,
            color_scheme="light",
        )
        page = context.new_page()

        capture_public_delivery_evidence(page)
        capture_bread_evidence(page)

        context.close()
        browser.close()

    print(f"Captured submission evidence in {OUTPUT}")


if __name__ == "__main__":
    main()
