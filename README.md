# R&B Fashion

R&B Fashion is a Streamlit storefront for the shop, including account registration and sign-in, Google OIDC, catalog and inventory, carts, wishlists, orders, manual Mobile Money checkout, the Style Forum, and administrator tools.

## Deploy on Streamlit Community Cloud

1. Create a free PostgreSQL project on [Neon](https://neon.com/). Copy its pooled connection string. The free plan currently includes 1 GB of storage per project and suspends idle compute; limits can change.
2. Push this project to a GitHub repository.
3. In Streamlit Community Cloud, create an app from that repository and select `streamlit_app.py` as the main file. The project targets Python 3.12.
4. In the app's **Settings → Secrets**, add the following TOML, replacing each placeholder:

   ```toml
   DATABASE_URL = "postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require"
   RB_ADMIN_EMAIL = "owner@example.com"

   [auth]
   redirect_uri = "https://YOUR-APP.streamlit.app/oauth2callback"
   cookie_secret = "REPLACE_WITH_A_LONG_RANDOM_SECRET"
   client_id = "YOUR_GOOGLE_OAUTH_CLIENT_ID"
   client_secret = "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
   ```

5. In Google Cloud Console, configure a Google OAuth **Web application** client. Add the exact Streamlit URL as an authorized JavaScript origin and the exact `redirect_uri` value as an authorized redirect URI. For local development, use `http://localhost:8501/oauth2callback`.
6. Set `RB_ADMIN_EMAIL` to the store owner's Google-verified email before the first sign-in. Sign in with Google once to create the administrator account, then remove `RB_ADMIN_EMAIL` from the app secrets and restart the app. The administrator role remains stored in PostgreSQL.

The database schema and starter products are initialized automatically. Use the pooled Neon connection string, keep all secrets out of Git, and back up the database. Community Cloud's local filesystem is temporary, so uploaded images are stored as data URIs in PostgreSQL. Keep uploads small; the application accepts images up to 700 KB.

Email/password accounts remain supported. An email/password account cannot be linked to Google automatically; an existing password-only account with the owner email must be removed or migrated before that email can be bootstrapped as an administrator using Google.

Mobile Money checkout creates an order and payment reference for manual confirmation. It does not verify payment automatically or mark orders as paid.

## Run locally

Install dependencies and add a local `.streamlit/secrets.toml` based on [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example), then start Streamlit:

```powershell
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app requires a PostgreSQL `DATABASE_URL` locally as well as on Community Cloud. Never commit `.streamlit/secrets.toml`.

## Tests

```powershell
python -m unittest backend.test_full_server
```

The existing HTTP API implementation remains in `backend/full_server.py` and is used directly by the Streamlit UI so authentication, stock, order, and admin rules stay shared.
