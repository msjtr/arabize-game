"""Patch the web page: bundled fonts, 3D tiles, templates, text effects, layers and the desktop download card."""
import json
import re
import sys

P = sys.argv[1]
s = open(P, encoding="utf-8").read()
TPL = json.load(open("/tmp/site_tpls.json", encoding="utf-8"))


def rep(old, new, count=1):
    global s
    assert old in s, f"missing: {old[:90]!r}"
    s = s.replace(old, new, count)


def rep_re(pat, new, flags=re.S):
    global s
    s2, n = re.subn(pat, new, s, count=1, flags=flags)
    assert n == 1, f"regex missing: {pat[:80]}"
    s = s2


# ------------------------------------------------------------------ fonts
rep_re(r'<link href="https://fonts\.googleapis\.com/css2\?[^"]+" rel="stylesheet">',
       '<link href="https://fonts.googleapis.com/css2?family=Alexandria:wght@500;700&family=IBM+Plex+Sans+Arabic:wght@400;500;700'
       '&family=Readex+Pro:wght@500;700&family=Tajawal:wght@700&family=Cairo:wght@700&family=Noto+Naskh+Arabic:wght@700&display=swap" rel="stylesheet">')
rep('--display:"Reem Kufi","IBM Plex Sans Arabic",sans-serif; --latin:"Outfit",system-ui,sans-serif;',
    '--display:"Alexandria","IBM Plex Sans Arabic",sans-serif; --latin:"IBM Plex Sans Arabic",system-ui,sans-serif;')
rep('--sub-font:"Cairo",sans-serif;', '--sub-font:"IBM Plex Sans Arabic",sans-serif; --sub-bgc:10,14,31; --sub-acc:#e7b964;')

# ------------------------------------------------------------------ 3D tiles (CSS)
rep_re(r'\.i3d\{--s:22px;--ib:var\(--muted\);.*?\.i3d\.huge\{--s:72px\}\n',
       '.i3d{--s:22px;position:relative;display:inline-block;flex:none;width:var(--s);height:var(--s);\n'
       '  transform:perspective(220px) rotateX(0) rotateY(0);transition:transform .55s cubic-bezier(.2,.8,.2,1),filter .3s}\n'
       '.i3d>svg{display:block;width:100%;height:100%;overflow:visible}\n'
       '.i3d.big{--s:58px}\n.i3d.huge{--s:76px}\n')
rep('.tabs button:hover .i3d{transform:perspective(170px) rotateX(10deg) rotateY(-40deg) translateY(-1px)}',
    '.tabs button .i3d{--s:26px;filter:saturate(.35) brightness(.78)}\n'
    '.tabs button:hover .i3d{filter:saturate(.8) brightness(.95);transform:perspective(220px) rotateX(10deg) rotateY(-24deg) translateY(-1px)}')
rep('.tabs button.on .i3d{--ib:var(--acc);--it:#fff6dc;transform:perspective(170px) rotateX(22deg) rotateY(-34deg) scale(1.12)}',
    '.tabs button.on .i3d{filter:none;transform:perspective(220px) rotateX(14deg) rotateY(-22deg) scale(1.1)}')
rep('.mode .i3d{--s:34px}', '.mode .i3d{--s:40px;filter:saturate(.4) brightness(.8)}')
rep('.mode.on .i3d{--ib:var(--acc);--it:#fff6dc;animation:bob 3.5s ease-in-out infinite}', '.mode.on .i3d{filter:none;animation:bob 3.5s ease-in-out infinite}')
rep('.box h3 .i3d{--s:24px;--ib:var(--acc);--it:#fff6dc}', '.box h3 .i3d{--s:30px}')
rep('.brand .i3d{--s:38px;animation:sway 7s ease-in-out infinite}', '.brand .i3d{--s:42px;animation:sway 7s ease-in-out infinite}')

# ------------------------------------------------------------------ new CSS
CSS = r'''
/* ============ subtitle looks: boxes, text effects, effects, layers ============ */
.sub[data-bg="glass"]{background:rgba(var(--sub-bgc),var(--sub-bga))}
.sub[data-bg="card"]{position:relative;background:rgba(var(--sub-bgc),var(--sub-bga));border:1.5px solid color-mix(in srgb,var(--sub-acc) 70%,transparent);
  border-radius:16px;padding-inline:1em 1.1em;box-shadow:inset 0 1px 0 rgba(255,255,255,.08),0 10px 30px rgba(0,0,0,.35)}
.sub[data-bg="card"]::after{content:"";position:absolute;inset-inline-start:5px;top:50%;width:4px;height:min(46px,58%);transform:translateY(-50%);border-radius:2px;background:var(--sub-acc)}
.sub[data-bg="bar"]{background:rgba(var(--sub-bgc),var(--sub-bga));border-radius:0;border-top:2px solid color-mix(in srgb,var(--sub-acc) 70%,transparent);width:100%;max-width:none}
.sub[data-bg="bubble"]{position:relative;background:rgba(var(--sub-bgc),var(--sub-bga));border:2px solid var(--sub-acc);border-radius:24px;margin-bottom:.5em}
.sub[data-bg="bubble"]::after{content:"";position:absolute;left:50%;bottom:-.5em;width:.85em;height:.85em;background:rgb(var(--sub-bgc));
  border-right:2px solid var(--sub-acc);border-bottom:2px solid var(--sub-acc);transform:translateX(-50%) rotate(45deg)}
.subwrap:has(.sub[data-bg="bar"]){padding-inline:0}
.sub[data-fx="shadow"]{text-shadow:0 2px 4px rgba(0,0,0,.85)}
.sub[data-fx="outline"]{text-shadow:-2px 0 #000,2px 0 #000,0 -2px #000,0 2px #000,-1.5px -1.5px #000,1.5px 1.5px #000,-1.5px 1.5px #000,1.5px -1.5px #000,0 3px 7px rgba(0,0,0,.7)}
.sub[data-fx="glow"]{text-shadow:0 0 6px var(--sub-acc),0 0 18px var(--sub-acc),0 2px 3px rgba(0,0,0,.6)}
.sub[data-fx="none"]{text-shadow:none}
.anim-zoom{animation:zoomIn .45s cubic-bezier(.2,.8,.2,1) both}
@keyframes zoomIn{from{opacity:0;transform:scale(.84)}}
.anim-glow{animation:glowIn .75s ease both}
@keyframes glowIn{from{opacity:0;text-shadow:0 0 26px var(--sub-acc),0 0 60px var(--sub-acc)}35%{opacity:1}}
.ex-zoom{animation:exZoom .34s ease-in forwards}
@keyframes exZoom{to{opacity:0;transform:scale(.84)}}
/* layers: quest + choices float in their own place while the dialogue plays */
.layer{position:absolute;z-index:4;max-width:36%;pointer-events:none;font-family:var(--sub-font);color:var(--sub-color);font-weight:700;
  font-size:max(11px,calc(var(--sub-size) * var(--sub-scale) * .56));line-height:1.55;padding:.5em .85em;border-radius:12px;
  background:rgba(var(--sub-bgc),max(.62,var(--sub-bga)));border:1px solid color-mix(in srgb,var(--sub-acc) 55%,transparent);
  box-shadow:0 10px 30px rgba(0,0,0,.35);opacity:0;transform:translateY(-8px);transition:opacity .45s,transform .45s cubic-bezier(.2,.8,.2,1);unicode-bidi:plaintext}
.layer.on{opacity:1;transform:none}
.layer .lh{display:block;color:var(--sub-acc);font-size:.78em;margin-bottom:.1em}
.layer ol{margin:0;padding:0;list-style:none}.layer li::before{content:"◆";color:var(--sub-acc);margin-inline-end:.5em;font-size:.8em}
.layer[data-fx="outline"],.layer[data-fx="glow"]{text-shadow:0 2px 4px rgba(0,0,0,.85)}
.layer[data-bg="edge"]{background:rgba(0,0,0,.35);border-color:transparent}
.layer.lq[data-pos="tr"]{top:calc(9% + 40px);right:3%}.layer.lq[data-pos="tl"]{top:calc(9% + 12px);left:3%}
.layer.lq[data-pos="tc"]{top:calc(9% + 12px);left:50%;transform:translateX(-50%)}.layer.lq[data-pos="tc"].on{transform:translateX(-50%)}
.layer.lc[data-pos="r"]{top:50%;right:3%;transform:translateY(-50%)}.layer.lc[data-pos="r"].on{transform:translateY(-50%)}
.layer.lc[data-pos="l"]{top:50%;left:3%;transform:translateY(-50%)}.layer.lc[data-pos="l"].on{transform:translateY(-50%)}
.cinema.idle .layer{opacity:0}
.minicine .layer{font-size:max(9px,calc(var(--sub-size) * .4))}
.minicine .layer.lq[data-pos="tr"],.minicine .layer.lq[data-pos="tl"],.minicine .layer.lq[data-pos="tc"]{top:calc(8% + 30px)}
@media (max-width:639px){.minicine .layer{display:none}}
/* template gallery */
.tpls{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:10px;margin-top:8px}
.tpl{display:flex;flex-direction:column;gap:6px;text-align:start;padding:8px 8px 10px;border-radius:16px;border:1px solid var(--line);background:rgba(255,255,255,.025);
  color:inherit;transition:border-color .25s,transform .2s,background .25s}
.tpl:hover{border-color:var(--line2);transform:translateY(-2px)}
.tpl.on{border:2px solid var(--acc);background:color-mix(in srgb,var(--acc) 10%,transparent);padding:7px 7px 9px}
.tpl .ts{position:relative;aspect-ratio:16/8.5;border-radius:11px;overflow:hidden;display:flex;align-items:flex-end;justify-content:center;padding:0 6% 9%;
  background:radial-gradient(60% 70% at 50% 72%,rgba(246,220,160,.42),transparent 70%),linear-gradient(#0b1033,#2a2156 50%,#7a4a52 78%,#1a1020)}
.tpl .ts::before{content:"";position:absolute;inset:auto 0 0;height:42%;background:#120b1c;clip-path:polygon(0 50%,15% 30%,32% 52%,50% 22%,68% 48%,84% 28%,100% 45%,100% 100%,0 100%)}
.tpl .ts .sub{position:relative;font-size:12px;line-height:1.5;padding:.25em .7em;font-weight:700}
.tpl .ts .sub[data-bg="bubble"]{margin-bottom:.6em}
.tpl b{font-size:14px;padding-inline:4px}
.tpl small{color:var(--muted);font-size:12px;line-height:1.5;padding-inline:4px}
/* font picker + chips */
.fonts{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;padding:10px 0}
.fonts button{border:1px solid var(--line2);background:rgba(0,0,0,.22);border-radius:12px;padding:8px 6px;color:var(--mist);transition:border-color .2s}
.fonts button b{display:block;font-size:20px;font-weight:700;line-height:1.5}
.fonts button small{display:block;color:var(--muted);font-size:11.5px;font-family:var(--ui)}
.fonts button.on{border:2px solid var(--acc);background:color-mix(in srgb,var(--acc) 12%,transparent);padding:7px 5px}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:4px 0 10px}
.chips button{border:1px solid var(--line2);background:rgba(255,255,255,.03);color:var(--mist);border-radius:999px;padding:7px 13px;font-size:13px}
.chips button.on{border-color:var(--acc);background:color-mix(in srgb,var(--acc) 16%,transparent);color:var(--acc2);font-weight:700}
.clabel{font-size:14px;padding-top:10px;border-top:1px solid var(--line)}
.box h3+.clabel{border-top:0}
.box.wide{grid-column:1/-1}
/* desktop app download */
.pcapp{display:flex;align-items:center;gap:16px;margin:0 0 16px;padding:14px 16px;border-radius:18px;
  border:1px solid color-mix(in srgb,var(--acc) 45%,transparent);background:linear-gradient(135deg,color-mix(in srgb,var(--acc) 13%,transparent),rgba(255,255,255,.02))}
.pcapp .i3d{--s:52px}
.pcapp div{flex:1;min-width:0}
.pcapp b{display:block;font-size:15.5px}
.pcapp small{display:block;color:var(--muted);font-size:13px;line-height:1.6;margin-top:2px}
.pcapp a{flex:none;display:inline-flex;align-items:center;gap:8px;text-decoration:none;font-weight:700;color:#1a1204;border-radius:12px;padding:10px 16px;
  background:linear-gradient(135deg,var(--acc2),var(--acc))}
@media (max-width:640px){.pcapp{flex-wrap:wrap}.pcapp a{width:100%;justify-content:center}}
'''
rep('/* ============ settings / forms ============ */', CSS + '\n/* ============ settings / forms ============ */')

# ------------------------------------------------------------------ icons
SYMS = '''  <symbol id="i-flag" viewBox="0 0 24 24"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/></symbol>
  <symbol id="i-layers" viewBox="0 0 24 24"><path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></symbol>
  <symbol id="i-wand" viewBox="0 0 24 24"><path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"/><path d="m14 7 3 3"/><path d="M5 6v4"/><path d="M19 14v4"/><path d="M10 2v2"/><path d="M7 8H3"/><path d="M21 16h-4"/><path d="M11 3H9"/></symbol>
  <symbol id="i-tpl" viewBox="0 0 24 24"><rect width="18" height="7" x="3" y="3" rx="1"/><rect width="9" height="7" x="3" y="14" rx="1"/><rect width="5" height="7" x="16" y="14" rx="1"/></symbol>
  <symbol id="i-monitor" viewBox="0 0 24 24"><rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></symbol>
'''
rep('  <symbol id="i-lang" viewBox="0 0 24 24">', SYMS + '  <symbol id="i-lang" viewBox="0 0 24 24">')

# ------------------------------------------------------------------ desktop download card (top of the translate view)
rep('''  <section class="view on" id="v-tr">
''', '''  <section class="view on" id="v-tr">
    <div class="pcapp" id="pcapp">
      <span class="i3d" data-i="monitor" data-h="blue"></span>
      <div><b>برنامج عرب لعبتك للكمبيوتر</b><small>يقرأ الشاشة أثناء اللعب ويعرض الترجمة فوق اللعبة مباشرة، على الشاشات والتلفزيونات المتصلة ونظارات VR. مجاني لويندوز 10 و11.</small></div>
      <a href="https://github.com/msjtr/arabize-game/releases/latest/download/ArabizeGame-Windows.zip" rel="noopener"><svg class="ic sm"><use href="#i-dl"/></svg>تحميل البرنامج</a>
    </div>
''')

# ------------------------------------------------------------------ cinema layers
rep('''        <div class="subwrap" id="subwrap" data-pos="bottom"><div class="sub" id="sub" data-bg="glass">ترجمتك ستظهر هنا</div></div>''',
    '''        <div class="layer lq" id="lyQuest" data-pos="tr"></div>
        <div class="layer lc" id="lyChoice" data-pos="r"></div>
        <div class="subwrap" id="subwrap" data-pos="bottom"><div class="sub" id="sub" data-bg="glass">ترجمتك ستظهر هنا</div></div>''')

# ------------------------------------------------------------------ appearance view
a = s.index('  <section class="view" id="v-sc">')
b = s.index('  <!-- ===== GLOSSARY ===== -->')
LOOK = '''  <section class="view" id="v-sc">
    <div class="vh"><h2>المظهر والقوالب</h2><p>اختر قالباً بضغطة، ثم عدّل ما تريد. كل تغيير يظهر فوراً في المعاينة.</p></div>
    <div class="minicine" id="mini">
      <div class="letter t"></div><div class="letter b"></div>
      <span class="minilabel"><svg class="ic sm"><use href="#i-eye"/></svg>معاينة مباشرة</span>
      <div class="layer lq on" id="miniQuest" data-pos="tr"><span class="lh">◆ المهمة</span>اذهب إلى المنارة القديمة</div>
      <div class="layer lc on" id="miniChoice" data-pos="r"><ol><li>أنا معك.</li><li>ليس اليوم.</li></ol></div>
      <div class="subwrap" id="miniWrap" data-pos="bottom"><div class="sub" id="miniSub" data-bg="glass"></div></div>
    </div>
    <div class="grid" style="margin-top:14px">
      <div class="box wide">
        <h3><span class="i3d" data-i="tpl" data-h="gold"></span>القوالب الجاهزة</h3>
        <div class="tpls" id="tpls"></div>
      </div>
      <div class="box">
        <h3><span class="i3d" data-i="type" data-h="blue"></span>الخط</h3>
        <div class="fonts" id="fontPick"></div>
        <div class="fr"><label for="subSize">حجم الخط<small>للتلفزيون البعيد اختر 36 فأكثر</small></label><input type="range" id="subSize" min="16" max="56" step="1"><span class="val" id="subSizeV"></span></div>
        <div class="fr"><span class="lb">لون الكلام</span><div class="swatches" id="subColor">
          <button style="--c:#ffffff" data-c="#ffffff" aria-label="أبيض"></button>
          <button style="--c:#ffe14d" data-c="#ffe14d" aria-label="أصفر"></button>
          <button style="--c:#f6dca0" data-c="#f6dca0" aria-label="ذهبي فاتح"></button>
          <button style="--c:#9fe8ff" data-c="#9fe8ff" aria-label="سماوي"></button>
          <button style="--c:#b7ffb0" data-c="#b7ffb0" aria-label="أخضر فاتح"></button>
          <button style="--c:#121212" data-c="#121212" aria-label="أسود"></button></div></div>
        <div class="fr"><span class="lb">لون الاسم والحافة</span><div class="swatches" id="subAcc">
          <button style="--c:#e7b964" data-c="#e7b964" aria-label="ذهبي"></button>
          <button style="--c:#5ce1e6" data-c="#5ce1e6" aria-label="سماوي"></button>
          <button style="--c:#ff4fd8" data-c="#ff4fd8" aria-label="وردي"></button>
          <button style="--c:#7cf29a" data-c="#7cf29a" aria-label="أخضر"></button>
          <button style="--c:#ff8466" data-c="#ff8466" aria-label="مرجاني"></button></div></div>
      </div>
      <div class="box">
        <h3><span class="i3d" data-i="palette" data-h="rose"></span>الخلفية والحروف</h3>
        <div class="clabel">شكل الخلفية</div>
        <div class="chips" id="subBgC" data-key="subBg"><button data-k="glass">زجاجي</button><button data-k="card">بطاقة بحافة ملوّنة</button><button data-k="bar">شريط بعرض الشاشة</button><button data-k="bubble">فقاعة حوار</button><button data-k="edge">بدون خلفية</button></div>
        <div class="fr"><span class="lb">لون الخلفية</span><div class="swatches" id="subBgCol">
          <button style="--c:#0a0e1f" data-c="#0a0e1f" aria-label="كحلي"></button>
          <button style="--c:#000000" data-c="#000000" aria-label="أسود"></button>
          <button style="--c:#1b1209" data-c="#1b1209" aria-label="بني"></button>
          <button style="--c:#03121a" data-c="#03121a" aria-label="أزرق داكن"></button>
          <button style="--c:#ffffff" data-c="#ffffff" aria-label="أبيض"></button></div></div>
        <div class="fr"><label for="subBgA">عتامة الخلفية</label><input type="range" id="subBgA" min="10" max="100" step="5"><span class="val" id="subBgAV"></span></div>
        <div class="clabel">تأثير الحروف</div>
        <div class="chips" id="textFxC" data-key="textFx"><button data-k="shadow">ظل ناعم</button><button data-k="outline">حدّ حول الحروف</button><button data-k="glow">توهّج</button><button data-k="none">بدون</button></div>
      </div>
      <div class="box">
        <h3><span class="i3d" data-i="wand" data-h="coral"></span>تأثيرات الظهور والاختفاء</h3>
        <div class="clabel">عند ظهور سطر جديد</div>
        <div class="chips" id="subAnimC" data-key="subAnim"><button data-k="rise">صعود الكلمات</button><button data-k="fade">ظهور تدريجي</button><button data-k="zoom">تكبير</button><button data-k="type">كتابة حرفاً حرفاً</button><button data-k="glow">وميض متوهّج</button><button data-k="blur">من الضباب</button><button data-k="none">فوري</button></div>
        <div class="clabel">عند انتهاء السطر</div>
        <div class="chips" id="subExitC" data-key="subExit"><button data-k="fade">اختفاء تدريجي</button><button data-k="slide">انزلاق للأسفل</button><button data-k="zoom">تصغير</button><button data-k="scatter">تطاير الكلمات</button><button data-k="blur">ذوبان في الضباب</button><button data-k="none">بدون</button></div>
        <div class="fr"><label for="autoPlay">تشغيل العرض بعد الترجمة</label><span class="sw"><input type="checkbox" id="autoPlay"><span></span></span></div>
      </div>
      <div class="box">
        <h3><span class="i3d" data-i="layers" data-h="emerald"></span>الطبقات</h3>
        <div class="fr"><label for="layersOn">فصل المهمة والخيارات عن الحوار<small>المهمة الحالية وخيارات الرد تبقى ظاهرة في مكانها بينما يُعرض الحوار سطراً بعد سطر</small></label><span class="sw"><input type="checkbox" id="layersOn"><span></span></span></div>
        <div class="fr"><label for="subPos">مكان الحوار</label><select id="subPos"><option value="bottom">أسفل</option><option value="center">وسط</option><option value="top">أعلى</option></select></div>
        <div class="fr"><label for="questPos">مكان المهمة</label><select id="questPos"><option value="tr">أعلى اليمين</option><option value="tl">أعلى اليسار</option><option value="tc">أعلى الوسط</option></select></div>
        <div class="fr"><label for="choicePos">مكان الخيارات</label><select id="choicePos"><option value="r">يمين الوسط</option><option value="l">يسار الوسط</option></select></div>
      </div>
      <div class="box">
        <h3><span class="i3d" data-i="cc" data-h="violet"></span>الشريط العائم و VR</h3>
        <div class="fr"><label for="floatOn">إظهار الشريط العائم<small>يعرض السطر الحالي ويمكن سحبه</small></label><span class="sw"><input type="checkbox" id="floatOn"><span></span></span></div>
        <div class="fr"><label for="floatW">عرض الشريط</label><input type="range" id="floatW" min="40" max="100" step="5"><span class="val" id="floatWV"></span></div>
        <div class="fr"><span class="lb">موضع الشريط</span><button class="tb" id="floatReset">إرجاعه للأسفل</button></div>
        <div class="fr"><label for="vrDepth">عمق الترجمة في VR<small>كلما زاد بدت الترجمة أقرب لعينك</small></label><input type="range" id="vrDepth" min="0" max="30" step="2"><span class="val" id="vrDepthV"></span></div>
      </div>
    </div>
  </section>

'''
s = s[:a] + LOOK + s[b:]

# ------------------------------------------------------------------ JS: 3D tile builder
a = s.index('/* ============ 3D icons: stacked extrusion layers ============ */')
b = s.index('const i3d=(name,cls,l)=>')
TILES = r'''/* ============ 3D icons: layered tiles (same design as the desktop app) ============ */
const HUES={gold:["#FFE7B0","#E7B964","#A8701F","#6B4310"],cyan:["#B8F6FF","#41C7E0","#147C9C","#0A4A60"],violet:["#E2CCFF","#9B6BF2","#5A2FC0","#371A7A"],
  emerald:["#BFF7DA","#3FCF8E","#16875A","#0B5236"],coral:["#FFD0BF","#FF8466","#C8462B","#7E2714"],rose:["#FFC9EB","#F062B8","#A8287A","#66124A"],
  blue:["#C8DAFF","#5C8BFF","#2A50C8","#16307E"],slate:["#E6E9F5","#8F98BE","#4E5679","#2C3250"]};
const HUE_OF={lang:"cyan",clap:"rose",book:"violet",hist:"emerald",set:"slate",scan:"cyan",type:"blue",pad:"gold",cam:"gold",msg:"violet",
  film:"rose",spark:"coral",cc:"violet",list:"cyan",target:"coral",menu:"slate",box:"emerald",info:"slate",alert:"coral",vr:"violet",tpl:"gold"};
let tileN=0;
function tile3D(name,hue){const [lt,mid,dk,side]=HUES[hue]||HUES.gold;const u="t"+(++tileN);
  const gl=`<g transform="translate(10.5 9) scale(1.125)"><use href="#i-${name}" width="24" height="24"/></g>`;
  return `<svg viewBox="0 0 48 48" aria-hidden="true"><defs><linearGradient id="f${u}" x1="0" y1="0" x2=".35" y2="1"><stop offset="0" stop-color="${lt}"/><stop offset=".55" stop-color="${mid}"/><stop offset="1" stop-color="${dk}"/></linearGradient>`+
   `<linearGradient id="s${u}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>`+
   `<linearGradient id="g${u}" gradientUnits="userSpaceOnUse" x1="0" y1="3" x2="0" y2="21"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="${lt}"/></linearGradient></defs>`+
   `<ellipse cx="24" cy="44.2" rx="16" ry="2.6" fill="#000" fill-opacity=".38"/><rect x="5" y="7.5" width="38" height="35" rx="11" fill="${side}"/>`+
   `<rect x="5" y="4" width="38" height="35" rx="11" fill="url(#f${u})"/>`+
   `<path d="M16 4.6h16a10.4 10.4 0 0 1 10.4 10.4v1.6C36 19.6 12 19.6 5.6 16.6V15A10.4 10.4 0 0 1 16 4.6z" fill="url(#s${u})"/>`+
   `<rect x="5.6" y="4.6" width="36.8" height="33.8" rx="10.4" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width=".9"/>`+
   `<g fill="none" stroke="${side}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".85"><g transform="translate(0 1.9)">${gl}</g><g transform="translate(0 1)">${gl}</g></g>`+
   `<g fill="none" stroke="url(#g${u})" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">${gl}</g></svg>`}
function build3D(root){
  (root||document).querySelectorAll(".i3d[data-i]:not([data-built])").forEach(el=>{
    const name=el.dataset.i;el.innerHTML=tile3D(name,el.dataset.h||HUE_OF[name]||"gold");el.dataset.built="1";el.setAttribute("aria-hidden","true")});
}
'''
s = s[:a] + TILES + s[b:]
rep('const i3d=(name,cls,l)=>`<span class="i3d ${cls||""}" data-i="${name}" data-l="${l||4}"></span>`;',
    'const i3d=(name,cls,l)=>`<span class="i3d ${cls||""}" data-i="${name}"></span>`;')

# ------------------------------------------------------------------ JS: settings, templates, fonts
rep('const DEFAULTS={theme:"gold",subFont:"Cairo",subSize:28,subColor:"#ffffff",subBg:"glass",subBgA:60,subPos:"bottom",subAnim:"rise",subExit:"scatter",',
    'const DEFAULTS={theme:"gold",subFont:"IBM Plex Sans Arabic",subSize:28,subColor:"#ffffff",subBg:"card",subBgA:80,subBgC:"#0a0e1f",subPos:"bottom",subAnim:"rise",subExit:"fade",\n'
    '  textFx:"shadow",accent:"#e7b964",tpl:"dialogue",layersOn:true,questPos:"tr",choicePos:"r",')
JS_TPL = ('const TEMPLATES=' + json.dumps(TPL, ensure_ascii=False) + ';\n'
          'const FONTS=[["IBM Plex Sans Arabic","بلكس"],["Readex Pro","ريدكس"],["Tajawal","تجوال"],["Cairo","القاهرة"],["Alexandria","الإسكندرية"],["Noto Naskh Arabic","نسخ"]];\n')
rep('const DEFAULTS={', JS_TPL + 'const DEFAULTS={')
rep('if(!["shot","text"].includes(S.mode))S.mode="shot";',
    'if(!["shot","text"].includes(S.mode))S.mode="shot";\n'
    'if(!FONTS.some(f=>f[0]===S.subFont))S.subFont=DEFAULTS.subFont;\n'
    'if(S.subBg==="solid")S.subBg="card";if(!["glass","card","bar","bubble","edge"].includes(S.subBg))S.subBg="card";\n'
    'if(!["shadow","outline","glow","none"].includes(S.textFx))S.textFx="shadow";\n'
    'if(!/^#[0-9a-f]{6}$/i.test(S.subBgC||""))S.subBgC=DEFAULTS.subBgC;if(!/^#[0-9a-f]{6}$/i.test(S.accent||""))S.accent=DEFAULTS.accent;\n'
    'if(S.subColor==="accent")S.subColor="#f6dca0";\n'
    'if(!["tr","tl","tc"].includes(S.questPos))S.questPos="tr";if(!["r","l"].includes(S.choicePos))S.choicePos="r";')

rep('const ALL_SUBS=()=>[$("sub"),$("subL"),$("subR"),$("miniSub")];',
    'const ALL_SUBS=()=>[$("sub"),$("subL"),$("subR"),$("miniSub")];\n'
    'const rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)).join(",");\n'
    'const LOOK_KEYS=["subFont","subSize","subColor","subBg","subBgA","subBgC","textFx","accent","subAnim","subExit"];\n'
    'function applyTemplate(id){const t=TEMPLATES[id];if(!t)return;LOOK_KEYS.forEach(k=>{if(k in t)S[k]=t[k]});S.tpl=id;applyAll();miniLoop(true);toast(`طُبّق قالب «${t.name}»`)}\n'
    'function renderTpls(){const box=$("tpls");box.innerHTML="";for(const [id,t] of Object.entries(TEMPLATES)){\n'
    '  const b=document.createElement("button");b.className="tpl";b.dataset.id=id;\n'
    '  b.innerHTML=`<span class="ts"><span class="sub" data-bg="${t.subBg}" data-fx="${t.textFx}" style="--sub-font:\'${t.subFont}\',sans-serif;--sub-color:${t.subColor};--sub-bgc:${rgb(t.subBgC)};--sub-bga:${(t.subBgA/100).toFixed(2)};--sub-acc:${t.accent};font-family:\'${t.subFont}\',sans-serif;color:${t.subColor}">سننطلق عند الفجر. أحضر سيفك.</span></span><b></b><small></small>`;\n'
    '  b.querySelector("b").textContent=t.name;b.querySelector("small").textContent=t.desc;b.onclick=()=>applyTemplate(id);box.appendChild(b)}}\n'
    'function renderFonts(){const box=$("fontPick");box.innerHTML="";for(const [f,ar] of FONTS){const b=document.createElement("button");b.dataset.f=f;\n'
    '  b.innerHTML=`<b style="font-family:\'${f}\',sans-serif">عرّب لعبتك</b><small></small>`;b.querySelector("small").textContent=ar;\n'
    '  b.onclick=()=>{S.subFont=f;S.tpl="custom";applyAll();miniLoop(true)};box.appendChild(b)}}\n'
    'renderTpls();renderFonts();build3D();\n'
    'function renderLayers(lines){const q=[],c=[],rest=[];for(const l of lines){if(/^المهمة\\s*[:：]/.test(l))q.push(l.replace(/^المهمة\\s*[:：]\\s*/,""));else if(/^◆/.test(l))c.push(l.replace(/^◆\\s*/,""));else rest.push(l)}\n'
    '  const on=S.layersOn&&matchMedia("(min-width:640px)").matches&&rest.length>0&&(q.length||c.length);const lq=$("lyQuest"),lc=$("lyChoice");\n'
    '  if(on&&q.length){lq.innerHTML=\'<span class="lh">◆ المهمة</span>\';const sp=document.createElement("span");sp.textContent=q.join(" — ");lq.appendChild(sp);lq.classList.add("on")}else lq.classList.remove("on");\n'
    '  if(on&&c.length){lc.innerHTML="";const ol=document.createElement("ol");c.forEach(x=>{const li=document.createElement("li");li.textContent=x;ol.appendChild(li)});lc.appendChild(ol);lc.classList.add("on")}else lc.classList.remove("on");\n'
    '  return on?rest:lines}')

rep('  R.style.setProperty("--sub-color",S.subColor==="accent"?"var(--acc2)":S.subColor);',
    '  R.style.setProperty("--sub-color",S.subColor);R.style.setProperty("--sub-bgc",rgb(S.subBgC));R.style.setProperty("--sub-acc",S.accent);')
rep('  ALL_SUBS().forEach(el=>el.dataset.bg=S.subBg);',
    '  ALL_SUBS().forEach(el=>{el.dataset.bg=S.subBg;el.dataset.fx=S.textFx});\n'
    '  document.querySelectorAll(".layer").forEach(el=>{el.dataset.bg=S.subBg;el.dataset.fx=S.textFx});\n'
    '  ["lyQuest","miniQuest"].forEach(id=>$(id).dataset.pos=S.questPos);["lyChoice","miniChoice"].forEach(id=>$(id).dataset.pos=S.choicePos);\n'
    '  $("miniQuest").hidden=$("miniChoice").hidden=!S.layersOn;$("layersOn").checked=S.layersOn;$("questPos").value=S.questPos;$("choicePos").value=S.choicePos;\n'
    '  document.querySelectorAll(".chips[data-key]").forEach(c=>c.querySelectorAll("button").forEach(b=>b.classList.toggle("on",b.dataset.k===S[c.dataset.key])));\n'
    '  document.querySelectorAll("#tpls .tpl").forEach(b=>b.classList.toggle("on",b.dataset.id===S.tpl));\n'
    '  document.querySelectorAll("#fontPick button").forEach(b=>b.classList.toggle("on",b.dataset.f===S.subFont));\n'
    '  document.querySelectorAll("#subAcc button").forEach(b=>b.classList.toggle("on",b.dataset.c===S.accent));\n'
    '  document.querySelectorAll("#subBgCol button").forEach(b=>b.classList.toggle("on",b.dataset.c===S.subBgC));')
rep('  $("subFont").value=S.subFont;$("subSize").value=S.subSize;$("subSizeV").textContent=S.subSize+"px";',
    '  $("subSize").value=S.subSize;$("subSizeV").textContent=S.subSize+"px";')
rep('  $("subBg").value=S.subBg;$("subBgA").value=S.subBgA;', '  $("subBgA").value=S.subBgA;')
rep('  $("subPos").value=S.subPos;$("subAnim").value=S.subAnim;$("subExit").value=S.subExit;', '  $("subPos").value=S.subPos;')
rep('const bindSel=(id,key)=>$(id).addEventListener("change",e=>{S[key]=e.target.value;applyAll();if(["subAnim","subExit","subFont","subPos","subBg"].includes(key))miniLoop(true)});',
    'const bindSel=(id,key)=>$(id).addEventListener("change",e=>{S[key]=e.target.value;applyAll();if(["subPos"].includes(key))miniLoop(true)});\n'
    'document.querySelectorAll(".chips[data-key]").forEach(c=>c.querySelectorAll("button").forEach(b=>b.onclick=()=>{S[c.dataset.key]=b.dataset.k;if(LOOK_KEYS.includes(c.dataset.key))S.tpl="custom";applyAll();miniLoop(true)}));\n'
    'document.querySelectorAll("#subAcc button").forEach(b=>b.onclick=()=>{S.accent=b.dataset.c;S.tpl="custom";applyAll()});\n'
    'document.querySelectorAll("#subBgCol button").forEach(b=>b.onclick=()=>{S.subBgC=b.dataset.c;S.tpl="custom";applyAll()});\n'
    '$("layersOn").addEventListener("change",e=>{S.layersOn=e.target.checked;applyAll();loadPlayer($("output").value,true)});\n'
    '["questPos","choicePos"].forEach(k=>$(k).addEventListener("change",e=>{S[k]=e.target.value;applyAll()}));')
rep('["subFont","subBg","subPos","subAnim","subExit","tStyle","ocrTier","voice","voiceSrc"].forEach(k=>bindSel(k,k));',
    '["subPos","tStyle","ocrTier","voice","voiceSrc"].forEach(k=>bindSel(k,k));')
rep('[["subSize","subSize"],["rate","rate"],["floatW","floatW"],["subBgA","subBgA"],["vrDepth","vrDepth"]].forEach(([id,k])=>$(id).addEventListener("input",e=>{S[k]=+e.target.value;applyAll()}));',
    '[["subSize","subSize"],["rate","rate"],["floatW","floatW"],["subBgA","subBgA"],["vrDepth","vrDepth"]].forEach(([id,k])=>$(id).addEventListener("input",e=>{S[k]=+e.target.value;if(["subSize","subBgA"].includes(k))S.tpl="custom";applyAll()}));')
rep('document.querySelectorAll("#subColor button").forEach(b=>b.onclick=()=>{S.subColor=b.dataset.c;applyAll()});',
    'document.querySelectorAll("#subColor button").forEach(b=>b.onclick=()=>{S.subColor=b.dataset.c;S.tpl="custom";applyAll()});')
rep('$("subBgA").disabled=S.subBg==="edge";', '$("subBgA").disabled=S.subBg==="edge";$("subBgCol").style.opacity=S.subBg==="edge"?.4:1;')

# effects in the renderer
rep('  if(anim==="fade"){el.textContent=text;void el.offsetWidth;el.classList.add("anim-fade");return}',
    '  if(anim==="fade"||anim==="zoom"||anim==="glow"){el.textContent=text;void el.offsetWidth;el.classList.add("anim-"+anim);return}')
rep('el.classList.remove("anim-rise","anim-blur","anim-fade","caret");', 'el.classList.remove("anim-rise","anim-blur","anim-fade","anim-zoom","anim-glow","caret");')
rep('const EXIT_MS={fade:320,blur:380,slide:380,scatter:560};', 'const EXIT_MS={fade:320,blur:380,slide:380,scatter:560,zoom:340};')

# word-by-word effects: each word is an inline-block, which hides the text's direction from the browser,
# so the line's direction is set explicitly from its first strong letter (Arabic lines kept reading right-to-left)
rep('function renderSub(el,text,anim){\n  clearInterval(el._t);el.className="sub";el.style.removeProperty("animation");',
    'const dirOf=t=>{const m=(t||"").match(/[A-Za-z\\u00C0-\\u024F\\u0370-\\u03FF\\u0400-\\u04FF]|[\\u0590-\\u08FF\\uFB1D-\\uFEFC]/);return m&&/[\\u0590-\\u08FF\\uFB1D-\\uFEFC]/.test(m[0])?"rtl":m?"ltr":"auto"};\n'
    'function renderSub(el,text,anim){\n  clearInterval(el._t);el.className="sub";el.style.removeProperty("animation");el.dir=dirOf(text);')
rep('.sub .w{display:inline-block;white-space:pre}', '.sub .w{display:inline-block;white-space:pre}\n.sub.anim-rise,.sub.anim-blur,.sub.ex-scatter{unicode-bidi:isolate}')

# layers in the player
rep('function loadPlayer(text,keep){const prev=player.i;player.stop();player.lines=toLines(text||"");',
    'function loadPlayer(text,keep){const prev=player.i;player.stop();player.lines=renderLayers(toLines(text||""));')

open(P, "w", encoding="utf-8").write(s)
print("patched", len(s))

# ====================================================================== live mode
s = open(P, encoding="utf-8").read()

rep('.modes{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px}',
    '.modes{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px}')
rep('''      <button class="mode" data-m="text" role="tab"><span class="i3d" data-i="type" data-l="6"></span><span><b>نص مكتوب</b><small>الصق الحوار أو ملف نصوص اللعبة</small></span></button>''',
    '''      <button class="mode" data-m="text" role="tab"><span class="i3d" data-i="type" data-l="6"></span><span><b>نص مكتوب</b><small>الصق الحوار أو ملف نصوص اللعبة</small></span></button>
      <button class="mode" data-m="live" role="tab"><span class="i3d" data-i="monitor" data-h="emerald"></span><span><b>مباشر من الشاشة</b><small>يقرأ اللعبة أو أي شاشة أو كاميرا الجوال ويترجم تلقائياً</small></span></button>''')

LIVE_HTML = '''    <!-- live mode -->
    <div id="m-live" hidden>
      <div class="lvstage" id="lvStage">
        <video id="lvVideo" muted playsinline></video>
        <div class="lvsel" id="lvSel" hidden></div>
        <div class="lvempty" id="lvEmpty">
          <span class="i3d big" data-i="monitor" data-h="emerald"></span>
          <h3>ترجمة مباشرة من أي شاشة</h3>
          <p>شارك نافذة اللعبة أو الشاشة كاملة (ومنها التلفزيون المتصل بالكمبيوتر)، أو وجّه كاميرا الجوال إلى شاشة التلفزيون أو جهاز الألعاب. يقرأ الموقع النص كلما تغيّر ويترجمه فوراً.</p>
          <div class="row">
            <button class="btn" id="lvScreen"><svg class="ic sm"><use href="#i-monitor"/></svg>شارك الشاشة أو نافذة اللعبة</button>
            <button class="btn ghost" id="lvCam"><svg class="ic sm"><use href="#i-cam"/></svg>كاميرا الجوال</button>
          </div>
        </div>
      </div>
      <div class="lvbar" id="lvBar" hidden>
        <span class="chip" id="lvChip">جاهز</span>
        <span class="sp"></span>
        <button class="tb" id="lvRegion"><svg class="ic sm"><use href="#i-scan"/></svg>حدّد منطقة النص</button>
        <button class="tb" id="lvFull"><svg class="ic sm"><use href="#i-max"/></svg>الشاشة كاملة</button>
        <button class="tb" id="lvPip"><svg class="ic sm"><use href="#i-cc"/></svg>نافذة عائمة فوق اللعبة</button>
        <button class="tb danger" id="lvStop"><svg class="ic sm"><use href="#i-sq"/></svg>إيقاف</button>
      </div>
      <p class="lvhint" id="lvHint" hidden>اسحب على الصورة لتحديد مكان الكلام فقط (صندوق الحوار مثلاً): القراءة تصبح أسرع وأدق. «النافذة العائمة» تبقى فوق اللعبة على Chrome وEdge في الكمبيوتر. للترجمة فوق اللعبة مباشرة بدون أي خطوة، استخدم برنامج الكمبيوتر.</p>
      <ul class="lvlast" id="lvLast"></ul>
    </div>

    <!-- screenshot mode -->'''
rep('    <!-- screenshot mode -->', LIVE_HTML)

LIVE_CSS = r'''
/* ============ live mode ============ */
.lvstage{position:relative;border-radius:18px;overflow:hidden;border:1px solid var(--line2);background:#05060f;aspect-ratio:16/9;touch-action:none;user-select:none}
.lvstage video{width:100%;height:100%;object-fit:contain;display:block}
.lvstage.on{cursor:crosshair}
.lvsel{position:absolute;border:2px dashed var(--acc);background:color-mix(in srgb,var(--acc) 8%,transparent);box-shadow:0 0 0 9999px rgba(0,0,0,.45);pointer-events:none;border-radius:6px}
.lvempty{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;text-align:center;padding:18px;
  background:radial-gradient(70% 70% at 50% 40%,color-mix(in srgb,var(--acc) 10%,transparent),transparent)}
.lvempty h3{margin:4px 0 0;font-family:var(--display);font-weight:500;font-size:20px}
.lvempty p{margin:0;color:var(--muted);font-size:13.5px;line-height:1.8;max-width:560px}
.lvbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}
.lvbar .sp{flex:1}
.lvbar .tb.danger{color:var(--err)}
.lvhint{color:var(--muted);font-size:12.5px;line-height:1.7;margin:8px 2px 0}
.lvlast{list-style:none;margin:10px 0 0;padding:0;display:grid;gap:8px}
.lvlast li{border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:rgba(255,255,255,.025)}
.lvlast li b{display:block;font-size:15px;line-height:1.7}
.lvlast li small{display:block;color:var(--muted);direction:ltr;text-align:left;font-size:12px;margin-top:2px}
.lvlast li .k{color:var(--acc);font-size:12px;font-weight:700}
@media (max-width:600px){.lvstage{aspect-ratio:4/3}.lvempty h3{font-size:17px}.lvempty p{font-size:12.5px}.lvbar .tb{font-size:12px}}
'''
rep('/* ============ settings / forms ============ */', LIVE_CSS + '\n/* ============ settings / forms ============ */')

rep('if(!["shot","text"].includes(S.mode))S.mode="shot";', 'if(!["shot","text","live"].includes(S.mode))S.mode="shot";')
rep('$("m-shot").hidden=m!=="shot";$("m-text").hidden=m!=="text"}', '$("m-shot").hidden=m!=="shot";$("m-text").hidden=m!=="text";$("m-live").hidden=m!=="live"}')

LIVE_JS = r'''
/* ============ live: read the game / any screen / the phone camera, translate whenever the text changes ============ */
async function readFrame(sample,blob,t,signal,skipIf){
  const raw=await sample.json(buildShotPrompt(t,S.tStyle),{images:[blob],modelTier:"quick",signal});
  return {lang:normLang(raw&&raw.lang),scene:"",blocks:cleanBlocks(raw)}}
const LV={stream:null,timer:0,prev:null,changed:false,still:0,busy:false,seen:"",lines:[],region:store.get("ag_lvreg",null),kind:"",pip:null,pipCanvas:null,ctl:null,sel:false};
const normKey=t=>(t||"").toLowerCase().replace(/[^\p{L}\p{N}]+/gu," ").trim();
function similar(a,b){a=normKey(a);b=normKey(b);if(!a||!b)return a===b;if(a===b)return true;
  const bg=s=>{const m=new Map();for(let i=0;i<s.length-1;i++){const k=s.slice(i,i+2);m.set(k,(m.get(k)||0)+1)}return m};
  const A=bg(a),B=bg(b);let inter=0;for(const [k,n] of A)inter+=Math.min(n,B.get(k)||0);return 2*inter/Math.max(1,a.length-1+b.length-1)>=.9}
function lvChip(txt,cls){const c=$("lvChip");c.className="chip "+(cls||"");c.innerHTML=cls==="live"?"<i></i><span></span>":"<span></span>";c.lastChild.textContent=txt}
async function liveStart(kind){
  if(LV.stream)liveStop(true);
  try{
    if(kind==="screen"){
      if(!navigator.mediaDevices||!navigator.mediaDevices.getDisplayMedia)
        return modal("مشاركة الشاشة غير متاحة","متصفحات الجوال لا تسمح للمواقع بقراءة الشاشة. اختر «كاميرا الجوال» ووجّهها إلى شاشة اللعبة، أو افتح الموقع من الكمبيوتر على Chrome أو Edge، أو حمّل برنامج الكمبيوتر.");
      LV.stream=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:{ideal:5,max:10}},audio:false,selfBrowserSurface:"exclude",surfaceSwitching:"include",preferCurrentTab:false});
    }else{
      if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)return modal("الكاميرا غير متاحة","هذا المتصفح لا يسمح باستخدام الكاميرا في هذه الصفحة.");
      LV.stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"},width:{ideal:1920},height:{ideal:1080}},audio:false});
    }
  }catch(e){
    if(e&&e.name==="NotAllowedError")return toast(kind==="screen"?"لم تُمنح مشاركة الشاشة":"لم يُمنح إذن الكاميرا",true);
    return modal("تعذّر بدء القراءة المباشرة",kind==="screen"?"هذه الصفحة لا تسمح بمشاركة الشاشة هنا. افتح الموقع العام msjtr.github.io/arabize-game على Chrome أو Edge في الكمبيوتر، أو استخدم برنامج الكمبيوتر.":"تعذّر فتح الكاميرا. اسمح للموقع باستخدامها من إعدادات المتصفح ثم أعد المحاولة.")}
  LV.kind=kind;const v=$("lvVideo");v.srcObject=LV.stream;try{await v.play()}catch(e){}
  LV.stream.getVideoTracks().forEach(tr=>tr.addEventListener("ended",()=>liveStop()));
  $("lvEmpty").hidden=true;$("lvBar").hidden=false;$("lvHint").hidden=false;$("lvStage").classList.add("on");
  LV.prev=null;LV.changed=true;LV.still=0;LV.seen="";drawSel();
  clearInterval(LV.timer);LV.timer=setInterval(liveTick,kind==="cam"?800:600);
  lvChip("يراقب الشاشة","live");setStatus("القراءة المباشرة تعمل: تُترجم النصوص كلما تغيّرت.","ok");
}
function liveStop(silent){
  clearInterval(LV.timer);LV.timer=0;if(LV.ctl)LV.ctl.abort();
  if(LV.stream)LV.stream.getTracks().forEach(t=>t.stop());LV.stream=null;$("lvVideo").srcObject=null;
  $("lvEmpty").hidden=false;$("lvBar").hidden=true;$("lvHint").hidden=true;$("lvSel").hidden=true;$("lvStage").classList.remove("on");
  if(!silent)setStatus("أُوقفت القراءة المباشرة.")}
function videoBox(){const v=$("lvVideo"),r=v.getBoundingClientRect(),W=v.videoWidth||16,H=v.videoHeight||9;
  const k=Math.min(r.width/W,r.height/H),w=W*k,h=H*k;return {x:r.left+(r.width-w)/2,y:r.top+(r.height-h)/2,w,h}}
function drawSel(){const el=$("lvSel");if(!LV.region||!LV.stream){el.hidden=true;return}
  const st=$("lvStage").getBoundingClientRect(),b=videoBox(),[x,y,w,h]=LV.region;el.hidden=false;
  el.style.left=(b.x-st.left+x*b.w)+"px";el.style.top=(b.y-st.top+y*b.h)+"px";el.style.width=w*b.w+"px";el.style.height=h*b.h+"px"}
addEventListener("resize",drawSel);$("lvVideo").addEventListener("loadedmetadata",drawSel);
(()=>{const st=$("lvStage");let p0=null;
  const pos=e=>{const b=videoBox();return [Math.min(1,Math.max(0,(e.clientX-b.x)/b.w)),Math.min(1,Math.max(0,(e.clientY-b.y)/b.h))]};
  st.addEventListener("pointerdown",e=>{if(!LV.stream||e.target.closest("button"))return;p0=pos(e);st.setPointerCapture(e.pointerId)});
  st.addEventListener("pointermove",e=>{if(!p0)return;const p=pos(e);LV.region=[Math.min(p0[0],p[0]),Math.min(p0[1],p[1]),Math.abs(p[0]-p0[0]),Math.abs(p[1]-p0[1])];drawSel()});
  st.addEventListener("pointerup",()=>{if(!p0)return;p0=null;
    if(!LV.region||LV.region[2]<.04||LV.region[3]<.03){LV.region=null;toast("اسحب مستطيلاً حول مكان الكلام")}
    else toast("حُددت المنطقة: ستُقرأ هذه المنطقة فقط");
    store.set("ag_lvreg",LV.region);drawSel();LV.prev=null;LV.changed=true;LV.seen=""})})();
$("lvScreen").onclick=()=>liveStart("screen");
$("lvCam").onclick=()=>liveStart("cam");
$("lvStop").onclick=()=>liveStop();
$("lvRegion").onclick=()=>toast("اسحب على الصورة حول صندوق الكلام في اللعبة");
$("lvFull").onclick=()=>{LV.region=null;store.set("ag_lvreg",null);drawSel();LV.prev=null;LV.changed=true;LV.seen="";toast("ستُقرأ الشاشة كاملة")};
function liveFrame(){const v=$("lvVideo"),W=v.videoWidth,H=v.videoHeight;if(!W||!H)return null;
  const [x,y,w,h]=LV.region||[0,0,1,1],sw=Math.max(8,Math.round(w*W)),sh=Math.max(8,Math.round(h*H));
  const c=document.createElement("canvas");c.width=sw;c.height=sh;c.getContext("2d").drawImage(v,Math.round(x*W),Math.round(y*H),sw,sh,0,0,sw,sh);return c}
function grayThumb(c){const t=document.createElement("canvas");t.width=160;t.height=Math.max(1,Math.round(160*c.height/c.width));
  const x=t.getContext("2d",{willReadFrequently:true});x.drawImage(c,0,0,t.width,t.height);const d=x.getImageData(0,0,t.width,t.height).data;
  const g=new Uint8Array(d.length/4);for(let i=0;i<g.length;i++)g[i]=(d[i*4]*77+d[i*4+1]*150+d[i*4+2]*29)>>8;return g}
async function liveTick(){
  if(LV.busy||!LV.stream)return;const c=liveFrame();if(!c)return;const g=grayThumb(c);
  let diff=255;if(LV.prev&&LV.prev.length===g.length){let s=0;for(let i=0;i<g.length;i++)s+=Math.abs(g[i]-LV.prev[i]);diff=s/g.length}
  LV.prev=g;const sens=LV.kind==="cam"?7:2.5;
  if(diff>sens){LV.changed=true;LV.still=0;return}        // still moving: wait until the text settles
  if(!LV.changed)return;LV.changed=false;await liveRead(c)}
async function liveRead(c){
  LV.busy=true;lvChip("يقرأ النص…","live");const t0=performance.now();
  try{
    const sample=await getSample();if(!sample)throw {code:"capability_disabled"};
    const blob=await new Promise(r=>c.toBlob(r,"image/png"));const t=tgt.value;LV.ctl=new AbortController();
    const data=await readFrame(sample,blob,t,LV.ctl.signal,orig=>similar(orig,LV.seen));
    if(!data||data.same){lvChip("لا نص جديد","live");return}
    const blocks=data.blocks||[];const orig=blocks.map(b=>b.original).join("\n");
    if(!blocks.length){lvChip("لا يوجد نص على الشاشة","live");return}
    if(similar(orig,LV.seen)){lvChip("لا نص جديد","live");return}
    LV.seen=orig;const lines=sceneToLines(blocks);LV.lines=lines;const text=lines.join("\n");
    $("output").value=text;outCount();loadPlayer(text);player.play();pipUpdate();
    const ul=$("lvLast");const li=document.createElement("li");
    for(const b of blocks){const k=b.type==="quest"?"المهمة":b.type==="choice"?"خيار":(b.speaker_tr||b.speaker||"");
      if(k){const s=document.createElement("span");s.className="k";s.textContent=k;li.appendChild(s)}
      const bt=document.createElement("b");bt.textContent=b.translation||"";bt.dir=dirOf(bt.textContent);li.appendChild(bt);
      const sm=document.createElement("small");sm.textContent=b.original;li.appendChild(sm)}
    ul.prepend(li);while(ul.children.length>4)ul.lastChild.remove();
    lvChip(`تُرجم في ${fmt(((performance.now()-t0)/1000).toFixed(1))} ث`,"live");
    addHistory({time:stamp(),source:"قراءة مباشرة: "+blocks.map(b=>b.original).join(" | ").slice(0,600),translation:text,from:data.lang||"auto",to:t,style:S.tStyle,kind:"shot"});
  }catch(e){const code=(e&&e.code)||"upstream_error";
    if(code!=="cancelled"){lvChip(code==="rate_limited"?"الخدمة مشغولة، سيُعاد المحاولة":"تعذّرت القراءة، سيُعاد المحاولة","");LV.changed=true}
  }finally{LV.busy=false;LV.ctl=null}}

/* floating window above the game: Document Picture-in-Picture (Chrome/Edge), or a video picture-in-picture fallback */
const PIP_CSS=`body{margin:0;background:#05060f;display:flex;align-items:center;justify-content:center;min-height:100vh;overflow:hidden}
#p{font-weight:700;line-height:1.6;text-align:center;padding:10px 18px;white-space:pre-wrap}#p .q{display:block;font-size:.62em;opacity:.95}`;
async function pipOpen(){
  if(LV.pip&&!LV.pip.closed){LV.pip.focus&&LV.pip.focus();return}
  if(window.documentPictureInPicture){
    try{const w=await documentPictureInPicture.requestWindow({width:Math.round(Math.min(960,screen.availWidth*.6)),height:180});
      LV.pip=w;const d=w.document;d.documentElement.dir="rtl";
      document.querySelectorAll('link[rel=stylesheet]').forEach(l=>{const n=d.createElement("link");n.rel="stylesheet";n.href=l.href;d.head.appendChild(n)});
      const st=d.createElement("style");st.textContent=PIP_CSS;d.head.appendChild(st);const p=d.createElement("div");p.id="p";d.body.appendChild(p);
      w.addEventListener("pagehide",()=>{LV.pip=null});pipUpdate();toast("ضع النافذة العائمة فوق اللعبة؛ تبقى ظاهرة فوق كل النوافذ");return}catch(e){}
  }
  const v=document.createElement("video");
  if(v.requestPictureInPicture&&document.pictureInPictureEnabled!==false&&HTMLCanvasElement.prototype.captureStream){
    try{const cv=document.createElement("canvas");cv.width=1280;cv.height=220;LV.pipCanvas=cv;pipUpdate();
      v.muted=true;v.srcObject=cv.captureStream(4);await v.play();await v.requestPictureInPicture();
      LV.pipVideo=v;clearInterval(LV.pipT);LV.pipT=setInterval(pipUpdate,1000);
      v.addEventListener("leavepictureinpicture",()=>{clearInterval(LV.pipT);LV.pipCanvas=null;LV.pipVideo=null});return}catch(e){LV.pipCanvas=null}
  }
  modal("النافذة العائمة غير مدعومة هنا","هذا المتصفح لا يدعم النوافذ العائمة. استخدم Chrome أو Edge على الكمبيوتر، أو «الشريط العائم» في هذه الصفحة، أو برنامج الكمبيوتر الذي يعرض الترجمة فوق اللعبة مباشرة.")}
function pipUpdate(){
  const lines=LV.lines.length?LV.lines:["الترجمة المباشرة ستظهر هنا"];
  const quest=lines.filter(l=>/^المهمة\s*[:：]/.test(l)),main=lines.filter(l=>!/^المهمة\s*[:：]/.test(l)).slice(-3);
  const col=S.subColor,bg=`rgba(${rgb(S.subBgC)},${Math.max(.75,S.subBgA/100)})`,font=`"${S.subFont}",sans-serif`;
  if(LV.pip&&!LV.pip.closed){const d=LV.pip.document,p=d.getElementById("p");if(!p)return;d.body.style.background=bg;
    p.style.fontFamily=font;p.style.color=col;p.style.fontSize=Math.max(18,Math.min(40,S.subSize))+"px";p.dir=dirOf(main.join(" "));p.textContent=main.join("\n");
    if(quest.length){const q=d.createElement("span");q.className="q";q.style.color=S.accent;q.textContent=quest.join(" ");p.prepend(q)}}
  const cv=LV.pipCanvas;if(cv){const x=cv.getContext("2d");x.fillStyle=bg;x.fillRect(0,0,cv.width,cv.height);
    x.direction="rtl";x.textAlign="center";x.fillStyle=col;let size=40;x.font=`700 ${size}px ${font}`;
    const wrap=[];for(const l of main){let cur="";for(const w of l.split(" ")){const tst=cur?cur+" "+w:w;if(x.measureText(tst).width>cv.width-60&&cur){wrap.push(cur);cur=w}else cur=tst}if(cur)wrap.push(cur)}
    const show=wrap.slice(-3);const lh=size*1.35,y0=cv.height/2-(show.length-1)*lh/2;
    x.textBaseline="middle";show.forEach((l,i)=>x.fillText(l,cv.width/2,y0+i*lh))}}
$("lvPip").onclick=pipOpen;
'''
rep('/* ============ subtitles: enter + exit effects ============ */', LIVE_JS + '\n/* ============ subtitles: enter + exit effects ============ */')

open(P, "w", encoding="utf-8").write(s)
print("live patched", len(s))
