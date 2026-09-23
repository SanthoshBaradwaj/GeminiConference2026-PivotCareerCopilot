import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()
        print("Navigating to http://localhost:8000...")
        await page.goto("http://localhost:8000")
        
        # Click the prompt button for readiness tiers
        print("Triggering career tier prompt...")
        await page.click("button:has-text('What roles am I actually ready for right now?')")
        
        # Wait for the card to render
        print("Waiting for A2UI card to render...")
        await page.wait_for_selector(".a2card", timeout=60000)
        
        # Give a moment for any styling / images to settle
        await page.wait_for_timeout(3000)
        
        screenshot_path = "assets/app_demo.jpg"
        print(f"Saving screenshot to {screenshot_path}...")
        await page.screenshot(path=screenshot_path, type="jpeg", quality=90)
        print("Screenshot successfully captured!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
