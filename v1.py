import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding= "utf-8")
import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url = "https://openrouter.ai/api/v1",
    api_key = os.environ.get("OPENROUTER_API_KEY")
)
MODEL = os.environ.get("AI_MODEL")

WORKSPACE = Path(__file__).parent/"workspace"
os.makedirs(WORKSPACE, exist_ok=True)

# File Look Up
def list_files() -> str:
    return "\n".join(p.name for p in WORKSPACE.iterdir()) or "(empty)"

# Read Files
def read_file(filename: str) -> str:
    path = WORKSPACE / filename
    if not path.is_file():
        return f"error: no file named {filename}"
    return path.read_text(encoding="utf-8")

TOOLS = {
    "list_files": list_files,
    "read_file": read_file
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List all file names in the workspace directory. "
                "Call this first when you don't know which files exist, "
                "or before read_file to get the exact filename. "
                "Returns one filename per line, or '(empty)' if workspace has no files."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read full text content of one file in the workspace. "
                "Use exact filename as returned by list_files, including extension. "
                "Text files only (UTF-8). Returns file content, "
                "or a string starting with 'error:' if file does not exist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Exact name of file to read, e.g. 'notes.txt'. No directory paths.",
                    }
                },
                "required": ["filename"],
            },
        },
    },
]

def chat(user_messege: str) -> str:
    messages=[
        {"role": "system", "content": "You are a helpful ai assistant"},
        {"role": "user", "content": user_messege},
    ]
    
    response = client.chat.completions.create(
        model=MODEL,
        messages= messages,
        tools=TOOL_SCHEMAS
    )

    message = response.choices[0].message

    if not message.tool_calls:
        return message.content or ""

    messages.append(message)

    for call in message.tool_calls:
        args = json.loads(call.function.arguments or "{}")
        print(f" [tool] {call.function.name}({args})")
        result = TOOLS[call.function.name](**args)
        messages.append(
            {"role": "tool", "tool_call_id": call.id, "content": result}
        )
    final = client.chat.completions.create(model=MODEL, messages=messages)
    return final.choices[0].message.content


if __name__ == "__main__":
    print(f"Assist ({MODEL})")
    try:
        while True:
            question = input("\nyou:")
            print(f"\nAssistant: {chat(question)}")
    except (EOFError, KeyboardInterrupt):
        print("\nbye")