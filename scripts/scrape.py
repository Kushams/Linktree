import csv, re, json, sys, urllib.parse, urllib.request, concurrent.futures as cf
csv.field_size_limit(10**9)
src='/root/.claude/uploads/a874a05b-6716-5d27-b23e-c7d6a96c10df/d7b1e534-data_www_google_com_20261008103427.csv'
rows=list(csv.DictReader(open(src,encoding='utf-8-sig',newline='')))
profiles={}
for r in rows:
    u=r['Col6_HREF'].split('?')[0].split('#')[0].rstrip('/')
    if 'linktr.ee/' in u: profiles.setdefault(u, r['Col0'])
epat=re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}')
bad=re.compile(r'\.(png|jpe?g|gif|webp|svg|css|js)$|sentry|linktr\.ee$|example\.com|@2x|@3x',re.I)
def fetch(u):
    for _ in range(2):
        try:
            req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
            return urllib.request.urlopen(req,timeout=30).read().decode('utf-8','replace')
        except Exception as e: err=str(e)
    return None
def work(item):
    u,name=item; h=fetch(u)
    if h is None: return u,name,None,[]
    h2=urllib.parse.unquote(h.replace('\\u0026','&').replace('\\u002F','/').replace('\\n',' ').replace('\\r',' '))
    ems={m.strip('.').lower() for m in epat.findall(h2) if not bad.search(m)}
    links=set(re.findall(r'"url":"(https?://[^"]+)"',h)) 
    return u,name,sorted(ems),sorted(links)
res=[]
with cf.ThreadPoolExecutor(6) as ex:
    for r in ex.map(work, profiles.items()): res.append(r)
json.dump(res,open('linktree_results.json','w'))
fail=[u for u,n,e,l in res if e is None]
print(len(profiles),'profiles;',len(fail),'failed')
allem={}
for u,n,e,l in res:
    for x in e or []: allem.setdefault(x,[]).append(u)
print(len(allem),'unique emails')
for x,us in sorted(allem.items()): print(x,'|',us[0])
