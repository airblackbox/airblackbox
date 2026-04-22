"""Render devto-cover-v1.12.html to a PNG image using Playwright."""

from pathlib import Path
from playwright.sync_api import sync_playwright


def render_cover():
    html_path = Path(__file__).parent / "devto-cover-v1.12.html"
    png_path = Path(__file__).parent / "devto-cover-v1.12.png"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1400, "height": 1000},
            device_scale_factor=2,  # Retina resolution
        )
        page = context.new_page()
        page.goto(f"file://{html_path.resolve()}")
        page.wait_for_load_state("networkidle")

        # Screenshot only the .cover div for a tight crop
        cover_element = page.locator(".cover")
        cover_element.screenshot(path=str(png_path))

        browser.close()

    print(f"Rendered: {png_path}")
    print(f"Size: {png_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    render_cover()
