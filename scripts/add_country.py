# Infer each artist's country from bio, link titles, search snippets and email domain. Adds country + country_basis.
import csv, re, json
csv.field_size_limit(10**9)
cache=json.load(open('data/profile_text.json'))
snip={}
for f in ['data/source_google_results.csv','data/source_duckduckgo_1.csv','data/source_duckduckgo_2.csv']:
    for r in csv.DictReader(open(f,encoding='utf-8-sig',newline='')):
        u=(r.get('Col6_HREF') or r.get('Col0_HREF') or '').split('?')[0].split('#')[0].rstrip('/')
        snip.setdefault(u,(r.get('Col4') if 'google' in f else r.get('Col2','')) or '')
NOISE=re.compile(r"rinse france|rinse fm|rinse\.fm|france inter|france 3|france 24|france info|france culture|france musique|radio france|dj ?mag(azine)? france|tour de france|made in france|france gall|mouv'|\bfip\b|trax magazine|techno mag france|dubstep france|magazine france|\bfrance fm\b|france télévisions|europe tour|world tour|north america",re.I)
C={
 'France':r"france|français|french|paris|lyon|marseille|toulouse|bordeaux|lille|nantes|nice\b|cannes|montpellier|strasbourg|rennes|grenoble|hauts-de-france|île-de-france|ile-de-france|meaux|réunion|martinique|aix-en-provence|toulon|dijon|tours\b|caen|rouen|brest|saint-|basé à|soirées|mariages|événements|animation|depuis plus",
 'Germany':r"germany|german|deutschland|berlin|hamburg|münchen|munich|köln|cologne|frankfurt|leipzig|bayreuth|düsseldorf|stuttgart|dortmund|impressum",
 'United Kingdom':r"\buk\b|united kingdom|england|london|manchester|bristol|glasgow|leeds|birmingham|nottingham|liverpool|scotland|wales|sheffield",
 'United States':r"\busa\b|\bu\.s\.|united states|new york|nyc|brooklyn|los angeles|chicago|miami|san francisco|detroit|texas|houston|dallas|atlanta|las vegas|seattle|orlando|indiana|maui|harlem|bay area|california|florida|\bohio\b|utah|cincinnati|michigan",
 'Spain':r"spain|españa|madrid|barcelona|valencia|ibiza|sevilla|bilbao|málaga",
 'Italy':r"italy|italia|roma\b|rome|milano|milan|napoli|torino|bologna",
 'Netherlands':r"netherlands|nederland|amsterdam|rotterdam|utrecht|eindhoven|holland",
 'Belgium':r"belgium|belgique|belgië|brussels|bruxelles|antwerp|ghent|gent\b|liège",
 'Switzerland':r"switzerland|suisse|zurich|zürich|geneva|genève|basel|lausanne|bern\b",
 'Ireland':r"ireland|dublin|cork\b",
 'Brazil':r"brazil|brasil|são paulo|sao paulo|rio de janeiro",
 'Mexico':r"mexico|méxico|cdmx",
 'Japan':r"japan|tokyo|osaka|kyoto",
 'South Korea':r"korea|seoul",
 'Canada':r"canada|toronto|montreal|montréal|vancouver|québec",
 'Australia':r"australia|sydney|melbourne|naarm|brisbane|perth",
 'Portugal':r"portugal|lisbon|lisboa|porto\b",
 'Belarus':r"belarus|minsk",'Ukraine':r"ukraine|kyiv|kiev|odesa",'Algeria':r"algeria|algérie|algiers",'India':r"india|mumbai|delhi|bangalore",
 'Lebanon':r"lebanon|beirut",'Colombia':r"colombia|medellín|bogotá",'Argentina':r"argentina|buenos aires",'Austria':r"austria|vienna|wien\b",'Poland':r"poland|warsaw|kraków",
}
TLD={'.fr':'France','.de':'Germany','.co.uk':'United Kingdom','.uk':'United Kingdom','.nl':'Netherlands','.es':'Spain','.it':'Italy','.ch':'Switzerland','.be':'Belgium','.jp':'Japan','.com.au':'Australia','.au':'Australia','.ie':'Ireland','.br':'Brazil','.pt':'Portugal','.gr':'Greece','.pl':'Poland','.at':'Austria','.ca':'Canada','.mx':'Mexico'}
FLAG={'🇫🇷':'France','🇩🇪':'Germany','🇬🇧':'United Kingdom','🇺🇸':'United States','🇪🇸':'Spain','🇮🇹':'Italy','🇳🇱':'Netherlands','🇧🇪':'Belgium','🇨🇭':'Switzerland','🇮🇪':'Ireland','🇧🇷':'Brazil','🇲🇽':'Mexico','🇯🇵':'Japan','🇰🇷':'South Korea','🇨🇦':'Canada','🇦🇺':'Australia','🇵🇹':'Portugal','🇺🇦':'Ukraine','🇮🇳':'India','🇧🇾':'Belarus','🇩🇿':'Algeria','🇨🇴':'Colombia','🇦🇷':'Argentina','🇦🇹':'Austria','🇵🇱':'Poland','🇱🇧':'Lebanon'}
BASED=re.compile(r"(?:based in|based at|from|living in|basé[e]? (?:à|a|en|sur)|\bin)\s+([A-Za-zÀ-ÿ' ,-]{3,40})",re.I)
OVERRIDE={
    'https://linktr.ee/djduvide':('United Kingdom', 'Mixcloud profile: DJ / Producer based in London'),
    'https://linktr.ee/djmoule':('France', 'booking via Unison Prod, a French production agency (Saintes)'),
    'https://linktr.ee/Ra.Ph':('France', 'Resident Advisor: eastern France, Silodom resident (label on his Linktree)'),
    'https://linktr.ee/reelow':('Spain', 'Hungarian-born, based in Barcelona (Radio Intense interview)'),
    'https://linktr.ee/olliemundy':('Spain', 'British DJ, currently based in Ibiza (interviews)'),
    'https://linktr.ee/djsource':('Europe (city unconfirmed)', 'plays Berlin/HÖR/Radio Rudina/Bratislava; home city not confirmed'),
    'https://linktr.ee/marligrosskopf':('Australia','agents/email: Australian (marlimusicau, Weaver Agency AU)'),
    'https://linktr.ee/DJWicked':('United States','agent Marc Allman (US)'),
    'https://linktr.ee/stghislain':('France','page title: Hauts-de-France, France'),
    'https://linktr.ee/deejay2fly':('Germany', 'page bio: Bayreuth'),
    'https://linktr.ee/MiniB.Events':('Belgium', 'own website: Liège, Belgique'),
    'https://linktr.ee/jef_nice':('Belgium', 'page link: Maanrock Festival (Mechelen)'),
    'https://linktr.ee/djathome':('Belgium', 'page links: Belgium Pride, De School Amsterdam (Europe)'),
    'https://linktr.ee/Nickygdj':('United Kingdom', 'UK phone number format'),
    'https://linktr.ee/djtomwax':('Germany', 'booking email .de domain'),
    'https://linktr.ee/Nathassia':('United Kingdom', 'agent domain .uk (archangeluk)'),
    'https://linktr.ee/DJJEANOFFICIAL':('Netherlands', 'booking agents on .nl domains (weak)'),
}
def infer(u,emails):
    if u in OVERRIDE: return OVERRIDE[u]
    # Only the artist's OWN Linktree bio and link titles count (not search snippets, not the page title/name).
    d=cache.get(u,{}); bio=NOISE.sub(' ',d.get('bio','')); links=NOISE.sub(' ',' '.join(d.get('links',[])))
    raw=d.get('bio','')+' '+' '.join(d.get('links',[]))
    score={}
    for fl,c in FLAG.items():
        if fl in raw: score[c]=score.get(c,0)+6
    for c,p in C.items():
        if c=='France': p=C['France'].split('|basé')[0]
        n=3*len(re.findall(p,bio.lower()))+len(re.findall(p,links.lower()))
        if n: score[c]=score.get(c,0)+n
    for m in BASED.finditer(bio):
        for c,p in C.items():
            if re.search(p.split('|basé')[0],m.group(1).lower()): score[c]=score.get(c,0)+5
    if score:
        c=max(score,key=score.get)
        if score[c]>=3: return c,'bio/links' if score[c]>=5 else 'weak bio hint'
    for e in emails:
        dom=e.split('@')[1]
        for t,c in sorted(TLD.items(),key=lambda x:-len(x[0])):
            if dom.endswith(t): return c,'email domain'
    return 'unknown',''
# long file
long=list(csv.DictReader(open('dj_emails.csv')))
emails_by={}
for r in long: emails_by.setdefault(r['profile_url'],[]).append(r['email'])
country={u:infer(u,e) for u,e in emails_by.items()}
for r in long: r['country'],r['country_basis']=country[r['profile_url']]
f=list(long[0].keys()); w=csv.DictWriter(open('dj_emails.csv','w',newline=''),fieldnames=f); w.writeheader(); w.writerows(long)
# one-per-artist file: map via email
em2c={r['email']:(r['country'],r['country_basis']) for r in long}
rows=list(csv.DictReader(open('dj_emails_only.csv')))
for r in rows: r['country'],r['country_basis']=em2c.get(r['email'],('unknown',''))
w=csv.DictWriter(open('dj_emails_only.csv','w',newline=''),fieldnames=['artist','email','email_type','country','country_basis','other_emails']); w.writeheader(); w.writerows(rows)
from collections import Counter
print(Counter(r['country'] for r in rows).most_common())
