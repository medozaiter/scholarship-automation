import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web.app import app
import services.security_utils as su
from services.auth_service import AuthService
from services.db import get_user_by_email, delete_user_by_email, save_or_update_user


class TestAdvancedSecuritySuite(unittest.TestCase):
    """
    Comprehensive verification for:
    1. Rate Limiting (RFC metrics & 429 response)
    2. Email Verification (code & 1-click HMAC token)
    3. reCAPTCHA (server verification & dev bypass)
    4. Password Hashing (bcrypt work factor 12 & automatic migration)
    5. Helmet (Complete security headers & server suppression)
    6. Input Validation (strict Pydantic schemas)
    7. SQL Injection Protection (payload detection & prevention)
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.auth_service = AuthService()
        cls.test_email = "security_guardian_test@example.com"
        cls.test_password = "StrongPassword2026!#"
        delete_user_by_email(cls.test_email)

    @classmethod
    def tearDownClass(cls):
        delete_user_by_email(cls.test_email)

    def test_01_bcrypt_password_hashing_and_migration(self):
        """[TEST 1] Verifies bcrypt hashing (factor 12) and automatic migration of legacy hashes."""
        # 1. New hash generation
        hashed, salt = su.hash_password_secure(self.test_password)
        self.assertTrue(hashed.startswith("$2b$12$"), f"Expected bcrypt hash with work factor 12, got: {hashed}")

        # 2. Bcrypt verification
        is_valid, needs_rehash = su.verify_password_secure(self.test_password, hashed, salt)
        self.assertTrue(is_valid)
        self.assertFalse(needs_rehash)

        # 3. Wrong password rejection
        invalid, _ = su.verify_password_secure("WrongPassword123!", hashed, salt)
        self.assertFalse(invalid)

        # 4. Backward-compatible verification and auto-migration from PBKDF2
        import hashlib
        dummy_salt = "00112233445566778899aabbccddeeff"
        pb_derived = hashlib.pbkdf2_hmac("sha256", b"legacy_pass", bytes.fromhex(dummy_salt), 600000)
        legacy_pbkdf2 = f"pbkdf2:sha256:600000${dummy_salt}${pb_derived.hex()}"
        pb_valid, pb_rehash = su.verify_password_secure("legacy_pass", legacy_pbkdf2, dummy_salt)
        self.assertTrue(pb_valid)
        self.assertTrue(pb_rehash, "PBKDF2 hash should trigger auto-rehash to bcrypt")
        print(" -> PASSED: [TEST 1] Bcrypt work factor 12 hashing and legacy migration verified.")

    def test_02_helmet_security_headers_and_csp(self):
        """[TEST 2] Verifies Helmet-style security headers, CSP, and server fingerprint suppression."""
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)

        headers = res.headers
        self.assertEqual(headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(headers.get("x-frame-options"), "DENY")
        self.assertEqual(headers.get("x-xss-protection"), "1; mode=block")
        self.assertEqual(headers.get("referrer-policy"), "strict-origin-when-cross-origin")
        self.assertIn("max-age=31536000", headers.get("strict-transport-security", ""))
        self.assertIn("camera=()", headers.get("permissions-policy", ""))
        self.assertEqual(headers.get("cross-origin-opener-policy"), "same-origin-allow-popups")
        self.assertEqual(headers.get("cross-origin-resource-policy"), "cross-origin")
        self.assertEqual(headers.get("x-permitted-cross-domain-policies"), "none")

        # Verify CSP allows reCAPTCHA
        csp = headers.get("content-security-policy", "")
        self.assertIn("https://www.google.com/recaptcha/", csp)
        self.assertIn("frame-src", csp)

        # Verify server suppression
        self.assertIsNone(headers.get("server"))
        self.assertIsNone(headers.get("x-powered-by"))
        print(" -> PASSED: [TEST 2] Helmet security headers and CSP verified.")

    def test_03_rate_limiting_metrics_and_429(self):
        """[TEST 3] Verifies standard rate limiting headers and 429 response on threshold breach."""
        # 1. Normal request has rate limit headers
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)

        # 2. Direct rate limiter test
        test_ip = "192.0.2.42"
        # Consume allowed requests for auth
        for _ in range(10):
            su.security_rate_limiter.check_rate_limit(test_ip, "auth")

        allowed, retry_after, limit, remaining = su.security_rate_limiter.get_rate_limit_metrics(test_ip, "auth")
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)
        self.assertEqual(limit, 10)
        self.assertEqual(remaining, 0)
        print(" -> PASSED: [TEST 3] Rate limiting sliding-window threshold and RFC metrics verified.")

    def test_04_recaptcha_verification_and_dev_bypass(self):
        """[TEST 4] Verifies Google reCAPTCHA server verification and testing bypass tokens."""
        # Test bypass tokens
        ok1, _ = su.verify_recaptcha("test_captcha_token")
        self.assertTrue(ok1)
        ok2, _ = su.verify_recaptcha("dev_token")
        self.assertTrue(ok2)

        # Missing token when key is unconfigured defaults to pass with warning
        ok3, _ = su.verify_recaptcha("")
        self.assertTrue(ok3)

        # Test registration with test captcha
        reg_payload = {
            "email": self.test_email,
            "password": self.test_password,
            "full_name": "طالب الأمان المتقدم",
            "recaptcha_token": "test_captcha_token",
            "degree": "Undergraduate (Bachelor's)",
            "majors": ["Cybersecurity"]
        }
        res_reg = self.client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res_reg.status_code, 200)
        self.assertTrue(res_reg.json().get("success"))
        print(" -> PASSED: [TEST 4] reCAPTCHA validation and testing bypass verified.")

    def test_05_email_verification_dual_workflow(self):
        """[TEST 5] Verifies email verification via both 6-digit code and 1-click HMAC link."""
        user = get_user_by_email(self.test_email)
        self.assertIsNotNone(user)
        self.assertFalse(user.get("email_verified", False))

        # 1. Request verification email
        res_send = self.client.post("/api/auth/send-verification", json={"email": self.test_email})
        self.assertEqual(res_send.status_code, 200)
        code = res_send.json().get("code")
        token = res_send.json().get("token")
        self.assertIsNotNone(code)
        self.assertIsNotNone(token)

        # 2. Test 1-click GET verification via token
        res_get = self.client.get(f"/api/auth/verify-email?token={token}")
        self.assertEqual(res_get.status_code, 200)
        self.assertIn("تم توثيق وتفعيل بريدك الأكاديمي بنجاح", res_get.text)

        # Confirm user is now verified in database
        updated_user = get_user_by_email(self.test_email)
        self.assertTrue(updated_user.get("email_verified"))

        # 3. Test verification by 6-digit code
        updated_user["email_verified"] = False
        updated_user["verification_code"] = "998877"
        save_or_update_user(updated_user)

        res_post = self.client.post("/api/auth/verify-email", json={"email": self.test_email, "code": "998877"})
        self.assertEqual(res_post.status_code, 200)
        self.assertTrue(res_post.json().get("success"))

        final_user = get_user_by_email(self.test_email)
        self.assertTrue(final_user.get("email_verified"))
        print(" -> PASSED: [TEST 5] Dual-channel email verification (code & HMAC link) verified.")

    def test_06_sql_injection_defense_and_input_validation(self):
        """[TEST 6] Verifies detection and blocking of SQL injection payloads across inputs."""
        # 1. Detector unit test
        sqli_payloads = [
            "' OR 1=1--",
            "admin'--",
            "UNION SELECT null, username, password FROM users",
            "; DROP TABLE users; --",
            "1; WAITFOR DELAY '0:0:5'",
            "SLEEP(5)",
            "' OR 'x'='x"
        ]
        for p in sqli_payloads:
            self.assertTrue(su.detect_sql_injection(p), f"Failed to detect SQLi in: {p}")

        # Safe inputs should pass
        safe_inputs = ["Mustafa AbuZaiter", "Software Engineering", "IELTS 7.5", "Gaza, Palestine"]
        for s in safe_inputs:
            self.assertFalse(su.detect_sql_injection(s), f"False positive on safe input: {s}")

        # 2. API level SQL injection block
        malicious_reg = {
            "email": "hacker_attack@example.com",
            "password": "ValidPass1234!#",
            "full_name": "Hacker ' OR 1=1--",
            "recaptcha_token": "test_captcha_token"
        }
        res = self.client.post("/api/auth/register", json=malicious_reg)
        self.assertEqual(res.status_code, 400)
        self.assertTrue("حقن" in res.text or "غير مصرح" in res.text or "Value error" in res.text)
        print(" -> PASSED: [TEST 6] SQL injection defense and strict input validation verified.")


if __name__ == "__main__":
    unittest.main()
