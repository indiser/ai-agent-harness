import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding= "utf-8")
import os
import asyncio
from contextlib import AsyncExitStack
import json
from pathlib import Path
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    base_url = "https://openrouter.ai/api/v1",
    api_key = os.environ.get("OPENROUTER_API_KEY")
)
MODEL = os.environ.get("AI_MODEL")

WORKSPACE = Path(__file__).parent/"workspace"
os.makedirs(WORKSPACE, exist_ok=True)

MEMORY_FILE = Path(__file__).parent/"memory.md"

def safe_path(filename: str) -> Path:
    path = (WORKSPACE / filename).resolve()
    if not path.is_relative_to(WORKSPACE.resolve()):
        raise ValueError("path outside workspace")
    return path

def load_memory() -> str:
    if MEMORY_FILE.is_file():
        return MEMORY_FILE.read_text(encoding="utf-8")
    return "(nothing saved yet)"

def save_memory(fact: str) -> str:
    with MEMORY_FILE.open("a", encoding="utf-8") as filp:
        filp.write(f"- {fact}\n")
    return f"saved: {fact}"

MCP_SERVERS = {
    "time": StdioServerParameters(command="uvx", args = ["mcp-server-time"]),
    "fetch": StdioServerParameters(command="uvx", args = ["mcp-server-fetch"]),
}
# File Look Up
def list_files() -> str:
    return "\n".join(p.name for p in WORKSPACE.iterdir()) or "(empty)"

# Read Files
def read_file(filename: str) -> str:
    path = safe_path(filename)
    if not path.is_file():
        return f"error: no file named {filename}"
    return path.read_text(encoding="utf-8")

def write_file(filename: str, contents: str) -> str:
    safe_path(filename=filename).write_text(contents, encoding="utf-8")
    return f"wrote: {filename}"

LOCAL_TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "save_memory": save_memory
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
        {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create a new file in the workspace, or overwrite an existing one. "
                "Writes full contents as UTF-8 text. Existing content is replaced, not appended, "
                "so call read_file first if you need to keep or edit old content. "
                "Use for saving notes, summaries, code, or any text output the user wants stored. "
                "Returns 'wrote: <filename>' on success."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of file to write, e.g. 'summary.md'. Include extension. No directory paths.",
                    },
                    "contents": {
                        "type": "string",
                        "description": "Full text to write into file. Replaces any existing content.",
                    },
                },
                "required": ["filename", "contents"],
            },
        },
    },
        {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": (
                "Save one lasting fact about the user to persistent memory, appended to memory.md. "
                "Use for stable info: name, job, preferences, goals, ongoing projects. "
                "Do NOT save temporary info, small talk, or facts already in memory. "
                "Write fact as one short self-contained sentence, e.g. 'User prefers Python over JavaScript.' "
                "Returns 'saved: <fact>' on success."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "One short sentence stating the fact about the user.",
                    }
                },
                "required": ["fact"],
            },
        },
    },
]

SYSTEM_PROMPT = """
You are a helpful personal assistant.

Here is what you remember about the user from previous sessions:
{memory}

When you learn a new lasting fact about the user, save it with save_memory.
"""
mcp_session: dict[str, ClientSession] = {}

async def connect_mcp(stack: AsyncExitStack):
    for name, params in MCP_SERVERS.items():
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        tools = (await session.list_tools()).tools
        for tool in tools:
            mcp_session[tool.name] = session
            TOOL_SCHEMAS.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
            )
        print(f" [mcp] connected: {name}: {[t.name for t in tools]}")

async def call_tool(name: str, args: dict) -> str:
    if name in LOCAL_TOOLS:
        return LOCAL_TOOLS[name](**args)
    result = await mcp_session[name].call_tool(name, args)
    return "\n".join(c.text for c in result.content if hasattr(c, "text"))


async def run_agent(messages: list) -> str:
        
    while True:
        response = await client.chat.completions.create(
            model=MODEL,
            messages= messages,
            tools=TOOL_SCHEMAS
        )
    
        message = response.choices[0].message
    
        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content})
            return message.content or ""
    
        messages.append(message)
    
        for call in message.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
                print(f" [tool] {call.function.name}({args})")
                result = await call_tool(call.function.name, args)
            except Exception as e:
                result = f"error: {e}"
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )

async def main():
    async with AsyncExitStack() as stack:
        await connect_mcp(stack)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(memory=load_memory())}
        ]
        print(f"\nAssitant 4 ({MODEL}) with {len(TOOL_SCHEMAS)} tools")
        try:
            while True:
                messages.append({"role": "user", "content": input("\nyou: ")})
                print(f"\nAssistant: {await run_agent(messages)}")
        except (EOFError, KeyboardInterrupt):
                print("\nbye")

if __name__ == "__main__":
    asyncio.run(main())