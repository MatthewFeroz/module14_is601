from uuid import uuid4

import pytest
import httpx
from playwright.sync_api import expect


pytestmark = pytest.mark.e2e


def unique_user():
    unique = uuid4().hex[:10]
    return {
        "first_name": "Katherine",
        "last_name": "Johnson",
        "username": f"katherine_{unique}",
        "email": f"katherine.{unique}@example.com",
        "password": "OrbitalPass13!",
        "confirm_password": "OrbitalPass13!",
    }


def fill_registration(page, user):
    page.get_by_label("First name").fill(user["first_name"])
    page.get_by_label("Last name").fill(user["last_name"])
    page.get_by_label("Email address").fill(user["email"])
    page.get_by_label("Username", exact=True).fill(user["username"])
    page.get_by_label("Password", exact=True).fill(user["password"])
    page.get_by_label("Confirm password").fill(user["confirm_password"])


def test_register_then_login_stores_token_and_authorizes_dashboard(
    page,
    live_server,
    screenshot_directory,
):
    user = unique_user()
    page.goto(f"{live_server}/register")
    fill_registration(page, user)
    page.get_by_role("button", name="Create secure account").click()

    alert = page.get_by_role("status")
    expect(alert).to_contain_text("Registration successful")
    page.screenshot(
        path=screenshot_directory / "registration-success.png",
        full_page=True,
    )
    page.wait_for_url(f"{live_server}/login")

    page.get_by_label("Email or username").fill(user["email"])
    page.get_by_label("Password", exact=True).fill(user["password"])
    page.get_by_role("button", name="Sign in securely").click()

    expect(alert).to_contain_text("Login successful")
    page.wait_for_url(f"{live_server}/dashboard")
    expect(page.get_by_text(f"Welcome, {user['first_name']}.")).to_be_visible()
    assert page.evaluate("localStorage.getItem('access_token')").count(".") == 2
    page.screenshot(
        path=screenshot_directory / "authenticated-dashboard.png",
        full_page=True,
    )


def test_short_password_shows_client_side_error(page, live_server):
    user = unique_user()
    user["password"] = user["confirm_password"] = "Short1!"
    page.goto(f"{live_server}/register")
    fill_registration(page, user)
    page.get_by_role("button", name="Create secure account").click()

    expect(page.get_by_role("status")).to_contain_text(
        "Please correct the highlighted registration fields"
    )
    expect(page.locator("[data-error-for='registerPassword']")).to_contain_text(
        "Use 8–72 characters"
    )
    assert page.url == f"{live_server}/register"


def test_wrong_password_shows_server_error(
    page,
    live_server,
    screenshot_directory,
):
    user = unique_user()
    response = httpx.post(f"{live_server}/register", json=user, timeout=5)
    assert response.status_code == 201

    page.goto(f"{live_server}/login")
    page.get_by_label("Email or username").fill(user["email"])
    page.get_by_label("Password", exact=True).fill("IncorrectPass13!")
    page.get_by_role("button", name="Sign in securely").click()

    expect(page.get_by_role("status")).to_contain_text(
        "Invalid email, username, or password"
    )
    assert page.evaluate("localStorage.getItem('access_token')") is None
    page.screenshot(
        path=screenshot_directory / "invalid-login.png",
        full_page=True,
    )
