#!/usr/bin/env python3
"""Exportiert die Marktpartner-Codenummern von bdew-codes.de als CSV für den EDIFACT-Viewer.

Aufruf:   python3 tools/bdew-codes-export.py [--out marktpartner.csv] [--delay 0.25]
Ergebnis: CSV (Semikolon, UTF-8) mit den Spalten Nummer;Name;Marktrolle.
          Im Viewer über "Marktpartner laden" einlesen.

Warum ein Skript und nicht der Viewer selbst: bdew-codes.de erlaubt keine Abfragen aus fremden Seiten
(kein CORS-Header), und der Viewer verbietet bewusst jede Netzwerkverbindung (Content-Security-Policy).

Datenschutz: Die Schnittstelle liefert auch "ContactName" (Ansprechpersonen). Dieses Feld wird nicht
gelesen und nicht gespeichert, übernommen werden nur Nummer, Firmenname und Marktrolle.

Rücksicht auf den Betreiber: Die Abfragen laufen nacheinander mit Pause (--delay). Rund 4.400 Firmen
bedeuten rund 4.400 Anfragen. Mit --cache lässt sich ein Abbruch fortsetzen, ohne alles neu zu laden.
"""
import argparse, csv, http.cookiejar, json, os, sys, time
import urllib.error, urllib.request

def make_opener():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def request(opener, base, method, path, retries=5):
    url = base + path
    headers = {
        'User-Agent': 'edifact-viewer-bdew-export/1.0 (privater Abgleich der Codenummern)',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': base + '/Codenumbers/BDEWCodes/CodeOverview',
        'Origin': base,
    }
    data = b'' if method == 'POST' else None
    wait = 2.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            with opener.open(req, timeout=30) as r:
                return r.read().decode('utf-8')
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            code = getattr(e, 'code', None)
            if code in (400, 401, 403, 404):  # sinnlos zu wiederholen
                raise SystemExit(f'Abbruch: {url} antwortet mit HTTP {code}')
            if attempt == retries - 1:
                raise SystemExit(f'Abbruch nach {retries} Versuchen: {url}: {e}')
            print(f'  Fehler ({e}), neuer Versuch in {wait:.0f} s', file=sys.stderr)
            time.sleep(wait); wait *= 2

def post_json(opener, base, path):
    body = json.loads(request(opener, base, 'POST', path))
    if body.get('Result') != 'OK':
        raise SystemExit(f'Unerwartete Antwort von {path}: {str(body)[:200]}')
    return body

def clean(s):
    return ' '.join(str(s or '').split())

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default='marktpartner.csv')
    ap.add_argument('--cache', default='marktpartner.cache.json', help='Zwischenstand zum Fortsetzen (wird am Ende gelöscht)')
    ap.add_argument('--delay', type=float, default=0.25, help='Pause zwischen Anfragen in Sekunden')
    ap.add_argument('--page-size', type=int, default=50)
    ap.add_argument('--limit', type=int, default=0, help='nur die ersten N Firmen (zum Testen)')
    ap.add_argument('--base', default='https://bdew-codes.de')
    a = ap.parse_args()
    base = a.base.rstrip('/')
    opener = make_opener()
    request(opener, base, 'GET', '/Codenumbers/BDEWCodes/CodeOverview')  # Sitzungs-Cookie holen

    companies, start, total = [], 0, None
    while total is None or start < total:
        body = post_json(opener, base, f'/Codenumbers/BDEWCodes/GetCompanyList?jtStartIndex={start}&jtPageSize={a.page_size}')
        recs = body.get('Records') or []
        total = int(body.get('TotalRecordCount', 0))
        if not recs: break
        companies += [(r['Id'], clean(r.get('Company'))) for r in recs]
        start += a.page_size
        print(f'Firmenliste: {min(len(companies), total)} von {total}', end='\r', file=sys.stderr)
        if a.limit and len(companies) >= a.limit: break
        time.sleep(a.delay)
    if a.limit: companies = companies[:a.limit]
    print(file=sys.stderr)

    cache = {}
    if os.path.exists(a.cache):
        with open(a.cache, encoding='utf-8') as f: cache = json.load(f)
        print(f'Zwischenstand gefunden: {len(cache)} Firmen bereits abgefragt', file=sys.stderr)
    for n, (cid, name) in enumerate(companies, 1):
        if str(cid) in cache: continue
        body = post_json(opener, base, f'/Codenumbers/BDEWCodes/GetBdewCodeListOfCompany?companyId={cid}&filter=')
        # ContactName wird bewusst ignoriert (personenbezogen)
        cache[str(cid)] = [[clean(r.get('BdewCode')), clean(r.get('MarketFunctionName'))] for r in body.get('Records') or []]
        print(f'Codes: {n} von {len(companies)}', end='\r', file=sys.stderr)
        if n % 100 == 0:
            with open(a.cache, 'w', encoding='utf-8') as f: json.dump(cache, f)
        time.sleep(a.delay)
    print(file=sys.stderr)

    rows = {}
    for cid, name in companies:
        for code, role in cache.get(str(cid), []):
            if code.isdigit() and len(code) == 13 and (code, role) not in rows:
                rows[(code, role)] = name
    with open(a.out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['Nummer', 'Name', 'Marktrolle'])
        for (code, role), name in sorted(rows.items()):
            w.writerow([code, name, role])
    if os.path.exists(a.cache): os.remove(a.cache)
    print(f'{len(rows)} Codenummern in {a.out} geschrieben', file=sys.stderr)

if __name__ == '__main__':
    main()
