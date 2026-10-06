import sys
import asyncio
import uvicorn

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    from backend_agent import app
    uvicorn.run(app, host="127.0.0.1", port=8001, loop="asyncio")

