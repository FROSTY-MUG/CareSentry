"""CareSentry Guard Console - End-to-End Live Frontend Verification with Playwright."""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(r"C:\Users\HP\.gemini\antigravity-ide\brain\d034f209-ce32-4da4-8026-c4041b5e84e1")


def run_e2e_verification():
    console_errors = []
    
    with sync_playwright() as p:
        print("[1/6] Launching Chromium browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        
        # Track console errors
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        print("[2/6] Navigating to http://127.0.0.1:8787/ui...")
        page.goto("http://127.0.0.1:8787/ui", wait_until="networkidle")

        # Verify page title and header
        assert "CareSentry Guard Console" in page.title(), f"Unexpected title: {page.title()}"
        assert page.locator(".brand-title").inner_text() == "Guard Console"
        
        # Verify status dot is active
        page.wait_for_selector("#statusText")
        status_text = page.locator("#statusText").inner_text()
        print(f"      Gateway Status: {status_text}")
        assert "Active" in status_text, f"Status is not active: {status_text}"

        # Verify Safety Banner
        safety_banner = page.locator(".safety-banner").inner_text()
        assert "Research tool. Not for clinical decision-making" in safety_banner
        print("      Safety Banner verified.")

        # --- Test Ask View & Demo Case ---
        print("[3/6] Testing Ask View & Demo Case interaction...")
        demo_btn = page.locator("#demoBtn")
        assert demo_btn.is_visible()
        demo_btn.click()

        # Wait for verdict card
        page.wait_for_selector(".verdict-card.withheld")
        verdict_title = page.locator(".verdict-title").inner_text()
        print(f"      Verdict Rendered: {verdict_title}")
        assert "WITHHELD" in verdict_title

        # Verify unverified text is concealed by default
        unverified_box = page.locator(".unverified-revealed-text")
        assert not unverified_box.is_visible(), "Unverified text must NOT be visible by default!"
        print("      Safeguard verified: unverified text is concealed by default.")

        # Click reveal button
        reveal_btn = page.locator(".reveal-unverified-btn")
        reveal_btn.click()
        assert unverified_box.is_visible(), "Unverified text must become visible after clicking reveal."
        sample_text = unverified_box.inner_text()[:60].encode("ascii", errors="replace").decode()
        print(f"      Revealed text sample: {sample_text}...")

        # Click hide button
        reveal_btn.click()
        assert not unverified_box.is_visible(), "Unverified text must hide when toggle clicked again."
        print("      Concealment toggle verified.")

        # Capture Ask view screenshot
        screenshot_ask = SCREENSHOTS_DIR / "guard_console_ask_view.png"
        page.screenshot(path=str(screenshot_ask))
        print(f"      Saved screenshot: {screenshot_ask.name}")

        # --- Test Check View (Audit-Only) ---
        print("[4/6] Testing Check View (Audit-Only)...")
        page.locator("#tabCheck").click()
        assert page.locator("#panelCheck").is_visible()

        test_record = (
            "PATIENT RECORD\n"
            "Allergies: Documented severe penicillin allergy with anaphylaxis.\n"
            "Diagnosis: Strep pharyngitis."
        )
        test_summary = "Initiate treatment with amoxicillin 500mg capsules orally."

        page.locator("#checkRecordInput").fill(test_record)
        page.locator("#checkSummaryInput").fill(test_summary)
        page.locator("#runCheckBtn").click()

        page.wait_for_selector("#checkResultsContainer .card")
        results_text = page.locator("#checkResultsContainer").inner_text()
        assert "FAIL" in results_text
        assert "Identified Safety Violations" in results_text
        assert "Missing from Summary" in results_text
        print("      Audit check detected violations & missing constraints correctly.")

        # Capture Check view screenshot
        screenshot_check = SCREENSHOTS_DIR / "guard_console_check_view.png"
        page.screenshot(path=str(screenshot_check))
        print(f"      Saved screenshot: {screenshot_check.name}")

        # --- Test Settings View ---
        print("[5/6] Testing Settings View...")
        page.locator("#tabSettings").click()
        assert page.locator("#panelSettings").is_visible()

        model_id = page.locator("#settingsModelId").inner_text()
        print(f"      Guarded Model ID: {model_id}")
        assert "Qwen" in model_id

        # Verify installed lanes list rendered
        lanes_text = page.locator("#installedLanesContainer").inner_text()
        assert "Track C (CareSentry Guard Gateway)" in lanes_text
        print("      Installed Lanes table verified.")

        # Test Clear Session
        page.locator("#clearSessionBtn").click()
        time.sleep(0.5)
        status_msg = page.locator("#sessionStatusMsg").inner_text()
        print(f"      Session Action: {status_msg}")
        assert "cleared" in status_msg.lower()

        browser.close()

    print("[6/6] Verifying browser console logs...")
    if console_errors:
        print(f"[FAIL] Encountered {len(console_errors)} console errors:")
        for err in console_errors:
            print(f"       - {err}")
        return False
    else:
        print("[PASS] Zero browser console errors. Frontend is completely healthy!")
        return True


if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
