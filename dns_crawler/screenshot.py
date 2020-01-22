from pyppeteer.errors import PageError


def get_coverage_bytes(coverage):
    total = 0
    used = 0
    for entry in coverage:
        total += len(entry["text"])
        for range in entry["ranges"]:
            used += range["end"] - range["start"] - 1
    return [used, total]


async def get_browser_info(domain, web_results, browser):
    page = await browser.newPage()
    await page.setViewport({
        "width": 1280,
        "height": 960
    })
    await page.coverage.startJSCoverage()
    await page.coverage.startCSSCoverage()
    try:
        await page.goto(f"http://www.{domain}/", {
            "waitUntil": "networkidle2"
        })
    except PageError as e:
        return {
            "error": str(e)
        }
    dom = await page.evaluate("document.documentElement.outerHTML")
    await page.screenshot({"path": f"{domain}.png"})
    cookies = await page.cookies()
    js_coverage = await page.coverage.stopJSCoverage()
    css_coverage = await page.coverage.stopCSSCoverage()
    await page.close()

    return {
        "dom": dom,
        "cookies": cookies,
        "bytes_used": {
            "js": get_coverage_bytes(js_coverage),
            "css": get_coverage_bytes(css_coverage)
        }
    }
