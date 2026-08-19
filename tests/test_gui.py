"""Playwright tests for the Streamlit GUI."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def streamlit_server():
    """Start Streamlit server for testing."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent)
    
    python_executable = sys.executable
    
    proc = subprocess.Popen(
        [
            python_executable,
            "-m", "streamlit", "run", "gui/app.py",
            "--server.port=8502",
            "--server.address=127.0.0.1",
            "--server.headless=true",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    
    time.sleep(10)
    
    yield proc
    
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture(scope="session")
def browser(streamlit_server):
    """Create browser instance."""
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        chromium = p.chromium
        browser = chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """Create page instance."""
    page = browser.new_page()
    yield page
    page.close()


@pytest.mark.playwright
def test_gui_loads(page):
    """Test that the GUI loads successfully."""
    page.goto("http://127.0.0.1:8502")
    page.wait_for_selector(".stApp", timeout=30000)
    page.wait_for_selector("role=tab", timeout=30000)
    
    tabs = page.locator("role=tab")
    assert tabs.count() == 5


@pytest.mark.playwright
def test_single_pdf_tab(page):
    """Test the Single PDF tab."""
    page.goto("http://127.0.0.1:8502")
    page.wait_for_selector(".stApp", timeout=30000)
    page.wait_for_selector("role=tab", timeout=30000)
    
    tabs = page.locator("role=tab")
    tabs.first.click()
    page.wait_for_selector("text=Convert Single PDF", timeout=10000)
    assert page.locator("text=Convert Single PDF").first.is_visible()


@pytest.mark.playwright
def test_folder_tab(page):
    """Test the Folder tab."""
    page.goto("http://127.0.0.1:8502")
    page.wait_for_selector(".stApp", timeout=30000)
    page.wait_for_selector("role=tab", timeout=30000)
    
    tabs = page.locator("role=tab")
    tabs.nth(1).click()
    page.wait_for_selector("text=Convert PDF Folder", timeout=10000)
    assert page.locator("text=Convert PDF Folder").first.is_visible()


@pytest.mark.playwright
def test_identify_tab(page):
    """Test the Identify Layout tab."""
    page.goto("http://127.0.0.1:8502")
    page.wait_for_selector(".stApp", timeout=30000)
    page.wait_for_selector("role=tab", timeout=30000)
    
    tabs = page.locator("role=tab")
    tabs.nth(2).click()
    page.wait_for_selector("text=Identify PDF Layout", timeout=10000)
    assert page.locator("text=Identify PDF Layout").first.is_visible()


@pytest.mark.playwright
def test_validate_tab(page):
    """Test the Validate tab."""
    page.goto("http://127.0.0.1:8502")
    page.wait_for_selector(".stApp", timeout=30000)
    page.wait_for_selector("role=tab", timeout=30000)
    
    tabs = page.locator("role=tab")
    tabs.nth(3).click()
    page.wait_for_selector("text=Validate PDF/UA-1 Compliance", timeout=10000)
    assert page.locator("text=Validate PDF/UA-1 Compliance").first.is_visible()


@pytest.mark.playwright
def test_batch_tab(page):
    """Test the Batch tab."""
    page.goto("http://127.0.0.1:8502")
    page.wait_for_selector(".stApp", timeout=30000)
    page.wait_for_selector("role=tab", timeout=30000)
    
    tabs = page.locator("role=tab")
    tabs.nth(4).click()
    page.wait_for_selector("text=Batch Convert PDFs", timeout=10000)
    assert page.locator("text=Batch Convert PDFs").first.is_visible()


@pytest.mark.playwright
def test_sidebar(page):
    """Test that sidebar has expected content."""
    page.goto("http://127.0.0.1:8502")
    page.wait_for_selector(".stApp", timeout=30000)
    page.wait_for_selector("section[data-testid='stSidebar']", timeout=30000)
    
    sidebar = page.locator("section[data-testid='stSidebar']")
    assert sidebar.locator("text=Settings").first.is_visible()
    assert sidebar.locator("text=About").first.is_visible()


@pytest.mark.playwright
def test_file_uploader_present(page):
    """Test that file upload area is present."""
    page.goto("http://127.0.0.1:8502")
    page.wait_for_selector(".stApp", timeout=30000)
    page.wait_for_selector("role=tab", timeout=30000)
    
    assert page.locator(".stFileUploader").first.is_visible()
