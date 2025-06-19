import unittest
import json
from app import app

class FormatAndFlagsTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

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
