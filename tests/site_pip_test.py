"""Headful Chrome: one click opens the floating window, the game is chosen from inside it, translations appear in it.
Run with a display (xvfb):  DISPLAY=:97 python tests/site_pip_test.py"""
import asyncio, base64, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import site_test as T
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"], headless=False)
        ctx = await b.new_context(viewport={"width": 1280, "height": 900})
        for pat, fn in (("**/translate.googleapis.com/**", T.fake_google), ("**/api.mymemory.translated.net/**", T.fake_mm),
                        ("**/cdn.jsdelivr.net/**", T.local_cdn), ("**/tessdata.projectnaptha.com/**", T.local_cdn),
                        ("**/fonts.googleapis.com/**", T.local_fonts), ("**/fonts.gstatic.com/**", T.local_fonts)):
            await ctx.route(pat, fn)
        pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script("sessionStorage.setItem('ag_intro','1')")
        await pg.goto((T.ROOT / "site/index.html").as_uri()); await pg.wait_for_timeout(800)
        d1 = base64.b64encode(open("/tmp/game_dialogue.png", "rb").read()).decode()
        await pg.evaluate("""([a])=>{const cv=document.createElement('canvas');cv.width=1920;cv.height=1080;const x=cv.getContext('2d');
          const i=new Image();i.onload=()=>x.drawImage(i,0,0);i.src='data:image/png;base64,'+a;
          setInterval(()=>{x.fillStyle='rgba(0,0,0,0.01)';x.fillRect(0,0,1,1)},200);
          navigator.mediaDevices.getDisplayMedia=async()=>{if(!navigator.userActivation.isActive)throw new DOMException('no activation','InvalidStateError');return cv.captureStream(5)}}""", [d1])
        await pg.click(".mode[data-m=live]")
        print("start button visible:", await pg.is_visible("#lvGo"))
        newp = asyncio.get_event_loop().create_future()
        ctx.on("page", lambda q: newp.done() or newp.set_result(q))
        await pg.click("#lvGo")
        pip = await asyncio.wait_for(newp, 8); await pip.wait_for_timeout(500)
        print("floating window opened:", await pip.evaluate("!!document.getElementById('pick')"))
        await pip.click("#pick")
        await pg.wait_for_function("document.querySelectorAll('#lvLast li').length>=1", timeout=120000)
        await pip.wait_for_timeout(800)
        txt = await pip.evaluate("document.getElementById('p').textContent")
        st = await pip.evaluate("[document.getElementById('st').textContent, document.getElementById('pick').hidden, !document.getElementById('v').hidden]")
        print("floating window text:", txt[:80], "| status/pick hidden/preview:", st)
        await pip.screenshot(path="/tmp/pip.png")
        ok = "lighthouse" in txt.lower() and st[1] and st[2] and not errs
        print("errors:", errs); print("ALL OK" if ok else "FAIL")
        await b.close()

asyncio.run(main())
