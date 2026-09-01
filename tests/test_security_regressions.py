import os
import subprocess
import sys
import unittest
from unittest import mock


class SecurityRegressionTests(unittest.TestCase):
    def test_admin_json_posts_require_csrf(self):
        import app as trendo_app

        client = trendo_app.app.test_client()

        service_response = client.post(
            "/admin/services/generate",
            json={"title": "Test service"},
        )
        bot_order_response = client.post(
            "/api/bot-order-status",
            json={"order_id": 1, "status": "confirmed"},
        )

        self.assertEqual(service_response.status_code, 400)
        self.assertEqual(bot_order_response.status_code, 400)

    def test_sensitive_cron_endpoints_require_secret(self):
        import app as trendo_app

        client = trendo_app.app.test_client()

        self.assertEqual(client.get("/api/init-db").status_code, 401)
        self.assertEqual(client.post("/api/cron/generate").status_code, 401)

    def test_public_health_endpoint_stays_open(self):
        import app as trendo_app

        response = trendo_app.app.test_client().get("/api/health")

        self.assertEqual(response.status_code, 200)

    def test_text_generation_models_skip_live_audio_and_image_models(self):
        from services import ai_service

        self.assertFalse(ai_service._is_text_generation_model("gemini-3.1-flash-live-preview"))
        self.assertFalse(ai_service._is_text_generation_model("gemini-2.5-flash-preview-native-audio"))
        self.assertFalse(ai_service._is_text_generation_model("gemini-3.1-flash-tts-preview"))
        self.assertFalse(ai_service._is_text_generation_model("gemini-2.5-flash-image"))
        self.assertTrue(ai_service._is_text_generation_model("gemini-2.5-flash"))

    def test_chat_has_local_fallback_when_gemini_quota_is_exhausted(self):
        from services import ai_service
        import app as trendo_app

        client = trendo_app.app.test_client()

        with mock.patch.object(ai_service, "generate_text", side_effect=RuntimeError("429 quota exceeded")):
            response = client.post(
                "/api/chat",
                json={"message": "salom", "messages": [{"role": "user", "content": "salom"}]},
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["ai_fallback"])
        self.assertIn("Salom", data["response"])

    def test_production_rejects_default_security_values(self):
        env = os.environ.copy()
        env.update(
            {
                "FLASK_ENV": "production",
                "ADMIN_PASSWORD": "trendoai2025",
                "SECRET_KEY": "trendoai-secret-key-change-in-production",
                "CRON_SECRET": "trendoai-cron-secret-2025",
            }
        )

        result = subprocess.run(
            [sys.executable, "-c", "import config"],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            env=env,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("production muhitida xavfsiz qiymat", result.stderr + result.stdout)

    def test_admin_media_fields_accept_relative_paths(self):
        """Yuklangan rasm nisbiy yo'l bilan saqlanadi, forma esa uni rad etmasligi kerak.

        `_save_uploaded_image` S3 sozlanmagan holatda `/static/uploads/...`
        qaytaradi. Agar forma maydoni `type="url"` bo'lsa, brauzer bu qiymatni
        "Please enter a URL" deb rad etadi va loyihani umuman saqlab
        bo'lmaydi — rasm yuklangan har bir loyiha tahrirlash uchun yopilib
        qoladi.
        """
        form_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", "admin", "portfolio_form.html",
        )
        with open(form_path, encoding="utf-8") as handle:
            markup = handle.read()

        for field in ("image_url", "video_url"):
            self.assertNotIn(
                f'type="url" id="{field}"',
                markup,
                f"{field} maydoni type=url bo'lsa nisbiy yo'llar bloklanadi",
            )


if __name__ == "__main__":
    unittest.main()
