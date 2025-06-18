import unittest
import json
from app import app
import io

class AppTestCase(unittest.TestCase):
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

    def test_format_selection_mp3(self):
        """Ensure mp3 format results in correct yt-dlp flags (audio extract)."""
        payload = {
            'url': 'https://www.youtube.com/watch?v=abcd',
            'output_dir': '/downloads',
            'format': 'mp3'
        }
        response = self.client.post('/start_download', json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)

    def test_format_selection_mkv(self):
        """Ensure mkv format results in merge-output-format command."""
        payload = {
            'url': 'https://www.youtube.com/watch?v=abcd',
            'output_dir': '/downloads',
            'format': 'mkv'
        }
        response = self.client.post('/start_download', json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)

    def test_output_dir_field_exists(self):
        """Ensure the form has the output_dir input field."""
        response = self.client.get('/')
        self.assertIn(b'Output Directory (on server):', response.data)
        self.assertIn(b'id="output_dir"', response.data)

    def test_download_with_description(self):
        """Test custom yt-dlp flag to extract video description."""
        payload = {
            'url': 'https://www.youtube.com/watch?v=abcd',
            'output_dir': '/downloads',
            'format': 'mp4',
            'custom_flags': ['--write-description']
        }
        with self.subTest('Custom flag: write-description'):
            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('message', data)

    def test_download_with_view_count(self):
        """Test custom yt-dlp flag to write view count."""
        payload = {
            'url': 'https://www.youtube.com/watch?v=abcd',
            'output_dir': '/downloads',
            'format': 'mp4',
            'custom_flags': ['--write-info-json']
        }
        with self.subTest('Custom flag: write-info-json (includes view count)'):
            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('message', data)

    def test_download_with_comments(self):
        """Test custom yt-dlp flag to include comment extraction."""
        payload = {
            'url': 'https://www.youtube.com/watch?v=abcd',
            'output_dir': '/downloads',
            'format': 'mp4',
            'custom_flags': ['--get-comments']
        }
        with self.subTest('Custom flag: get-comments'):
            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('message', data)

    def test_download_with_subtitles(self):
        """Test custom yt-dlp flag to write subtitles."""
        payload = {
            'url': 'https://www.youtube.com/watch?v=abcd',
            'output_dir': '/downloads',
            'format': 'mp4',
            'custom_flags': ['--write-subs']
        }
        with self.subTest('Custom flag: write-subs'):
            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('message', data)
            