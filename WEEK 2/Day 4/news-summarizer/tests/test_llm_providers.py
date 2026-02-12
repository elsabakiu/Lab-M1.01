from __future__ import annotations

from types import SimpleNamespace

from news_summarizer.providers.llm_providers import LLMProviders


class FakeOpenAICompletions:
    def __init__(self, text: str = "OpenAI says hello.", should_fail: bool = False) -> None:
        self._text = text
        self._should_fail = should_fail

    def create(self, **_kwargs):
        if self._should_fail:
            raise RuntimeError("OpenAI unavailable")
        message = SimpleNamespace(content=self._text)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


class FakeOpenAIClient:
    def __init__(self, text: str = "OpenAI says hello.", should_fail: bool = False) -> None:
        completions = FakeOpenAICompletions(text=text, should_fail=should_fail)
        self.chat = SimpleNamespace(completions=completions)


class FakeCohereClient:
    def __init__(self, text: str = "Cohere says hello.") -> None:
        self._text = text

    def chat(self, **_kwargs):
        return SimpleNamespace(text=self._text)


def test_llm_providers_flow_like_module_example() -> None:
    """
    Covers the same flow as the original module example:
    1) OpenAI call
    2) Cohere call
    3) Fallback path
    4) Cost summary
    """
    providers = LLMProviders(
        openai_client=FakeOpenAIClient(text="Python is a high-level language."),
        cohere_client=FakeCohereClient(text="Python is an interpreted programming language."),
        sleep_fn=lambda _seconds: None,
    )

    openai_response = providers.ask_openai("What is Python? Answer in one sentence.")
    assert "Python" in openai_response

    cohere_response = providers.ask_cohere("What is Python? Answer in one sentence.")
    assert "Python" in cohere_response

    # Force fallback by swapping in a failing OpenAI fake.
    providers.openai_client = FakeOpenAIClient(should_fail=True)
    fallback_result = providers.ask_with_fallback(
        "What is machine learning? Answer in one sentence.",
        primary="openai",
    )
    assert fallback_result["provider"] == "cohere"
    assert fallback_result["response"]

    summary = providers.cost_tracker.get_summary()
    assert summary["total_requests"] == 3.0
    assert summary["total_cost"] > 0
