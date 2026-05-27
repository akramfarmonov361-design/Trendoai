import unittest
import base64
import json
from app import app

class AudioChatTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_audio_chat_missing_audio(self):
        response = self.client.post('/api/chat/audio', json={})
        self.assertEqual(response.status_code, 400)

    def test_audio_chat_empty_audio(self):
        response = self.client.post('/api/chat/audio', json={'audio': ''})
        self.assertEqual(response.status_code, 400)

    def test_audio_chat_with_dummy_audio(self):
        # A tiny valid dummy 1-second silence webm base64 (or just dummy base64)
        dummy_base64 = "GkXfo6NgoSZntalStriVgoOEAkQrk0vdZmFzZg=="
        response = self.client.post(
            '/api/chat/audio',
            data=json.dumps({'audio': dummy_base64}),
            content_type='application/json'
        )
        print("Status code:", response.status_code)
        print("Response data:", response.data.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()
