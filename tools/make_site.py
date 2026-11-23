"""Turn the Claude-hosted web page into the public GitHub Pages site (free engines, no sign-in)."""
import re

src = open('/tmp/stage1.html', encoding='utf-8').read()


def sub(a, b):
    global src
    assert a in src, a[:90]
    src = src.replace(a, b, 1)


sub('<title>عرب لعبتك | Arabize Game</title>', '''<title>عرب لعبتك | Arabize Game</title>
<meta name="description" content="عرب لعبتك: ترجم نصوص الألعاب ولقطات الشاشة إلى العربية مجاناً، مع عرض سينمائي للترجمة.">
<meta property="og:title" content="عرب لعبتك | Arabize Game">
<meta property="og:description" content="ترجم نصوص الألعاب ولقطات الشاشة إلى العربية مجاناً.">
<meta name="theme-color" content="#070A16">
<link rel="icon" type="image/png" href="favicon.png">''')

s0 = src.index('    <div class="gate" id="gate" hidden>'); s1 = src.index('    <!-- live mode -->')
src = src[:s0] + src[s1:]

for a in ['<div class="fr"><label for="tStyle">', '<div class="fr"><label for="ocrTier">',
          '<div class="fr"><label for="voiceSrc">', '<div class="fr"><label for="voice">']:
    sub(a, a.replace('<div class="fr">', '<div class="fr" hidden>'))
sub('<small>ارفع صورة الشاشة ويقرأ النص ويفهم الحوار والمهمة والخيارات</small>',
    '<small>ارفع صورة الشاشة فيقرأ النص ويرتّب الحوار والمهمة والخيارات</small>')
sub('<span>بعد قراءة الصورة يظهر هنا: من يتكلم، وماذا يقول، ومهمتك الحالية، والخيارات المتاحة.</span>',
    '<span>بعد قراءة الصورة يظهر هنا: من يتكلم، وماذا يقول، ومهمتك، والخيارات المتاحة. تُقرأ الصورة داخل متصفحك ولا تُرفع لأي خادم.</span>')

FREE_JS = r'''function setEngine(st){const e=$("engine");e.className="engine "+(st||"");e.lastChild.textContent=st==="ok"?"ترجمة مجانية":st==="bad"?"لا يوجد اتصال":"جارٍ الفحص";e.title="Google، ثم MyMemory عند التعطل"}
async function getSample(){setEngine(navigator.onLine===false?"bad":"ok");return FREE}
addEventListener("online",()=>setEngine("ok"));addEventListener("offline",()=>setEngine("bad"));

/* ============ free engine: Google, then MyMemory; OCR with Tesseract inside the browser ============ */
const escRe=s=>s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
const FREE={
  async _get(url,signal){
    let r;try{r=await fetch(url,{signal})}catch(e){if(signal&&signal.aborted)throw {code:"cancelled"};throw {code:"upstream_error",net:true}}
    if(r.status===429)throw {code:"rate_limited"};if(!r.ok)throw {code:"upstream_error"};return r.json()},
  async google(text,s,t,signal){
    const d=await this._get("https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&sl="+(s==="auto"?"auto":s)+"&tl="+t+"&q="+encodeURIComponent(text),signal);
    const out=(d[0]||[]).map(x=>(x&&x[0])||"").join("");if(!out.trim())throw {code:"empty_completion"};
    return {text:out,lang:typeof d[2]==="string"?d[2]:null,engine:"Google"}},
  async mymemory(text,s,t,signal){
    const parts=[];let buf="";for(const w of text.split(/(?<=[.!?؟。\n])\s*/)){if((buf+" "+w).length>450&&buf){parts.push(buf);buf=w}else buf=buf?buf+" "+w:w}if(buf)parts.push(buf);
    const out=[];let lang=null;
    for(const p of parts){const d=await this._get("https://api.mymemory.translated.net/get?q="+encodeURIComponent(p)+"&langpair="+(s==="auto"?"autodetect":s)+"|"+t,signal);
      const tx=d&&d.responseData&&d.responseData.translatedText;if(+d.responseStatus!==200||!tx||/MYMEMORY WARNING/i.test(tx))throw {code:+d.responseStatus===429?"rate_limited":"upstream_error"};
      out.push(tx);lang=lang||d.responseData.detectedLanguage||null}
    return {text:out.join(" "),lang,engine:"MyMemory"}},
  async translate(text,s,t,terms,signal){
    let src0=text;for(const g of terms||[])src0=src0.replace(new RegExp(escRe(g.from),"gi"),g.to);   // glossary: the fixed term wins
    const pieces=splitText(src0,1200),out=[];let lang=null,engine="";
    for(const p of pieces){
      if(!p.trim()){out.push(p);continue}
      const lead=p.match(/^\s*/)[0],trail=p.match(/\s*$/)[0];let r=null,err=null;
      for(const f of ["google","mymemory"]){
        for(let a=0;a<2&&!r;a++){try{r=await this[f](p.trim(),s,t,signal)}catch(e){if(e.code==="cancelled")throw e;err=e;if(e.code!=="upstream_error"||!e.net)break;await new Promise(z=>setTimeout(z,600))}}
        if(r)break}
      if(!r)throw err||{code:"upstream_error"};
      out.push(lead+r.text+trail);lang=lang||r.lang;engine=r.engine}
    return {text:out.join(""),lang,engine}},
  async limits(){return {images:{}}},
  _tess:null,_workers:{},
  async _loadTess(){if(window.Tesseract)return;if(!this._tess)this._tess=new Promise((ok,no)=>{const sc=document.createElement("script");sc.src="https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js";sc.onload=ok;sc.onerror=()=>{this._tess=null;no({code:"upstream_error"})};document.head.appendChild(sc)});await this._tess},
  async _worker(lang,onProgress){
    await this._loadTess();
    if(!this._workers[lang])this._workers[lang]=Tesseract.createWorker(lang,1,{logger:m=>{if(FREE._onProgress&&m.status&&typeof m.progress==="number")FREE._onProgress(m.status,m.progress)}});
    FREE._onProgress=onProgress;
    return this._workers[lang]},
  async _canvas(blob){
    const bmp=await createImageBitmap(blob);const w=bmp.width,h=bmp.height;
    const sc=w<2200?Math.min(2.5,2200/w):(w>2800?2800/w:1);   // ~2200px wide reads small game text best
    const c=document.createElement("canvas");c.width=Math.round(w*sc);c.height=Math.round(h*sc);
    const x=c.getContext("2d",{willReadFrequently:true});x.imageSmoothingQuality="high";x.drawImage(bmp,0,0,c.width,c.height);
    // grayscale, and invert dark scenes: Tesseract reads dark text on a light page best (game text is usually light on dark)
    const im=x.getImageData(0,0,c.width,c.height),d=im.data;let sum=0;
    for(let i=0;i<d.length;i+=4){const g=(d[i]*77+d[i+1]*150+d[i+2]*29)>>8;d[i]=d[i+1]=d[i+2]=g;sum+=g}
    if(sum/(d.length/4)<128)for(let i=0;i<d.length;i+=4){d[i]=d[i+1]=d[i+2]=255-d[i]}
    x.putImageData(im,0,0);return c},
  async readImage(blob,t,{signal,onProgress,skipIf}={}){
    const lang=TESS[src.value]||"eng";
    const worker=await (await this._worker(lang,onProgress));
    if(signal&&signal.aborted)throw {code:"cancelled"};
    const canvas=await this._canvas(blob);
    const {data}=await worker.recognize(canvas,{},{blocks:true,text:false,hocr:false,tsv:false});
    if(signal&&signal.aborted)throw {code:"cancelled"};
    const W=canvas.width,H=canvas.height,blocks=[];
    // own geometric grouping (same rules as the desktop app): Tesseract's paragraphs merge distant texts
    const lines0=[];for(const bl of data.blocks||[])for(const pa of bl.paragraphs||[])for(const l of pa.lines||[]){
      const text=l.text.replace(/\s+/g," ").trim();if(l.confidence>=35&&(text.match(/\p{L}/gu)||[]).length>=2)lines0.push({text,b:l.bbox,h:l.bbox.y1-l.bbox.y0})}
    lines0.sort((a,b)=>(Math.round(a.b.y0/4)-Math.round(b.b.y0/4))||(a.b.x0-b.b.x0));
    const groups=[];
    for(const ln of lines0){let target=null;
      for(const g of groups.slice(-4).reverse()){const last=g[g.length-1],gap=ln.b.y0-last.b.y1,h=Math.max(last.h,ln.h);
        const overlap=Math.min(last.b.x1,ln.b.x1)-Math.max(last.b.x0,ln.b.x0);
        const left=Math.abs(ln.b.x0-last.b.x0)<h*1.5,centered=Math.abs((ln.b.x0+ln.b.x1)/2-(last.b.x0+last.b.x1)/2)<h*2;
        const newItem=/[.!?。؟…]$/.test(last.text)&&/^[\p{Lu}\d]/u.test(ln.text);
        if(gap>-h*.5&&gap<h*.9&&Math.abs(ln.h-last.h)<h*.45&&(overlap>0||left||centered)&&!newItem){target=g;break}}
      target?target.push(ln):groups.push([ln])}
    // a vertical run of short single lines, aligned and evenly spaced = dialogue choices / menu
    const choice=new Set();
    for(let i=0;i<groups.length;i++){let j=i;
      while(j+1<groups.length&&groups[j].length===1&&groups[j+1].length===1){const a=groups[j][0],c=groups[j+1][0],h=Math.max(a.h,c.h);
        if(Math.abs(a.b.x0-c.b.x0)<h*1.5&&c.b.y0-a.b.y1>=0&&c.b.y0-a.b.y1<h*2.5&&a.text.length<60&&c.text.length<60)j++;else break}
      if(j>i){for(let k=i;k<=j;k++)choice.add(k);i=j}}
    groups.forEach((g,gi)=>{
      let label="";
      if(g.length>1){const f=g[0],widest=Math.max(...g.slice(1).map(l=>l.b.x1-l.b.x0));
        if(f.text.split(" ").length<=3&&f.text.length<=26&&!/[.!?,;]$/.test(f.text)&&(f.b.x1-f.b.x0)<widest*.6){label=f.text.replace(/[:：]$/,"");g=g.slice(1)}}
      const x0=Math.min(...g.map(l=>l.b.x0)),y0=Math.min(...g.map(l=>l.b.y0)),x1=Math.max(...g.map(l=>l.b.x1)),y1=Math.max(...g.map(l=>l.b.y1));
      const quest=/^(quest|objective|mission|task|goal)s?$/i.test(label);
      blocks.push({type:choice.has(gi)?"choice":quest?"quest":label?"dialogue":"other",speaker:quest?"":label,original:g.map(l=>l.text).join(" "),
        box:[x0/W*100,y0/H*100,(x1-x0)/W*100,(y1-y0)/H*100]})});
    if(!blocks.length)return {lang:null,scene:"",blocks:[]};
    if(skipIf&&skipIf(blocks.map(b=>b.original).join("\n")))return {same:true,blocks:[]};   // live mode: same text as before, no translation request
    const terms=glossFor(blocks.map(b=>b.original).join(" "));
    const all=await this.translate(blocks.map(b=>b.original).join("\n"),src.value==="auto"?"auto":src.value,t,terms,signal);
    let parts=all.text.split("\n").map(x=>x.trim()).filter(Boolean);
    if(parts.length!==blocks.length){parts=[];for(const b of blocks)parts.push((await this.translate(b.original,"auto",t,terms,signal)).text)}
    blocks.forEach((b,i)=>b.translation=parts[i]);
    const sp=blocks.filter(b=>b.speaker);
    if(sp.length){const st=await this.translate(sp.map(b=>b.speaker).join("\n"),"auto",t,[],signal);const ps=st.text.split("\n");sp.forEach((b,i)=>b.speaker_tr=(ps[i]||b.speaker).trim())}
    const counts={dialogue:0,choice:0,quest:0};blocks.forEach(b=>{if(counts[b.type]!==undefined)counts[b.type]++});
    const scene=[counts.dialogue&&"حوار",counts.quest&&"مهمة",counts.choice&&`${fmt(counts.choice)} خيارات`].filter(Boolean).join("، ");
    return {lang:normLang(all.lang),scene:scene?("في هذه اللقطة: "+scene+"."):"",blocks}}
};
const TESS={auto:"eng",en:"eng",fr:"fra",es:"spa",de:"deu",it:"ita",pt:"por",tr:"tur",ru:"rus",uk:"ukr",pl:"pol",nl:"nld",id:"ind",vi:"vie",ja:"jpn",ko:"kor","zh-CN":"chi_sim","zh-TW":"chi_tra",ar:"ara",fa:"fas",ur:"urd",hi:"hin",th:"tha"};'''

i = src.index('function setEngine(st){'); j = src.index('getSample();', i)
src = src[:i] + FREE_JS + "\n" + src[j:]

sub('''      const r=await sample(buildPrompt(chunk.trim(),s,t,style,terms),{signal,modelTier:"quick",
        onText:({text})=>{$("output").value=before+lead+extract(text).text;outCount();$("output").scrollTop=1e9}});
      const x=extract(r.text||"");if(!x.text.trim())throw {code:"empty_completion"};if(r.truncated)trunc=true;''',
    '''      const r=await sample.translate(chunk.trim(),s,t,terms,signal);
      const x={text:r.text||"",lang:r.lang};if(!x.text.trim())throw {code:"empty_completion"};''')
sub('''      const raw=await sample.json(buildShotPrompt(t,style),{images:[shot.blob],modelTier:tier,signal:controller.signal});''',
    '''      const raw=await sample.readImage(shot.blob,t,{signal:controller.signal,onProgress:(st,p)=>{
        if(/load|initializ/.test(st))setStatus(`تجهيز قارئ النصوص (أول مرة فقط)… ${Math.round(p*100)}%`);
        else if(/recogniz/.test(st)){setStatus(`قراءة النص من الصورة… ${Math.round(p*100)}%`);setProg(10+p*70)}}});''')
sub('''    setProg(8);setStatus(tier==="default"?"جارٍ قراءة الصورة بدقة… قد يستغرق ذلك نصف دقيقة.":"جارٍ قراءة الصورة وفهم المشهد…");''',
    '''    setProg(8);setStatus("جارٍ قراءة الصورة…");''')
sub('''    let prog=8;const pt=setInterval(()=>{prog=Math.min(90,prog+(90-prog)*.08);setProg(prog)},400);''', '''    const pt=0;''')

sub('''  const raw=await sample.json(buildShotPrompt(t,S.tStyle),{images:[blob],modelTier:"quick",signal});
  return {lang:normLang(raw&&raw.lang),scene:"",blocks:cleanBlocks(raw)}}''',
    '''  const raw=await sample.readImage(blob,t,{signal,skipIf});if(raw&&raw.same)return raw;
  return {lang:normLang(raw&&raw.lang),scene:"",blocks:cleanBlocks(raw)}}''')
sub('const ERR={not_granted:', '''const ERR_FREE={rate_limited:"وصلت خدمة الترجمة المجانية إلى حدّها مؤقتاً. انتظر دقيقة ثم أعد المحاولة؛ الأجزاء المترجمة محفوظة.",
  upstream_error:"تعذّر الوصول إلى خدمة الترجمة. تأكد من اتصالك بالإنترنت ثم أعد المحاولة.",
  empty_completion:"رجعت خدمة الترجمة بنتيجة فارغة. أعد المحاولة."};
const ERR={not_granted:''')
src = src.replace('ERR[code]||ERR.upstream_error', 'ERR_FREE[code]||ERR[code]||ERR_FREE.upstream_error')

i = src.index('function getTts(){ttsP=ttsP||'); j = src.index('\n', i)
src = src[:i] + 'function getTts(){return Promise.resolve(null)}  // public site: the device voice only' + src[j:]
sub('  if(S.voiceSrc!=="device"){const t=await getTts();', '  if(false){const t=await getTts();')
sub('  $("styleChip").textContent=STYLES[S.tStyle].label;', '  $("styleChip").textContent="ترجمة مجانية";')

assert "claude.use" not in src, "leftover claude.use"
open('/home/claude/arabize-game/site/index.html', 'w', encoding='utf-8').write(src)
print("site written", len(src))
