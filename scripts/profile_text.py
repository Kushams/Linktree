# Cache each Linktree profile's title, bio and link titles (used for names and country inference).
import re, json, sys, csv, urllib.request, concurrent.futures as cf
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'}
def get(u):
    for _ in range(2):
        try:
            t=urllib.request.urlopen(urllib.request.Request(u,headers=HDR),timeout=30).read().decode('utf-8','replace')
            pp=json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',t,re.S).group(1))['props']['pageProps']
            a=pp.get('account',{})
            return u,{'title':a.get('pageTitle') or '','bio':a.get('description') or '','links':[x.get('title') for x in pp.get('links',[]) if x.get('title')][:40]}
        except Exception: pass
    return u,{'title':'','bio':'','links':[]}
urls=json.load(open(sys.argv[1])); cache={}
try: cache=json.load(open(sys.argv[2]))
except Exception: pass
todo=[u for u in urls if u not in cache]
with cf.ThreadPoolExecutor(6) as ex:
    for u,d in ex.map(get,todo): cache[u]=d
json.dump(cache,open(sys.argv[2],'w'),ensure_ascii=False)
print(len(cache),'cached')
