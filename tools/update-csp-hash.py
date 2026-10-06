import re,hashlib,base64
import sys
p = sys.argv[1] if len(sys.argv) > 1 else 'EDIFACT-Viewer.html'
s=open(p,encoding='utf-8').read()
def h(t): return base64.b64encode(hashlib.sha256(t.encode('utf-8')).digest()).decode()
st=re.findall(r'<style>(.*?)</style>',s,re.S); sc=re.findall(r'<script>(.*?)</script>',s,re.S)
assert len(st)==1 and len(sc)==1
s=re.sub(r"'sha256-[^']*'(?=; style-src-elem)", "'sha256-%s'"%h(sc[0]), s)
s=re.sub(r"style-src-elem 'sha256-[^']*'", "style-src-elem 'sha256-%s'"%h(st[0]), s)
open(p,'w',encoding='utf-8').write(s)
print(h(sc[0]),h(st[0]))
