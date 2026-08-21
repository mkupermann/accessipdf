#!/usr/bin/env python3
"""Capture screenshots of the Streamlit GUI for documentation."""

import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    """Capture screenshots of the GUI."""
    # Start Streamlit server
    print("Starting Streamlit server...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "gui/app.py",
            "--server.port=8503",
            "--server.address=127.0.0.1",
            "--server.headless=true",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for server to start
    time.sleep(15)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            chromium = p.chromium
            browser = chromium.launch(headless=True)
            page = browser.new_page()

            # Set viewport
            page.set_viewport_size({"width": 1280, "height": 800})

            base_url = "http://127.0.0.1:8503"
            output_dir = Path(__file__).parent.parent / "docs" / "media" / "gui"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Capture main page
            print("Capturing main page...")
            page.goto(base_url)
            page.wait_for_selector(".stApp", timeout=30000)
            page.wait_for_selector("role=tab", timeout=30000)
            time.sleep(2)
            page.screenshot(path=str(output_dir / "01-main.png"), full_page=True)

            # Capture Single PDF tab
            print("Capturing Single PDF tab...")
            tabs = page.locator("role=tab")
            tabs.first.click()
            page.wait_for_selector("text=Convert Single PDF", timeout=10000)
            time.sleep(2)
            page.screenshot(path=str(output_dir / "02-single-pdf.png"), full_page=True)

            # Capture Folder tab
            print("Capturing Folder tab...")
            tabs.nth(1).click()
            page.wait_for_selector("text=Convert PDF Folder", timeout=10000)
            time.sleep(2)
            page.screenshot(path=str(output_dir / "03-folder.png"), full_page=True)

            # Capture Identify Layout tab
            print("Capturing Identify Layout tab...")
            tabs.nth(2).click()
            page.wait_for_selector("text=Identify PDF Layout", timeout=10000)
            time.sleep(2)
            page.screenshot(path=str(output_dir / "04-identify.png"), full_page=True)

            # Capture Validate tab
            print("Capturing Validate tab...")
            tabs.nth(3).click()
            page.wait_for_selector("text=Validate PDF/UA-1 Compliance", timeout=10000)
            time.sleep(2)
            page.screenshot(path=str(output_dir / "05-validate.png"), full_page=True)

            # Capture Batch tab
            print("Capturing Batch tab...")
            tabs.nth(4).click()
            page.wait_for_selector("text=Batch Convert PDFs", timeout=10000)
            time.sleep(2)
            page.screenshot(path=str(output_dir / "06-batch.png"), full_page=True)

            # Capture sidebar
            print("Capturing sidebar...")
            sidebar = page.locator("section[data-testid='stSidebar']")
            sidebar.screenshot(path=str(output_dir / "07-sidebar.png"))

            browser.close()

        print("Screenshots captured successfully!")
        print(f"Saved to: {output_dir}")

    finally:
        # Stop server
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


if __name__ == "__main__":
    main()
