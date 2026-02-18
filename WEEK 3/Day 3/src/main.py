"""Minimal LangChain app that replies to a hello message."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


def main() -> int:
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        print("Missing OPENAI_API_KEY. Add it to your environment or .env file.")
        return 1

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = model.invoke(
        [
            SystemMessage(content="Reply in one short, friendly sentence."),
            HumanMessage(content="hello"),
        ]
    )

    print("User: hello")
    print(f"Assistant: {response.content}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
