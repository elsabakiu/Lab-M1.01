import os
import sys
import unittest
from pathlib import Path

# Allow importing sibling module when tests are run from repository root.
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from openai_production_client import ProductionOpenAIClient, read_openai_api_key


class TestProductionOpenAIClient(unittest.TestCase):
    def test_client_creation(self) -> None:
        """Test that a client object can be created."""
        client = ProductionOpenAIClient(api_key=read_openai_api_key())
        self.assertIsInstance(client, ProductionOpenAIClient)

    def test_openai_hello_message(self) -> None:
        """Test a real OpenAI call that returns a hello message."""
        client = ProductionOpenAIClient(api_key=read_openai_api_key())
        response = client.call("Say hello in one short sentence.")
        print("OpenAI response:", response)

        self.assertIsInstance(response, str)
        self.assertTrue(response.strip())
        self.assertIn("hello", response.lower())


if __name__ == "__main__":
    test_openai_hello_message = TestProductionOpenAIClient("test_openai_hello_message")
    test_openai_hello_message.setUp()
    unittest.main()

