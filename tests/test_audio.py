import unittest
import base64
import json
from unittest import mock
from app import app
import app as trendo_app

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
        captured = {}

        def fake_live_reply(audio_bytes, mime_type, system_prompt):
            captured['audio_bytes'] = audio_bytes
            captured['mime_type'] = mime_type
            captured['system_prompt'] = system_prompt
            return {
                'text': 'Salom, ovozingiz eshitildi.',
                'audio_base64': 'UklGRg==',
                'input_transcription': 'salom',
                'model': trendo_app.GEMINI_LIVE_MODEL,
            }

        dummy_audio = b'fake webm audio'
        dummy_base64 = base64.b64encode(dummy_audio).decode('ascii')

        with mock.patch.object(trendo_app.app, 'config', {**trendo_app.app.config, 'GEMINI_API_KEY': 'test-key'}):
            with mock.patch.object(trendo_app, 'get_live_audio_reply', side_effect=fake_live_reply):
                response = self.client.post(
                    '/api/chat/audio',
                    data=json.dumps({'audio': dummy_base64, 'mime_type': 'audio/webm'}),
                    content_type='application/json'
                )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['model'], 'gemini-3.1-flash-live-preview')
        self.assertEqual(data['response'], 'Salom, ovozingiz eshitildi.')
        self.assertEqual(captured['audio_bytes'], dummy_audio)
        self.assertEqual(captured['mime_type'], 'audio/webm')

    def test_audio_chat_explains_live_access_denied(self):
        dummy_base64 = base64.b64encode(b'fake webm audio').decode('ascii')

        with mock.patch.object(trendo_app.app, 'config', {**trendo_app.app.config, 'GEMINI_API_KEY': 'test-key'}):
            with mock.patch.object(
                trendo_app,
                'get_live_audio_reply',
                side_effect=RuntimeError('Your project has been denied access. Please contact support.'),
            ):
                response = self.client.post(
                    '/api/chat/audio',
                    data=json.dumps({'audio': dummy_base64, 'mime_type': 'audio/webm'}),
                    content_type='application/json'
                )

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertEqual(data['model'], 'gemini-3.1-flash-live-preview')
        self.assertIn('Gemini Live uchun API project access yoqilmagan', data['response'])

if __name__ == '__main__':
    unittest.main()
