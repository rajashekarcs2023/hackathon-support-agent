"""Local terminal chatbot: type in the terminal, get QA engine responses."""

import logging

from env import config, require_env
from qa_engine.engine import QAEngine


def _configure_logging() -> None:
    level = getattr(logging, config.LOG_LEVEL, logging.ERROR)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    _configure_logging()
    require_env()
    qa = QAEngine(openai_api_key=config.OPENAI_API_KEY)
    print("Hackathon Q&A bot. Type 'quit' or 'exit' to stop.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break
        response = qa.answer(user_input, session_id="local")
        print(f"Bot: {response}\n")


if __name__ == "__main__":
    main()
