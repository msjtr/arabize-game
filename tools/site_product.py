"""Add the «البرنامج» product page (first tab, default view) built from the product spec:
explainer video, how it works, features, VR, learning, stability, download."""
import sys

P = sys.argv[1]
s = open(P, encoding="utf-8").read()


def rep(old, new, count=1):
    global s
    assert s.count(old) >= 1, old[:90]
    s = s.replace(old, new, count)


DL = "https://github.com/msjtr/arabize-game/releases/latest/download/ArabizeGame-Windows.zip"

# ------------------------------------------------------------------ extra icons
rep('  <symbol id="i-eye"',
    '  <symbol id="i-bolt" viewBox="0 0 24 24"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/></symbol>\n'
    '  <symbol id="i-shield" viewBox="0 0 24 24"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></symbol>\n'
    '  <symbol id="i-tv" viewBox="0 0 24 24"><rect width="20" height="15" x="2" y="3" rx="2"/><path d="M7 21h10"/><path d="M12 18v3"/></symbol>\n'
    '  <symbol id="i-grad" viewBox="0 0 24 24"><path d="M21.42 10.92a1 1 0 0 0-.02-1.84L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.83l8.57 3.91a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/></symbol>\n'
    '  <symbol id="i-eye"')

# ------------------------------------------------------------------ CSS
CSS = r'''
/* ===== product page ===== */
.pr{--gap:clamp(40px,7vw,84px)}
.pr section+section{margin-top:var(--gap)}
.pr h2{font-family:var(--display);font-size:clamp(22px,3.2vw,30px);line-height:1.35;margin:0 0 10px;color:var(--mist)}
.pr .lede{color:var(--muted);font-size:15.5px;line-height:1.9;max-width:62ch;margin:0}
.pr-hero{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:clamp(22px,4vw,48px);align-items:center}
.pr-hero .name{display:flex;align-items:center;gap:12px;color:var(--acc2);font-weight:700;font-size:15px;margin-bottom:14px}
.pr-hero .name .i3d{--s:40px;margin:0}
.pr-hero h1{font-family:var(--display);font-weight:700;font-size:clamp(30px,5vw,52px);line-height:1.3;margin:0 0 14px;color:#fff;text-wrap:balance}
.pr-hero p{color:var(--mist);opacity:.8;font-size:16.5px;line-height:1.9;margin:0 0 24px;max-width:44ch}
.pr-cta{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.pr-cta .btn{padding:13px 22px;font-size:15px;text-decoration:none}
.pr-cta .btn.ghost{text-decoration:none}
.pr-req{color:var(--muted);font-size:13px;margin-top:14px}
/* explainer video */
.xp{background:#05070f;border:1px solid var(--line2);border-radius:20px;overflow:hidden;box-shadow:0 30px 60px -30px rgba(0,0,0,.8),0 0 0 1px rgba(255,255,255,.02)}
.xp-stage{position:relative;aspect-ratio:16/9;overflow:hidden;background:radial-gradient(120% 90% at 70% 0%,#1b2350 0%,#0b0f24 55%,#05070f 100%)}
.xp-sc{position:absolute;inset:0;display:grid;place-items:center;opacity:0;transition:opacity .45s;pointer-events:none}
.xp-sc.on{opacity:1}
.xp-bar{display:flex;align-items:center;gap:12px;padding:12px 14px;border-top:1px solid var(--line)}
.xp-bar button{flex:none;display:grid;place-items:center;width:38px;height:38px;border-radius:50%;border:1px solid var(--line2);background:rgba(255,255,255,.05);color:var(--mist)}
.xp-bar button:hover{border-color:var(--acc);color:var(--acc2)}
.xp-bar .ic{width:17px;height:17px}
.xp-cap{flex:1;min-width:0}
.xp-cap b{display:block;font-size:14.5px;color:#fff}
.xp-segs{display:flex;gap:5px;margin-top:7px}
.xp-segs button{all:unset;cursor:pointer;flex:1;height:4px;border-radius:3px;background:rgba(255,255,255,.12);overflow:hidden;position:relative}
.xp-segs button i{position:absolute;inset:0;transform-origin:right;transform:scaleX(0);background:var(--acc)}
.xp-segs button.done i{transform:scaleX(1)}
.xp-segs button.on i{animation:segFill var(--dur,5.5s) linear forwards}
.xp.paused .xp-segs button.on i{animation-play-state:paused}
.xp-segs button:focus-visible{outline:2px solid var(--acc);outline-offset:3px}
.xp-bar .xp-again{flex:none;width:auto;height:auto;border:0;border-radius:8px;background:none;color:var(--acc2);font-weight:700;font-size:13px;padding:6px 4px;cursor:pointer;white-space:nowrap}
@keyframes segFill{to{transform:scaleX(1)}}
.xp.paused .xp-sc.on *{animation-play-state:paused!important}
/* scene 1: download */
.x-win{width:62%;background:#121734;border:1px solid var(--line2);border-radius:12px;padding:16px 18px;font-size:13px;color:var(--mist)}
.x-win .t{display:flex;align-items:center;gap:8px;margin-bottom:12px;direction:ltr;justify-content:flex-end;font-family:var(--latin)}
.x-win .t .ic{width:16px;height:16px;color:var(--acc)}
.x-prog{height:8px;border-radius:5px;background:rgba(255,255,255,.08);overflow:hidden}
.x-prog i{display:block;height:100%;width:100%;transform-origin:right;background:linear-gradient(90deg,var(--acc),var(--acc2))}
.on .x-prog i{animation:xFill 2.4s .3s cubic-bezier(.4,.1,.3,1) both}
.x-win .d{display:flex;justify-content:space-between;margin-top:10px;color:var(--muted);font-size:12px}
.x-ok{display:inline-flex;align-items:center;gap:6px;color:var(--ok);opacity:0}
.on .x-ok{animation:xPop .4s 2.8s both}
.x-ok .ic{width:15px;height:15px}
@keyframes xFill{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes xPop{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
/* scene 2: pick the game */
.x-list{width:62%;display:grid;gap:8px}
.x-row{display:flex;align-items:center;gap:10px;background:#121734;border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:13px;color:var(--muted)}
.x-row .ic{width:16px;height:16px}
.x-row span{flex:1;direction:ltr;text-align:right;font-family:var(--latin)}
.x-row.pick{color:#fff}
.on .x-row.pick{animation:xPick .5s 1s both}
@keyframes xPick{to{border-color:var(--acc);background:#1c2247;box-shadow:0 0 0 3px var(--glow)}}
.x-tg{width:38px;height:22px;border-radius:12px;background:rgba(255,255,255,.12);position:relative;flex:none}
.x-tg::after{content:"";position:absolute;top:3px;right:3px;width:16px;height:16px;border-radius:50%;background:#cfd5ee}
.on .x-row.pick .x-tg{animation:xTgB .3s 2.1s both}
.on .x-row.pick .x-tg::after{animation:xTgK .3s 2.1s both}
@keyframes xTgB{to{background:var(--ok)}}
@keyframes xTgK{to{right:19px;background:#fff}}
.x-live{justify-self:start;display:inline-flex;align-items:center;gap:7px;color:var(--ok);font-size:12.5px;font-weight:700;opacity:0}
.x-live i{width:8px;height:8px;border-radius:50%;background:var(--ok);box-shadow:0 0 8px var(--ok)}
.on .x-live{animation:xPop .4s 2.6s both}
/* scene 3 + 4: a game frame */
.x-game{position:absolute;inset:0;background:linear-gradient(180deg,#2a3a6e 0%,#3d3560 42%,#1a1430 43%,#0d0a1c 100%)}
.x-game::before{content:"";position:absolute;left:8%;right:8%;bottom:43%;height:24%;background:linear-gradient(90deg,transparent,#0d0a1c 15%,#0d0a1c 85%,transparent);clip-path:polygon(0 100%,10% 40%,22% 70%,36% 20%,50% 60%,64% 10%,78% 55%,90% 30%,100% 100%)}
.x-game::after{content:"";position:absolute;width:9%;aspect-ratio:1;border-radius:50%;top:12%;left:18%;background:radial-gradient(circle,#ffe7b0,#e7b964 60%,transparent 62%);filter:drop-shadow(0 0 18px #e7b96488)}
.x-en{position:absolute;bottom:7%;left:50%;transform:translateX(-50%);direction:ltr;font-family:var(--latin);font-size:clamp(11px,1.6vw,14px);color:#fff;background:rgba(0,0,0,.55);padding:5px 12px;border-radius:6px;white-space:nowrap}
.x-sub{position:absolute;left:50%;bottom:22%;transform:translateX(-50%);font-family:var(--display);font-weight:700;font-size:clamp(14px,2.4vw,22px);color:#fff;padding:7px 18px;border-radius:12px;background:rgba(10,14,31,.72);border:1px solid rgba(231,185,100,.45);white-space:nowrap;opacity:0;text-shadow:0 2px 8px #000}
.on .x-sub.s3{animation:xSubIn .5s .6s both,xSubMove 3.4s 1.6s cubic-bezier(.5,0,.3,1) both}
@keyframes xSubIn{from{opacity:0;transform:translate(-50%,10px)}to{opacity:1;transform:translateX(-50%)}}
@keyframes xSubMove{0%{bottom:22%;color:#fff;background:rgba(10,14,31,.72)}
  35%{bottom:66%;color:#fff;background:rgba(10,14,31,.72)}
  65%{bottom:66%;color:#1a1204;background:rgba(246,220,160,.95);border-color:transparent;text-shadow:none}
  100%{bottom:66%;color:#1a1204;background:rgba(246,220,160,.95);border-color:transparent;text-shadow:none;opacity:1}}
.x-hand{position:absolute;width:22px;height:22px;border-radius:50%;border:2px solid #fff;background:rgba(255,255,255,.25);left:56%;bottom:24%;opacity:0}
.on .x-hand{animation:xHand 2.4s 1.4s both}
@keyframes xHand{0%{opacity:0}15%{opacity:1;bottom:24%}60%{opacity:1;bottom:68%}100%{opacity:0;bottom:68%}}
.x-pal{position:absolute;top:8%;right:4%;display:grid;gap:6px;opacity:0}
.x-pal i{width:20px;height:20px;border-radius:50%;border:2px solid rgba(255,255,255,.5)}
.on .x-pal{animation:xPop .4s 3.4s both}
/* scene 4: screens + VR */
.x-two{width:88%;display:grid;grid-template-columns:1fr 1fr;gap:6%;align-items:center}
.x-tv{position:relative;aspect-ratio:16/9;border-radius:6px;border:5px solid #20263f;border-bottom-width:8px;overflow:hidden}
.x-tv .x-sub{bottom:14%;font-size:clamp(9px,1.4vw,13px);padding:4px 10px;opacity:1}
.x-cap{text-align:center;color:var(--muted);font-size:12px;margin-top:8px}
.x-vr{position:relative;aspect-ratio:16/9;perspective:500px;display:grid;place-items:center;border-radius:6px;background:radial-gradient(circle at 50% 60%,#2b2350,#0a0820)}
.x-vr .pn{transform:rotateY(-18deg) rotateX(4deg);background:rgba(10,14,31,.8);border:1px solid rgba(155,107,242,.7);border-radius:10px;padding:8px 14px;color:#fff;font-family:var(--display);font-weight:700;font-size:clamp(9px,1.4vw,13px);box-shadow:0 0 24px rgba(155,107,242,.5)}
.on .x-vr .pn{animation:xFloat 3s ease-in-out infinite}
@keyframes xFloat{50%{transform:rotateY(-12deg) rotateX(2deg) translateY(-4px)}}
.on .x-two>div{animation:xPop .5s both}.on .x-two>div+div{animation-delay:.6s}
/* how it works */
.pr-flow{padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:22px;counter-reset:f}
.pr-flow li{list-style:none;position:relative;background:var(--deep);border:1px solid var(--line);border-radius:16px;padding:18px 16px}
.pr-flow li .i3d{--s:42px;margin:0 0 10px}
.pr-flow li b{display:block;font-size:15px;margin-bottom:4px}
.pr-flow li small{color:var(--muted);font-size:13px;line-height:1.7}
.pr-flow li:not(:last-child)::after{content:"";position:absolute;top:50%;left:-11px;width:10px;height:10px;border-top:2px solid var(--acc);border-left:2px solid var(--acc);transform:translateY(-50%) rotate(-45deg);opacity:.7}
.pr-note{margin-top:14px;color:var(--muted);font-size:13.5px;display:flex;gap:8px;align-items:flex-start;line-height:1.8}
.pr-note .ic{flex:none;width:16px;height:16px;margin-top:4px;color:var(--ok)}
/* features */
.pr-feats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:22px}
.pr-f{background:var(--deep);border:1px solid var(--line);border-radius:18px;padding:20px}
.pr-f.wide{grid-column:span 2}
.pr-f header{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.pr-f header .i3d{--s:40px;margin:0}
.pr-f h3{font-size:16.5px;margin:0;color:#fff}
.pr ul.ck{margin:0;padding:0;list-style:none;display:grid;gap:8px}
.pr ul.ck li{position:relative;padding-right:20px;color:var(--mist);opacity:.88;font-size:14px;line-height:1.7}
.pr ul.ck li::before{content:"";position:absolute;right:2px;top:.62em;width:7px;height:7px;border-radius:2px;background:var(--acc);transform:rotate(45deg)}
.pr-f.wide ul.ck{grid-template-columns:1fr 1fr;column-gap:24px}
/* VR */
.pr-vr{position:relative;border-radius:24px;padding:clamp(22px,4vw,40px);background:radial-gradient(90% 120% at 100% 0%,rgba(155,107,242,.22),transparent 60%),var(--deep);border:1px solid rgba(155,107,242,.3)}
.pr-vr .head{display:flex;gap:16px;align-items:flex-start}
.pr-vr .head .i3d{--s:56px;margin:0;flex:none}
.pr-vr-grid{display:grid;grid-template-columns:1fr 1fr;gap:clamp(18px,3vw,36px);margin-top:26px}
.pr-vr h3{font-size:15.5px;margin:0 0 12px;color:#e2ccff}
.pr-steps{margin:0;padding:0;list-style:none;counter-reset:s;display:grid;gap:10px}
.pr-steps li{counter-increment:s;display:flex;gap:12px;align-items:flex-start;font-size:14px;line-height:1.7;color:var(--mist)}
.pr-steps li::before{content:counter(s);flex:none;display:grid;place-items:center;width:26px;height:26px;border-radius:50%;background:rgba(155,107,242,.2);color:#e2ccff;font-weight:700;font-size:13px}
.kbd-t{width:100%;border-collapse:collapse;font-size:13.5px}
.kbd-t td{padding:7px 0;border-bottom:1px solid var(--line);color:var(--mist)}
.kbd-t td:last-child{text-align:left}
kbd{font-family:var(--latin);direction:ltr;display:inline-block;font-size:12px;padding:3px 8px;border-radius:6px;background:rgba(255,255,255,.06);border:1px solid var(--line2);border-bottom-width:2px;color:#fff;white-space:nowrap}
.pr-modes{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:26px}
.pr-modes div{border:1px solid var(--line);border-radius:14px;padding:14px;background:rgba(0,0,0,.2)}
.pr-modes b{display:block;font-size:14px;color:#fff;margin-bottom:4px}
.pr-modes small{color:var(--muted);font-size:12.5px;line-height:1.7}
.pr-tech{margin-top:20px;font-size:13px;color:var(--muted);line-height:1.9;border-top:1px solid var(--line);padding-top:14px}
/* two columns */
.pr-two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
/* final */
.pr-end{text-align:center;padding:clamp(28px,5vw,48px) 20px;border-radius:24px;background:radial-gradient(80% 140% at 50% 0%,rgba(231,185,100,.16),transparent 70%);border:1px solid var(--line)}
.pr-end h2{margin-bottom:8px}
.pr-end .pr-cta{justify-content:center;margin-top:20px}
@media (max-width:900px){
  .pr-hero{grid-template-columns:1fr}
  .pr-feats{grid-template-columns:1fr 1fr}.pr-f.wide{grid-column:span 2}
  .pr-modes{grid-template-columns:1fr 1fr}
}
@media (max-width:640px){
  .pr-flow{grid-template-columns:1fr 1fr}.pr-flow li:nth-child(2)::after{display:none}
  .pr-feats,.pr-vr-grid,.pr-two{grid-template-columns:1fr}.pr-f.wide{grid-column:auto}.pr-f.wide ul.ck{grid-template-columns:1fr}
  .pr-cta .btn{flex:1 1 100%}
  .x-win,.x-list{width:84%}
}
@media (prefers-reduced-motion:reduce){.xp-sc.on *{animation-duration:.01s!important;animation-delay:0s!important}}
'''
rep('</style>', CSS + '</style>', 1)

# ------------------------------------------------------------------ nav: product tab first, default view
rep('    <button data-v="tr" class="on" role="tab">',
    '    <button data-v="pr" class="on" role="tab"><span class="i3d" data-i="pad" data-h="gold"></span><span>البرنامج</span></button>\n'
    '    <button data-v="tr" role="tab">')
rep('<a class="brand" href="#tr">', '<a class="brand" href="#pr">')
rep('  <section class="view on" id="v-tr">', '  <section class="view" id="v-tr">')
rep('const VIEWS=["tr","sc","gl","hi","st"];', 'const VIEWS=["pr","tr","sc","gl","hi","st"];')
rep('  if(!VIEWS.includes(v))v="tr";', '  if(!VIEWS.includes(v))v="pr";')
rep('if(v==="sc")miniLoop(true)};', 'if(v==="sc")miniLoop(true);xpView(v==="pr")};')


def li(items):
    return "".join(f"<li>{x}</li>" for x in items)


def feat(icon, hue, title, items, wide=False):
    return (f'<article class="pr-f{" wide" if wide else ""}"><header><span class="i3d" data-i="{icon}" data-h="{hue}"></span>'
            f'<h3>{title}</h3></header><ul class="ck">{li(items)}</ul></article>')


FEATS = "".join([
    feat("scan", "cyan", "ترجمة الشاشة", [
        "ترجمة تلقائية بدون نسخ أو لصق.", "قراءة دقيقة للنص بتقنية OCR.",
        "الشاشة كاملة، أو منطقة تحددها أنت.", "يكتشف النص الجديد ولا يعيد ترجمة الموجود.",
        "سرعة عالية وتأخير قليل.", "يلحق بالنصوص المتحركة والحوارات السريعة."]),
    feat("lang", "blue", "جودة الترجمة", [
        "عدة محركات ترجمة، وتبدّل بينها بضغطة.", "ترجمة سياقية تفهم الحوار، لا حرفية.",
        "أسماء الشخصيات والأسلحة والأماكن تبقى صحيحة.", "تعدّل أي ترجمة بيدك.",
        "يحفظ ما ترجمه سابقاً، فيقلّ استهلاك الإنترنت."]),
    feat("palette", "rose", "شكل الترجمة", [
        "تختار مكان الترجمة على الشاشة.", "الخط وحجمه ولونه.", "الشفافية والخلفية.",
        "قوالب جاهزة، وإعداد مستقل لكل لعبة.", "وضع سينمائي للحوارات."]),
    feat("pad", "gold", "دعم الألعاب", [
        "ملء الشاشة وبلا حدود ونافذة عادية.", "الترجمة تبقى ظاهرة وأنت تتنقل داخل اللعبة.",
        "يحفظ إعدادات كل لعبة تلقائياً.", "اختصار لوحة مفاتيح للتشغيل والإيقاف.",
        "استهلاك قليل للمعالج والذاكرة أثناء اللعب."]),
    feat("tv", "emerald", "الشاشات والتلفزيونات", [
        "شاشات متعددة، وتختار أين تظهر الترجمة.", "دقة 1080p و1440p و4K.",
        "تلفزيونات LG وSamsung وغيرها عند توصيلها بالكمبيوتر.", "تنقل الترجمة بين الشاشات وتحدد مكانها."]),
    feat("box", "violet", "إضافات", [
        "سجل للترجمات السابقة.", "قاموس خاص لكل لعبة، مع استيراد وتصدير.",
        "لغة اللعبة ولغة الترجمة تلقائياً أو يدوياً.", "حفظ الإعدادات واستعادتها، وتصديرها واستيرادها."]),
])

KEYS = [("تحريك يميناً ويساراً", "Ctrl+Shift+← →"), ("تحريك أعلى وأسفل", "Ctrl+Shift+↑ ↓"),
        ("أقرب أو أبعد", "Ctrl+Shift+PgUp / PgDn"), ("تكبير أو تصغير", "Ctrl+Shift+Home / End"),
        ("إعادة التوسيط أمامك", "Ctrl+Shift+C"), ("مثبّتة في نظرك أو في مكانها", "Ctrl+Shift+P"),
        ("إخفاء وإظهار سريع", "Ctrl+Shift+H")]
KEYROWS = "".join(f"<tr><td>{a}</td><td><kbd>{b}</kbd></td></tr>" for a, b in KEYS)

SCENES = [
    ("حمّل البرنامج وثبّته على ويندوز 10 أو 11",
     f'<div class="x-win"><div class="t">ArabizeGame-Windows.zip <svg class="ic"><use href="#i-dl"/></svg></div>'
     '<div class="x-prog"><i></i></div><div class="d"><span class="x-ok"><svg class="ic"><use href="#i-check"/></svg>جاهز للتشغيل</span><span>مجاني</span></div></div>'),
    ("اختر نافذة اللعبة وشغّل الترجمة",
     '<div class="x-list">'
     '<div class="x-row pick"><svg class="ic"><use href="#i-pad"/></svg><span>Game.exe</span><i class="x-tg"></i></div>'
     '<div class="x-row"><svg class="ic"><use href="#i-monitor"/></svg><span>Launcher.exe</span><i class="x-tg"></i></div>'
     '<div class="x-row"><svg class="ic"><use href="#i-monitor"/></svg><span>Discord.exe</span><i class="x-tg"></i></div>'
     '<span class="x-live"><i></i>الترجمة تعمل</span></div>'),
    ("خصّص شكل الترجمة ومكانها",
     '<div class="x-game"></div><div class="x-en">Where is the old bridge?</div>'
     '<div class="x-sub s3">أين الجسر القديم؟</div><i class="x-hand"></i>'
     '<div class="x-pal"><i style="background:#fff"></i><i style="background:#f6dca0"></i><i style="background:#4fd8ff"></i></div>'),
    ("على الشاشة والتلفزيون، وداخل نظارة الواقع الافتراضي",
     '<div class="x-two"><div><div class="x-tv"><div class="x-game"></div><div class="x-sub">أين الجسر القديم؟</div></div>'
     '<div class="x-cap">شاشة أو تلفزيون</div></div>'
     '<div><div class="x-vr"><div class="pn">أين الجسر القديم؟</div></div><div class="x-cap">داخل النظارة</div></div></div>'),
]
SC_HTML = "".join(f'<div class="xp-sc" data-n="{i}" aria-hidden="true">{h}</div>' for i, (_, h) in enumerate(SCENES))
SEGS = "".join(f'<button type="button" aria-label="الخطوة {i + 1}: {t}"><i></i></button>' for i, (t, _) in enumerate(SCENES))

VIEW = f'''  <!-- ===== PRODUCT ===== -->
  <section class="view on pr" id="v-pr">
    <section class="pr-hero">
      <div>
        <div class="name"><span class="i3d" data-i="pad" data-h="gold"></span>عرّب لعبتك، برنامج ويندوز</div>
        <h1>العب بلغتك، بدون ما تغيّر شيئاً في اللعبة</h1>
        <p>ترجمة فورية لأي لعبة على ويندوز، حتى في ملء الشاشة وداخل الواقع الافتراضي، بدون تسجيل أو تصوير.</p>
        <div class="pr-cta">
          <a class="btn" href="{DL}" rel="noopener"><svg class="ic sm"><use href="#i-dl"/></svg>تحميل البرنامج لويندوز</a>
          <a class="btn ghost" href="#tr">جرّب الترجمة في المتصفح</a>
        </div>
        <div class="pr-req">مجاني لويندوز 10 و11، ولا يحتاج حساباً.</div>
      </div>
      <figure class="xp" id="xp" style="margin:0" aria-label="فيديو الشرح">
        <div class="xp-stage">{SC_HTML}</div>
        <figcaption class="xp-bar">
          <button type="button" id="xpPlay" aria-label="إيقاف مؤقت"><svg class="ic"><use href="#i-pause"/></svg></button>
          <div class="xp-cap"><b id="xpCap" aria-live="polite">{SCENES[0][0]}</b><div class="xp-segs" id="xpSegs">{SEGS}</div></div>
          <button type="button" class="xp-again" id="xpAgain">إعادة الشرح</button>
        </figcaption>
      </figure>
    </section>

    <section>
      <h2>كيف يعمل؟</h2>
      <p class="lede">يلتقط البرنامج نافذة اللعبة بنفس أسلوب Game Capture في OBS، لكنه لا يسجّل ولا يبث ولا يحفظ أي فيديو. يقرأ النص فقط، ثم يعرض الترجمة فوق اللعبة مباشرة.</p>
      <ol class="pr-flow">
        <li><span class="i3d" data-i="monitor" data-h="blue"></span><b>التقاط</b><small>من نافذة اللعبة نفسها، حتى لو غطّتها نافذة أخرى.</small></li>
        <li><span class="i3d" data-i="scan" data-h="cyan"></span><b>قراءة النص</b><small>OCR على الجهاز، ويتجاهل ما لم يتغيّر.</small></li>
        <li><span class="i3d" data-i="lang" data-h="violet"></span><b>ترجمة</b><small>تفهم الحوار وتحفظ أسماء لعبتك من القاموس.</small></li>
        <li><span class="i3d" data-i="cc" data-h="gold"></span><b>عرض فوق اللعبة</b><small>بالشكل والمكان الذي تختاره، أو داخل النظارة.</small></li>
      </ol>
      <p class="pr-note"><svg class="ic"><use href="#i-check"/></svg>لا يعدّل ملفات اللعبة ولا يحقن فيها شيئاً، فهو آمن مع الألعاب الأونلاين.</p>
    </section>

    <section>
      <h2>المميزات</h2>
      <div class="pr-feats">{FEATS}</div>
    </section>

    <section class="pr-vr">
      <div class="head"><span class="i3d" data-i="vr" data-h="violet"></span><div>
        <h2>الواقع الافتراضي</h2>
        <p class="lede">العب بالنظارة واقرأ الترجمة العربية أمامك، دون أن تخرج من اللعبة أو تنزع النظارة.</p></div></div>
      <div class="pr-vr-grid">
        <div><h3>كيف تعمل الترجمة داخل النظارة؟</h3>
          <ol class="pr-steps">
            <li>يقرأ النصوص والحوارات بتقنية OCR من نافذة اللعبة أو الصورة التي تراها.</li>
            <li>يرسلها إلى محرك الترجمة ويعالجها.</li>
            <li>يعرض الترجمة في لوحة عائمة ثلاثية الأبعاد داخل مجال رؤيتك.</li>
            <li>تتحدث تلقائياً مع كل حوار أو مهمة جديدة، ثابتة بلا اهتزاز.</li>
          </ol></div>
        <div><h3>التحكم وأنت داخل النظارة</h3>
          <table class="kbd-t"><tbody>{KEYROWS}</tbody></table>
          <p class="pr-note" style="margin-top:10px"><svg class="ic"><use href="#i-check"/></svg>لون النص والخلفية والشفافية من البرنامج، وإعدادات الواقع الافتراضي مستقلة عن إعدادات الشاشة.</p></div>
      </div>
      <div class="pr-modes">
        <div><b>PCVR</b><small>البرنامج على الكمبيوتر والنظارة متصلة به، والترجمة داخل البيئة الافتراضية.</small></div>
        <div><b>التقاط شاشة اللعبة</b><small>يقرأ النص من صورة اللعبة ثم يرسل الترجمة إلى عرض النظارة.</small></div>
        <div><b>لوحة عائمة</b><small>لوحة مستقلة تضعها في المكان الذي يريحك.</small></div>
        <div><b>أجهزة متعددة</b><small>تصميم يتوسّع ليناسب أجهزة VR المختلفة حسب إمكانياتها.</small></div>
      </div>
      <p class="pr-tech">يعمل عبر OpenVR Overlay مع SteamVR، فتظهر اللوحة فوق أي لعبة VR على ويندوز. النظارات المستقلة مثل Quest بدون كمبيوتر تحتاج حلاً منفصلاً لاحقاً، ويمكن استخدامها الآن عبر Link أو Air Link.</p>
    </section>

    <section class="pr-two">
      {feat("grad", "emerald", "الواجهة والتعليم", [
          "فيديو شرح عند أول تشغيل، من الألف إلى الياء.",
          "يشرح الإعداد والتخصيص ووضع الشاشة ووضع VR.",
          "زر «إعادة الشرح» لمشاهدته متى شئت.",
          "واجهة سهلة للمبتدئين وسريعة الاستخدام."])}
      {feat("shield", "slate", "الاستقرار والأداء", [
          "إعادة محاولة تلقائية عند تعطل الخدمة أو انقطاع الإنترنت.",
          "لا يتجمد البرنامج أثناء الترجمة.",
          "ذاكرة ذكية تمنع تكرار الطلبات.",
          "سجل أخطاء يساعد في معرفة المشكلة وإصلاحها.",
          "يعالج النص المتغيّر فقط بدل تحليل الشاشة كلها باستمرار.",
          "كرت الشاشة اختياري، وإعداد للأجهزة الضعيفة وآخر للقوية."])}
    </section>

    <section class="pr-end">
      <h2>جاهز تلعب بالعربي؟</h2>
      <p class="lede" style="margin:0 auto">حمّل البرنامج، فك الضغط، وشغّل ArabizeGame.exe. فيديو الشرح يبدأ معك من أول مرة.</p>
      <div class="pr-cta">
        <a class="btn" href="{DL}" rel="noopener"><svg class="ic sm"><use href="#i-dl"/></svg>تحميل البرنامج لويندوز</a>
        <a class="btn ghost" href="#tr">جرّب الترجمة في المتصفح</a>
      </div>
    </section>
  </section>

  <!-- ===== TRANSLATE ===== -->
'''
rep('  <!-- ===== TRANSLATE ===== -->\n', VIEW)

# ------------------------------------------------------------------ JS: explainer player
CAPS = ",".join('"' + t + '"' for t, _ in SCENES)
JS = '''/* ============ product page: explainer video ============ */
const XP={i:0,t:0,playing:false,dur:5500,caps:[''' + CAPS + ''']};
function xpGo(i,play){const root=$("xp");if(!root)return;XP.i=(i+XP.caps.length)%XP.caps.length;clearTimeout(XP.t);
  root.querySelectorAll(".xp-sc").forEach(sc=>{const on=+sc.dataset.n===XP.i;sc.classList.remove("on");if(on){void sc.offsetWidth;sc.classList.add("on")}});
  root.querySelectorAll("#xpSegs button").forEach((b,k)=>{b.classList.remove("on");b.classList.toggle("done",k<XP.i);if(k===XP.i){void b.offsetWidth;b.classList.add("on")}
    b.style.setProperty("--dur",XP.dur+"ms");b.setAttribute("aria-current",k===XP.i?"step":"false")});
  $("xpCap").textContent=XP.caps[XP.i];
  if(play!==undefined)XP.playing=play;xpState();if(XP.playing)XP.t=setTimeout(xpNext,XP.dur)}
function xpNext(){if(XP.i>=XP.caps.length-1){XP.playing=false;xpState();$("xpSegs").lastChild.classList.add("done");return}xpGo(XP.i+1)}
function xpState(){const root=$("xp");if(!root)return;root.classList.toggle("paused",!XP.playing);
  $("xpPlay").innerHTML=`<svg class="ic"><use href="#i-${XP.playing?"pause":"play"}"/></svg>`;$("xpPlay").setAttribute("aria-label",XP.playing?"إيقاف مؤقت":"تشغيل")}
function xpView(on){if(!$("xp"))return;if(on)xpGo(0,!reduceMotion);else{XP.playing=false;clearTimeout(XP.t)}}
if($("xp")){
  $("xpPlay").onclick=()=>{if(XP.playing){XP.playing=false;clearTimeout(XP.t);xpState()}else if(XP.i>=XP.caps.length-1&&$("xpSegs").lastChild.classList.contains("done"))xpGo(0,true);else xpGo(XP.i,true)};
  $("xpAgain").onclick=()=>xpGo(0,true);
  document.querySelectorAll("#xpSegs button").forEach((b,k)=>b.onclick=()=>xpGo(k,true));
  document.querySelectorAll('#v-pr a[href="#tr"]').forEach(a=>a.onclick=e=>{e.preventDefault();show("tr");scrollTo({top:0,behavior:"smooth"})});
}

/* ============ intro ============ */
(function(){const el=$("intro");'''
rep('/* ============ intro ============ */\n(function(){const el=$("intro");', JS)

open(P, "w", encoding="utf-8").write(s)
print("product page patched", len(s))
