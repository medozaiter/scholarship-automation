import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
from fastapi.testclient import TestClient

from web.app import app
from services.auth_service import AuthService
from services.advisor_service import AdvisorService
from services.db import get_user_by_email, get_user_by_username


class TestAcademicIdentitySystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.auth_service = AuthService()
        cls.advisor_service = AdvisorService()
        cls.test_email = "academic_student_test@example.com"
        cls.test_password = "SecureStudentPass2026!"
        cls.test_username = "academic-samir"

    def setUp(self):
        from services.security_utils import security_rate_limiter
        security_rate_limiter._requests.clear()
        security_rate_limiter._failed_logins.clear()
        # Clean up any leftover test student record
        try:
            self.auth_service.delete_account(self.test_email, self.test_password)
        except Exception:
            pass

    def tearDown(self):
        # Clean up after test
        try:
            self.auth_service.delete_account(self.test_email, self.test_password)
        except Exception:
            pass
        try:
            self.auth_service.delete_account(self.test_email, "NewSecurePassword2026!")
        except Exception:
            pass

    def test_01_registration_with_academic_identity(self):
        """Test registration creates user with username, profile details, and session token."""
        payload = {
            "full_name": "Samir Al-Quds",
            "email": self.test_email,
            "username": self.test_username,
            "password": self.test_password,
            "degree": "Undergraduate (Bachelor's)",
            "majors": ["Artificial Intelligence", "Computer Science"],
            "gpa": "92%",
            "country": "Palestine",
            "city": "Jerusalem",
            "university": "Al-Quds University",
            "graduation_year": "2027",
            "bio": "باحث شغوف بالذكاء الاصطناعي ومعالجة اللغات الطبيعية.",
            "skills": ["Python", "PyTorch", "FastAPI"],
            "languages": [{"name": "العربية", "level": "اللغة الأم"}, {"name": "English", "level": "IELTS 7.0"}],
            "target_countries": ["Germany", "Canada"],
            "scholarship_interests": ["DAAD", "Lester B. Pearson"],
            "social_links": {
                "linkedin": "https://linkedin.com/in/samir-ai",
                "github": "https://github.com/samir-ai"
            }
        }

        res = self.client.post("/api/auth/register", json=payload)
        self.assertEqual(res.status_code, 200, f"Registration failed: {res.text}")
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("token", data)
        user = data["user"]
        self.assertEqual(user["username"], self.test_username)
        self.assertEqual(user["full_name"], "Samir Al-Quds")
        self.assertEqual(user["city"], "Jerusalem")
        self.assertEqual(user["university"], "Al-Quds University")
        self.assertIn("completeness", user)
        self.assertGreater(user["completeness"]["percentage"], 50)
        print(" -> PASSED: [TEST 1] Registration with academic profile & unique handle verified.")

    def test_02_login_and_remember_me_session_expiry(self):
        """Test login with remember_me generates 30-day session token, else 24-hour token."""
        # First register
        self.auth_service.register(
            email=self.test_email,
            password=self.test_password,
            full_name="Samir Al-Quds",
            username=self.test_username
        )

        # 1. Standard login (remember_me = False -> 24 hours = 86400s)
        res_std = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password,
            "remember_me": False
        })
        self.assertEqual(res_std.status_code, 200)
        user_std = res_std.json()["user"]
        self.assertEqual(user_std["expires_in_seconds"], 86400)

        # 2. Remember me login (remember_me = True -> 30 days = 30 * 86400s)
        res_rmb = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password,
            "remember_me": True
        })
        self.assertEqual(res_rmb.status_code, 200)
        user_rmb = res_rmb.json()["user"]
        self.assertEqual(user_rmb["expires_in_seconds"], 30 * 86400)
        print(" -> PASSED: [TEST 2] Standard and Remember-Me (30-day) authentication verified.")

    def test_03_forgot_and_reset_password_workflow(self):
        """Test password reset workflow with cryptographic reset token & PBKDF2 rehash."""
        self.auth_service.register(
            email=self.test_email,
            password=self.test_password,
            full_name="Samir Al-Quds",
            username=self.test_username
        )

        # 1. Request reset token
        res_forgot = self.client.post("/api/auth/forgot-password", json={"email": self.test_email})
        self.assertEqual(res_forgot.status_code, 200)
        data_forgot = res_forgot.json()
        self.assertTrue(data_forgot["success"])
        token = data_forgot.get("reset_token")
        self.assertTrue(bool(token))

        # 2. Reset password using token
        new_password = "NewSecurePassword2026!"
        res_reset = self.client.post("/api/auth/reset-password", json={
            "email": self.test_email,
            "token": token,
            "new_password": new_password
        })
        self.assertEqual(res_reset.status_code, 200)
        self.assertTrue(res_reset.json()["success"])

        # 3. Old password should now fail
        res_old = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(res_old.status_code, 401)

        # 4. New password should succeed
        res_new = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": new_password
        })
        self.assertEqual(res_new.status_code, 200)
        print(" -> PASSED: [TEST 3] Cryptographic password reset & PBKDF2 rehash verified.")

    def test_04_email_verification_workflow(self):
        """Test sending 6-digit code and verifying student academic email."""
        self.auth_service.register(
            email=self.test_email,
            password=self.test_password,
            full_name="Samir Al-Quds",
            username=self.test_username
        )

        # Check initial unverified state
        u_before = self.auth_service.get_by_email(self.test_email)
        self.assertFalse(u_before["email_verified"])

        # Request verification code
        res_send = self.client.post("/api/auth/send-verification", json={"email": self.test_email})
        self.assertEqual(res_send.status_code, 200)
        code = res_send.json().get("code")
        self.assertTrue(bool(code) and len(code) == 6)

        # Verify with code
        res_verify = self.client.post("/api/auth/verify-email", json={
            "email": self.test_email,
            "code": code
        })
        self.assertEqual(res_verify.status_code, 200)
        self.assertTrue(res_verify.json()["success"])

        # Confirm verified in storage
        u_after = self.auth_service.get_by_email(self.test_email)
        self.assertTrue(u_after["email_verified"])
        print(" -> PASSED: [TEST 4] 6-digit email verification workflow verified.")

    def test_05_profile_updates_and_completeness_indicator(self):
        """Test updating profile attributes and completeness meter score calculation."""
        reg_user = self.auth_service.register(
            email=self.test_email,
            password=self.test_password,
            full_name="Samir Al-Quds",
            username=self.test_username
        )
        token = reg_user["session_token"]
        score_initial = reg_user["completeness"]["percentage"]

        # Update profile with full details
        updates = {
            "email": self.test_email,
            "avatar_url": "https://example.com/samir-avatar.jpg",
            "cover_url": "https://example.com/banner.jpg",
            "city": "Jerusalem",
            "university": "Faculty of Engineering",
            "bio": "طالب متخصص في الذكاء الاصطناعي وباحث عن منح الماجستير في ألمانيا وكندا.",
            "skills": ["Python", "FastAPI", "Deep Learning", "Docker"],
            "languages": [{"name": "العربية", "level": "اللغة الأم"}, {"name": "English", "level": "IELTS 7.5"}],
            "target_countries": ["Germany", "Canada"],
            "scholarship_interests": ["DAAD", "Erasmus"],
            "social_links": {
                "linkedin": "https://linkedin.com/in/samir",
                "github": "https://github.com/samir",
                "whatsapp": "+970599123456"
            }
        }

        res_update = self.client.put(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {token}"},
            json=updates
        )
        self.assertEqual(res_update.status_code, 200)
        data = res_update.json()
        self.assertTrue(data["success"])
        score_after = data["profile"]["completeness"]["percentage"]
        self.assertGreater(score_after, score_initial)
        self.assertEqual(score_after, 100)
        self.assertTrue(data["profile"]["completeness"]["is_complete"])
        print(" -> PASSED: [TEST 5] Profile customization & 100% completeness score verified.")

    def test_06_public_profile_and_privacy_controls(self):
        """Test public profile view /profile/{username} and privacy visibility settings."""
        self.auth_service.register(
            email=self.test_email,
            password=self.test_password,
            full_name="Samir Al-Quds",
            username=self.test_username,
            gpa="94%",
            university="Al-Quds University"
        )

        # 1. Test public profile HTML route
        res_html = self.client.get(f"/profile/{self.test_username}")
        self.assertEqual(res_html.status_code, 200)
        self.assertIn("ScholarPilot AI", res_html.text)

        # 2. Test public profile API
        res_api = self.client.get(f"/api/profile/{self.test_username}")
        self.assertEqual(res_api.status_code, 200)
        p_data = res_api.json()["profile"]
        self.assertFalse(p_data["is_private"])
        self.assertEqual(p_data["username"], self.test_username)
        self.assertEqual(p_data["full_name"], "Samir Al-Quds")
        self.assertEqual(p_data["gpa"], "94%")

        # 3. Test Privacy Setting: Hide GPA
        self.auth_service.update_profile(self.test_email, {
            "privacy_settings": {"public_profile": True, "show_gpa": False, "show_contact": True}
        })
        res_api_nogpa = self.client.get(f"/api/profile/{self.test_username}")
        self.assertIsNone(res_api_nogpa.json()["profile"]["gpa"])

        # 4. Test Privacy Setting: Make Entire Profile Private
        self.auth_service.update_profile(self.test_email, {
            "privacy_settings": {"public_profile": False, "show_gpa": False, "show_contact": False}
        })
        res_api_priv = self.client.get(f"/api/profile/{self.test_username}")
        self.assertTrue(res_api_priv.json()["profile"]["is_private"])
        self.assertNotIn("social_links", res_api_priv.json()["profile"])
        print(" -> PASSED: [TEST 6] Public portfolio & privacy toggles (Private/Hide GPA) verified.")

    def test_07_settings_change_password_and_delete_account(self):
        """Test authenticated password change and permanent account deletion."""
        reg_user = self.auth_service.register(
            email=self.test_email,
            password=self.test_password,
            full_name="Samir Al-Quds",
            username=self.test_username
        )
        token = reg_user["session_token"]

        # 1. Change password with wrong current password should fail
        res_pw_err = self.client.post(
            "/api/user/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": self.test_email,
                "current_password": "WrongPassword123!",
                "new_password": "BrandNewPassword2026!"
            }
        )
        self.assertEqual(res_pw_err.status_code, 400)

        # 2. Change password with correct current password should succeed
        res_pw_ok = self.client.post(
            "/api/user/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": self.test_email,
                "current_password": self.test_password,
                "new_password": "BrandNewPassword2026!"
            }
        )
        self.assertEqual(res_pw_ok.status_code, 200)

        # 3. Delete account permanently
        res_del = self.client.post(
            "/api/user/delete-account",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": self.test_email,
                "password": "BrandNewPassword2026!"
            }
        )
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json()["success"])

        # Verify user is gone
        u_del = self.auth_service.get_by_email(self.test_email)
        self.assertIsNone(u_del)
        print(" -> PASSED: [TEST 7] Change password & permanent account deletion verified.")

    def test_08_scholarship_matching_profile_integration(self):
        """Test recommendation and matching engine factors in student target destinations, interests, and skills."""
        student_profile = {
            "gpa": "92%",
            "majors": ["Artificial Intelligence", "Computer Science"],
            "degree": "Undergraduate (Bachelor's)",
            "country": "Palestine",
            "target_countries": ["Germany", "Canada"],
            "interests": ["Machine Learning", "Autonomous Systems"],
            "skills": ["Python", "TensorFlow"]
        }

        # Match against a Canadian scholarship
        sch_canada = {
            "name": "Lester B. Pearson International Scholarship",
            "country": "Canada",
            "target_majors": ["Computer Science", "Engineering"],
            "degree": "Undergraduate",
            "min_gpa_percent": 88.0,
            "quota_palestine": True
        }

        match_res = self.advisor_service.calculate_smart_match(student_profile, sch_canada)
        self.assertGreaterEqual(match_res["match_score"], 80)
        # Strengths should reflect matching target country and technical interests
        strengths_joined = " ".join(match_res["strengths"])
        self.assertTrue("وجهات الابتعاث المفضلة" in strengths_joined or "Canada" in strengths_joined or "الجهة المانحة" in strengths_joined)
        print(" -> PASSED: [TEST 8] Scholarship matching algorithm integrates target countries & profile skills.")


if __name__ == "__main__":
    unittest.main()
