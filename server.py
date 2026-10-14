"""
Local Web Server for Game Module.
Serves the HTML5 interactive canvas engine, telemetry studio, and REST endpoints
for running Python test suites and simulations on localhost:8000.

Zero external dependencies - uses standard library http.server.
"""
from __future__ import annotations
import http.server
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


class GameStudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/download-zip":
            zip_path = BASE_DIR / "week2_game_module_submission.zip"
            if zip_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{zip_path.name}"')
                self.send_header("Content-Length", str(zip_path.stat().st_size))
                self.end_headers()
                with open(zip_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Submission zip not found")
                return

        if parsed.path == "/api/status":
            self.send_json({
                "status": "online",
                "version": "1.0.0",
                "python_version": sys.version,
                "project": "Week 2 Game Module Deliverable"
            })
            return

        # Default static file handling from WEB_DIR
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/run-tests":
            try:
                proc = subprocess.run(
                    [sys.executable, str(BASE_DIR / "run_tests.py")],
                    cwd=str(BASE_DIR),
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
                self.send_json({"code": proc.returncode, "output": output})
            except Exception as e:
                self.send_json({"code": 1, "output": f"Error running tests: {e}"})
            return

        if parsed.path == "/api/run-simulation":
            try:
                proc = subprocess.run(
                    [sys.executable, str(BASE_DIR / "main.py"), "--duration", "5.0"],
                    cwd=str(BASE_DIR),
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
                self.send_json({"code": proc.returncode, "output": output})
            except Exception as e:
                self.send_json({"code": 1, "output": f"Error running simulation: {e}"})
            return

        self.send_error(404, "Endpoint not found")

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Concise logging
        sys.stderr.write(f"[GameStudio] {args[0]} -> {args[1]}\n")


def run_server():
    server_address = ("", PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, GameStudioHandler)
    print("=" * 65)
    print(f"  GAME MODULE STUDIO RUNNING ON LOCALHOST")
    print(f"  Open in your browser: http://localhost:{PORT}")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
