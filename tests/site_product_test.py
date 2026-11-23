"""Browser test of the product page (first tab): it is the default view, the explainer plays and replays,
the download buttons point at the latest release, and phones get no horizontal scroll."""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
DL = "https://github.com/msjtr/arabize-game/releases/latest/download/ArabizeGame-Windows.zip"


async def main():
    ok = True
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, vp, mob in [("desktop", {"width": 1366, "height": 860}, False), ("phone", {"width": 390, "height": 844}, True)]:
            ctx = await b.new_context(viewport=vp, is_mobile=mob, has_touch=mob)
            pg = await ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.add_init_script("sessionStorage.setItem('ag_intro','1')")
            await pg.goto((ROOT / "site/index.html").as_uri())
            await pg.wait_for_timeout(800)
            default = await pg.is_visible("#v-pr") and not await pg.is_visible("#v-tr")
            cap0 = await pg.text_content("#xpCap")
            await pg.wait_for_timeout(5900)
            cap1 = await pg.text_content("#xpCap")
            await pg.click("#xpPlay")
            paused = await pg.evaluate("document.getElementById('xp').classList.contains('paused')")
            await pg.click("#xpAgain")
            again = await pg.text_content("#xpCap") == cap0
            links = await pg.eval_on_selector_all("#v-pr a.btn:not(.ghost)", "a=>a.map(x=>x.href)")
            wide = await pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            await pg.click("#v-pr .pr-hero a[href='#tr']")
            await pg.wait_for_timeout(500)
            to_tr = await pg.is_visible("#v-tr")
            print(name, "default:", default, "| advances:", cap0 != cap1, "| paused:", paused, "| replay:", again,
                  "| downloads:", len(links), all(x == DL for x in links), "| no h-scroll:", wide, "| try in browser:", to_tr,
                  "| errors:", errs)
            ok &= default and cap0 != cap1 and paused and again and len(links) == 2 and all(x == DL for x in links) and wide and to_tr and not errs
            await ctx.close()
        await b.close()
    print("ALL OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


asyncio.run(main())
