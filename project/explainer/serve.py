#!/usr/bin/env python
"""Serves the architecture explainer on http://localhost:8080.

Stdlib only — no npm install, no build step, nothing to add to requirements.txt.
The site is plain HTML/CSS/JS, so `python explainer/serve.py` from the project
root is the whole setup.

    python explainer/serve.py            # http://localhost:8080
    python explainer/serve.py 9000       # a different port

Opening index.html directly with file:// also works (the scripts are classic
scripts, not ES modules), but a real origin is closer to how it deploys.
"""
import http.server
import socketserver
import sys
import webbrowser
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Explainer assets change every time someone edits them during a demo
        # rehearsal; a cached stale copy is more confusing than a re-fetch.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    handler = partial(Handler, directory=str(ROOT))

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        url = f"http://localhost:{port}/"
        print(f"TenderGuard architecture explainer -> {url}")
        print("Ctrl+C to stop.\n")
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001 - a headless box just skips the browser
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
