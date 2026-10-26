"""Local server for the company site and the message book.

Run from the NovaInsight folder:

    py cloud/functions/server.py
"""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "web" / "company-website"
PLATFORM = ROOT / "web" / "platform"
DATABASE = ROOT / "cloud" / "database" / "messages.sqlite"
HOST = "127.0.0.1"
PORT = 8765
MAX_BODY = 20_000

LIMITS = {
    "name": 120,
    "organization": 160,
    "email": 200,
    "message": 4000,
}


def connect():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          organization TEXT,
          email TEXT NOT NULL,
          message TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def clean(value, limit):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit] if limit != LIMITS["message"] else value.strip()[:limit]


def message_from_body(raw):
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "Send the note as JSON."
    if not isinstance(payload, dict):
        return None, "Send the note as JSON."

    name = clean(payload.get("name", ""), LIMITS["name"])
    organization = clean(payload.get("organization", ""), LIMITS["organization"])
    email = clean(payload.get("email", ""), LIMITS["email"])
    message = clean(payload.get("message", ""), LIMITS["message"])

    if not name or not email or not message:
        return None, "Name, email, and a note are required."
    if "@" not in email or "." not in email.split("@")[-1]:
        return None, "Enter an email address."
    return {
        "name": name,
        "organization": organization or None,
        "email": email,
        "message": message,
    }, None


def inside(root, candidate):
    root = root.resolve()
    candidate = candidate.resolve()
    return candidate == root or root in candidate.parents


def static_file(root, url_path):
    relative = unquote(url_path).lstrip("/")
    if relative.endswith("/"):
        relative += "index.html"
    if not relative:
        relative = "index.html"
    candidate = (root / relative).resolve()
    if not inside(root, candidate) or not candidate.is_file():
        return None
    return candidate


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/messages":
            self.list_messages()
            return
        if path == "/platform" or path.startswith("/platform/"):
            self.serve(PLATFORM, path.removeprefix("/platform"))
            return
        self.serve(SITE, path)

    def do_POST(self):
        if urlparse(self.path).path != "/api/messages":
            self.send_error(404)
            return
        self.create_message()

    def serve(self, root, url_path):
        target = static_file(root, url_path)
        if target is None:
            missing = SITE / "404.html"
            self.send_file(missing, 404)
            return
        self.send_file(target, 200)

    def send_file(self, target, status):
        content = target.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", self.guess_type(str(target)))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def list_messages(self):
        with closing(connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, name, organization, email, message, created_at
                FROM messages
                ORDER BY id DESC
                """
            ).fetchall()
        messages = [dict(row) for row in rows]
        self.send_json(200, {"messages": messages})

    def create_message(self):
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            self.send_json(400, {"error": "Send the note as JSON."})
            return
        if length < 0 or length > MAX_BODY:
            self.send_json(413, {"error": "That note is too long."})
            return
        note, error = message_from_body(self.rfile.read(length))
        if error:
            self.send_json(400, {"error": error})
            return
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(connect()) as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages (name, organization, email, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (note["name"], note["organization"], note["email"], note["message"], created_at),
            )
            connection.commit()
            message_id = cursor.lastrowid
        self.send_json(201, {"id": message_id})

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    connect().close()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Company site  http://{HOST}:{PORT}/")
    print(f"Messages      http://{HOST}:{PORT}/platform/")
    server.serve_forever()


if __name__ == "__main__":
    main()
