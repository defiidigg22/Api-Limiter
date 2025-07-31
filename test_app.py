import unittest
import time
from app import app, r # Import the app and redis client from your main file

class RateLimiterTestCase(unittest.TestCase):

    def setUp(self):
        """Set up a test client and clear Redis before each test."""
        self.app = app.test_client()
        self.app.testing = True
        # Clear all keys in the test Redis database to ensure a clean slate
        r.flushdb()

    def test_ping_success(self):
        """Test a single successful request."""
        response = self.app.get('/api/ping')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'pong', response.data)

    def test_free_tier_rate_limit(self):
        """Test that the free tier rate limit is enforced."""
        headers = {'X-API-Key': 'free_user_key_123'}
        limit = app.config["TIERS"]["FREE"]["limit"]

        # Make requests up to the limit, which should succeed
        for i in range(limit):
            response = self.app.get('/api/ping', headers=headers)
            self.assertEqual(response.status_code, 200)

        # The next request should be blocked
        response = self.app.get('/api/ping', headers=headers)
        self.assertEqual(response.status_code, 429)
        self.assertIn(b'Rate limit for FREE tier exceeded', response.data)

    def test_pro_tier_is_not_blocked_by_free_limit(self):
        """Test that the pro tier is not blocked by the free tier's limit."""
        free_headers = {'X-API-Key': 'free_user_key_123'}
        pro_headers = {'X-API-Key': 'pro_user_key_456'}
        limit = app.config["TIERS"]["FREE"]["limit"]

        # Exhaust the free tier limit
        for i in range(limit + 1):
            self.app.get('/api/ping', headers=free_headers)
        
        # A pro user should still be able to make a request
        response = self.app.get('/api/ping', headers=pro_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'PRO', response.data)


if __name__ == '__main__':
    unittest.main()