"""Tests du cockpit commercial (page, API, droits, validation, non-regression).
Utilisation : python tools/test_cockpit.py [dossier_projet]
Code de sortie 0 = tout passe."""
import os, sys, warnings
warnings.filterwarnings('ignore')

proj = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
os.chdir(proj); sys.path.insert(0, proj)
import app as m
m.app.config['PROPAGATE_EXCEPTIONS'] = True

res = []
def check(name, cond, info=''):
    info = str(info)[:120]
    res.append(bool(cond))
    print(f'{"OK  " if cond else "ECHEC"} | {name} {info}')

with m.app.app_context():
    m.CockpitState.query.delete(); m.db.session.commit()

admin = m.app.test_client(); admin.post('/login', data={'email': 'admin@imagine-events.com', 'password': 'admin123'})
staff = m.app.test_client(); staff.post('/login', data={'email': 'staff@imagine-events.com', 'password': 'staff123'})
anon  = m.app.test_client()

r = admin.get('/cockpit'); h = r.get_data(as_text=True)
check('admin GET /cockpit = 200', r.status_code == 200, f'[{r.status_code}]')
check('iframe -> fichier statique', '/static/cockpit/cockpit-agence.html?embed=1' in h)
check('iframe -> API', '/api/cockpit/state' in h)
check('lien de menu visible', 'Cockpit commercial' in admin.get('/dashboard').get_data(as_text=True))

r = admin.get('/static/cockpit/cockpit-agence.html')
check('fichier cockpit servi', r.status_code == 200 and len(r.get_data()) > 50000, f'[{r.status_code}]')

check('API GET vide = {}', admin.get('/api/cockpit/state').get_json() == {})

payload = {'leads': [{'id': 'L1', 'societe': 'Banque Zitouna', 'contact': 'Mme Trabelsi', 'secteur': 'Banque',
                      'evenement': 'Seminaire 300 pax', 'pax': 300, 'valeur': 78000, 'source': 'Recommandation',
                      'stage': 'nego', 'next': 'Appeler', 'nextDate': '2026-11-20', 'notes': 'ok'}],
           'devis': [{'id': 'D1', 'client': 'Vermeg', 'event': 'Team building', 'date': '2026-12-05', 'pax': 120,
                      'remise': 5, 'tva': 19, 'lines': [{'label': 'Salle', 'cat': 'Lieu', 'qty': 1, 'cost': 9000, 'coef': 1.25}],
                      'created': '2026-11-14'}],
           'proposal': {'client': 'Vermeg', 'objectif': 'Federer', 'concept': 'Parcours', 'budget': '34000'},
           'content': [0, 3, 7], 'profile': {'agency': 'Imagine Events Tunisia', 'tva': 19}}
r = admin.put('/api/cockpit/state', json=payload)
check('PUT = 200', r.status_code == 200, f'[{r.status_code}] {r.get_json()}')
d = admin.get('/api/cockpit/state').get_json()
check('leads relus', len(d.get('leads', [])) == 1 and d['leads'][0]['societe'] == 'Banque Zitouna')
check('devis relus', len(d.get('devis', [])) == 1 and d['devis'][0]['lines'][0]['coef'] == 1.25)
check('profil conserve', d.get('profile', {}).get('agency') == 'Imagine Events Tunisia')

with m.app.app_context():
    row = m.CockpitState.query.filter_by(org='default').first()
    check('ligne en base', row is not None and len(row.payload) > 100)

check('JSON invalide = 400', admin.put('/api/cockpit/state', data='x', content_type='application/json').status_code == 400)
check('type inattendu = 400', admin.put('/api/cockpit/state', json=['liste']).status_code == 400)
check('structure bancale normalisee', admin.put('/api/cockpit/state', json={'leads': 'x', 'proposal': 42}).status_code == 200)
check('payload trop gros = 413',
      admin.put('/api/cockpit/state', json={'leads': [{'id': f'L{i}', 'societe': 'X' * 4000, 'notes': 'y' * 4000} for i in range(2500)]}).status_code == 413)

check('staff sans permission -> redirection', staff.get('/cockpit').status_code == 302)
check('staff : pas de lien menu', 'Cockpit commercial' not in staff.get('/dashboard').get_data(as_text=True))
r = staff.get('/api/cockpit/state')
check('staff API = 403 JSON', r.status_code == 403 and r.get_json().get('error') == 'permission_required')
r = anon.get('/cockpit')
check('anonyme -> login', r.status_code == 302 and '/login' in r.headers.get('Location', ''))
check('anonyme GET /register = 200', anon.get('/register').status_code == 200)

for u in ['/schedule', '/clients', '/stats', '/inventory', '/borrows', '/repairs', '/notifications', '/admin/users', '/admin/roles', '/recaps']:
    st = admin.get(u).status_code
    check(f'page {u}', st in (200, 302), f'[{st}]')

print(f'\nRESULTAT : {sum(res)} / {len(res)} tests passes')
sys.exit(0 if all(res) else 1)
