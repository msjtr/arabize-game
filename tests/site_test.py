"""Browser test of the public site (site/index.html).

Translation services are simulated with their real response formats; the OCR library is served
from local npm copies (NPM env var) because CDNs may be unreachable in CI sandboxes.
Run:  NPM=/path/to/node_modules python tests/site_test.py
"""
import asyncio
import json
import os
import sys
import urllib.parse
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from gameshots import choices_scene, dialogue_scene  # noqa: E402

NPM = Path(os.environ.get("NPM", "/tmp/tnpm/node_modules"))
AR = {"Press start to continue": "اضغط ابدأ للمتابعة", "Open the gate": "افتح البوابة"}
state = {"google_fail": False, "google": 0, "mymemory": 0}


async def fake_google(route):
    state["google"] += 1
    if state["google_fail"]:
        return await route.fulfill(status=503, body="busy")
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(route.request.url).query))
    out = "\n".join(AR.get(x, "ع:" + x) if x else x for x in q["q"].split("\n"))
    await route.fulfill(status=200, content_type="application/json",
                        headers={"access-control-allow-origin": "*"},
                        body=json.dumps([[[out, q["q"], None, None, 10]], None, "en"], ensure_ascii=False))


async def fake_mm(route):
    state["mymemory"] += 1
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(route.request.url).query))
    await route.fulfill(status=200, content_type="application/json", headers={"access-control-allow-origin": "*"},
                        body=json.dumps({"responseData": {"translatedText": "م:" + q["q"], "detectedLanguage": "en"},
                                         "responseStatus": 200}, ensure_ascii=False))


async def local_cdn(route):
    url = route.request.url
    name = url.split("?")[0].rsplit("/", 1)[-1]
    if "traineddata" in url:
        path = NPM / "@tesseract.js-data/eng/4.0.0_best_int/eng.traineddata.gz"
    elif "tesseract.js-core" in url:
        path = NPM / "tesseract.js-core" / name
    else:
        path = NPM / "tesseract.js/dist" / name
    if not path.exists():
        return await route.fulfill(status=404, body="missing " + name)
    ctype = "application/wasm" if name.endswith(".wasm") else "application/javascript" if name.endswith(".js") else "application/octet-stream"
    await route.fulfill(status=200, body=path.read_bytes(), content_type=ctype, headers={"access-control-allow-origin": "*"})


FONT_DIR = ROOT / "arabize/assets/fonts"
FONT_CSS = "".join(
    f"@font-face{{font-family:'{fam}';font-weight:{w};src:url(https://fonts.gstatic.com/local/{f}) format('truetype')}}"
    for fam, w, f in [("Alexandria", 700, "Alexandria-Bold.ttf"), ("Alexandria", 500, "Alexandria-Bold.ttf"),
                      ("IBM Plex Sans Arabic", 400, "IBMPlexSansArabic-Regular.ttf"), ("IBM Plex Sans Arabic", 500, "IBMPlexSansArabic-Medium.ttf"),
                      ("IBM Plex Sans Arabic", 700, "IBMPlexSansArabic-Bold.ttf"), ("Readex Pro", 700, "ReadexPro-Bold.ttf"),
                      ("Readex Pro", 500, "ReadexPro-Regular.ttf"), ("Tajawal", 700, "Tajawal-Bold.ttf"), ("Cairo", 700, "Cairo-Bold.ttf"),
                      ("Noto Naskh Arabic", 700, "NotoNaskhArabic-Bold.ttf")])


async def local_fonts(route):
    """Google Fonts stand-in: the same families, served from the app's bundled copies."""
    url = route.request.url
    if "fonts.googleapis.com" in url:
        return await route.fulfill(status=200, body=FONT_CSS, content_type="text/css", headers={"access-control-allow-origin": "*"})
    path = FONT_DIR / url.rsplit("/", 1)[-1]
    await route.fulfill(status=200, body=path.read_bytes(), content_type="font/ttf", headers={"access-control-allow-origin": "*"})


async def main():
    import PIL.Image
    img, _ = dialogue_scene()
    PIL.Image.fromarray(img[:, :, ::-1]).save("/tmp/game_dialogue.png")
    img2, _ = choices_scene()
    PIL.Image.fromarray(img2[:, :, ::-1]).save("/tmp/game_choices.png")
    ok = True
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--allow-file-access-from-files"])
        for name, vp in (("mobile", (390, 844)), ("desktop", (1280, 900))):
            ctx = await b.new_context(viewport={"width": vp[0], "height": vp[1]})
            await ctx.route("**/translate.googleapis.com/**", fake_google)
            await ctx.route("**/api.mymemory.translated.net/**", fake_mm)
            await ctx.route("**/cdn.jsdelivr.net/**", local_cdn)
            await ctx.route("**/tessdata.projectnaptha.com/**", local_cdn)
            await ctx.route("**/fonts.googleapis.com/**", local_fonts)
            await ctx.route("**/fonts.gstatic.com/**", local_fonts)
            pg = await ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.add_init_script("sessionStorage.setItem('ag_intro','1')")
            await pg.goto((ROOT / "site/index.html").as_uri())
            await pg.wait_for_timeout(600)
            print(name, "engine chip:", await pg.text_content("#engine"))
            # --- text mode, Google
            await pg.click(".mode[data-m=text]")
            await pg.fill("#input", "Press start to continue\n\nOpen the gate")
            await pg.click("#tbtn")
            await pg.wait_for_function("!document.getElementById('tbtn').disabled", timeout=15000)
            out = await pg.input_value("#output")
            print(name, "text:", repr(out), "|", await pg.text_content("#status"))
            ok &= out == "اضغط ابدأ للمتابعة\n\nافتح البوابة"
            # --- Google down -> MyMemory
            state["google_fail"] = True
            await pg.fill("#input", "A brand new line of dialogue")
            await pg.click("#tbtn")
            await pg.wait_for_function("!document.getElementById('tbtn').disabled", timeout=20000)
            out2 = await pg.input_value("#output")
            print(name, "fallback:", repr(out2))
            ok &= out2.startswith("م:")
            state["google_fail"] = False
            # --- screenshot OCR in the browser
            await pg.click(".mode[data-m=shot]")
            await pg.set_input_files("#fileImg", "/tmp/game_dialogue.png")
            await pg.wait_for_function("document.getElementById('shotLabel').textContent==='أعد القراءة' || document.querySelector('#modal.on')", timeout=120000)
            await pg.wait_for_timeout(800)
            cards = await pg.evaluate("[...document.querySelectorAll('.bk')].map(c=>c.className.replace('bk ','')+' | '+(c.querySelector('.who')?c.querySelector('.who').textContent:'')+' | '+c.querySelector('.og').textContent)")
            print(name, "ocr cards:", cards)
            print(name, "status:", await pg.text_content("#status"), "| boxes:", await pg.evaluate("document.querySelectorAll('.bx').length"))
            ok &= any("lighthouse" in c.lower() for c in cards) and any("dawn" in c.lower() for c in cards)
            await pg.wait_for_timeout(600)
            layer = await pg.evaluate("[document.getElementById('lyQuest').classList.contains('on'), document.getElementById('lyQuest').textContent, document.getElementById('pInfo').textContent]")
            print(name, "quest layer:", layer)
            if name == "desktop":       # wide screens: quest in its own layer
                ok &= layer[0] and "lighthouse" in layer[1].lower() and layer[2] == "1 / 1"
            else:                       # phones: no room for side layers, everything plays as subtitles
                ok &= not layer[0] and layer[2] == "1 / 2"
            await pg.evaluate("document.getElementById('cinema').scrollIntoView()")
            await pg.wait_for_timeout(1500)
            await (await pg.query_selector("#cinema")).screenshot(path=f"/tmp/site-{name}-cinema.png")
            await pg.screenshot(path=f"/tmp/site-{name}-shot.png")
            await pg.set_input_files("#fileImg", "/tmp/game_choices.png")
            await pg.wait_for_function("document.querySelectorAll('.bk.choice li').length>0", timeout=120000)
            await pg.wait_for_timeout(500)
            print(name, "choices:", await pg.evaluate("[...document.querySelectorAll('.bk.choice li .og')].map(x=>x.textContent)"))
            # --- appearance: 3D icons, fonts, templates
            fam = await pg.evaluate("document.fonts.check('700 20px \"Alexandria\"') && document.fonts.check('16px \"IBM Plex Sans Arabic\"')")
            tiles = await pg.evaluate("document.querySelectorAll('.i3d svg rect').length")
            print(name, "fonts loaded:", fam, "| 3D tile layers:", tiles)
            ok &= fam and tiles > 20
            await pg.evaluate("location.hash='#sc'")
            await pg.wait_for_timeout(700)
            n_tpl = await pg.evaluate("document.querySelectorAll('#tpls .tpl').length")
            # Arabic words animated one by one must still read right-to-left
            await pg.click("#subAnimC button[data-k=rise]")
            await pg.wait_for_timeout(1500)
            order = await pg.evaluate("(()=>{const w=[...document.querySelectorAll('#miniSub .w')];return w.length>1?w[0].getBoundingClientRect().right>w[w.length-1].getBoundingClientRect().right:null})()")
            print(name, "arabic word order right-to-left:", order)
            ok &= order is True
            await pg.click("#tpls .tpl[data-id=tv]")
            await pg.wait_for_timeout(900)
            st = await pg.evaluate("[getComputedStyle(document.getElementById('miniSub')).fontFamily, document.getElementById('miniSub').dataset.bg, JSON.parse(localStorage.getItem('ag_set')).tpl]")
            print(name, "templates:", n_tpl, "| after TV:", st)
            ok &= n_tpl == 8 and "Readex Pro" in st[0] and st[1] == "bar" and st[2] == "tv"
            await pg.screenshot(path=f"/tmp/site-{name}-look.png", full_page=True)
            await pg.click("#tpls .tpl[data-id=dialogue]")
            await pg.wait_for_timeout(400)
            print(name, "errors:", errs)
            ok &= not errs
            await ctx.close()
        await b.close()
    print("ALL OK" if ok else "FAILURES")


if __name__ == "__main__":
    asyncio.run(main())
