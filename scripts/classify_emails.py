# Label each email (personal / own booking / management / agency / label / general) and build one row per artist.
import csv, re
from collections import defaultdict
FREE=re.compile(r'^(gmail|googlemail|outlook|hotmail|live|icloud|me|mac|yahoo|ymail|proton|protonmail|pm|free|wanadoo|orange|gmx|web|aol|msn|laposte|sfr|hotmail\.co)\.',re.I)
norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
def lcs(a,b):
    best=0
    for i in range(len(a)):
        for j in range(i+best+1,len(a)+1):
            if a[i:j] in b: best=j-i
            else: break
    return best
KW_BOOK=re.compile(r'book|bkng|booking',re.I); KW_MGMT=re.compile(r'mgmt|management|manager|^mgt',re.I)
KW_PROMO=re.compile(r'promo|press|pr$|demo',re.I); KW_GEN=re.compile(r'^(info|contact|hello|hi|mail|office|enquir|inquir|general|team|support|studio|events?)',re.I)
AGENCY=re.compile(r'agency|agent|talent|artists|booking|management|mgmt|touring|bookings|presents|entertainment|events|promo|prod',re.I)
LABEL=re.compile(r'record|label|music|sound|audio|studio|media',re.I)
def classify(email,handle,title):
    local,dom=email.split('@'); domstem=norm(dom.rsplit('.',1)[0].split('.')[-1] if dom.count('.')>1 and dom.split('.')[-2] in('co','com','org') else dom.rsplit('.',1)[0])
    names=[norm(handle),norm(title)]
    mine=lambda s:any(len(n)>=4 and lcs(n,norm(s))>=min(5,len(n)) for n in names)
    free=bool(FREE.match(dom))
    if free:
        if KW_BOOK.search(local): return 'booking (own address)'
        if KW_MGMT.search(local): return 'management'
        if KW_PROMO.search(local): return 'promo/demos'
        return 'personal'
    if mine(dom):  # artist's own domain
        if KW_BOOK.search(local): return 'booking (own address)'
        if KW_MGMT.search(local): return 'management'
        if KW_PROMO.search(local): return 'promo/demos'
        if KW_GEN.match(local): return 'general contact (own domain)'
        return 'personal'
    if KW_BOOK.search(local) or KW_MGMT.search(local) or AGENCY.search(dom): return 'agency/management'
    if LABEL.search(dom) and not AGENCY.search(dom): return 'label'
    return 'agency/management'
RANK=['personal','general contact (own domain)','booking (own address)','promo/demos','management','agency/management','label']
rows=list(csv.DictReader(open('dj_emails.csv')))
by=defaultdict(list)
for r in rows:
    h=r['profile_url'].rsplit('/',1)[1]
    t=re.split(r' Official| - Listen| \| | - TikTok| - Linktree',r['profile_title'])[0].strip(' "') or h
    if re.search(r'[@:]',t) and not t.startswith('@'): t=h
    r['email_type']=classify(r['email'],h,t); r['artist']=t; by[r['profile_url']].append(r)
fields=['email','email_type','source','profile_title','profile_url','found_on']
w=csv.DictWriter(open('dj_emails.csv','w',newline=''),fieldnames=fields,extrasaction='ignore'); w.writeheader()
for r in sorted(rows,key=lambda r:r['email']): w.writerow(r)
out=csv.writer(open('dj_emails_only.csv','w',newline='')); out.writerow(['artist','email','email_type','other_emails'])
res=[]
for u,rs in by.items():
    rs.sort(key=lambda r:(RANK.index(r['email_type']) if r['email_type'] in RANK else 9, r['email']))
    p=rs[0]; others='; '.join(f"{r['email']} ({r['email_type']})" for r in rs[1:])
    res.append((p['artist'],p['email'],p['email_type'],others))
res.sort(key=lambda x:x[0].lower()); out.writerows(res)
from collections import Counter
print(len(res),'artists'); print(Counter(r[2] for r in res))
