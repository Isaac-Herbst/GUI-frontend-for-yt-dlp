import unittest
import json
import os
from app import app, DOWNLOAD_FOLDER, UPLOAD_FOLDER
from unittest.mock import patch, MagicMock

class FormatAndFlagsTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def post_download(self, payload, mock_lines=None):
        """Helper to post to /start_download and optionally patch subprocess."""
        mock_popen = None
        if mock_lines is not None:
            patcher = patch('app.subprocess.Popen')
            mock_popen = patcher.start()
            self.addCleanup(patcher.stop)

            mock_proc = MagicMock()
            mock_proc.stdout = iter(mock_lines)
            mock_popen.return_value = mock_proc

        response = self.client.post('/start_download', json=payload)
        return response, mock_popen

    def assert_successful_download(self, response):
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)

    def test_format_selection(self):
        for fmt in ['mp3', 'mkv']:
            with self.subTest(format=fmt):
                payload = {
                    'url': 'https://www.youtube.com/watch?v=abcd',
                    'output_dir': '/downloads',
                    'format': fmt
                }
                res, _ = self.post_download(payload)
                self.assert_successful_download(res)

    def test_output_dir_field_exists(self):
        response = self.client.get('/')
        self.assertIn(b'Output Directory (on server):', response.data)
        self.assertIn(b'id="output_dir"', response.data)

    def test_custom_flags(self):
        flags = [
            ('--write-description', 'write-description'),
            ('--write-info-json', 'info-json (includes view count)'),
            ('--get-comments', 'get-comments'),
            ('--write-subs', 'write-subs')
        ]
        for flag, name in flags:
            with self.subTest(flag=name):
                payload = {
                    'url': 'https://www.youtube.com/watch?v=abcd',
                    'output_dir': '/downloads',
                    'format': 'mp4',
                    'custom_flags': [flag]
                }
                res, _ = self.post_download(payload)
                self.assert_successful_download(res)

    def test_download_options_combination_flags(self):
        cases = [
            ('sponsorblock_remove', '--sponsorblock-remove'),
            ('thumbnail', ['--write-thumbnail', '--embed-thumbnail']),
            ('description', ['--write-description', '--embed-metadata']),
            ('comments', '--write-comments'),
            ('info_json', ['--write-info-json', '--embed-info-json']),
            ('subtitles', ['--write-subs', '--write-auto-subs', '--embed-subs'])
        ]

        for opt_key, expected_flags in cases:
            with self.subTest(option=opt_key):
                payload = {
                    'url': f'https://www.youtube.com/watch?v=test_{opt_key}',
                    'format': 'mp4',
                    'output_dir': DOWNLOAD_FOLDER,
                    'cookies_path': '',
                    'download_options': {
                        'description': False,
                        'comments': False,
                        'info_json': False,
                        'subtitles': False,
                        'thumbnail': False,
                        'sponsorblock_remove': False,
                        opt_key: True
                    },
                    'custom_flags': []
                }

                res, mock_popen = self.post_download(payload, mock_lines=[
                    "[download] Destination: video.mp4", "[DONE]"
                ])
                self.assertEqual(res.status_code, 200)

                called_args = mock_popen.call_args[0][0]
                if isinstance(expected_flags, str):
                    expected_flags = [expected_flags]
                for flag in expected_flags:
                    self.assertIn(flag, called_args)

    def test_sponsorblock_segments_handling(self):
        payload = {
            "url": "https://www.youtube.com/watch?v=video_with_sponsorblock",
            "format": "mp4",
            "output_dir": DOWNLOAD_FOLDER,
            "cookies_path": "",
            "download_options": {
                "sponsorblock_remove": True
            },
            "custom_flags": []
        }

        mock_lines = [
            "[info] SponsorBlock segments found and removed",
            "[download] Destination: video.mp4",
            "[DONE]"
        ]

        res, mock_popen = self.post_download(payload, mock_lines=mock_lines)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Download started", res.get_json()["message"])

        called_args = mock_popen.call_args[0][0]
        self.assertIn("--sponsorblock-remove", called_args)

    def test_start_download_unlisted_video_mocked(self):
        payload = {
            "url": "https://www.youtube.com/watch?v=Unlisted12345",
            "format": "mp4",
            "output_dir": DOWNLOAD_FOLDER,
            "cookies_path": "",
            "download_options": {},
            "custom_flags": []
        }

        mock_lines = ["[download] Destination: video.mp4", "[DONE]"]
        response, _ = self.post_download(payload, mock_lines)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Download started", response.get_json()["message"])

    def test_private_video_download_with_cookies(self):
        cookies_path = os.path.join(UPLOAD_FOLDER, 'test_cookies.txt')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        with open(cookies_path, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/")

        payload = {
            "url": "https://www.youtube.com/watch?v=PRIVATE123",
            "format": "mp4",
            "output_dir": DOWNLOAD_FOLDER,
            "cookies_path": cookies_path,
            "download_options": {
                "description": True,
                "comments": False,
                "info_json": True,
                "subtitles": False,
                "thumbnail": False
            },
            "custom_flags": []
        }

        mock_lines = ["[download] Destination: private.mp4", "[DONE]"]
        response, _ = self.post_download(payload, mock_lines)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Download started", response.get_json()["message"])

        os.remove(cookies_path)

    def test_unlisted_playlist_download(self):
        payload = {
            "url": "https://www.youtube.com/playlist?list=UNLISTED_PLAYLIST_123",
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

        mock_lines = [
            "[download] Downloading playlist: My Playlist",
            "[download] Playlist My Playlist: Downloading 2 videos",
            "[download] Destination: video1.mp4",
            "[download] Destination: video2.mp4",
            "[DONE]"
        ]

        response, _ = self.post_download(payload, mock_lines)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Download started", response.get_json()["message"])

    def test_max_filesize_enforcement(self):
        payload = {
            "url": "https://www.youtube.com/watch?v=small_video",
            "format": "mp4",
            "output_dir": DOWNLOAD_FOLDER,
            "cookies_path": "",
            "download_options": {},
            "custom_flags": ["--max-filesize", "5M"]
        }

        mock_lines = [
            "[info] Downloading video under size limit",
            "[download] Destination: smallfile.mp4",
            "[DONE]"
        ]

        response, mock_popen = self.post_download(payload, mock_lines)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Download started", response.get_json()["message"])

        called_args = mock_popen.call_args[0][0]
        self.assertIn("--max-filesize", called_args)
        self.assertIn("5M", called_args)
