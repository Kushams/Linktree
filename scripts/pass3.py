import re, json, csv, urllib.request, urllib.parse, concurrent.futures as cf
remove=set('Bigmoecoo Fermenteddarknessradio Lepopupparisien MC5agency RCFr alicedicredico anotherbiowithalinktree atarashi beaumont.presents bjorkfr blackjackrecords bsidelosangeles djcontrolinpulset7 eclecticeventsfrance fab17 franceinhk franceinsouthafrica goldengateband itlldoclub lefrance1 lekkerleute mana.intl meet.thebizz music.4.animals nowadaysrecords openherbeprod plvr.io seanapse thirdfloorsounds zebbiesgarden eco_sistema durevie'.split())
have={r['profile_url'] for r in csv.DictReader(open('/home/user/Linktree/dj_emails.csv'))}
no=json.load(open('noemail.json'))
targets=[u for u in no if u not in have and u.rsplit('/',1)[1] not in remove]
print(len(targets),'targets')
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'en'}
def fetch(u,t=20):
    for _ in range(2):
        try:
            r=urllib.request.urlopen(urllib.request.Request(u,headers=HDR),timeout=t)
            return r.read(2_500_000).decode('utf-8','replace')
        except Exception: pass
    return ''
epat=re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}')
bad=re.compile(r'\.(png|jpe?g|gif|webp|svg|css|js|woff2?)$|sentry|wixpress|example|exemple|domain|noreply|no-reply|@2x|@3x|soundcloud|tiktok|youtube|google|bandcamp|facebook|instagram|mixcloud|spotify|apple\.com|cloudflare|schema\.org|u003e|yourname|email@|your@|xxx',re.I)
def emails(h):
    h=urllib.parse.unquote(h.replace('\\u0040','@').replace('\\u002F','/').replace('&#64;','@').replace('\\n',' ').replace('\\"',' '))
    return {m.strip('.').lower() for m in epat.findall(h) if not bad.search(m)}
def links(u):
    h=fetch(u,30)
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',h,re.S)
    if not m: return []
    pp=json.loads(m.group(1))['props']['pageProps']
    urls=[x.get('url') for x in pp.get('links',[]) if x.get('url')]+[x.get('url') for x in pp.get('socialLinks',[]) if x.get('url')]
    return list(dict.fromkeys(x for x in urls if x.startswith('http')))
def pick(urls):
    out=[]
    for x in urls:
        p=urllib.parse.urlparse(x); host=p.netloc.lower().replace('www.',''); segs=[s for s in p.path.split('/') if s]
        if host=='soundcloud.com' and len(segs)==1: out.append(x)
        elif host in('tiktok.com','m.tiktok.com') and segs and segs[0].startswith('@') and len(segs)==1: out.append(x)
        elif host=='youtube.com' and segs and (segs[0].startswith('@') or segs[0] in('c','channel','user')) : out.append(x.rstrip('/')+'/about' if not x.rstrip('/').endswith('about') else x)
        elif host.endswith('bandcamp.com') and host!='bandcamp.com' and len(segs)<=1: out.append(x)
        elif host=='mixcloud.com' and len(segs)==1: out.append(x)
        elif host in('facebook.com','m.facebook.com') and len(segs)==1 and segs[0] not in('sharer','share.php'): out.append(x.replace('www.facebook','m.facebook'))
        elif host in('x.com','twitter.com') and len(segs)==1: out.append(x)
        elif host=='linktr.ee' : pass
        elif host in('ra.co','residentadvisor.net') and 'dj' in x: out.append(x)
    return list(dict.fromkeys(out))[:6]
def work(u):
    found={}
    for l in pick(links(u)):
        for e in emails(fetch(l)): found.setdefault(e,l)
    return u,found
with cf.ThreadPoolExecutor(5) as ex: res=list(ex.map(work,targets))
json.dump(res,open('pass3_results.json','w'))
hits=[(u,f) for u,f in res if f]
print(len(hits),'profiles with a hit')
for u,f in hits:
    for e,s in f.items(): print(u.rsplit('/',1)[1],'|',e,'|',s[:70])
