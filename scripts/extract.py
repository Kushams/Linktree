import csv, re, sys, urllib.parse
src = sys.argv[1]; out = sys.argv[2]
csv.field_size_limit(10**9)
pat = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}')
rows = list(csv.DictReader(open(src, encoding='utf-8-sig', newline='')))
found = {}
for r in rows:
    texts = []
    for k, v in r.items():
        if v and not v.startswith('data:'):
            texts.append(v); texts.append(urllib.parse.unquote(v))
    blob = ' '.join(texts)
    for m in pat.findall(blob):
        e = m.strip('.').lower()
        if re.search(r'\.(png|jpg|jpeg|gif|webp|svg)$', e): continue
        d = found.setdefault(e, {'name': r['Col0'], 'url': r['Col6_HREF'], 'snippet': r['Col4']})
with open(out, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['email','profile_title','profile_url'])
    for e, d in sorted(found.items()): w.writerow([e, d['name'], d['url']])
print(len(rows), 'rows;', len(found), 'unique emails')
for e, d in sorted(found.items()): print(e, '|', d['url'])
