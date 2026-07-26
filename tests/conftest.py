import os
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest


if "DATABASE_URL" not in os.environ:
    test_database = Path(tempfile.gettempdir()) / "module13_jwt_test.db"
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{test_database}"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-and-deterministic")

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.bind(("127.0.0.1", 0))
        return connection.getsockname()[1]


def wait_until_ready(url: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{url}/health", timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"FastAPI server did not become ready at {url}")


@pytest.fixture(scope="session")
def live_server() -> Generator[str, None, None]:
    port = available_port()
    url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_until_ready(url)
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000},
        reduced_motion="reduce",
    )
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def screenshot_directory() -> Path:
    directory = Path("test-results/screenshots")
    directory.mkdir(parents=True, exist_ok=True)
    return directory
