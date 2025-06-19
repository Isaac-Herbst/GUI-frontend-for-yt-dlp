import unittest
import json
from app import app
import io

class BasicFunctionalityTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_homepage_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'yt-dlp Download Manager', response.data)

    def test_download_endpoint_without_url(self):
        response = self.client.post('/start_download', json={'url': ''})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "URL and output directory required")

    def test_download_endpoint_with_valid_url_and_output(self):
        payload = {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'output_dir': '/downloads'
        }
        response = self.client.post('/start_download', json=payload)
        self.assertIn(response.status_code, (200, 202))
        data = json.loads(response.data)
        self.assertIn('message', data)

    def test_download_endpoint_missing_output_dir(self):
        payload = {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            # 'output_dir' missing
        }
        response = self.client.post('/start_download', json=payload)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get('error'), "URL and output directory required")

    def test_download_endpoint_invalid_method_get(self):
        response = self.client.get('/start_download')
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_cookie_upload_endpoint(self):
        data = {
            'cookies_file': (io.BytesIO(b'test_cookie_content'), 'cookies.txt')
        }
        response = self.client.post('/upload_cookies', data=data, content_type='multipart/form-data')
        self.assertIn(response.status_code, (200, 201))
        data = json.loads(response.data)
        self.assertIn('message', data)

    def test_cookie_upload_endpoint_invalid_method_get(self):
        response = self.client.get('/upload_cookies')
        self.assertEqual(response.status_code, 405)

    def test_download_endpoint_with_invalid_url_format(self):
        payload = {
            'url': 'not-a-valid-url',
            'output_dir': '/downloads'
        }
        response = self.client.post('/start_download', json=payload)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_download_endpoint_with_missing_json(self):
        response = self.client.post('/start_download', data='notjson', content_type='text/plain')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
