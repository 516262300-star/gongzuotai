import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import erp_desktop_auth as auth


class DesktopAuthTests(unittest.TestCase):
    def setUp(self):
        auth._cookies = None

    def test_cookie_domains_do_not_match_unrelated_sites(self):
        for domain in ('ldswj.net', '.ldswj.net', 'app.ldswj.net'):
            self.assertTrue(auth.is_erp_cookie({'domain': domain}))
        for domain in ('evil-ldswj.net', 'ldswj.net.evil.test', '', 'pinduoduo.com'):
            self.assertFalse(auth.is_erp_cookie({'domain': domain}))

    def test_login_detection_allows_protected_profile(self):
        self.assertFalse(auth.is_login_page('<a onclick="logout()">退出</a>', auth.PROFILE_URL))
        self.assertTrue(auth.is_login_page('<input name="password">', auth.PROFILE_URL))
        self.assertTrue(auth.is_login_page('', 'https://ldswj.net/leedis/index.php/welcome/loginpage'))

    def test_client_failure_never_uses_browser_or_password_fallback(self):
        with patch.object(auth, 'client_action', side_effect=auth.DesktopLoginRequired('not logged in')), patch.object(auth, '_read_browser_cookies', new_callable=AsyncMock) as read:
            with self.assertRaises(auth.DesktopLoginRequired):
                auth.get_client_cookies(force=True)
            read.assert_not_called()
            self.assertIsNone(auth._cookies)

    def test_refresh_replaces_cache_and_returns_independent_copy(self):
        first = [{'name': 'session', 'value': 'synthetic-one', 'domain': 'ldswj.net'}]
        second = [{'name': 'session', 'value': 'synthetic-two', 'domain': 'ldswj.net'}]
        with patch.object(auth, 'client_action') as command, patch.object(auth, '_read_browser_cookies', new_callable=AsyncMock, side_effect=[first, second]):
            result = auth.get_client_cookies()
            result[0]['value'] = 'mutated'
            self.assertEqual(auth.get_client_cookies()[0]['value'], 'synthetic-one')
            self.assertEqual(auth.get_client_cookies(force=True)[0]['value'], 'synthetic-two')
            self.assertEqual(command.call_count, 1)

    def test_sync_adapter_can_run_inside_playwright_event_loop(self):
        async def run():
            return auth.get_client_cookies()
        with patch.object(auth, 'client_action'), patch.object(auth, '_read_browser_cookies', new_callable=AsyncMock, return_value=[{'name': 'x'}]):
            self.assertEqual(asyncio.run(run()), [{'name': 'x'}])

    def test_force_failure_discards_previous_cache(self):
        auth._cookies = [{'name': 'old'}]
        with patch.object(auth, 'client_action', side_effect=auth.DesktopLoginRequired('expired')):
            with self.assertRaises(auth.DesktopLoginRequired):
                auth.get_client_cookies(force=True)
        self.assertIsNone(auth._cookies)

    def test_client_result_errors_are_not_echoed(self):
        def command(args, **kwargs):
            Path(args[-1]).write_text(json.dumps({'ok': False, 'message': 'private detail'}), encoding='utf-8')
            return Mock(returncode=1)
        with patch.object(auth, 'client_executable', return_value=Path('client.exe')), patch.object(auth.subprocess, 'run', side_effect=command):
            with self.assertRaises(auth.DesktopLoginRequired) as result:
                auth.client_action('open')
        self.assertNotIn('private detail', str(result.exception))


if __name__ == '__main__':
    unittest.main()
