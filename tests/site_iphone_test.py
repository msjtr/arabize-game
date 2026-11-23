import asyncio, sys, base64
sys.path.insert(0,'/home/claude/arabize-game/tests')
import site_test as T
from playwright.async_api import async_playwright
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width":390,"height":844},device_scale_factor=2,is_mobile=True,has_touch=True,user_agent=UA)
        for pat,fn in (("**/translate.googleapis.com/**",T.fake_google),("**/api.mymemory.translated.net/**",T.fake_mm),("**/cdn.jsdelivr.net/**",T.local_cdn),
                       ("**/tessdata.projectnaptha.com/**",T.local_cdn),("**/fonts.googleapis.com/**",T.local_fonts),("**/fonts.gstatic.com/**",T.local_fonts)):
            await ctx.route(pat,fn)
        pg = await ctx.new_page(); errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script("sessionStorage.setItem('ag_intro','1')")
        await pg.goto((T.ROOT/"site/index.html").as_uri() + "#tr"); await pg.wait_for_timeout(800)
        await pg.click(".mode[data-m=live]"); await pg.wait_for_timeout(500)
        st = await pg.evaluate("[document.getElementById('lvScreen').hidden, document.getElementById('lvPhone').hidden, document.getElementById('lvCam').textContent.trim()]")
        print("screen hidden, phone hidden, cam label:", st)
        await pg.screenshot(path="/tmp/ios-live.png", full_page=True)
        d1 = base64.b64encode(open("/tmp/game_dialogue.png","rb").read()).decode()
        await pg.evaluate("""([a])=>{const cv=document.createElement('canvas');cv.width=1920;cv.height=1080;const x=cv.getContext('2d');
          const i=new Image();i.onload=()=>x.drawImage(i,0,0);i.src='data:image/png;base64,'+a;
          setInterval(()=>{x.fillStyle='rgba(0,0,0,0.01)';x.fillRect(0,0,1,1)},200);
          navigator.mediaDevices.getUserMedia=async()=>cv.captureStream(5);}""",[d1])
        await pg.click("#lvCam")
        await pg.wait_for_function("document.querySelectorAll('#lvLast li').length>=1", timeout=120000)
        print("camera live read:", (await pg.evaluate("document.querySelector('#lvLast li').textContent"))[:80], "| errors:", errs)
        await b.close()
asyncio.run(main())
