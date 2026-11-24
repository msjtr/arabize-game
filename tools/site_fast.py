"""Live mode: read text over a moving picture too (the scene rarely stands still), and look twice as often."""
import sys
P = sys.argv[1]
s = open(P, encoding="utf-8").read()
old = '''  if(diff>sens){LV.changed=true;LV.still=0;return}        // still moving: wait until the text settles
  if(!LV.changed)return;LV.changed=false;await liveRead(c)}'''
new = '''  const now=performance.now();
  if(diff>sens){if(!LV.changed){LV.changed=true;LV.moveT=now}LV.still=0;
    // a game picture rarely stands still (camera, water, effects): while it keeps moving, read anyway every ~0.9 s
    if(now-LV.moveT>=900&&now-(LV.readT||0)>=900){LV.readT=now;await liveRead(c)}
    return}
  if(!LV.changed)return;LV.changed=false;LV.readT=now;await liveRead(c)}'''
assert old in s, "liveTick not found"
s = s.replace(old, new)
old2 = 'setInterval(()=>postMessage(0),${kind==="cam"?800:600})'
assert old2 in s
s = s.replace(old2, 'setInterval(()=>postMessage(0),${kind==="cam"?500:250})')
s = s.replace('LV.timer=setInterval(liveTick,kind==="cam"?800:600)', 'LV.timer=setInterval(liveTick,kind==="cam"?500:250)')
open(P, "w", encoding="utf-8").write(s)
print("fast live patched")
