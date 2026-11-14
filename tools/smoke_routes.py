"""Test de non-regression Imagine Inventory.
Se connecte en admin puis fait un GET sur toutes les routes sans parametre.
Utilisation :  python tools/smoke_routes.py [dossier_projet] [-o sortie.json]

Objectif : apres une modification, comparer le resultat a celui d'avant.
Toute route qui passe de 200/302 a 500 est une regression.
"""
import sys, os, json, warnings
warnings.filterwarnings('ignore')

proj = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else os.getcwd()
out = None
if '-o' in sys.argv:
    out = sys.argv[sys.argv.index('-o') + 1]
os.chdir(proj); sys.path.insert(0, proj)
import app as m

c = m.app.test_client()
c.get('/')
login = c.post('/login', data={'email': 'admin@imagine-events.com', 'password': 'admin123'},
               follow_redirects=False)

results, skipped = [], []
for rule in sorted(m.app.url_map.iter_rules(), key=lambda x: str(x)):
    if 'GET' not in rule.methods or rule.arguments:
        continue
    url = str(rule)
    if url.startswith(('/static', '/uploads')) or url == '/logout':
        skipped.append(url); continue
    try:
        resp = c.get(url, follow_redirects=False)
        raw = resp.get_data()
        text = raw.decode('utf-8', 'replace') if (resp.mimetype or '').startswith(('text/', 'application/json')) else ''
        results.append({'endpoint': rule.endpoint, 'url': url, 'status': resp.status_code,
                        'size': len(raw), 'trace': 'Traceback' in text or 'Internal Server Error' in text})
    except Exception as e:
        results.append({'endpoint': rule.endpoint, 'url': url, 'status': 'EXC', 'error': f'{type(e).__name__}: {e}'})

bad = [r for r in results if r['status'] not in (200, 301, 302) or r.get('trace')]
print(f'login={login.status_code} · routes testees={len(results)} · anomalies={len(bad)}')
for b in bad:
    print('  !', b)
if out:
    json.dump({'login': login.status_code, 'results': results, 'skipped': skipped},
              open(out, 'w'), indent=1, ensure_ascii=False)
    print('resultat ecrit dans', out)
