import asyncio
import os
import sys

env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v

from ai_worker_project.agent.llm import call_nvidia, call_groq, call_gemini

async def test_apis():
    messages = [{"role": "user", "content": "Say 'hello world' and nothing else."}]
    print("Testing NVIDIA...")
    try:
        res = await call_nvidia("You are a helpful assistant.", messages)
        print("NVIDIA SUCCESS:", res)
    except Exception as e:
        print("NVIDIA FAILED:", e)

    print("Testing Groq...")
    try:
        res = await call_groq("You are a helpful assistant.", messages)
        print("Groq SUCCESS:", res)
    except Exception as e:
        print("Groq FAILED:", e)

    print("Testing Gemini...")
    try:
        res = await call_gemini("You are a helpful assistant.", messages)
        print("Gemini SUCCESS:", res)
    except Exception as e:
        print("Gemini FAILED:", e)

if __name__ == "__main__":
    asyncio.run(test_apis())
