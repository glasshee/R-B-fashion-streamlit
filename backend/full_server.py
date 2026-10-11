from __future__ import annotations

import base64
import binascii
from contextlib import contextmanager
import hashlib
import json
import mimetypes
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qs, unquote, urlparse

import psycopg

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = Path(os.environ.get("RB_FULL_DB_PATH", DATA_DIR / "rb-fashion-full.sqlite3"))
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
UPLOAD_DIR = Path(os.environ.get("RB_UPLOAD_DIR", DATA_DIR / "uploads"))
ADMIN_EMAIL = os.environ.get("RB_ADMIN_EMAIL", "").strip().lower()
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
BUSINESS_PHONE = "0547042682"
WHATSAPP_PHONE = "0598585080"
MOBILE_MONEY_NUMBERS = (BUSINESS_PHONE, WHATSAPP_PHONE)
BUSINESS_EMAIL = "brownkwame123@gmail.com"
SESSION_DAYS = 14
MAX_BODY_SIZE = 1_000_000
MAX_IMAGE_SIZE = 700_000
ORDER_STATUSES = {
    "pending_payment", "paid", "processing", "packed", "shipped",
    "delivered", "cancelled", "refunded",
}

PRODUCTS = [
    ("baggy-blue-denim", "Baggy blue denim", "Denim", 320, 20),
    ("baggy-cargo-denim", "Baggy cargo denim", "Denim", 360, 20),
    ("oversized-graphic-tee", "Oversized graphic tee", "Streetwear", 240, 20),
    ("oversized-campus-fit", "Oversized campus fit", "Streetwear", 390, 20),
    ("asics-gel-street-runners", "ASICS GEL street runners", "Sneakers", 720, 20),
    ("platform-street-sneakers", "Platform street sneakers", "Sneakers", 590, 20),
    ("dr-martens-street-boots", "Dr. Martens street boots", "Boots", 780, 20),
    ("clean-white-low-tops", "Clean white low-tops", "Sneakers", 490, 20),
    ("oversized-varsity-hoodie", "Oversized varsity hoodie", "Layers", 410, 20),
    ("tailored-black-suit", "Tailored black suit", "Formal", 950, 20),
    ("satin-evening-dress", "Satin evening dress", "Formal", 820, 20),
    ("clean-cut-formal-shirt", "Clean cut formal shirt", "Formal", 360, 20),
]


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


class PostgresConnection:
    def __init__(self, connection: Any):
        self.connection = connection

    def execute(self, query: str, parameters: tuple = ()):
        statement = query.strip()
        if statement == "BEGIN IMMEDIATE":
            query = "BEGIN"
        elif statement.startswith("INSERT OR IGNORE INTO"):
            query = query.replace("INSERT OR IGNORE INTO", "INSERT INTO", 1).rstrip().rstrip(";")
            query += " ON CONFLICT DO NOTHING"
        return self.connection.execute(query.replace("?", "%s"), parameters)

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            if statement.strip():
                self.execute(statement)


@contextmanager
def connect_db() -> Iterator[Any]:
    if DATABASE_URL:
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(
            DATABASE_URL,
            connect_timeout=10,
            row_factory=dict_row,
        )
        try:
            with connection:
                yield PostgresConnection(connection)
        finally:
            connection.close()
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp() -> str:
    return utc_now().isoformat()


def sale_price(price: int) -> int:
    return ((price * 9 + 50) // 100) * 10


def hash_password(value: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt, 210_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(value: str, saved: str) -> bool:
    try:
        salt_hex, saved_digest = saved.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt, 210_000)
        return secrets.compare_digest(digest.hex(), saved_digest)
    except (ValueError, TypeError):
        return False


def initialize_db() -> None:
    if os.environ.get("RB_UPLOADS_AS_DATA_URI") != "1":
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with connect_db() as db:
        schema = """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer',
                google_sub TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                price INTEGER NOT NULL CHECK(price >= 0),
                image_url TEXT NOT NULL DEFAULT '',
                stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS carts (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                product_id TEXT NOT NULL REFERENCES products(id),
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                PRIMARY KEY(user_id, product_id)
            );
            CREATE TABLE IF NOT EXISTS wishlists (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                product_id TEXT NOT NULL REFERENCES products(id),
                PRIMARY KEY(user_id, product_id)
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                items_json TEXT NOT NULL,
                total INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_payment',
                shipping_name TEXT NOT NULL,
                shipping_phone TEXT NOT NULL,
                shipping_address TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS payments (
                order_id INTEGER PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                reference TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY,
                visitor_id TEXT NOT NULL,
                page TEXT NOT NULL,
                visited_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS forum_requests (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                feeling TEXT NOT NULL,
                request_type TEXT NOT NULL,
                message TEXT NOT NULL,
                contact TEXT NOT NULL,
                image_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        if DATABASE_URL:
            schema = schema.replace(
                "id INTEGER PRIMARY KEY,",
                "id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,",
            )
            db.executescript(schema)
            user_columns = {
                row["name"]
                for row in db.execute(
                    "SELECT column_name AS name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = 'users'"
                ).fetchall()
            }
            if "google_sub" not in user_columns:
                db.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
        else:
            db.executescript(schema)
            user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
            if "google_sub" not in user_columns:
                db.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS users_google_sub_idx "
            "ON users(google_sub) WHERE google_sub IS NOT NULL"
        )
        for product in PRODUCTS:
            db.execute(
                "INSERT OR IGNORE INTO products(id, name, category, price, stock) "
                "VALUES(?, ?, ?, ?, ?)",
                product,
            )


def daily_summary(date_text: str | None = None) -> dict:
    date_text = date_text or utc_now().strftime("%Y-%m-%d")
    visit_date = "CAST(visited_at AS DATE)" if DATABASE_URL else "date(visited_at)"
    order_date = "CAST(created_at AS DATE)" if DATABASE_URL else "date(created_at)"
    with connect_db() as db:
        today_visitors = db.execute(
            f"SELECT COUNT(DISTINCT visitor_id) AS total FROM visits WHERE {visit_date} = ?",
            (date_text,),
        ).fetchone()["total"]
        today_orders = db.execute(
            f"SELECT COUNT(*) AS total FROM orders WHERE {order_date} = ?", (date_text,)
        ).fetchone()["total"]
        today_people = db.execute(
            f"SELECT COUNT(DISTINCT user_id) AS total FROM orders WHERE {order_date} = ?",
            (date_text,),
        ).fetchone()["total"]
        today_accounts = db.execute(
            f"SELECT COUNT(*) AS total FROM users WHERE {order_date} = ?", (date_text,)
        ).fetchone()["total"]
        today_revenue = db.execute(
            f"SELECT COALESCE(SUM(total), 0) AS total FROM orders WHERE {order_date} = ?",
            (date_text,),
        ).fetchone()["total"]
        overall_visitors = db.execute(
            "SELECT COUNT(DISTINCT visitor_id) AS total FROM visits"
        ).fetchone()["total"]
        overall_orders = db.execute("SELECT COUNT(*) AS total FROM orders").fetchone()["total"]
        overall_accounts = db.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
        overall_revenue = db.execute(
            "SELECT COALESCE(SUM(total), 0) AS total FROM orders"
        ).fetchone()["total"]
    return {
        "date": date_text,
        "today": {
            "visitors": today_visitors,
            "orders": today_orders,
            "peopleOrdered": today_people,
            "newAccounts": today_accounts,
            "revenue": today_revenue,
        },
        "overall": {
            "visitors": overall_visitors,
            "orders": overall_orders,
            "accounts": overall_accounts,
            "revenue": overall_revenue,
        },
    }


def store_uploaded_image(folder: str, filename: str, content: bytes, content_type: str) -> str:
    if os.environ.get("RB_UPLOADS_AS_DATA_URI") == "1":
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / filename).write_bytes(content)
    return f"/uploads/{filename}"


class ApiHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        relative = Path(unquote(urlparse(path).path).lstrip("/"))
        if relative.parts and relative.parts[0] == "uploads":
            upload_root = UPLOAD_DIR.resolve()
            upload_path = (upload_root / Path(*relative.parts[1:])).resolve()
            if len(relative.parts) == 2 and upload_path.is_relative_to(upload_root):
                return str(upload_path)
            return str(ROOT / "__blocked_static_path__")
        resolved = (ROOT / relative).resolve()
        protected = {"backend", ".git", "New folder"}
        if (
            (relative.parts and relative.parts[0] in protected)
            or any(part in {".git", "__pycache__"} for part in relative.parts)
            or not resolved.is_relative_to(ROOT)
        ):
            return str(ROOT / "__blocked_static_path__")
        return str(resolved)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        origin = self.headers.get("Origin", "")
        if origin == "null" or origin.startswith(("http://localhost:", "http://127.0.0.1:")):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PUT(self):
        self.dispatch("PUT")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def send_json(self, status: int, payload: dict | list):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ApiError(400, "Invalid content length") from error
        if length > MAX_BODY_SIZE:
            raise ApiError(413, "Request is too large")
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ApiError(400, "Invalid JSON") from error
        if not isinstance(payload, dict):
            raise ApiError(400, "JSON must be an object")
        return payload

    def dispatch(self, method: str):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if not path.startswith("/api/") and path != "/api":
            if method == "GET":
                return super().do_GET()
            return self.send_error(405)
        try:
            payload = self.read_json() if method in {"POST", "PUT"} else {}
            self.route(method, path, payload)
        except ApiError as error:
            self.send_json(error.status, {"error": error.message})
        except (sqlite3.IntegrityError, psycopg.IntegrityError):
            self.send_json(409, {"error": "That record already exists"})
        except (ValueError, TypeError, OverflowError):
            self.send_json(400, {"error": "Invalid request values"})
        except Exception as error:
            print("API error:", error)
            self.send_json(500, {"error": "Unexpected server error"})

    def route(self, method: str, path: str, payload: dict):
        if method == "GET" and path == "/api/health":
            return self.send_json(200, {"ok": True, "service": "rb-fashion"})
        if method == "GET" and path == "/api/products":
            return self.products()
        if method == "GET" and path.startswith("/api/products/"):
            return self.one_product(unquote(path.rsplit("/", 1)[1]))
        if method == "GET" and path == "/api/business-contact":
            return self.send_json(200, {
                "email": BUSINESS_EMAIL,
                "phone": BUSINESS_PHONE,
                "whatsapp": WHATSAPP_PHONE,
                "payment": {
                    "method": "Mobile Money",
                    "number": BUSINESS_PHONE,
                    "numbers": list(MOBILE_MONEY_NUMBERS),
                    "status": "manual_confirmation",
                },
            })
        if method == "GET" and path == "/api/analytics/summary":
            return self.send_json(200, daily_summary())
        if method == "GET" and path == "/api/auth/google/config":
            return self.send_json(200, {"clientId": GOOGLE_CLIENT_ID})
        if method == "POST" and path in {"/api/accounts", "/api/auth/register"}:
            return self.register(payload)
        if method == "POST" and path == "/api/auth/login":
            return self.login(payload)
        if method == "POST" and path == "/api/auth/google":
            return self.google_login(payload)
        if method == "POST" and path == "/api/auth/logout":
            return self.logout()
        if method == "GET" and path == "/api/me":
            user = self.user()
            return self.send_json(200, {"user": self.public_user(user)})
        if method == "POST" and path == "/api/visits":
            return self.visit(payload)
        if method == "POST" and path == "/api/forum-requests":
            return self.forum_request(payload)
        if path == "/api/cart" and method == "GET":
            return self.send_json(200, self.cart_data(self.user()["id"]))
        if path == "/api/cart/items" and method == "POST":
            return self.add_cart(payload)
        if path.startswith("/api/cart/items/") and method in {"PUT", "DELETE"}:
            return self.change_cart(unquote(path.rsplit("/", 1)[1]), payload, method)
        if path == "/api/wishlist" and method == "GET":
            return self.wishlist()
        if path.startswith("/api/wishlist/") and method in {"POST", "DELETE"}:
            return self.change_wishlist(unquote(path.rsplit("/", 1)[1]), method)
        if path == "/api/orders" and method == "POST":
            return self.create_order(payload)
        if path == "/api/orders" and method == "GET":
            return self.orders()
        if path == "/api/payments/checkout" and method == "POST":
            return self.checkout(payload)
        if path.startswith("/api/admin/"):
            return self.admin(method, path, payload)
        raise ApiError(404, "Endpoint not found")

    @staticmethod
    def public_user(user: sqlite3.Row) -> dict:
        return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}

    def products(self):
        with connect_db() as db:
            rows = db.execute(
                "SELECT * FROM products WHERE active = 1 ORDER BY category, name"
            ).fetchall()
        products = []
        for row in rows:
            item = dict(row)
            item["active"] = bool(item["active"])
            item["discountPrice"] = sale_price(item["price"])
            products.append(item)
        self.send_json(200, {"products": products})

    def one_product(self, product_id: str):
        with connect_db() as db:
            row = db.execute(
                "SELECT * FROM products WHERE id = ? AND active = 1", (product_id,)
            ).fetchone()
        if not row:
            raise ApiError(404, "Product not found")
        item = dict(row)
        item["active"] = bool(item["active"])
        item["discountPrice"] = sale_price(item["price"])
        self.send_json(200, {"product": item})

    def new_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        expires = (utc_now() + timedelta(days=SESSION_DAYS)).isoformat()
        with connect_db() as db:
            db.execute("INSERT INTO sessions(token, user_id, expires_at) VALUES(?, ?, ?)", (token, user_id, expires))
        return token

    def register(self, payload: dict):
        name = str(payload.get("name", "")).strip()
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        if len(name) < 2 or "@" not in email or len(password) < 8:
            raise ApiError(400, "Use a name, valid email, and password of at least eight characters")
        role = "customer"
        with connect_db() as db:
            cursor = db.execute(
                "INSERT INTO users(name, email, password_hash, role) VALUES(?, ?, ?, ?) "
                "RETURNING id",
                (name, email, hash_password(password), role),
            )
            user_id = cursor.fetchone()["id"]
        token = self.new_session(user_id)
        self.send_json(201, {"token": token, "user": {"id": user_id, "name": name, "email": email, "role": role}})

    def login(self, payload: dict):
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        with connect_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            raise ApiError(401, "Email or password is incorrect")
        self.send_json(200, {"token": self.new_session(user["id"]), "user": self.public_user(user)})

    def verify_google_credential(self, credential: str) -> dict:
        try:
            from google.auth.exceptions import GoogleAuthError, TransportError
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.oauth2 import id_token as google_id_token

            claims = google_id_token.verify_oauth2_token(
                credential, GoogleAuthRequest(), GOOGLE_CLIENT_ID
            )
        except ImportError as error:
            raise ApiError(503, "Google sign-in is not installed on this server yet") from error
        except TransportError as error:
            raise ApiError(503, "Google sign-in is temporarily unavailable. Try email sign-in.") from error
        except (GoogleAuthError, ValueError) as error:
            raise ApiError(401, "Google could not verify this sign-in. Try again.") from error
        return claims

    def google_login(self, payload: dict):
        if not GOOGLE_CLIENT_ID:
            raise ApiError(503, "Google sign-in is not configured for this site yet")
        credential = payload.get("credential")
        nonce = payload.get("nonce")
        if not isinstance(credential, str) or not credential or len(credential) > 16_000:
            raise ApiError(400, "Google sign-in response is invalid. Please try again.")
        if not isinstance(nonce, str) or not nonce or len(nonce) > 200:
            raise ApiError(400, "Google sign-in expired. Please try again.")

        claims = self.verify_google_credential(credential)
        issuer = claims.get("iss")
        email = str(claims.get("email", "")).strip().lower()
        subject = str(claims.get("sub", "")).strip()
        try:
            expires_at = int(claims.get("exp", 0))
        except (TypeError, ValueError) as error:
            raise ApiError(401, "Google sign-in response is invalid") from error
        email_verified = str(claims.get("email_verified", "")).lower() == "true"
        if (
            claims.get("aud") != GOOGLE_CLIENT_ID
            or issuer not in {"accounts.google.com", "https://accounts.google.com"}
            or expires_at <= int(time.time())
            or not secrets.compare_digest(str(claims.get("nonce", "")), nonce)
            or not email_verified
            or not subject
            or "@" not in email
        ):
            raise ApiError(401, "Google sign-in could not verify this account. Please try again.")

        return self.google_login_verified_claims(claims)

    def google_login_from_oidc(self, claims: dict):
        verified = claims.get("email_verified", False)
        email_verified = verified is True or str(verified).lower() == "true"
        issuer = claims.get("iss")
        if (
            not email_verified
            or (issuer and issuer not in {"accounts.google.com", "https://accounts.google.com"})
        ):
            raise ApiError(401, "Google sign-in could not verify this account. Please try again.")
        return self.google_login_verified_claims(claims)

    def google_login_verified_claims(self, claims: dict):
        email = str(claims.get("email", "")).strip().lower()
        subject = str(claims.get("sub", "")).strip()
        if not subject or "@" not in email:
            raise ApiError(401, "Google sign-in could not verify this account. Please try again.")
        name = str(claims.get("name", "")).strip()[:200] or email.split("@", 1)[0]
        role = "admin" if ADMIN_EMAIL and email == ADMIN_EMAIL else "customer"
        with connect_db() as db:
            user = db.execute("SELECT * FROM users WHERE google_sub = ?", (subject,)).fetchone()
            status = 200
            if user and ADMIN_EMAIL and email == ADMIN_EMAIL and user["role"] != "admin":
                db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user["id"],))
                user = db.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
            if not user:
                user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                if user:
                    if user["google_sub"] and user["google_sub"] != subject:
                        raise ApiError(409, "This email is already linked to another Google account")
                    raise ApiError(
                        409,
                        "This email already has an account. Sign in with that account instead.",
                    )
                else:
                    cursor = db.execute(
                        "INSERT INTO users(name, email, password_hash, role, google_sub) "
                        "VALUES(?, ?, ?, ?, ?) RETURNING id",
                        (name, email, hash_password(secrets.token_urlsafe(48)), role, subject),
                    )
                    user_id = cursor.fetchone()["id"]
                    status = 201
                user = db.execute(
                    "SELECT * FROM users WHERE id = ?", (user_id if status == 201 else user["id"],)
                ).fetchone()

        token = self.new_session(user["id"])
        self.send_json(status, {"token": token, "user": self.public_user(user)})

    def logout(self):
        token = self.bearer_token()
        if token:
            with connect_db() as db:
                db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self.send_json(200, {"ok": True})

    def bearer_token(self) -> str:
        header = self.headers.get("Authorization", "")
        return header[7:].strip() if header.startswith("Bearer ") else ""

    def user(self, admin: bool = False) -> sqlite3.Row:
        with connect_db() as db:
            user = db.execute(
                """SELECT users.* FROM users JOIN sessions ON users.id = sessions.user_id
                   WHERE sessions.token = ? AND sessions.expires_at > ?""",
                (self.bearer_token(), timestamp()),
            ).fetchone()
        if not user:
            raise ApiError(401, "Sign in is required")
        if admin and user["role"] != "admin":
            raise ApiError(403, "Administrator access is required")
        return user

    def visit(self, payload: dict):
        visitor_id = str(payload.get("visitorId", "")).strip()
        page = str(payload.get("page", "/")).strip()[:200] or "/"
        if not visitor_id:
            raise ApiError(400, "visitorId is required")
        with connect_db() as db:
            db.execute("INSERT INTO visits(visitor_id, page) VALUES(?, ?)", (visitor_id[:128], page))
        self.send_json(201, {"ok": True})

    def forum_request(self, payload: dict):
        user = self.user()
        feeling = str(payload.get("feeling", "")).strip()
        request_type = str(payload.get("type", "")).strip()
        message = str(payload.get("message", "")).strip()
        contact = str(payload.get("contact", user["email"])).strip()
        image_path = None
        image_data = payload.get("imageData", "")
        if not feeling or not request_type or not message or not contact:
            raise ApiError(400, "Feeling, request type, message, and contact are required")
        if image_data:
            if not isinstance(image_data, str) or "," not in image_data:
                raise ApiError(400, "Invalid image data")
            header, encoded = image_data.split(",", 1)
            content_type = header.partition(";")[0].removeprefix("data:")
            extension = mimetypes.guess_extension(content_type)
            if content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"} or not extension:
                raise ApiError(400, "Only JPEG, PNG, WebP, and GIF images are supported")
            if len(encoded) > MAX_IMAGE_SIZE * 4 // 3 + 8:
                raise ApiError(413, "Image is too large")
            try:
                image_bytes = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as error:
                raise ApiError(400, "Invalid image data") from error
            if len(image_bytes) > MAX_IMAGE_SIZE:
                raise ApiError(413, "Image is too large")
            filename = f"request-{secrets.token_hex(12)}{extension}"
            image_path = store_uploaded_image(
                "forum", filename, image_bytes, content_type
            )
        with connect_db() as db:
            cursor = db.execute(
                """INSERT INTO forum_requests(user_id, feeling, request_type, message, contact, image_path)
                   VALUES(?, ?, ?, ?, ?, ?) RETURNING id""",
                (user["id"], feeling[:100], request_type[:100], message[:5000], contact[:300], image_path),
            )
            request_id = cursor.fetchone()["id"]
            self.send_json(201, {"requestId": request_id, "status": "received", "imagePath": image_path})

    def cart_data(self, user_id: int) -> dict:
        with connect_db() as db:
            rows = db.execute(
                """SELECT carts.product_id, carts.quantity, products.name, products.price,
                          products.stock, products.image_url
                   FROM carts JOIN products ON carts.product_id = products.id
                   WHERE carts.user_id = ? ORDER BY products.name""",
                (user_id,),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["unitPrice"] = sale_price(item["price"])
            item["lineTotal"] = item["unitPrice"] * item["quantity"]
            items.append(item)
        return {"items": items, "total": sum(item["lineTotal"] for item in items)}

    def add_cart(self, payload: dict):
        user = self.user()
        product_id = str(payload.get("productId", "")).strip()
        try:
            quantity = int(payload.get("quantity", 1))
        except (ValueError, TypeError) as error:
            raise ApiError(400, "Quantity must be a positive integer") from error
        if not 1 <= quantity <= 99:
            raise ApiError(400, "Quantity must be between 1 and 99")
        with connect_db() as db:
            db.execute("BEGIN IMMEDIATE")
            product = db.execute(
                "SELECT stock FROM products WHERE id = ? AND active = 1"
                + (" FOR UPDATE" if DATABASE_URL else ""),
                (product_id,),
            ).fetchone()
            if not product:
                raise ApiError(404, "Product not found")
            existing = db.execute(
                "SELECT quantity FROM carts WHERE user_id = ? AND product_id = ?",
                (user["id"], product_id),
            ).fetchone()
            total_quantity = quantity + (existing["quantity"] if existing else 0)
            if total_quantity > product["stock"]:
                raise ApiError(400, "Requested quantity is unavailable")
            db.execute(
                """INSERT INTO carts(user_id, product_id, quantity) VALUES(?, ?, ?)
                   ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = excluded.quantity""",
                (user["id"], product_id, total_quantity),
            )
        self.send_json(200, self.cart_data(user["id"]))

    def change_cart(self, product_id: str, payload: dict, method: str):
        user = self.user()
        with connect_db() as db:
            if method == "DELETE":
                db.execute("DELETE FROM carts WHERE user_id = ? AND product_id = ?", (user["id"], product_id))
            else:
                try:
                    quantity = int(payload.get("quantity", 0))
                except (ValueError, TypeError) as error:
                    raise ApiError(400, "Quantity must be a positive integer") from error
                if quantity <= 0:
                    db.execute("DELETE FROM carts WHERE user_id = ? AND product_id = ?", (user["id"], product_id))
                else:
                    product = db.execute(
                        "SELECT stock FROM products WHERE id = ? AND active = 1", (product_id,)
                    ).fetchone()
                    if not product or quantity > product["stock"] or quantity > 99:
                        raise ApiError(400, "Requested quantity is unavailable")
                    db.execute(
                        "UPDATE carts SET quantity = ? WHERE user_id = ? AND product_id = ?",
                        (quantity, user["id"], product_id),
                    )
        self.send_json(200, self.cart_data(user["id"]))

    def wishlist(self):
        user = self.user()
        with connect_db() as db:
            rows = db.execute(
                """SELECT products.* FROM wishlists JOIN products ON products.id = wishlists.product_id
                   WHERE wishlists.user_id = ? ORDER BY products.name""",
                (user["id"],),
            ).fetchall()
        self.send_json(200, {"products": [dict(row) for row in rows]})

    def change_wishlist(self, product_id: str, method: str):
        user = self.user()
        with connect_db() as db:
            if method == "POST":
                product = db.execute(
                    "SELECT id FROM products WHERE id = ? AND active = 1", (product_id,)
                ).fetchone()
                if not product:
                    raise ApiError(404, "Product not found")
                db.execute(
                    "INSERT OR IGNORE INTO wishlists(user_id, product_id) VALUES(?, ?)",
                    (user["id"], product_id),
                )
            else:
                db.execute(
                    "DELETE FROM wishlists WHERE user_id = ? AND product_id = ?",
                    (user["id"], product_id),
                )
        self.wishlist()

    def create_order(self, payload: dict):
        user = self.user()
        shipping = payload.get("shipping", {})
        if not isinstance(shipping, dict):
            raise ApiError(400, "Shipping details are required")
        name = str(shipping.get("name", user["name"])).strip()[:200]
        phone = str(shipping.get("phone", "")).strip()[:50]
        address = str(shipping.get("address", "")).strip()[:500]
        if not name or not phone or not address:
            raise ApiError(400, "Shipping name, phone, and address are required")
        with connect_db() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                """SELECT carts.product_id, carts.quantity, products.name, products.price, products.stock
                   FROM carts JOIN products ON products.id = carts.product_id
                   WHERE carts.user_id = ? AND products.active = 1"""
                + (" FOR UPDATE OF carts, products" if DATABASE_URL else ""),
                (user["id"],),
            ).fetchall()
            if not rows:
                raise ApiError(400, "Your bag is empty")
            if any(row["quantity"] > row["stock"] for row in rows):
                raise ApiError(409, "Your bag contains unavailable stock")
            items = [
                {
                    "id": row["product_id"],
                    "name": row["name"],
                    "unitPrice": sale_price(row["price"]),
                    "quantity": row["quantity"],
                }
                for row in rows
            ]
            total = sum(item["unitPrice"] * item["quantity"] for item in items)
            cursor = db.execute(
                """INSERT INTO orders(user_id, items_json, total, shipping_name, shipping_phone,
                                      shipping_address, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?) RETURNING id""",
                (user["id"], json.dumps(items), total, name, phone, address, timestamp()),
            )
            db.execute("DELETE FROM carts WHERE user_id = ?", (user["id"],))
            order_id = cursor.fetchone()["id"]
        self.send_json(201, {"order": {"id": order_id, "total": total, "status": "pending_payment"}})

    def orders(self):
        user = self.user()
        with connect_db() as db:
            rows = db.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user["id"],)
            ).fetchall()
        orders = [{**dict(row), "items": json.loads(row["items_json"])} for row in rows]
        self.send_json(200, {"orders": orders})

    def checkout(self, payload: dict):
        user = self.user()
        try:
            order_id = int(payload.get("orderId", 0))
        except (TypeError, ValueError) as error:
            raise ApiError(400, "A valid order ID is required") from error
        with connect_db() as db:
            order = db.execute(
                "SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user["id"])
            ).fetchone()
            if not order:
                raise ApiError(404, "Order not found")
            if order["status"] != "pending_payment":
                raise ApiError(409, "This order is not awaiting payment")
            reference = db.execute(
                "SELECT reference FROM payments WHERE order_id = ?", (order_id,)
            ).fetchone()
            if reference:
                reference = reference["reference"]
            else:
                reference = f"RB-{order_id}-{secrets.token_hex(4).upper()}"
                db.execute(
                    "INSERT INTO payments(order_id, provider, reference) VALUES(?, ?, ?)",
                    (order_id, "manual_momo", reference),
                )
        self.send_json(200, {
            "reference": reference,
            "instructions": (
                f"Send GH₵ {order['total']} to either Mobile Money number "
                f"{' or '.join(MOBILE_MONEY_NUMBERS)}, then contact "
                f"{BUSINESS_EMAIL} with this reference."
            ),
        })

    def admin(self, method: str, path: str, payload: dict):
        self.user(admin=True)
        if method == "POST" and path == "/api/admin/uploads":
            return self.upload_product_image(payload)
        if method == "GET" and path == "/api/admin/products":
            with connect_db() as db:
                rows = db.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()
            return self.send_json(200, {"products": [dict(row) for row in rows]})
        if method == "POST" and path == "/api/admin/products":
            return self.save_product(None, payload)
        if method == "PUT" and path.startswith("/api/admin/products/"):
            return self.save_product(unquote(path.rsplit("/", 1)[1]), payload)
        if method == "DELETE" and path.startswith("/api/admin/products/"):
            product_id = unquote(path.rsplit("/", 1)[1])
            with connect_db() as db:
                cursor = db.execute(
                    "UPDATE products SET active = 0, updated_at = ? WHERE id = ?",
                    (timestamp(), product_id),
                )
            if not cursor.rowcount:
                raise ApiError(404, "Product not found")
            return self.send_json(200, {"ok": True})
        if method == "GET" and path == "/api/admin/orders":
            with connect_db() as db:
                rows = db.execute(
                    """SELECT orders.*, users.name AS customer_name, users.email AS customer_email,
                              payments.reference AS payment_reference, payments.status AS payment_status
                       FROM orders JOIN users ON users.id = orders.user_id
                       LEFT JOIN payments ON payments.order_id = orders.id
                       ORDER BY orders.id DESC"""
                ).fetchall()
            orders = [{**dict(row), "items": json.loads(row["items_json"])} for row in rows]
            return self.send_json(200, {"orders": orders})
        if method == "PUT" and path.startswith("/api/admin/orders/") and path.endswith("/status"):
            return self.update_order_status(path, payload)
        raise ApiError(404, "Admin endpoint not found")

    def upload_product_image(self, payload: dict):
        image_data = payload.get("imageData")
        if not isinstance(image_data, str) or "," not in image_data:
            raise ApiError(400, "Choose a valid image to upload")
        header, encoded = image_data.split(",", 1)
        image_types = {
            "data:image/jpeg;base64": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
            "data:image/png;base64": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
            "data:image/webp;base64": (".webp", lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP"),
            "data:image/gif;base64": (".gif", lambda data: data.startswith((b"GIF87a", b"GIF89a"))),
        }
        image_type = image_types.get(header)
        if not image_type:
            raise ApiError(400, "Only JPEG, PNG, WebP, and GIF images are supported")
        if len(encoded) > MAX_IMAGE_SIZE * 4 // 3 + 8:
            raise ApiError(413, "Image is too large")
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ApiError(400, "Invalid image data") from error
        extension, is_valid_image = image_type
        if len(image_bytes) > MAX_IMAGE_SIZE:
            raise ApiError(413, "Image is too large")
        if not image_bytes or not is_valid_image(image_bytes):
            raise ApiError(400, "The selected file is not a valid image")
        filename = f"product-{secrets.token_hex(12)}{extension}"
        image_url = store_uploaded_image(
            "products",
            filename,
            image_bytes,
            header.partition(";")[0].removeprefix("data:"),
        )
        self.send_json(201, {"imageUrl": image_url})

    def update_order_status(self, path: str, payload: dict):
        parts = path.strip("/").split("/")
        try:
            order_id = int(parts[-2])
        except (IndexError, ValueError) as error:
            raise ApiError(400, "A valid order ID is required") from error
        status = str(payload.get("status", "")).strip()
        if status not in ORDER_STATUSES:
            raise ApiError(400, "Invalid order status")
        with connect_db() as db:
            db.execute("BEGIN IMMEDIATE")
            order = db.execute(
                "SELECT * FROM orders WHERE id = ?" + (" FOR UPDATE" if DATABASE_URL else ""),
                (order_id,),
            ).fetchone()
            if not order:
                raise ApiError(404, "Order not found")
            payment = db.execute(
                "SELECT status FROM payments WHERE order_id = ?", (order_id,)
            ).fetchone()
            inventory_already_deducted = payment and payment["status"] == "paid"
            if status == "paid" and not inventory_already_deducted:
                items = json.loads(order["items_json"])
                for item in items:
                    stock = db.execute(
                        "SELECT stock FROM products WHERE id = ?"
                        + (" FOR UPDATE" if DATABASE_URL else ""),
                        (item["id"],),
                    ).fetchone()
                    if not stock or stock["stock"] < item["quantity"]:
                        raise ApiError(409, f"Insufficient stock for {item['name']}")
                for item in items:
                    db.execute(
                        "UPDATE products SET stock = stock - ?, updated_at = ? WHERE id = ?",
                        (item["quantity"], timestamp(), item["id"]),
                    )
                db.execute(
                    """INSERT INTO payments(order_id, provider, reference, status)
                       VALUES(?, 'admin_manual', ?, 'paid')
                       ON CONFLICT(order_id) DO UPDATE SET status = 'paid'""",
                    (order_id, f"ADMIN-{order_id}"),
                )
            db.execute(
                "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                (status, timestamp(), order_id),
            )
        self.send_json(200, {"ok": True})

    def save_product(self, product_id: str | None, payload: dict):
        name = str(payload.get("name", "")).strip()
        category = str(payload.get("category", "")).strip()
        try:
            price = int(payload.get("price", -1))
            stock = int(payload.get("stock", -1))
        except (ValueError, TypeError) as error:
            raise ApiError(400, "Price and stock must be integers") from error
        if not name or not category or price < 0 or stock < 0:
            raise ApiError(400, "Name, category, and non-negative price/stock are required")
        is_create = product_id is None
        if is_create:
            product_id = str(payload.get("id", "")).strip().lower()
            if not product_id or not product_id.replace("-", "").isalnum():
                raise ApiError(400, "Use a product ID with letters, numbers, and hyphens")
        values = (
            name[:200], category[:100], str(payload.get("description", "")).strip()[:2000],
            price, str(payload.get("imageUrl", "")).strip()[:1000], stock,
            1 if payload.get("active", True) else 0, timestamp(),
        )
        with connect_db() as db:
            existing = db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
            if is_create:
                if existing:
                    raise ApiError(409, "A product with that ID already exists")
                db.execute(
                    """INSERT INTO products(id, name, category, description, price, image_url,
                       stock, active, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (product_id, *values),
                )
                status = 201
            elif existing:
                db.execute(
                    """UPDATE products SET name = ?, category = ?, description = ?, price = ?,
                       image_url = ?, stock = ?, active = ?, updated_at = ? WHERE id = ?""",
                    (*values, product_id),
                )
            else:
                raise ApiError(404, "Product not found")
            if not is_create:
                status = 200
            row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        item = dict(row)
        item["active"] = bool(item["active"])
        self.send_json(status, {"product": item})


def main():
    initialize_db()
    host = os.environ.get("RB_HOST", "127.0.0.1")
    port = int(os.environ.get("RB_PORT") or os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"R&B Fashion full backend running at http://{server.server_address[0]}:{server.server_address[1]}")
    print("Storefront: http://127.0.0.1:8000/index.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()