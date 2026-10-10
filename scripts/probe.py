import re, json, urllib.request, urllib.parse
def fetch(u,t=20):
    try:
        req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'en'})
        r=urllib.request.urlopen(req,timeout=t); return r.getcode(), r.read(2_000_000).decode('utf-8','replace')
    except Exception as e: return str(e)[:60], ''
h=fetch('https://linktr.ee/Akkelarre.dj')[1]
d=json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',h,re.S).group(1))['props']['pageProps']
urls=[x['url'] for x in d.get('links',[]) if x.get('url')]+[x['url'] for x in d.get('socialLinks',[]) if x.get('url')]
print(urls)
for u in urls:
    if re.search(r'instagram|soundcloud|youtube|bandcamp|facebook|tiktok|mixcloud',u):
        c,b=fetch(u); print(c,len(b),u[:70], re.findall(r'<meta[^>]+(?:og:description|name="description")[^>]+>',b)[:1])
