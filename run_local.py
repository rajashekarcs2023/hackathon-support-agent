"""Local terminal chatbot: type in the terminal, get QA engine responses."""

from env import config, require_env
from qa_engine.engine import QAEngine


def main() -> None:
    require_env()
    qa = QAEngine(openai_api_key=config.OPENAI_API_KEY)
    print("Local chatbot (subject: the sun). Type 'quit' or 'exit' to stop.\n")
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
        response = qa.answer(user_input)
        print(f"Bot: {response}\n")


if __name__ == "__main__":
    main()
