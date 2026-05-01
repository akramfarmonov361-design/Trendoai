import os
import subprocess
import sys
import unittest


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
        import ai_generator

        self.assertFalse(ai_generator._is_text_generation_model("gemini-3.1-flash-live-preview"))
        self.assertFalse(ai_generator._is_text_generation_model("gemini-2.5-flash-preview-native-audio"))
        self.assertFalse(ai_generator._is_text_generation_model("gemini-3.1-flash-tts-preview"))
        self.assertFalse(ai_generator._is_text_generation_model("gemini-2.5-flash-image"))
        self.assertTrue(ai_generator._is_text_generation_model("gemini-2.5-flash"))

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


if __name__ == "__main__":
    unittest.main()
