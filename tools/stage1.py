"""Artifact HTML -> stage1 (plain browser download instead of the claude.ai downloads capability)."""
import sys
s = open(sys.argv[1], encoding="utf-8").read()
old = '''  dlP=dlP||((window.claude&&window.claude.use)?window.claude.use("downloads").catch(()=>null):Promise.resolve(null));
  const d=await dlP;if(!d)return toast("الحفظ غير متاح هنا؛ استخدم «نسخ»",true);
  try{await d.save({filename:"arabize_translation.txt",data:new Blob(["\ufeff"+t],{type:"text/plain;charset=utf-8"})});toast("تم حفظ الملف")}catch(e){toast("لم يتم الحفظ",true)}};'''
new = '''  const a=document.createElement("a");a.href=URL.createObjectURL(new Blob(["\\ufeff"+t],{type:"text/plain;charset=utf-8"}));
  a.download="arabize_translation.txt";document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500);toast("تم حفظ الملف")};'''
assert old in s
open(sys.argv[2], "w", encoding="utf-8").write(s.replace(old, new))
