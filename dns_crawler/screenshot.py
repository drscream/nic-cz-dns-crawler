from pyppeteer.errors import TimeoutError, PageError, NetworkError
import asyncio


def get_coverage_bytes(coverage):
    total = 0
    used = 0
    for entry in coverage:
        total += len(entry["text"])
        for range in entry["ranges"]:
            used += range["end"] - range["start"] - 1
    return [used, total]


async def close_dialog(dialog):
    await dialog.dismiss()


async def get_browser_info(domain, web_results, dnssec_valid, browser):
    if (
        dnssec_valid is False
        or not web_results
        or all(v is None for v in web_results.values())
        or all("error" in i for v in web_results.values() if v for i in v if i)
    ):
        return None
    subdomain = ""
    if (
        web_results["WEB4_80_www"] or web_results["WEB6_80_www"]
        or web_results["WEB4_443_www"] or web_results["WEB6_443_www"]
    ):
        subdomain = "www."
    page = await browser.newPage()
    await page.setViewport({
        "width": 1280,
        "height": 960
    })
    # await page.evaluateOnNewDocument("window.open = () => null; setTimeout(()=>window.close(), 7000);")
    page.on(
        "dialog",
        lambda dialog: asyncio.ensure_future(close_dialog(dialog))
    )
    try:
        await asyncio.gather(
            page.goto(f"http://{subdomain}{domain}/", {
                "waitUntil": "networkidle2"
            }),
            page.waitForNavigation({
                "waitUntil": "networkidle2"
            })
        )
    except (TimeoutError, PageError, NetworkError) as e:
        return {
            "error": str(e)
        }

    await page.screenshot({"path": f"{domain}.png", "fullPage": True})

    # try:
    url = page.url
    # dom = await page.evaluate("document.documentElement.outerHTML")
    # except (PageError, TimeoutError, NetworkError):
    #     dom = None

    # try:
    # cookies = await page.cookies()
    # except (PageError, TimeoutError, NetworkError):
    #     cookies = None

    # try:
    # metrics = await page.metrics()
    # except (PageError, TimeoutError, NetworkError):
    #     metrics = None

    # if not page.isClosed() and page._client._connection:
    await page.close()
    # return
    return {
        "url": url,
        # "dom": dom,
        # "cookies": cookies,
        # "metrics": metrics
        #     # "bytes_used": {
        #     #     "js": get_coverage_bytes(js_coverage),
        #     #     "css": get_coverage_bytes(css_coverage)
        #     # }
    }
