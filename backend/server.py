from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import secrets
import smtplib
import sqlite3
import threading
import time
from datetime import datetime
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "rb-fashion.sqlite3"
HOST = "127.0.0.1"
PORT = 8000
BUSINESS_EMAIL = "brownkwame123@gmail.com"
BUSINESS_PHONE = "0547042682"
WHATSAPP_PHONE = "0598585080"
MOBILE_MONEY_NUMBERS = (BUSINESS_PHONE, WHATSAPP_PHONE)
SUMMARY_HOUR = 22

PRODUCTS = [
    ("baggy-blue-denim", "Baggy blue denim", "Denim", 320),
    ("baggy-cargo-denim", "Baggy cargo denim", "Denim", 360),
    ("oversized-graphic-tee", "Oversized graphic tee", "Streetwear", 240),
    ("oversized-campus-fit", "Oversized campus fit", "Streetwear", 390),
    ("asics-gel-street-runners", "ASICS GEL street runners", "Sneakers", 720),
    ("platform-street-sneakers", "Platform street sneakers", "Sneakers", 590),
    ("dr-martens-street-boots", "Dr. Martens street boots", "Boots", 780),
    ("clean-white-low-tops", "Clean white low-tops", "Sneakers", 490),
    ("oversized-varsity-hoodie", "Oversized varsity hoodie", "Layers", 410),
    ("tailored-black-suit", "Tailored black suit", "Formal", 950),
    ("satin-evening-dress", "Satin evening dress", "Formal", 820),
    ("clean-cut-formal-shirt", "Clean cut formal shirt", "Formal", 360),
]


def connect_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                items_json TEXT NOT NULL,
                total INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_payment',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS forum_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                feeling TEXT NOT NULL,
                request_type TEXT NOT NULL,
                message TEXT NOT NULL,
                contact TEXT NOT NULL,
                image_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id TEXT NOT NULL,
                page TEXT NOT NULL,
                visited_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        db.executemany(
            "INSERT OR IGNORE INTO products (id, name, category, price) VALUES (?, ?, ?, ?)",
            PRODUCTS,
        )


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 120_000)
    return secrets.compare_digest(digest.hex(), digest_hex)


def sale_price(price: int) -> int:
    return ((price * 9 + 50) // 100) * 10


def daily_summary(date_text: str | None = None) -> dict:
    date_text = date_text or datetime.now().strftime("%Y-%m-%d")
    with connect_db() as db:
        today_visitors = db.execute("SELECT COUNT(DISTINCT visitor_id) FROM visits WHERE date(visited_at) = ?", (date_text,)).fetchone()[0]
        today_orders = db.execute("SELECT COUNT(*) FROM orders WHERE date(created_at) = ?", (date_text,)).fetchone()[0]
        today_ordered_people = db.execute("SELECT COUNT(DISTINCT user_id) FROM orders WHERE date(created_at) = ?", (date_text,)).fetchone()[0]
        today_new_users = db.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = ?", (date_text,)).fetchone()[0]
        today_revenue = db.execute("SELECT COALESCE(SUM(total), 0) FROM orders WHERE date(created_at) = ?", (date_text,)).fetchone()[0]
        overall_visitors = db.execute("SELECT COUNT(DISTINCT visitor_id) FROM visits").fetchone()[0]
        overall_orders = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        overall_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        overall_revenue = db.execute("SELECT COALESCE(SUM(total), 0) FROM orders").fetchone()[0]
    return {
        "date": date_text,
        "today": {"visitors": today_visitors, "orders": today_orders, "peopleOrdered": today_ordered_people, "newAccounts": today_new_users, "revenue": today_revenue},
        "overall": {"visitors": overall_visitors, "orders": overall_orders, "accounts": overall_users, "revenue": overall_revenue},
    }


def summary_text(summary: dict) -> str:
    today = summary["today"]
    overall = summary["overall"]
    return (
        f"R&B Fashion daily summary - {summary['date']}\n\n"
        f"Today\n- Visitors: {today['visitors']}\n- People who ordered: {today['peopleOrdered']}\n"
        f"- Orders: {today['orders']}\n- New accounts: {today['newAccounts']}\n- Revenue recorded: GH₵ {today['revenue']}\n\n"
        f"Overall\n- Unique visitors: {overall['visitors']}\n- Orders: {overall['orders']}\n"
        f"- Accounts: {overall['accounts']}\n- Revenue recorded: GH₵ {overall['revenue']}\n"
    )


def send_daily_summary() -> bool:
    smtp_host = os.environ.get("RB_SMTP_HOST")
    smtp_user = os.environ.get("RB_SMTP_USER")
    smtp_password = os.environ.get("RB_SMTP_PASSWORD")
    if not all((smtp_host, smtp_user, smtp_password)):
        print("Daily summary ready but email is not configured. Set RB_SMTP_HOST, RB_SMTP_USER, and RB_SMTP_PASSWORD.")
        print(summary_text(daily_summary()))
        return False
    message = EmailMessage()
    message["Subject"] = f"R&B Fashion daily summary - {datetime.now():%Y-%m-%d}"
    message["From"] = smtp_user
    message["To"] = BUSINESS_EMAIL
    message.set_content(summary_text(daily_summary()))
    with smtplib.SMTP(smtp_host, int(os.environ.get("RB_SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)
    print(f"Daily summary emailed to {BUSINESS_EMAIL}.")
    return True


def summary_scheduler() -> None:
    last_sent_date = None
    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if now.hour == SUMMARY_HOUR and now.minute == 0 and last_sent_date != today:
            try:
                send_daily_summary()
            except Exception as error:
                print(f"Daily summary email failed: {error}")
            last_sent_date = today
        time.sleep(30)


class ApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self.handle_api_get(path)
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self.handle_api_post(path)
            return
        self.send_error(404)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 5_000_000:
            raise ValueError("Request is too large")
        raw = self.rfile.read(length)
        return json.loads(raw or b"{}")

    def send_json(self, status: int, payload: dict | list):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_api_get(self, path: str):
        if path == "/api/health":
            self.send_json(200, {"ok": True, "service": "rb-fashion"})
            return
        if path == "/api/products":
            with connect_db() as db:
                rows = db.execute("SELECT id, name, category, price FROM products WHERE active = 1 ORDER BY name").fetchall()
            self.send_json(200, [{**dict(row), "discountPrice": sale_price(row["price"])} for row in rows])
            return
        if path == "/api/business-contact":
            self.send_json(200, {
                "email": BUSINESS_EMAIL,
                "phone": BUSINESS_PHONE,
                "whatsapp": WHATSAPP_PHONE,
                "payment": {
                    "method": "Mobile Money",
                    "number": BUSINESS_PHONE,
                    "numbers": list(MOBILE_MONEY_NUMBERS),
                    "status": "manual_confirmation"
                }
            })
            return
        if path == "/api/analytics/summary":
            self.send_json(200, daily_summary())
            return
        if path == "/api/me":
            user = self.authenticated_user()
            if not user:
                self.send_json(401, {"error": "Authentication required"})
                return
            self.send_json(200, {"id": user["id"], "name": user["name"], "email": user["email"]})
            return
        self.send_json(404, {"error": "Endpoint not found"})

    def handle_api_post(self, path: str):
        try:
            payload = self.read_json()
            if path == "/api/accounts":
                self.create_account(payload)
            elif path == "/api/visits":
                self.record_visit(payload)
            elif path == "/api/orders":
                self.create_order(payload)
            elif path == "/api/forum-requests":
                self.create_forum_request(payload)
            elif path == "/api/payments/checkout":
                self.send_json(501, {"error": "Payment provider is not configured", "status": "pending_payment"})
            else:
                self.send_json(404, {"error": "Endpoint not found"})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error)})
        except sqlite3.IntegrityError:
            self.send_json(409, {"error": "An account with that email already exists"})

    def create_account(self, payload: dict):
        name = str(payload.get("name", "")).strip()
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        if not name or not email or len(password) < 6:
            raise ValueError("Name, email, and a password of at least six characters are required")
        with connect_db() as db:
            cursor = db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, hash_password(password)),
            )
            user_id = cursor.lastrowid
            token = secrets.token_urlsafe(32)
            db.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
        self.send_json(201, {"token": token, "user": {"id": user_id, "name": name, "email": email}})

    def record_visit(self, payload: dict):
        visitor_id = str(payload.get("visitorId", "")).strip()
        page = str(payload.get("page", "")).strip() or "/"
        if not visitor_id:
            raise ValueError("visitorId is required")
        with connect_db() as db:
            db.execute("INSERT INTO visits (visitor_id, page) VALUES (?, ?)", (visitor_id, page[:200]))
        self.send_json(201, {"status": "recorded"})

    def create_order(self, payload: dict):
        user = self.authenticated_user()
        if not user:
            self.send_json(401, {"error": "Authentication required"})
            return
        requested_items = payload.get("items", [])
        if not requested_items:
            raise ValueError("At least one item is required")
        ids = [str(item.get("id", "")) for item in requested_items]
        placeholders = ",".join("?" for _ in ids)
        with connect_db() as db:
            products = db.execute(f"SELECT id, name, price FROM products WHERE id IN ({placeholders}) AND active = 1", ids).fetchall()
        product_map = {row["id"]: row for row in products}
        items = []
        total = 0
        for item in requested_items:
            product = product_map.get(str(item.get("id", "")))
            quantity = max(1, int(item.get("quantity", 1)))
            if not product:
                raise ValueError("One or more products are unavailable")
            unit_price = sale_price(product["price"])
            items.append({"id": product["id"], "name": product["name"], "quantity": quantity, "unitPrice": unit_price})
            total += unit_price * quantity
        with connect_db() as db:
            cursor = db.execute(
                "INSERT INTO orders (user_id, items_json, total) VALUES (?, ?, ?)",
                (user["id"], json.dumps(items), total),
            )
            order_id = cursor.lastrowid
        self.send_json(201, {
            "orderId": order_id,
            "total": total,
            "status": "pending_payment",
            "items": items,
            "notification": {"email": BUSINESS_EMAIL, "phone": BUSINESS_PHONE},
            "payment": {
                "method": "Mobile Money",
                "number": BUSINESS_PHONE,
                "numbers": list(MOBILE_MONEY_NUMBERS),
                "status": "manual_confirmation"
            }
        })

    def create_forum_request(self, payload: dict):
        user = self.authenticated_user()
        if not user:
            self.send_json(401, {"error": "Authentication required"})
            return
        feeling = str(payload.get("feeling", "")).strip()
        request_type = str(payload.get("type", "")).strip()
        message = str(payload.get("message", "")).strip()
        contact = str(payload.get("contact", user["email"])).strip()
        image_path = None
        image_data = payload.get("imageData")
        if image_data and "," in image_data:
            header, encoded = image_data.split(",", 1)
            extension = mimetypes.guess_extension(header.split(";", 1)[0].split(":", 1)[-1]) or ".bin"
            image_path = UPLOAD_DIR / f"request-{int(time.time())}-{secrets.token_hex(4)}{extension}"
            image_path.write_bytes(base64.b64decode(encoded))
            image_path = str(image_path.relative_to(ROOT))
        if not feeling or not request_type or not message:
            raise ValueError("Feeling, request type, and message are required")
        with connect_db() as db:
            cursor = db.execute(
                "INSERT INTO forum_requests (user_id, feeling, request_type, message, contact, image_path) VALUES (?, ?, ?, ?, ?, ?)",
                (user["id"], feeling, request_type, message, contact, image_path),
            )
            request_id = cursor.lastrowid
        self.send_json(201, {
            "requestId": request_id,
            "status": "received",
            "imagePath": image_path,
            "notification": {"email": BUSINESS_EMAIL, "phone": BUSINESS_PHONE}
        })

    def authenticated_user(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        token = header.removeprefix("Bearer ").strip()
        with connect_db() as db:
            return db.execute(
                "SELECT users.id, users.name, users.email FROM users JOIN sessions ON sessions.user_id = users.id WHERE sessions.token = ?",
                (token,),
            ).fetchone()


if __name__ == "__main__":
    initialize_db()
    threading.Thread(target=summary_scheduler, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), ApiHandler)
    print(f"R&B Fashion backend running at http://{HOST}:{PORT}")
    print("Static site: http://127.0.0.1:8000/index.html")
    server.serve_forever()
