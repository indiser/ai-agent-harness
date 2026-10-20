import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding= "utf-8")
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url = "https://openrouter.ai/api/v1",
    api_key = os.environ.get("OPENROUTER_API_KEY")
)
MODEL = os.environ.get("AI_MODEL")

def chat(user_messege: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful ai assistant"},
            {"role": "user", "content": user_messege},
        ],
    )
    return response.choices[0].message.content or ""

if __name__ == "__main__":
    print(f"Assist ({MODEL})")
    try:
        while True:
            question = input("\nyou:")
            print(f"\nAssistant: {chat(question)}")
    except (EOFError, KeyboardInterrupt):
        print("\nbye")