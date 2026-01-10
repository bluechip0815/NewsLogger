import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import os

# Add src to path so we can import test_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src import test_utils

class TestAIConfigLogic(unittest.TestCase):
    def setUp(self):
        # Sample subscriptions configuration with aliases
        self.subscriptions = [
            {
                "channel_name": "OpenAI Channel",
                "provider": "openai",
                "model": "gpt-4-turbo"
            },
            {
                "channel_name": "Google Channel",
                "provider": "google",
                "model": "gemini-1.5-pro"
            },
            {
                "channel_name": "Gemini Alias Channel",
                "provider": "gemini",
                "model": "gemini-flash-lite-latest"
            },
             {
                "channel_name": "ChatGPT Alias Channel",
                "provider": "chatgpt",
                "model": "gpt-3.5-turbo"
            },
            {
                "channel_name": "Anthropic Channel",
                "provider": "anthropic",
                "model": "claude-3-opus"
            },
            {
                "channel_name": "Claude Alias Channel",
                "provider": "claude",
                "model": "claude-3-sonnet"
            }
        ]

    @patch('src.test_utils.genai')
    @patch('src.test_utils.openai')
    @patch('src.test_utils.anthropic')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_ai_connections_logic(self, mock_stdout, mock_anthropic, mock_openai, mock_genai):
        # Mock Environment variables
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "fake_gemini",
            "OPENAI_API_KEY": "fake_openai",
            "ANTHROPIC_API_KEY": "fake_anthropic"
        }):
            # Mock successful responses
            # OpenAI
            mock_openai_client = MagicMock()
            mock_openai.OpenAI.return_value = mock_openai_client
            mock_openai_client.chat.completions.create.return_value.choices[0].message.content = "OK"

            # Google
            mock_genai_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_genai_model
            mock_genai_model.generate_content.return_value = "OK"

            # Anthropic
            mock_anthropic_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_anthropic_client
            mock_anthropic_client.messages.create.return_value.content = [MagicMock(text="OK")]

            test_utils.test_ai_connections(self.subscriptions)

            output = mock_stdout.getvalue()

            # Verify explicit providers
            self.assertIn("gpt-4-turbo", output)
            self.assertIn("gemini-1.5-pro", output)
            self.assertIn("claude-3-opus", output)

            # Verify Aliases
            self.assertIn("gemini-flash-lite-latest", output) # Should be tested under 'google' logic
            self.assertIn("gpt-3.5-turbo", output) # Should be tested under 'openai' logic
            self.assertIn("claude-3-sonnet", output) # Should be tested under 'anthropic' logic

            # Verify calls

            # Google/Gemini calls
            # Expect 2 calls: one for 'gemini-1.5-pro' and one for 'gemini-flash-lite-latest'
            mock_genai.GenerativeModel.assert_any_call('gemini-1.5-pro')
            mock_genai.GenerativeModel.assert_any_call('gemini-flash-lite-latest')

            # OpenAI/ChatGPT calls
            # Expect 2 calls
            mock_openai_client.chat.completions.create.assert_any_call(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": "Hello"}]
            )
            mock_openai_client.chat.completions.create.assert_any_call(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}]
            )

            # Anthropic/Claude calls
            mock_anthropic_client.messages.create.assert_any_call(
                 model="claude-3-opus",
                 max_tokens=100,
                 messages=[{"role": "user", "content": "Hello"}]
            )
            mock_anthropic_client.messages.create.assert_any_call(
                 model="claude-3-sonnet",
                 max_tokens=100,
                 messages=[{"role": "user", "content": "Hello"}]
            )


if __name__ == '__main__':
    unittest.main()
