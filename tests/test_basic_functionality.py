import unittest
import json
from app import app
import io
import os
import re
from app import app, UPLOAD_FOLDER, DOWNLOAD_FOLDER
from unittest.mock import patch, MagicMock

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

    def test_playlist_download_with_partial_failures(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter([
                "[download] Downloading playlist: PlaylistName",
                "[download] Playlist PlaylistName: Downloading 3 videos",
                "[download] Destination: video1.mp4",
                "ERROR: video2 unavailable",
                "[download] Destination: video3.mp4",
                "[DONE]"
            ])
            mock_popen.return_value = mock_proc

            playlist_url = 'https://www.youtube.com/playlist?list=PLAYLIST_WITH_ERRORS'

            payload = {
                "url": playlist_url,
                "format": "mp4",
                "output_dir": DOWNLOAD_FOLDER,
                "cookies_path": "",
                "download_options": {
                    "description": False,
                    "comments": False,
                    "info_json": True,
                    "subtitles": False,
                    "thumbnail": False
                },
                "custom_flags": []
            }

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn("message", data)
            self.assertIn("Download started", data["message"])

    def test_playlist_download_outputs_to_playlist_folder(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter([
                "[download] Downloading playlist: MyPlaylist",
                "[download] Playlist MyPlaylist: Downloading 2 videos",
                "[download] Destination: MyPlaylist/video1.mp4",
                "[download] Destination: MyPlaylist/video2.mp4",
                "[DONE]"
            ])
            mock_popen.return_value = mock_proc

            playlist_url = 'https://www.youtube.com/playlist?list=MY_PLAYLIST'

            payload = {
                "url": playlist_url,
                "format": "mp4",
                "output_dir": DOWNLOAD_FOLDER,
                "cookies_path": "",
                "download_options": {},
                "custom_flags": []
            }

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn("message", data)
            self.assertIn("Download started", data["message"])

            # Check that output template includes playlist folder
            called_args = mock_popen.call_args[0][0]
            # Find the '-o' argument index
            try:
                o_index = called_args.index('-o')
                output_template = called_args[o_index + 1]
            except ValueError:
                output_template = ""

            # The output template should contain %(playlist_title)s or folder name like 'MyPlaylist/%(title)s.%(ext)s'
            self.assertTrue(
                ('%(playlist_title)s' in output_template) or
                ('MyPlaylist' in output_template),
                msg=f"Expected output template to include playlist folder but got: {output_template}"
            )
