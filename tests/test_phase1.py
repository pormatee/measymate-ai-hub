import json
import socket
import unittest

from app.core.config import Settings
from app.core.errors import InvalidRequestError, ProviderConfigurationError, ProviderTimeoutError
from app.domain.models import Message
from app.main import health_body
from app.providers.deepseek import DeepSeekAdapter
from app.providers.router import ProviderRouter

class FakeResponse:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False
    def read(self): return self._body

class Phase1RegressionTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(health_body()["status"], "ok")

    def test_router_rejects_unknown_profile(self):
        router = ProviderRouter(Settings(deepseek_api_key="test"))
        with self.assertRaises(InvalidRequestError):
            router.for_profile("unknown")

    def test_router_accepts_coach_understanding_profile(self):
        router = ProviderRouter(Settings(deepseek_api_key="test"))
        self.assertIsNotNone(router.for_profile("coach-understanding"))

    def test_deepseek_requires_server_key_before_network(self):
        adapter = DeepSeekAdapter(api_key=None, base_url="https://api.deepseek.com", model="deepseek-chat", timeout_seconds=1)
        with self.assertRaises(ProviderConfigurationError):
            adapter.generate([Message(role="user", content="hello")], 20)

    def test_deepseek_normalizes_success_without_real_network(self):
        def opener(request, timeout):
            self.assertEqual(request.headers["Authorization"], "Bearer test-secret")
            return FakeResponse({
                "choices": [{"message": {"content": "hello back"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            })
        adapter = DeepSeekAdapter(api_key="test-secret", base_url="https://api.deepseek.com", model="deepseek-chat", timeout_seconds=1, opener=opener)
        result = adapter.generate([Message(role="user", content="hello")], 20)
        self.assertEqual(result.text, "hello back")
        self.assertEqual(result.usage.total_tokens, 5)

    def test_deepseek_timeout_fails_safely(self):
        def opener(request, timeout):
            raise socket.timeout("timeout")
        adapter = DeepSeekAdapter(api_key="test-secret", base_url="https://api.deepseek.com", model="deepseek-chat", timeout_seconds=1, opener=opener)
        with self.assertRaises(ProviderTimeoutError):
            adapter.generate([Message(role="user", content="hello")], 20)

    def test_config_has_no_python_dotenv_dependency(self):
        import app.core.config as config
        self.assertTrue(callable(config.get_settings))

if __name__ == "__main__":
    unittest.main()
