"""Website live mode: dialogue lines that change every few seconds over a picture that never stops moving."""
import asyncio
import sys

from playwright.async_api import async_playwright

import site_test as T

LINES = ["The bridge is out.", "Take the north road.", "Hurry, they are coming!", "Hide behind the wagon.", "Now run to the gate!"]
SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 2.5


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1366, "height": 860})
        for pat, fn in (("**/translate.googleapis.com/**", T.fake_google), ("**/api.mymemory.translated.net/**", T.fake_mm),
                        ("**/cdn.jsdelivr.net/**", T.local_cdn), ("**/tessdata.projectnaptha.com/**", T.local_cdn),
                        ("**/fonts.googleapis.com/**", T.local_fonts), ("**/fonts.gstatic.com/**", T.local_fonts)):
            await ctx.route(pat, fn)
        pg = await ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script("sessionStorage.setItem('ag_intro','1')")
        await pg.goto((T.ROOT / "site/index.html").as_uri() + "#tr")
        await pg.wait_for_timeout(800)
        await pg.evaluate("""([lines, secs])=>{
          const c=document.createElement('canvas');c.width=1280;c.height=720;const g=c.getContext('2d');
          window.__t0=performance.now()+2500;window.__shown={};
          setInterval(()=>{const t=(performance.now()-__t0)/1000;
            const gr=g.createLinearGradient(0,0,0,720);gr.addColorStop(0,'hsl('+(220+20*Math.sin(t))+',50%,25%)');gr.addColorStop(1,'hsl('+(20+10*Math.sin(t*1.3))+',40%,30%)');
            g.fillStyle=gr;g.fillRect(0,0,1280,720);
            for(let i=0;i<8;i++){g.fillStyle='rgba(255,255,255,'+(.06+.05*Math.sin(t*2+i))+')';g.fillRect(((t*140+i*170)%1400)-100,80+i*40,160,22)}
            g.fillStyle='#f0dca0';g.beginPath();g.arc(((t*80)%1400)-60,120,50,0,7);g.fill();
            const k=Math.floor(t/secs);const ln=(t>0&&k<lines.length)?lines[k]:'';
            if(ln){g.font='bold 40px Arial';const w=g.measureText(ln).width;g.fillStyle='#0b0e1c';g.fillRect(640-w/2-30,560,w+60,80);g.fillStyle='#fff';g.fillText(ln,640-w/2,614)}
          },66);
          navigator.mediaDevices.getDisplayMedia=async()=>c.captureStream(15);}""", [LINES, SECS])
        await pg.click(".mode[data-m=live]")
        await pg.click("#lvScreen")
        await pg.wait_for_timeout(int((2.5 + SECS * len(LINES) + 4) * 1000))
        got = await pg.evaluate("[...document.querySelectorAll('#lvLast li small')].map(x=>x.textContent).concat(JSON.parse(localStorage.getItem('ag_hist')||'[]').map(h=>h.source||''))")
        hit = [l for l in LINES if any(l.rstrip(".!").lower() in g.lower() for g in got)]
        print(f"{SECS}s per line, moving scene: translated {len(hit)}/{len(LINES)}", hit, "| errors:", errs)
        await b.close()
        sys.exit(0 if len(hit) == len(LINES) and not errs else 1)


asyncio.run(main())
