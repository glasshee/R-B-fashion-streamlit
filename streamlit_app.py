from __future__ import annotations

import base64
import os
import sqlite3
from pathlib import Path
from typing import Any

import psycopg
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

def _get_secret(name: str, default: Any = None) -> Any:
    try:
        return st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default

for secret_name in ("DATABASE_URL", "RB_ADMIN_EMAIL", "RB_FULL_DB_PATH", "RB_UPLOAD_DIR"):
    secret_value = _get_secret(secret_name) or os.environ.get(secret_name)
    if secret_value:
        os.environ[secret_name] = str(secret_value)

os.environ["RB_UPLOADS_AS_DATA_URI"] = "1"

from backend import full_server
from backend.full_server import ApiError, ApiHandler


PRODUCT_IMAGES = {
    "baggy-blue-denim": "https://images.unsplash.com/photo-1628196871136-a6e5fc060309?auto=format&fit=crop&w=900&q=80",
    "baggy-cargo-denim": "https://images.unsplash.com/photo-1628196871136-a6e5fc060309?auto=format&fit=crop&w=900&q=80",
    "oversized-graphic-tee": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80",
    "oversized-campus-fit": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80",
    "asics-gel-street-runners": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
    "platform-street-sneakers": "https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?auto=format&fit=crop&w=900&q=80",
    "dr-martens-street-boots": "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?auto=format&fit=crop&w=900&q=80",
    "clean-white-low-tops": "https://images.unsplash.com/photo-1628196871136-a6e5fc060309?auto=format&fit=crop&w=900&q=80",
    "oversized-varsity-hoodie": "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?auto=format&fit=crop&w=900&q=80",
    "tailored-black-suit": "https://images.unsplash.com/photo-1618886614638-80e3c103d31a?auto=format&fit=crop&w=900&q=80",
    "satin-evening-dress": "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=900&q=80",
    "clean-cut-formal-shirt": "https://images.unsplash.com/photo-1618886614638-80e3c103d31a?auto=format&fit=crop&w=900&q=80",
}


class StoreError(Exception):
    pass


def _invoke_api(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    handler = ApiHandler.__new__(ApiHandler)
    handler.headers = {}
    token = st.session_state.get("token", "")
    if token:
        handler.headers["Authorization"] = f"Bearer {token}"

    response: dict[str, Any] = {}

    def capture(status: int, body: dict | list) -> None:
        response["status"] = status
        response["body"] = body

    handler.send_json = capture
    try:
        handler.route(method, path, payload or {})
    except ApiError as error:
        raise StoreError(error.message) from error
    except (sqlite3.IntegrityError, psycopg.IntegrityError) as error:
        raise StoreError("That record already exists.") from error
    except (ValueError, TypeError, OverflowError) as error:
        raise StoreError("The request contains invalid values.") from error

    if "status" not in response:
        raise RuntimeError(f"The backend did not return a response for {method} {path}.")
    if response["status"] >= 400:
        body = response["body"]
        raise StoreError(body.get("error", "The request failed.") if isinstance(body, dict) else "The request failed.")
    if not isinstance(response["body"], dict):
        raise RuntimeError(f"The backend returned an unexpected response for {method} {path}.")
    return response["body"]


def _sign_in_with_oidc(claims: dict[str, Any]) -> dict[str, Any]:
    handler = ApiHandler.__new__(ApiHandler)
    response: dict[str, Any] = {}
    handler.send_json = lambda status, body: response.update(status=status, body=body)
    try:
        handler.google_login_from_oidc(claims)
    except ApiError as error:
        raise StoreError(error.message) from error
    except (sqlite3.IntegrityError, psycopg.IntegrityError) as error:
        raise StoreError("That account already exists.") from error

    if response.get("status", 500) >= 400:
        body = response.get("body", {})
        raise StoreError(body.get("error", "Google sign-in failed."))
    return response["body"]


@st.cache_resource
def initialize_database() -> None:
    full_server.initialize_db()


def _set_account(result: dict[str, Any]) -> None:
    st.session_state["token"] = result["token"]
    st.session_state["account"] = result["user"]
    st.session_state["oidc_subject"] = result["user"].get("google_sub")


def _sync_oidc_account() -> None:
    if not st.user.is_logged_in:
        return
    subject = str(getattr(st.user, "sub", "") or "")
    if not subject or st.session_state.get("oidc_subject") == subject:
        return

    claims = {
        name: getattr(st.user, name, None)
        for name in ("sub", "email", "email_verified", "name", "iss")
    }
    result = _sign_in_with_oidc(claims)
    _set_account(result)
    st.session_state["oidc_subject"] = subject


def _money(value: int | float) -> str:
    return f"GH₵ {value:,.0f}"


def _image(url: str | None) -> None:
    if not url:
        st.caption("No product image")
    elif url.startswith("data:") and "," in url:
        st.image(base64.b64decode(url.split(",", 1)[1]), use_container_width=True)
    elif url.startswith(("https://", "http://")):
        st.image(url, use_container_width=True)
    else:
        st.caption("Image unavailable in this deployment")


def _require_account() -> bool:
    if st.session_state.get("token"):
        return True
    st.info("Sign in to use this feature.")
    return False


def _products() -> list[dict[str, Any]]:
    products = _invoke_api("GET", "/api/products").get("products", [])
    for product in products:
        if not product.get("image_url"):
            product["image_url"] = PRODUCT_IMAGES.get(product["id"], "")
    return products


def _product_cards(products: list[dict[str, Any]]) -> None:
    if not products:
        st.info("No products are available in this category yet.")
        return

    for start in range(0, len(products), 3):
        columns = st.columns(3)
        for column, product in zip(columns, products[start : start + 3]):
            with column:
                with st.container(border=True):
                    _image(product.get("image_url"))
                    st.caption(product.get("category", "Fashion"))
                    st.subheader(product["name"])
                    st.write(_money(product.get("discountPrice", product["price"])))
                    stock = int(product.get("stock", 0))
                    if stock < 1:
                        st.caption("Currently out of stock")
                    else:
                        st.caption(f"{stock} in stock")
                    if st.button(
                        "Add to bag",
                        key=f"add-{product['id']}",
                        disabled=stock < 1,
                        use_container_width=True,
                    ):
                        if not _require_account():
                            continue
                        try:
                            _invoke_api(
                                "POST",
                                "/api/cart/items",
                                {"productId": product["id"], "quantity": 1},
                            )
                        except StoreError as error:
                            st.error(str(error))
                        else:
                            st.success(f"{product['name']} added to your bag.")
                    if st.session_state.get("token") and st.button(
                        "Save to wishlist",
                        key=f"wish-{product['id']}",
                        use_container_width=True,
                    ):
                        try:
                            _invoke_api("POST", f"/api/wishlist/{product['id']}")
                        except StoreError as error:
                            st.error(str(error))
                        else:
                            st.success("Saved to your wishlist.")


def _show_home() -> None:
    st.title("R&B Fashion")
    st.subheader("Your everyday, elevated.")
    st.write("Curated fashion with Ghanaian energy. Premium pieces, easy prices, and delivery across Ghana.")
    st.markdown("---")
    st.header("New arrivals")
    products = _products()
    _product_cards(products[:6])


def _show_shop() -> None:
    st.title("Shop")
    products = _products()
    categories = ["All"] + sorted({item["category"] for item in products})
    category = st.selectbox("Category", categories)
    filtered = products if category == "All" else [
        item for item in products if item["category"] == category
    ]
    _product_cards(filtered)


def _show_account() -> None:
    st.title("Your account")
    if st.session_state.get("account"):
        account = st.session_state["account"]
        st.success(f"Signed in as {account['name']} ({account['email']}).")
        return

    mode = st.radio("Account action", ("Sign in", "Create account"), horizontal=True)
    with st.form("account-form"):
        name = st.text_input("Name") if mode == "Create account" else ""
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(mode)
    if submitted:
        path = "/api/accounts" if mode == "Create account" else "/api/auth/login"
        payload = {"email": email, "password": password}
        if mode == "Create account":
            payload["name"] = name
        try:
            result = _invoke_api("POST", path, payload)
        except StoreError as error:
            st.error(str(error))
        else:
            _set_account(result)
            st.success(f"Welcome, {result['user']['name']}.")
            st.rerun()

    auth = _get_secret("auth", {})
    if all(auth.get(key) for key in ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")):
        st.divider()
        if st.button("Continue with Google"):
            st.login()
    else:
        st.caption("Google sign-in can be enabled with the [auth] settings in Streamlit secrets.")


def _show_cart() -> None:
    st.title("Your bag")
    if not _require_account():
        return
    cart = _invoke_api("GET", "/api/cart")
    items = cart.get("items", [])
    if not items:
        st.info("Your bag is empty.")
        return

    for item in items:
        left, middle, right = st.columns([5, 2, 1])
        left.write(f"**{item['name']}** — {_money(item['unitPrice'])} each")
        quantity = middle.number_input(
            "Quantity",
            min_value=1,
            max_value=max(1, int(item["stock"])),
            value=int(item["quantity"]),
            key=f"quantity-{item['product_id']}",
        )
        if quantity != item["quantity"]:
            try:
                _invoke_api(
                    "PUT",
                    f"/api/cart/items/{item['product_id']}",
                    {"quantity": quantity},
                )
            except StoreError as error:
                st.error(str(error))
            else:
                st.rerun()
        if right.button("Remove", key=f"remove-{item['product_id']}"):
            _invoke_api("DELETE", f"/api/cart/items/{item['product_id']}")
            st.rerun()
    st.metric("Bag total", _money(cart["total"]))

    with st.form("checkout-form"):
        st.subheader("Delivery details")
        name = st.text_input("Full name", value=st.session_state["account"]["name"])
        phone = st.text_input("Phone number")
        address = st.text_area("Delivery address")
        submitted = st.form_submit_button("Place order and get payment instructions")
    if submitted:
        try:
            order = _invoke_api(
                "POST",
                "/api/orders",
                {"shipping": {"name": name, "phone": phone, "address": address}},
            )["order"]
            checkout = _invoke_api(
                "POST", "/api/payments/checkout", {"orderId": order["id"]}
            )
        except StoreError as error:
            st.error(str(error))
        else:
            st.success(f"Order #{order['id']} created.")
            st.info(f"{checkout['instructions']}\n\nPayment reference: **{checkout['reference']}**")


def _show_wishlist() -> None:
    st.title("Wishlist")
    if not _require_account():
        return
    saved = _invoke_api("GET", "/api/wishlist").get("products", [])
    if not saved:
        st.info("Your wishlist is empty.")
        return
    for product in saved:
        left, right = st.columns([5, 1])
        left.write(f"**{product['name']}** — {_money(product['price'])}")
        if right.button("Remove", key=f"unwish-{product['id']}"):
            _invoke_api("DELETE", f"/api/wishlist/{product['id']}")
            st.rerun()


def _show_orders() -> None:
    st.title("Your orders")
    if not _require_account():
        return
    orders = _invoke_api("GET", "/api/orders").get("orders", [])
    if not orders:
        st.info("No orders yet.")
        return
    for order in orders:
        with st.expander(f"Order #{order['id']} · {_money(order['total'])} · {order['status']}"):
            st.write(f"Delivery to: {order['shipping_name']}, {order['shipping_phone']}")
            st.write(order["shipping_address"])
            for item in order["items"]:
                st.write(f"{item['name']} × {item['quantity']}")


def _show_forum() -> None:
    st.title("Style Forum")
    if not _require_account():
        return
    with st.form("forum-form"):
        feeling = st.text_input("How are you feeling?")
        request_type = st.selectbox("What do you need?", ("Style advice", "Custom look", "Outfit request"))
        message = st.text_area("Tell us more")
        contact = st.text_input(
            "How should we contact you?",
            value=st.session_state["account"]["email"],
        )
        image = st.file_uploader(
            "Optional inspiration image",
            type=("jpg", "jpeg", "png", "webp", "gif"),
        )
        submitted = st.form_submit_button("Send request")
    if submitted:
        payload: dict[str, Any] = {
            "feeling": feeling,
            "type": request_type,
            "message": message,
            "contact": contact,
        }
        if image:
            payload["imageData"] = (
                f"data:{image.type};base64,{base64.b64encode(image.getvalue()).decode('ascii')}"
            )
        try:
            result = _invoke_api("POST", "/api/forum-requests", payload)
        except StoreError as error:
            st.error(str(error))
        else:
            st.success(f"Request received (#{result['requestId']}).")


def _show_admin() -> None:
    account = st.session_state.get("account")
    if not account or account.get("role") != "admin":
        st.error("Administrator access is required.")
        return

    st.title("Store administration")
    products_tab, orders_tab, summary_tab = st.tabs(("Products", "Orders", "Summary"))
    with products_tab:
        products = _invoke_api("GET", "/api/admin/products").get("products", [])
        labels = ["Add a product"] + [f"{item['name']} ({item['id']})" for item in products]
        selected = st.selectbox("Product", labels)
        editing = next(
            (item for item in products if f"{item['name']} ({item['id']})" == selected),
            None,
        )
        with st.form("admin-product-form"):
            product_id = st.text_input(
                "Product ID",
                value=editing["id"] if editing else "",
                disabled=bool(editing),
            )
            name = st.text_input("Name", value=editing["name"] if editing else "")
            category = st.text_input("Category", value=editing["category"] if editing else "")
            price = st.number_input(
                "Price (GH₵)",
                min_value=0,
                value=int(editing["price"]) if editing else 0,
            )
            stock = st.number_input(
                "Stock",
                min_value=0,
                value=int(editing["stock"]) if editing else 0,
            )
            description = st.text_area(
                "Description", value=editing["description"] if editing else ""
            )
            image_url = st.text_input(
                "Image URL", value=editing["image_url"] if editing else ""
            )
            uploaded = st.file_uploader(
                "Upload image (max 700 KB)",
                type=("jpg", "jpeg", "png", "webp", "gif"),
                key="admin-image",
            )
            active = st.checkbox(
                "Visible in the shop",
                value=bool(editing["active"]) if editing else True,
            )
            submitted = st.form_submit_button("Save product")
        if submitted:
            if uploaded and uploaded.size > full_server.MAX_IMAGE_SIZE:
                st.error("Images must be 700 KB or smaller.")
            else:
                image_value = image_url
                if uploaded:
                    data = base64.b64encode(uploaded.getvalue()).decode("ascii")
                    image_data = f"data:{uploaded.type};base64,{data}"
                    try:
                        image_value = _invoke_api(
                            "POST",
                            "/api/admin/uploads",
                            {"imageData": image_data},
                        )["imageUrl"]
                    except StoreError as error:
                        st.error(str(error))
                        image_value = ""
                if image_value or not uploaded:
                    payload = {
                        "name": name,
                        "category": category,
                        "price": price,
                        "stock": stock,
                        "description": description,
                        "imageUrl": image_value,
                        "active": active,
                    }
                    if not editing:
                        payload["id"] = product_id
                    method = "PUT" if editing else "POST"
                    endpoint = (
                        f"/api/admin/products/{editing['id']}"
                        if editing
                        else "/api/admin/products"
                    )
                    try:
                        _invoke_api(method, endpoint, payload)
                    except StoreError as error:
                        st.error(str(error))
                    else:
                        st.success("Product saved.")
                        st.rerun()
        for product in products:
            if product["active"] and st.button(
                f"Archive {product['name']}", key=f"archive-{product['id']}"
            ):
                _invoke_api("DELETE", f"/api/admin/products/{product['id']}")
                st.rerun()

    with orders_tab:
        orders = _invoke_api("GET", "/api/admin/orders").get("orders", [])
        if not orders:
            st.info("No orders yet.")
        for order in orders:
            with st.expander(f"Order #{order['id']} · {_money(order['total'])} · {order['status']}"):
                st.write(f"{order['customer_name']} · {order['customer_email']}")
                st.write(f"{order['shipping_name']} · {order['shipping_phone']}")
                st.write(order["shipping_address"])
                st.write(", ".join(
                    f"{item['name']} × {item['quantity']}" for item in order["items"]
                ))
                status = st.selectbox(
                    "Status",
                    full_server.ORDER_STATUSES,
                    index=list(full_server.ORDER_STATUSES).index(order["status"]),
                    key=f"order-status-{order['id']}",
                )
                if st.button("Update order", key=f"update-order-{order['id']}"):
                    _invoke_api(
                        "PUT",
                        f"/api/admin/orders/{order['id']}/status",
                        {"status": status},
                    )
                    st.success("Order status updated.")
                    st.rerun()

    with summary_tab:
        summary = _invoke_api("GET", "/api/analytics/summary")
        today = summary["today"]
        metrics = st.columns(4)
        metrics[0].metric("Today's visitors", today["visitors"])
        metrics[1].metric("Today's orders", today["orders"])
        metrics[2].metric("New accounts", today["newAccounts"])
        metrics[3].metric("Today's revenue", _money(today["revenue"]))


st.set_page_config(page_title="R&B Fashion", page_icon="assets/rb-logo.png", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #f7f2ea; }
    [data-testid="stSidebar"] { background: #090909; }
    [data-testid="stSidebar"] * { color: #fff; }
    h1, h2, h3 { color: #17130c; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not full_server.DATABASE_URL:
    st.error("Set DATABASE_URL in Streamlit secrets to connect the persistent PostgreSQL database.")
    st.info("For a free-tier setup, create a Neon PostgreSQL project and add its pooled connection string as DATABASE_URL.")
    st.stop()

initialize_database()

try:
    _sync_oidc_account()
except StoreError as error:
    st.error(f"Google sign-in failed: {error}")

if "visitor_id" not in st.session_state:
    import secrets

    st.session_state["visitor_id"] = secrets.token_urlsafe(24)
    _invoke_api(
        "POST",
        "/api/visits",
        {"visitorId": st.session_state["visitor_id"], "page": "/"},
    )

with st.sidebar:
    st.image(str(Path(__file__).parent / "assets" / "rb-logo.png"), width=70)
    st.title("R&B Fashion")
    current_account = st.session_state.get("account")
    pages = ["Home", "Shop", "Your bag", "Wishlist", "Orders", "Style Forum", "Account"]
    if current_account and current_account["role"] == "admin":
        pages.append("Administration")
    page = st.radio("Navigate", pages)
    if current_account:
        st.caption(f"{current_account['name']} · {current_account['role']}")
        if st.button("Sign out"):
            _invoke_api("POST", "/api/auth/logout")
            st.session_state.pop("token", None)
            st.session_state.pop("account", None)
            st.session_state.pop("oidc_subject", None)
            if st.user.is_logged_in:
                st.logout()
            st.rerun()

if page == "Home":
    _show_home()
elif page == "Shop":
    _show_shop()
elif page == "Your bag":
    _show_cart()
elif page == "Wishlist":
    _show_wishlist()
elif page == "Orders":
    _show_orders()
elif page == "Style Forum":
    _show_forum()
elif page == "Account":
    _show_account()
elif page == "Administration":
    _show_admin()
