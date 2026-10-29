import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url=os.getenv(
        "NVIDIA_BASE_URL",
        "https://integrate.api.nvidia.com/v1",
    ),
    timeout=60.0,
)

MODEL = os.getenv(
    "NVIDIA_MODEL",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
)


def generate_answer(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You answer airline information questions using only the supplied "
                    "document context. Do not invent facts or provide information about "
                    "live flights, bookings, or seat availability unless the context "
                    "contains it. Answer each part, identify missing information, and "
                    "cite only the source and page metadata shown in the context."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.2,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError("The LLM returned an empty answer.")

    return answer.strip()
