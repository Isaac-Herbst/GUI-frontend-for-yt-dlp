import unittest
import os
import re
from app import app, UPLOAD_FOLDER, DOWNLOAD_FOLDER
from unittest.mock import patch, MagicMock

class AdvancedFeatureTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_start_download_unlisted_video_mocked(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["[download] Destination: video.mp4", "[DONE]"])
            mock_popen.return_value = mock_proc

            unlisted_url = 'https://www.youtube.com/watch?v=Unlisted12345'
            payload = {
                "url": unlisted_url,
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

    def test_private_video_download_with_cookies(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["[download] Destination: private.mp4", "[DONE]"])
            mock_popen.return_value = mock_proc

            private_url = 'https://www.youtube.com/watch?v=PRIVATE123'
            cookies_path = os.path.join(UPLOAD_FOLDER, 'test_cookies.txt')

            # Simulate cookies file existence
            with open(cookies_path, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/")

            payload = {
                "url": private_url,
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

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn("message", data)
            self.assertIn("Download started", data["message"])

            os.remove(cookies_path)  # cleanup

    def test_unlisted_playlist_download(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter([
                "[download] Downloading playlist: My Playlist",
                "[download] Playlist My Playlist: Downloading 2 videos",
                "[download] Destination: video1.mp4",
                "[download] Destination: video2.mp4",
                "[DONE]"
            ])
            mock_popen.return_value = mock_proc

            unlisted_playlist_url = 'https://www.youtube.com/playlist?list=UNLISTED_PLAYLIST_123'
            
            payload = {
                "url": unlisted_playlist_url,
                "format": "mp4",
                "output_dir": DOWNLOAD_FOLDER,
                "cookies_path": "",  # no auth required for unlisted
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

    def test_sponsorblock_segments_handling(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter([
                "[info] SponsorBlock segments found and removed",
                "[download] Destination: video.mp4",
                "[DONE]"
            ])
            mock_popen.return_value = mock_proc

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

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn("Download started", data["message"])

            called_args = mock_popen.call_args[0][0]
            self.assertIn("--sponsorblock-remove", called_args)

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

    def test_embed_thumbnail_used_with_write_thumbnail(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["[download] Destination: video.mp4", "[DONE]"])
            mock_popen.return_value = mock_proc

            payload = {
                "url": "https://www.youtube.com/watch?v=testvideo",
                "format": "mp4",
                "output_dir": DOWNLOAD_FOLDER,
                "cookies_path": "",
                "download_options": {
                    "description": False,
                    "comments": False,
                    "info_json": False,
                    "subtitles": False,
                    "thumbnail": True
                },
                "custom_flags": []
            }

            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)

            called_args = mock_popen.call_args[0][0]
            self.assertIn('--write-thumbnail', called_args)
            self.assertIn('--embed-thumbnail', called_args)

    def test_embed_description_used_with_write_description(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["[download] Destination: video.mp4", "[DONE]"])
            mock_popen.return_value = mock_proc

            payload = {
                "url": "https://www.youtube.com/watch?v=video1",
                "format": "mp4",
                "output_dir": DOWNLOAD_FOLDER,
                "cookies_path": "",
                "download_options": {
                    "description": True,
                    "comments": False,
                    "info_json": False,
                    "subtitles": False,
                    "thumbnail": False
                },
                "custom_flags": []
            }
            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)

            called_args = mock_popen.call_args[0][0]
            self.assertIn('--write-description', called_args)
            self.assertIn('--embed-metadata', called_args)

    def test_write_comments(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["[download] Destination: video.mp4", "[DONE]"])
            mock_popen.return_value = mock_proc

            payload = {
                "url": "https://www.youtube.com/watch?v=video2",
                "format": "mp4",
                "output_dir": DOWNLOAD_FOLDER,
                "cookies_path": "",
                "download_options": {
                    "description": False,
                    "comments": True,
                    "info_json": False,
                    "subtitles": False,
                    "thumbnail": False
                },
                "custom_flags": []
            }
            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)

            called_args = mock_popen.call_args[0][0]
            self.assertIn('--write-comments', called_args)

    def test_embed_info_json_used_with_write_info_json(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["[download] Destination: video.mp4", "[DONE]"])
            mock_popen.return_value = mock_proc

            payload = {
                "url": "https://www.youtube.com/watch?v=video3",
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

            called_args = mock_popen.call_args[0][0]
            self.assertIn('--write-info-json', called_args)
            self.assertIn('--embed-info-json', called_args)

    def test_embed_subs_used_with_write_subs(self):
        with patch('app.subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["[download] Destination: video.mp4", "[DONE]"])
            mock_popen.return_value = mock_proc

            payload = {
                "url": "https://www.youtube.com/watch?v=video4",
                "format": "mp4",
                "output_dir": DOWNLOAD_FOLDER,
                "cookies_path": "",
                "download_options": {
                    "description": False,
                    "comments": False,
                    "info_json": False,
                    "subtitles": True,
                    "thumbnail": False
                },
                "custom_flags": []
            }
            response = self.client.post('/start_download', json=payload)
            self.assertEqual(response.status_code, 200)

            called_args = mock_popen.call_args[0][0]
            self.assertIn('--write-subs', called_args)
            self.assertIn('--write-auto-subs', called_args)
            self.assertIn('--embed-subs', called_args)

if __name__ == '__main__':
    unittest.main()
