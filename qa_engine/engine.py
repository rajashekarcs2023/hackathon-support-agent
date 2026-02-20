"""QA engine: answers questions within a subject-matter scope."""

from openai import OpenAI

# Subject matter expertise (single scope for now)
SUBJECT_MATTER = "the sun"

DEFAULT_FALLBACK = "Unable to answer your question at this time"


class QAEngine:
    def __init__(self, openai_api_key: str):
        self._client = OpenAI(api_key=openai_api_key)

    def answer(self, question: str) -> str:
        r = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a helpful assistant who only answers questions about {SUBJECT_MATTER}.
If the user asks about any other topics, politely decline.""",
                },
                {"role": "user", "content": question},
            ],
            max_tokens=2048,
        )
        return str(r.choices[0].message.content)
