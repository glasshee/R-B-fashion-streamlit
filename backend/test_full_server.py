import importlib.util
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).with_name('full_server.py')
SPEC = importlib.util.spec_from_file_location('rb_full_server', MODULE_PATH)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


class FullServerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory(prefix='rb-fashion-tests-')
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / 'rb-fashion-full.sqlite3'
        self.upload_dir = self.root / 'uploads'
        os.environ['RB_FULL_DB_PATH'] = str(self.db_path)
        os.environ['RB_UPLOAD_DIR'] = str(self.upload_dir)
        os.environ['RB_ADMIN_EMAIL'] = 'admin@example.com'
        os.environ['GOOGLE_CLIENT_ID'] = 'test-google-client-id'
        mod.DB_PATH = self.db_path
        mod.UPLOAD_DIR = self.upload_dir
        mod.ADMIN_EMAIL = 'admin@example.com'
        mod.GOOGLE_CLIENT_ID = 'test-google-client-id'
        mod.initialize_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_handler(self, token: str | None = None):
        handler = mod.ApiHandler.__new__(mod.ApiHandler)
        handler.headers = {}
        if token:
            handler.headers['Authorization'] = f'Bearer {token}'

        def send_json(status, payload):
            handler._last_response = (status, payload)

        handler.send_json = send_json
        return handler

    def last_response(self, handler):
        return handler._last_response

    def test_register_and_login_flow(self):
        handler = self.make_handler()
        handler.register({
            'name': 'Alice Johnson',
            'email': 'alice@example.com',
            'password': 'secret123',
        })
        status, payload = self.last_response(handler)
        self.assertEqual(status, 201)
        self.assertEqual(payload['user']['email'], 'alice@example.com')

        token = payload['token']
        me_handler = self.make_handler(token)
        me_handler.route('GET', '/api/me', {})
        status, me = self.last_response(me_handler)
        self.assertEqual(status, 200)

        login_handler = self.make_handler(token)
        login_handler.login({
            'email': 'alice@example.com',
            'password': 'secret123',
        })
        status, payload = self.last_response(login_handler)
        self.assertEqual(status, 200)
        self.assertEqual(payload['user']['name'], 'Alice Johnson')

    def test_email_registration_cannot_claim_admin_role(self):
        handler = self.make_handler()
        handler.register({
            'name': 'Store Owner',
            'email': 'admin@example.com',
            'password': 'admintest123',
        })
        mod.initialize_db()
        status, payload = self.last_response(handler)
        self.assertEqual(status, 201)
        self.assertEqual(payload['user']['role'], 'customer')
        handler = self.make_handler(payload['token'])
        with self.assertRaises(mod.ApiError) as error:
            handler.route('GET', '/api/admin/products', {})
        self.assertEqual(error.exception.status, 403)

    def test_postgres_connection_adapts_sqlite_placeholders_and_ignores(self):
        connection = Mock()
        db = mod.PostgresConnection(connection)

        db.execute(
            'INSERT OR IGNORE INTO wishlists(user_id, product_id) VALUES(?, ?)',
            (7, 'test-product'),
        )
        connection.execute.assert_called_once_with(
            'INSERT INTO wishlists(user_id, product_id) VALUES(%s, %s) ON CONFLICT DO NOTHING',
            (7, 'test-product'),
        )

        db.execute('BEGIN IMMEDIATE')
        self.assertEqual(connection.execute.call_args.args[0], 'BEGIN')

    def test_google_sign_in_creates_account_and_promotes_admin_email(self):
        handler = self.make_handler()
        claims = {
            'aud': mod.GOOGLE_CLIENT_ID,
            'iss': 'https://accounts.google.com',
            'exp': int(mod.time.time()) + 300,
            'nonce': 'test-nonce',
            'email_verified': 'true',
            'sub': 'google-user-123',
            'email': 'admin@example.com',
            'name': 'Store Owner',
        }
        with patch.object(mod.ApiHandler, 'verify_google_credential', return_value=claims):
            handler.route('POST', '/api/auth/google', {
                'credential': 'signed-google-token',
                'nonce': 'test-nonce',
            })

        status, payload = self.last_response(handler)
        self.assertEqual(status, 201)
        self.assertEqual(payload['user']['role'], 'admin')
        self.assertEqual(payload['user']['email'], 'admin@example.com')

    def test_streamlit_oidc_sign_in_uses_verified_google_claims(self):
        handler = self.make_handler()
        handler.google_login_from_oidc({
            'iss': 'https://accounts.google.com',
            'email_verified': True,
            'sub': 'streamlit-google-admin',
            'email': 'admin@example.com',
            'name': 'Store Owner',
        })

        status, payload = self.last_response(handler)
        self.assertEqual(status, 201)
        self.assertEqual(payload['user']['role'], 'admin')
        self.assertEqual(payload['user']['email'], 'admin@example.com')

    def test_streamlit_oidc_sign_in_rejects_unverified_google_email(self):
        handler = self.make_handler()
        with self.assertRaises(mod.ApiError) as error:
            handler.google_login_from_oidc({
                'email_verified': False,
                'sub': 'unverified-google-user',
                'email': 'customer@example.com',
            })

        self.assertEqual(error.exception.status, 401)

    def test_google_sign_in_does_not_link_unverified_existing_account(self):
        owner = self.make_handler()
        owner.register({
            'name': 'Existing Owner',
            'email': 'admin@example.com',
            'password': 'admintest123',
        })
        handler = self.make_handler()
        claims = {
            'aud': mod.GOOGLE_CLIENT_ID,
            'iss': 'accounts.google.com',
            'exp': int(mod.time.time()) + 300,
            'nonce': 'test-nonce',
            'email_verified': True,
            'sub': 'google-owner-456',
            'email': 'admin@example.com',
            'name': 'Google Owner',
        }
        with patch.object(mod.ApiHandler, 'verify_google_credential', return_value=claims):
            with self.assertRaises(mod.ApiError) as error:
                handler.route('POST', '/api/auth/google', {
                    'credential': 'signed-google-token',
                    'nonce': 'test-nonce',
                })
        self.assertEqual(error.exception.status, 409)
        with mod.connect_db() as db:
            linked = db.execute(
                'SELECT google_sub FROM users WHERE email = ?', ('admin@example.com',)
            ).fetchone()
        self.assertIsNone(linked['google_sub'])

    def create_google_admin(self):
        handler = self.make_handler()
        claims = {
            'aud': mod.GOOGLE_CLIENT_ID,
            'iss': 'https://accounts.google.com',
            'exp': int(mod.time.time()) + 300,
            'nonce': 'test-nonce',
            'email_verified': 'true',
            'sub': 'google-admin-123',
            'email': 'admin@example.com',
            'name': 'Store Owner',
        }
        with patch.object(mod.ApiHandler, 'verify_google_credential', return_value=claims):
            handler.route('POST', '/api/auth/google', {
                'credential': 'signed-google-token',
                'nonce': 'test-nonce',
            })
        return handler

    def test_google_sign_in_rejects_unverified_email_and_nonce_mismatch(self):
        handler = self.make_handler()
        claims = {
            'aud': mod.GOOGLE_CLIENT_ID,
            'iss': 'https://accounts.google.com',
            'exp': int(mod.time.time()) + 300,
            'nonce': 'wrong-nonce',
            'email_verified': 'false',
            'sub': 'google-user-789',
            'email': 'customer@example.com',
            'name': 'Customer',
        }
        with patch.object(mod.ApiHandler, 'verify_google_credential', return_value=claims):
            with self.assertRaises(mod.ApiError) as error:
                handler.route('POST', '/api/auth/google', {
                    'credential': 'signed-google-token',
                    'nonce': 'test-nonce',
                })
        self.assertEqual(error.exception.status, 401)

    def test_admin_can_create_product(self):
        owner = self.create_google_admin()
        token = self.last_response(owner)[1]['token']

        admin_handler = self.make_handler(token)
        admin_handler.save_product(None, {
            'id': 'test-oversized-shirt',
            'name': 'Test oversized shirt',
            'category': 'Streetwear',
            'price': 210,
            'stock': 11,
            'description': 'A test item',
            'imageUrl': 'https://example.com/image.jpg',
            'active': True,
        })
        status, product_payload = self.last_response(admin_handler)
        self.assertEqual(status, 201)
        self.assertEqual(product_payload['product']['id'], 'test-oversized-shirt')
        self.assertEqual(product_payload['product']['price'], 210)

    def test_admin_can_upload_product_image(self):
        owner = self.create_google_admin()
        token = self.last_response(owner)[1]['token']
        image_data = 'data:image/png;base64,' + mod.base64.b64encode(
            b'\x89PNG\r\n\x1a\nimage-bytes'
        ).decode()

        admin_handler = self.make_handler(token)
        admin_handler.route('POST', '/api/admin/uploads', {'imageData': image_data})

        status, payload = self.last_response(admin_handler)
        self.assertEqual(status, 201)
        self.assertTrue(payload['imageUrl'].startswith('/uploads/product-'))
        saved_image = self.upload_dir / payload['imageUrl'].rsplit('/', 1)[1]
        self.assertEqual(saved_image.read_bytes(), b'\x89PNG\r\n\x1a\nimage-bytes')
        self.assertEqual(admin_handler.translate_path(payload['imageUrl']), str(saved_image.resolve()))
        self.assertNotEqual(admin_handler.translate_path('/uploads/'), str(self.upload_dir.resolve()))

        unauthenticated_handler = self.make_handler()
        with self.assertRaises(mod.ApiError):
            unauthenticated_handler.route('POST', '/api/admin/uploads', {'imageData': image_data})

    def test_admin_product_image_upload_uses_blob_storage_url(self):
        owner = self.create_google_admin()
        token = self.last_response(owner)[1]['token']
        handler = self.make_handler(token)
        image_data = 'data:image/png;base64,' + mod.base64.b64encode(
            b'\x89PNG\r\n\x1a\nimage-bytes'
        ).decode()

        with patch.object(mod, 'store_uploaded_image', return_value='https://blob.example/image.png') as put:
            handler.route('POST', '/api/admin/uploads', {'imageData': image_data})

        status, payload = self.last_response(handler)
        self.assertEqual(status, 201)
        self.assertEqual(payload['imageUrl'], 'https://blob.example/image.png')
        self.assertEqual(put.call_args.args[0], 'products')
        self.assertEqual(put.call_args.args[2], b'\x89PNG\r\n\x1a\nimage-bytes')
        self.assertEqual(put.call_args.args[3], 'image/png')

    def test_streamlit_image_storage_returns_database_safe_data_uri(self):
        with patch.dict(os.environ, {'RB_UPLOADS_AS_DATA_URI': '1'}, clear=True):
            image_url = mod.store_uploaded_image(
                'products', 'image.png', b'image', 'image/png'
            )

        self.assertEqual(image_url, 'data:image/png;base64,aW1hZ2U=')


if __name__ == '__main__':
    unittest.main()
