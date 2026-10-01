"""Real Chromium -> Vite -> Flask upload smoke test, using synthetic fixtures.

Requires the backend dependencies, playwright, npm dependencies, and Chrome.
Run from the repository root with the backend virtualenv's Python.
No existing database, account, or private uploads are used.
"""

import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]


def main():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        frontend_port = listener.getsockname()[1]
    frontend_url = f"http://127.0.0.1:{frontend_port}"
    os.environ["CORS_ORIGINS"] = frontend_url
    sys.path.insert(0, str(ROOT / "backend"))
    from app import create_app
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright, expect

    with tempfile.TemporaryDirectory(prefix="glassbox-upload-") as temporary:
        app = create_app("testing")
        app.config.update(
            DOCUMENT_UPLOAD_DIR=temporary,
            AADHAAR_HASH_KEY="browser-smoke-test-only-key",
        )
        server = make_server("127.0.0.1", 0, app, threaded=True)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        api_url = f"http://127.0.0.1:{server.server_port}/api"
        env = {**os.environ, "VITE_API_BASE_URL": api_url}
        with open(Path(temporary) / "vite.log", "w", encoding="utf-8") as log:
            vite = subprocess.Popen(
                [shutil.which("node"), str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
                 "--host", "127.0.0.1", "--port", str(frontend_port), "--strictPort"],
                cwd=ROOT / "frontend", env=env, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                for _ in range(100):
                    try:
                        with urlopen(frontend_url, timeout=1):
                            break
                    except OSError:
                        if vite.poll() is not None:
                            raise RuntimeError("Vite did not start")
                        time.sleep(0.2)
                else:
                    raise RuntimeError("Timed out waiting for Vite")
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(channel="chrome", headless=True)
                    try:
                        page = browser.new_page()
                        page_errors = []
                        page.on("pageerror", lambda error: page_errors.append(str(error)))
                        registration = page.request.post(api_url + "/auth/register", data={
                            "full_name": "Asha Example", "email": "browser-smoke@example.test",
                            "password": "synthetic-test-password-123",
                        })
                        assert registration.status == 201
                        token = registration.json()["token"]
                        page.add_init_script(
                            "localStorage.setItem('xai_loan_token', " + json.dumps(token) + ");"
                        )
                        page.goto(frontend_url + "/apply")
                        expect(page.get_by_role("heading", name="Upload documents", exact=True)).to_be_visible()
                        fixtures = ROOT / "tests/fixtures/documents"
                        from PIL import Image
                        scanned = Path(temporary) / "scanned-aadhaar.pdf"
                        with Image.open(fixtures / "aadhaar.png") as image:
                            image.convert("RGB").save(scanned, format="PDF")
                        for title, filename, expected_status in [
                            ("Aadhaar", "aadhaar.pdf", 201),
                            ("Aadhaar", "aadhaar.png", 201),
                            ("Aadhaar", str(scanned), 201),
                            ("PAN Card", "pan.pdf", 201),
                            ("Salary slip", "salary_slip.pdf", 201),
                            ("Bank statement", "bank_statement.pdf", 201),
                            ("Aadhaar", "pan.pdf", 422),
                        ]:
                            control = page.get_by_label(re.compile("^" + title))
                            expect(control).to_be_enabled(timeout=30000)
                            with page.expect_response(
                                lambda response: response.url == api_url + "/documents"
                                and response.request.method == "POST", timeout=60000
                            ) as pending:
                                control.set_input_files(fixtures / filename)
                            response = pending.value
                            body = response.json()
                            assert response.status == expected_status, (title, response.status, body)
                            card = control.locator("xpath=ancestor::article")
                            expect(card.get_by_text(body["document"]["status"], exact=True)).to_be_visible()
                            expect(card.get_by_role("button", name="Remove " + title)).to_be_visible()
                            if title == "Bank statement":
                                expect(page.get_by_role("button", name="Analyze Application")).to_be_enabled()
                            if expected_status == 422:
                                expect(card.get_by_text(re.compile("Wrong document type")).first).to_be_visible()
                                expect(page.get_by_role("button", name="Analyze Application")).to_be_disabled()
                            print(f"PASS {title}: {filename} -> HTTP {response.status}, {body['document']['status']}", flush=True)
                        assert not page_errors, page_errors
                    finally:
                        browser.close()
            finally:
                vite.terminate()
                vite.wait(timeout=15)
                server.shutdown()
                worker.join(timeout=5)


if __name__ == "__main__":
    main()
