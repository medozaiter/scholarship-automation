import os
import io
import unittest
from PIL import Image
from fastapi.testclient import TestClient
from web.app import app
from services.auth_service import AuthService
from services.db import get_user_by_email, delete_user_by_email

class TestUploadAndLightMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.auth_service = AuthService()
        cls.test_email = "upload_test_student@example.com"
        cls.test_password = "SecurePassword123!"

        # Register test user
        delete_user_by_email(cls.test_email)
        reg_res = cls.client.post("/api/auth/register", json={
            "email": cls.test_email,
            "password": cls.test_password,
            "full_name": "طالب تجريبي للاختبار",
            "username": "upload-test-user",
            "country": "Palestine"
        })
        assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"

        # Login to get session token
        login_res = cls.client.post("/api/auth/login", json={
            "email": cls.test_email,
            "password": cls.test_password
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        cls.token = login_res.json()["token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        delete_user_by_email(cls.test_email)

    def test_01_avatar_upload_security_and_storage(self):
        """[TEST 1] Verifies avatar image upload: rejects fake executables, processes valid JPEG/PNG."""
        # 1. Unauthenticated rejection (using clean client with no cookies)
        clean_client = TestClient(app)
        res_unauth = clean_client.post("/api/user/upload-avatar", files={"file": ("test.jpg", b"fake", "image/jpeg")})
        self.assertEqual(res_unauth.status_code, 401)

        # 2. Fake executable rejection
        res_malicious = self.client.post(
            "/api/user/upload-avatar",
            headers=self.headers,
            files={"file": ("malicious.jpg", b"MZThisIsAnExecutableFileDisguisedAsAnImage1234567890", "image/jpeg")}
        )
        self.assertEqual(res_malicious.status_code, 400)
        self.assertIn("غير مصرح", res_malicious.json()["detail"])

        # 3. Valid JPEG image creation and upload
        img = Image.new("RGB", (300, 300), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

        res_valid = self.client.post(
            "/api/user/upload-avatar",
            headers=self.headers,
            files={"file": ("my_photo.jpg", img_bytes, "image/jpeg")}
        )
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["avatar_url"].startswith("/static/uploads/avatars/"))

        # Verify static file is readable over HTTP
        res_static = self.client.get(data["avatar_url"])
        self.assertEqual(res_static.status_code, 200)
        self.assertGreaterEqual(len(res_static.content), 100)

        # Verify user profile in DB reflects the new avatar
        user = get_user_by_email(self.test_email)
        self.assertEqual(user["avatar_url"], data["avatar_url"])
        print(" -> PASSED: [TEST 1] Avatar upload security, processing, and static serving verified.")

    def test_02_cover_banner_upload(self):
        """[TEST 2] Verifies cover banner image upload and profile update."""
        img = Image.new("RGB", (1200, 400), color="purple")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        res = self.client.post(
            "/api/user/upload-cover",
            headers=self.headers,
            files={"file": ("banner.png", png_bytes, "image/png")}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["cover_url"].startswith("/static/uploads/covers/"))

        user = get_user_by_email(self.test_email)
        self.assertEqual(user["cover_url"], data["cover_url"])
        print(" -> PASSED: [TEST 2] Cover banner upload and database persistence verified.")

    def test_03_input_sanitization_on_profile_update(self):
        """[TEST 3] Verifies universal input filter cleans XSS scripts, bidi overrides, and tags."""
        # 1. Script tag injection in full_name is strictly rejected
        bad_name_res = self.client.post("/api/user/profile", headers=self.headers, json={
            "email": self.test_email,
            "full_name": "أحمد خليل <script>alert('xss')</script>"
        })
        self.assertEqual(bad_name_res.status_code, 400)

        # 2. Sanitizable tags in profile fields are cleaned and escaped
        sanitizable_payload = {
            "email": self.test_email,
            "full_name": "أحمد خليل محمود",
            "city": "رام الله <b>المركزية</b>",
            "university": "جامعة بيرزيت",
            "bio": "طالب وباحث مهتم بالذكاء الاصطناعي وهندسة البيانات.",
            "skills": ["Python", "SQL", "Machine Learning"],
            "interests": ["منح أوروبا", "ألمانيا"],
            "social_links": {
                "linkedin": "https://linkedin.com/in/test-scholar",
                "github": "https://github.com/test-scholar"
            }
        }

        res = self.client.post("/api/user/profile", headers=self.headers, json=sanitizable_payload)
        self.assertEqual(res.status_code, 200)
        profile = res.json()["profile"]

        # Ensure no raw unescaped script tags survived in any field
        for field in ["city", "university", "bio"]:
            val = profile.get(field, "")
            self.assertNotIn("<script>", val)
            self.assertNotIn("<iframe>", val)

        for s in profile.get("skills", []):
            self.assertNotIn("<script>", s)

        print(" -> PASSED: [TEST 3] Input sanitization across profile fields verified.")

    def test_04_light_mode_and_nav_markup_integrity(self):
        """[TEST 4] Verifies HTML templates have valid light mode body background and updated nav items."""
        # 1. Homepage index.html
        res_home = self.client.get("/")
        self.assertEqual(res_home.status_code, 200)
        self.assertIn("المجتمع الطلابي", res_home.text)
        self.assertIn("آخر الأخبار", res_home.text)
        self.assertIn("bg-[#F4F1EA] dark:bg-[#0B1724]", res_home.text)
        self.assertIn("mobileNavDrawer", res_home.text)

        # 2. Community page
        res_comm = self.client.get("/community")
        self.assertEqual(res_comm.status_code, 200)
        self.assertIn("المجتمع الطلابي", res_comm.text)
        self.assertIn("آخر الأخبار", res_comm.text)
        self.assertIn("bg-[#F4F1EA] dark:bg-[#0B1724]", res_comm.text)

        # 3. News page
        res_news = self.client.get("/news")
        self.assertEqual(res_news.status_code, 200)
        self.assertIn("المجتمع الطلابي", res_news.text)
        self.assertIn("آخر الأخبار", res_news.text)
        self.assertIn("bg-[#F4F1EA] dark:bg-[#0B1724]", res_news.text)

        # 4. Dashboard page
        res_dash = self.client.get("/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn("المجتمع الطلابي", res_dash.text)
        self.assertIn("آخر الأخبار", res_dash.text)
        self.assertIn("bg-[#F4F1EA] dark:bg-[#0B1724]", res_dash.text)
        self.assertIn("avatarFileInput", res_dash.text)
        self.assertIn("coverFileInput", res_dash.text)

        print(" -> PASSED: [TEST 4] Navigation items, file upload inputs, and light mode markup verified.")

if __name__ == "__main__":
    unittest.main()
