# Dig through all of an artist's linked pages for location evidence. Usage: locate.py handle [handle...]
import re, json, sys, urllib.request, urllib.parse, concurrent.futures as cf
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'en'}
def fetch(u,t=25):
    for _ in range(2):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=HDR),timeout=t).read(3_000_000).decode('utf-8','replace')
        except Exception: pass
    return ''
def links(h):
    t=fetch('https://linktr.ee/'+h,30); m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',t,re.S)
    pp=json.loads(m.group(1))['props']['pageProps']
    return [x.get('url') for x in pp.get('links',[])+pp.get('socialLinks',[]) if x.get('url','').startswith('http')]
SKIP=re.compile(r'instagram|facebook|spotify|apple\.com|deezer|tidal|amazon|paypal|wa\.me|whatsapp|patreon|shop|merch|ticket|eventbrite|dice\.fm|shotgun',re.I)
def evidence(url,h):
    host=urllib.parse.urlparse(url).netloc.lower().replace('www.','')
    if SKIP.search(host): return []
    if host.startswith('on.soundcloud') or host=='soundcloud.app.goo.gl': 
        try: url=urllib.request.urlopen(urllib.request.Request(url,headers=HDR),timeout=20).geturl()
        except Exception: return []
    t=fetch(url)
    if not t: return []
    out=[]
    # SoundCloud hydration: "city":"..","country_code":".."
    for m in re.finditer(r'"city":"([^"]*)"[^{}]{0,200}?"country_code":"([A-Za-z]{2})"',t): out.append(('soundcloud',m.group(1),m.group(2)))
    for m in re.finditer(r'"country_code":"([A-Za-z]{2})"[^{}]{0,200}?"city":"([^"]*)"',t): out.append(('soundcloud',m.group(2),m.group(1)))
    # Bandcamp / generic location fields
    for m in re.finditer(r'class="location[^"]*"[^>]*>([^<]{2,60})<',t): out.append(('location-field',m.group(1).strip(),''))
    for m in re.finditer(r'"addressCountry":"([^"]+)"|"addressLocality":"([^"]+)"',t): out.append(('schema',m.group(1) or m.group(2),''))
    for m in re.finditer(r'(?:Based in|based in|Basé à|Based out of|Location|From)[:\s]+([A-Z][A-Za-zÀ-ÿ\' ,-]{2,40})',re.sub(r'<[^>]+>',' ',t)): out.append(('text',m.group(1).strip(),''))
    return [(host,)+o for o in dict.fromkeys(out)][:8]
def work(h):
    ls=list(dict.fromkeys(links(h))); ev=[]
    for u in ls[:14]: ev+=evidence(u,h)
    return h,ls,ev
if __name__=='__main__':
    with cf.ThreadPoolExecutor(5) as ex:
        for h,ls,ev in ex.map(work,sys.argv[1:]):
            print('=====',h,'|',len(ls),'links')
            for e in ev[:10]: print('  ',e)
