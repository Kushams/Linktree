import json, re, csv, urllib.parse
res=json.load(open('linktree_results.json')); r2=json.load(open('pass2_results.json'))
titles={u:n for u,n,e,l in res}
placeholder=re.compile(r'(example|exemple|domaine|domain\.|company\.com|xxx|^nom@|^pro@gmail|utilisateur|^u003e|youremail|votre)',re.I)
def norm(s): return re.sub(r'[^a-z0-9]','',s.lower())
def lcs(a,b):
    best=0
    for i in range(len(a)):
        for j in range(i+best+1,len(a)+1):
            if a[i:j] in b: best=j-i
            else: break
    return best
def clean(e):
    e=re.sub(r'^u003e','',e)
    return e
rows={}  # email -> dict
for u,n,ems,l in res:
    for e in ems or []:
        if e=='maddyjay.contact@gmail.comfrench' or e=='onlybooking@lethimcookradio.com': continue
        rows.setdefault(e,{'email':e,'source':'linktree page','profile':u,'found_on':u})
for u,links,out in r2:
    h=norm(u.rsplit('/',1)[1])
    for e,site in out.items():
        e=clean(e)
        if placeholder.search(e) or re.search(r'\.(com|fr|org|net)[a-z]{3,}$',e) and e.count('.')>=1 and False: continue
        host=urllib.parse.urlparse(site).netloc.lower().replace('www.','')
        stem=norm(host.rsplit('.',1)[0])
        if lcs(h,stem)>=5 or lcs(h,norm(e.split('@')[0]))>=5:
            rows.setdefault(e,{'email':e,'source':'artist website','profile':u,'found_on':site.split('?')[0]})
with open('/home/user/Linktree/dj_emails.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['email','source','profile_title','profile_url','found_on'])
    for e in sorted(rows):
        d=rows[e]; w.writerow([e,d['source'],titles.get(d['profile'],''),d['profile'],d['found_on']])
from collections import Counter
print(len(rows),Counter(d['source'] for d in rows.values()))
for e,d in sorted(rows.items()):
    if d['source']=='artist website': print(e,'|',d['profile'],'|',d['found_on'])
