from __future__ import annotations

try:
    from .graph import run_operational_graph
    from .run_agent import main as run_insights_main
except ImportError:
    from graph import run_operational_graph
    from run_agent import main as run_insights_main


def answer_operational_question(question: str) -> dict:
    return run_operational_graph(question)


def main() -> None:
    run_insights_main()


if __name__ == "__main__":
    main()
