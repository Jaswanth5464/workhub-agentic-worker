import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import asyncio
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def main():
    print("Opening visible Chromium browser window on your desktop...")
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=False,
        slow_mo=200,
        args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
    )
    context = await browser.new_context(viewport=None)
    page = await context.new_page()
    await page.goto("http://localhost:3000/index.html")
    print("Chromium window is active and loaded http://localhost:3000/index.html")
    await asyncio.sleep(5)
    await browser.close()
    await p.stop()
    print("Chromium window closed.")

if __name__ == "__main__":
    asyncio.run(main())