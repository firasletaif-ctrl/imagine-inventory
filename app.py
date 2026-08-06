"""Imagine Inventory v2 — Imagine Events Tunisia
Gestion de depot + Emploi du temps + Export + Notifications"""
import os, uuid, json, io
from datetime import datetime, date, timedelta, timezone
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from PIL import Image
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# ── Heure Tunis ──
TUNISIA_TZ = timezone(timedelta(hours=1))
def tunisia_now(): return datetime.now(TUNISIA_TZ)

# ── Config ──
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'imagine-events-tunisia-secret-2026')
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter.'

# ═══════════ M O D E L S ═══════════
class CustomRole(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True); name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='👤'); description = db.Column(db.String(250), default='')
    permissions = db.Column(db.Text, default=''); created_at = db.Column(db.DateTime, default=tunisia_now)
    users = db.relationship('User', backref='role', lazy=True)
    def get_permissions(self):
        try: return json.loads(self.permissions) if self.permissions else []
        except: return []
    def set_permissions(self, pl): self.permissions = json.dumps(pl) if isinstance(pl, list) else '[]'
    def has_permission(self, p): return p in self.get_permissions()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True); email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False); full_name = db.Column(db.String(150), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=tunisia_now)
    borrows = db.relationship('Borrow', backref='user', lazy=True)
    event_assignments = db.relationship('EventAssignment', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, foreign_keys='Notification.user_id')
    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)
    def has_permission(self, perm):
        role = db.session.get(CustomRole, self.role_id) if self.role_id else None
        return role.has_permission(perm) if role else False
    @property
    def role_name(self):
        role = db.session.get(CustomRole, self.role_id) if self.role_id else None
        return role.name if role else 'Aucun role'
    @property
    def unread_notifications(self):
        return Notification.query.filter_by(user_id=self.id, read=False).count()

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True); name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='📦')
    equipment = db.relationship('Equipment', backref='category', lazy=True)

class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True); name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default=''); reference = db.Column(db.String(100), unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    total_quantity = db.Column(db.Integer, default=1); available_quantity = db.Column(db.Integer, default=1)
    specifications = db.Column(db.Text, default=''); condition = db.Column(db.String(50), default='Bon etat')
    location = db.Column(db.String(100), default='Depot principal'); created_at = db.Column(db.DateTime, default=tunisia_now)
    images = db.relationship('EquipmentImage', backref='equipment', lazy=True, cascade='all, delete-orphan')
    borrows = db.relationship('Borrow', backref='equipment', lazy=True)
    def primary_image(self): return self.images[0].filename if self.images else None
    def all_images(self): return [img.filename for img in self.images]

class EquipmentImage(db.Model):
    __tablename__ = 'equipment_images'
    id = db.Column(db.Integer, primary_key=True); filename = db.Column(db.String(300), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=tunisia_now)

class Borrow(db.Model):
    __tablename__ = 'borrows'
    id = db.Column(db.Integer, primary_key=True); user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1); borrow_date = db.Column(db.DateTime, default=tunisia_now)
    expected_return_date = db.Column(db.Date, nullable=False); actual_return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='active'); notes = db.Column(db.Text, default='')
    event_name = db.Column(db.String(200), default='')

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True); user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False); description = db.Column(db.Text, default='')
    equipment_name = db.Column(db.String(200), default=''); quantity = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=tunisia_now)

# ── NEW: Events (emploi du temps) ──
class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    event_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), default='08:00')  # HH:MM
    end_time = db.Column(db.String(10), default='17:00')
    location = db.Column(db.String(200), default='')
    status = db.Column(db.String(50), default='upcoming')  # upcoming / ongoing / completed / cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=tunisia_now)
    assignments = db.relationship('EventAssignment', backref='event', lazy=True, cascade='all, delete-orphan')

class EventAssignment(db.Model):
    __tablename__ = 'event_assignments'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(100), default='Staff')  # Staff, Responsable, Technicien, etc.
    notes = db.Column(db.Text, default='')

# ── NEW: Notifications ──
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, default='')
    link = db.Column(db.String(300), default='')
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=tunisia_now)

# ═══════════ H E L P E R S ═══════════
@login_manager.user_loader
def load_user(uid): return db.session.get(User, int(uid))

@app.template_filter('get_user')
def get_user_filter(uid): return db.session.get(User, int(uid)) if uid else None

def allowed_file(fn): return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_image(file):
    if not file or not file.filename: return None
    if not allowed_file(file.filename): return None
    file.seek(0,2); size = file.tell(); file.seek(0)
    if size == 0: return None
    ext = file.filename.rsplit('.',1)[1].lower(); uname = f"{uuid.uuid4().hex}.{ext}"
    fpath = os.path.join(app.config['UPLOAD_FOLDER'], uname)
    try:
        file.save(fpath); img = Image.open(fpath); img.thumbnail((1200,1200))
        if img.mode in ('RGBA','P'): img = img.convert('RGB')
        jname = f"{uuid.uuid4().hex}.jpg"; jpath = os.path.join(app.config['UPLOAD_FOLDER'], jname)
        img.save(jpath, 'JPEG', optimize=True, quality=85)
        if ext != 'jpg':
            try: os.remove(fpath)
            except: pass
        return jname
    except:
        if os.path.exists(fpath): return uname
        return None

def update_availability(eq_id):
    eq = db.session.get(Equipment, eq_id)
    if eq:
        qty = db.session.query(db.func.sum(Borrow.quantity)).filter_by(equipment_id=eq_id, status='active').scalar() or 0
        eq.available_quantity = max(0, eq.total_quantity - qty); db.session.commit()


def is_pending_user():
    """Verifie si l'utilisateur est en attente (aucune permission)"""
    return not current_user.has_permission('borrow_equipment') and not current_user.has_permission('manage_equipment') and not current_user.has_permission('manage_users')

def log_action(action, description='', equipment_name='', quantity=0):
    """Enregistre une action. Si l'utilisateur n'est pas connecte, user_id = None."""
    uid = current_user.id if current_user.is_authenticated else None
    log = ActivityLog(user_id=uid, action=action, description=description, equipment_name=equipment_name, quantity=quantity)
    db.session.add(log); db.session.commit()

def notify_user(uid, title, message, link=''):
    n = Notification(user_id=uid, title=title, message=message, link=link)
    db.session.add(n); db.session.commit()
    # Envoi email si cle API configuree
    try:
        u = db.session.get(User, uid)
        if u and os.environ.get('SMTP_PASSWORD'):
            html = email_template(title, f'Bonjour {u.full_name},', message, link, 'Voir dans Imagine Inventory')
            send_email(u.email, title, html, message)
    except Exception as e:
        print(f'[EMAIL ERROR] {type(e).__name__}: {e}')


def send_email(to, subject, body_html, body_text=''):
    """Envoi email via Brevo API HTTP avec template HTML"""
    import urllib.request, json as jmod
    api_key = os.environ.get('SMTP_PASSWORD','')
    if not api_key: return
    sender_email = os.environ.get('SMTP_FROM','')
    if not sender_email: return
    data = jmod.dumps({
        "sender": {"name": "Imagine Events Tunisia", "email": sender_email},
        "to": [{"email": to}],
        "subject": f'[Imagine Inventory] {subject}',
        "htmlContent": body_html,
        "textContent": body_text or subject
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.brevo.com/v3/smtp/email',
        data=data,
        headers={'accept':'application/json','api-key':api_key,'content-type':'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f'[EMAIL] OK -> {to}')
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()[:200] if e.fp else 'N/A'
        print(f'[EMAIL] HTTP {e.code}: {err_body}')
    except Exception as e:
        print(f'[EMAIL] Error: {e}')


def email_template(title, greeting, content, action_link='', action_text=''):
    """Template HTML pour les emails Imagine Events"""
    action_btn = f'<a href="{action_link}" style="display:inline-block;background:#C41E3A;color:white;padding:12px 30px;border-radius:6px;text-decoration:none;font-weight:bold;margin:15px 0;font-size:14px">{action_text}</a>' if action_link else ''
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background:#F8FAFC">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F8FAFC;padding:20px">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.08)">
<tr><td style="background:linear-gradient(135deg,#0B1D3A,#13294B);padding:25px 30px;text-align:center">
    <div style="font-size:32px;margin-bottom:8px">\u2726</div>
    <div style="font-family:Georgia,serif;font-size:20px;font-weight:bold;color:white;letter-spacing:2px">IMAGINE<span style="color:#E63946"> EVENTS</span></div>
    <div style="font-size:11px;color:rgba(255,255,255,.5);letter-spacing:2px;margin-top:4px">TUNISIA · EXCELLENCE EVENEMENTIELLE</div>
</td></tr>
<tr><td style="padding:30px">
    <h2 style="color:#0B1D3A;font-size:18px;margin:0 0 10px">{title}</h2>
    <p style="color:#64748B;font-size:14px;line-height:1.6;margin:0 0 15px">{greeting}</p>
    <div style="background:#F1F5F9;border-left:4px solid #C41E3A;padding:15px;border-radius:0 8px 8px 0;margin:15px 0">
        <p style="color:#334155;font-size:14px;margin:0;line-height:1.6">{content}</p>
    </div>
    {action_btn}
    <p style="color:#94A3B8;font-size:12px;margin-top:20px">Cet email a ete envoye automatiquement par Imagine Inventory.</p>
</td></tr>
<tr><td style="background:#0B1D3A;padding:15px 30px;text-align:center">
    <p style="color:rgba(255,255,255,.5);font-size:11px;margin:0">
        Rue du Lac Loch Ness, Imm Neo, 3eme etage, 1053 Les Berges du Lac, Tunis<br>
        +216 71 656 056 | info@imagine-events.com
    </p>
</td></tr>
</table>
</td></tr></table>
</body></html>'''


def notify_admins(title, message, link=''):
    for a in User.query.filter(User.role_id.in_(db.session.query(CustomRole.id).filter_by(name='Admin'))).all():
        notify_user(a.id, title, message, link)

ALL_PERMISSIONS = [
    {"key":"manage_users","label":"Gerer les utilisateurs","desc":"Creer, modifier, supprimer des comptes","icon":"👥"},
    {"key":"manage_roles","label":"Gerer les roles","desc":"Creer et modifier les roles et permissions","icon":"🔐"},
    {"key":"manage_equipment","label":"Gerer le materiel","desc":"Ajouter, modifier, supprimer du materiel","icon":"📦"},
    {"key":"borrow_equipment","label":"Emprunter","desc":"Emprunter du materiel","icon":"📤"},
    {"key":"return_equipment","label":"Retourner","desc":"Marquer un emprunt comme retourne","icon":"✅"},
    {"key":"manage_categories","label":"Gerer les categories","desc":"Ajouter des categories de materiel","icon":"📂"},
    {"key":"view_logs","label":"Voir les logs","desc":"Consulter l'historique d'activite","icon":"📜"},
    {"key":"clear_history","label":"Effacer l'historique","desc":"Supprimer l'historique des emprunts","icon":"🗑️"},
    {"key":"manage_schedule","label":"Gerer le planning","desc":"Creer et gerer l'emploi du temps","icon":"📅"},
    {"key":"manage_database","label":"Gerer la base de donnees","desc":"Reset, import CSV, restauration photos, migration","icon":"🗄️"},
]

def permission_required(perm):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if not current_user.has_permission(perm):
                try: log_action('permission_denied', f'Tentative d\'acces refuse : {perm}')
                except: pass
                flash('Acces refuse. Permission requise : ' + perm, 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ═══════════ R O U T E S ═══════════
@app.route('/')
def index():
    return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower(); pw = request.form.get('password','')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(pw):
            login_user(user, remember=True)
            db.session.add(ActivityLog(user_id=user.id, action='login', description=f'Connexion de {user.full_name}')); db.session.commit()
            flash(f'Bienvenue {user.full_name} !', 'success')
            return redirect(request.args.get('next') or url_for('dashboard'))
        log_action('failed_login', f'Tentative echouee pour {email}'); flash('Email ou mot de passe incorrect.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower(); name = request.form.get('full_name','').strip()
        pw = request.form.get('password','')
        if not email or not name or not pw: flash('Tous les champs requis.','error')
        elif request.form.get('confirm_password') != pw: flash('Mots de passe differents.','error')
        elif len(pw) < 6: flash('6 caracteres minimum.','error')
        elif User.query.filter_by(email=email).first(): flash('Email deja utilise.','error')
        else:
            u = User(email=email, full_name=name); u.set_password(pw)
            if User.query.count() == 0: u.role_id = 1
            else:
                pending = CustomRole.query.filter_by(name='En attente').first()
                if pending: u.role_id = pending.id
            db.session.add(u); db.session.commit()
            # Notify admins
            notify_admins(f'Nouveau compte : {name}', f'{name} ({email}) vient de creer un compte. Action requise.', url_for('manage_users', _external=True))
            log_action('register', f'Nouveau compte cree par {name} ({email})'); flash('Compte cree ! En attente de validation par l\'admin.','success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    log_action('logout', f'Deconnexion de {current_user.full_name}')
    logout_user()
    flash('Vous etes deconnecte.','info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    search = request.args.get('search','').strip(); cat_filter = request.args.get('category','')
    q = Equipment.query
    if search: q = q.filter(db.or_(Equipment.name.ilike(f'%{search}%'),Equipment.description.ilike(f'%{search}%'),Equipment.reference.ilike(f'%{search}%'),Equipment.specifications.ilike(f'%{search}%'),Equipment.location.ilike(f'%{search}%')))
    if cat_filter: q = q.filter_by(category_id=int(cat_filter))
    eqs = q.order_by(Equipment.name).all(); cats = Category.query.order_by(Category.name).all()
    ab = Borrow.query.filter(Borrow.status.in_(['active','late'])).order_by(Borrow.expected_return_date).all()
    today = date.today()
    for b in ab:
        if b.status == 'active' and b.expected_return_date < today: b.status = 'late'
    db.session.commit()
    eq_json = json.dumps([{'id':e.id,'name':e.name,'available_quantity':e.available_quantity} for e in Equipment.query.all()])
    is_pending = not current_user.has_permission('borrow_equipment') and not current_user.has_permission('manage_equipment') and not current_user.has_permission('manage_users')
    return render_template('dashboard.html', equipment=eqs, categories=cats, active_borrows=ab, search=search, cat_filter=cat_filter, all_count=Equipment.query.count(), available_count=Equipment.query.filter(Equipment.available_quantity>0).count(), late_count=Borrow.query.filter_by(status='late').count(), equipment_json=eq_json, today=today, is_pending=is_pending)

@app.route('/equipment/<int:eid>')
@login_required
def equipment_detail(eid):
    if is_pending_user(): flash('Votre compte est en attente de validation.','error'); return redirect(url_for('dashboard'))
    eq = db.session.get(Equipment, eid)
    if not eq: flash('Introuvable.','error'); return redirect(url_for('dashboard'))
    borrows = Borrow.query.filter_by(equipment_id=eid).order_by(Borrow.borrow_date.desc()).all()
    return render_template('equipment_detail.html', eq=eq, borrows=borrows, today=date.today())

@app.route('/borrow/<int:eid>', methods=['POST'])
@permission_required('borrow_equipment')
def borrow_equipment(eid):
    eq = db.session.get(Equipment, eid)
    if not eq: flash('Introuvable.','error'); return redirect(url_for('dashboard'))
    qty = int(request.form.get('quantity',1)); rd = request.form.get('return_date','')
    try: return_date = datetime.strptime(rd,'%Y-%m-%d').date()
    except: flash('Date invalide.','error'); return redirect(url_for('dashboard'))
    if return_date < date.today(): flash('Date dans le passe.','error'); return redirect(url_for('dashboard'))
    if qty < 1 or qty > eq.available_quantity: flash(f'Quantite invalide (max {eq.available_quantity}).','error'); return redirect(url_for('dashboard'))
    b = Borrow(user_id=current_user.id, equipment_id=eid, quantity=qty, expected_return_date=return_date, event_name=request.form.get('event_name','').strip(), notes=request.form.get('notes','').strip())
    db.session.add(b); db.session.commit(); update_availability(eid)
    log_action('borrow', f'Emprunt de {qty}x {eq.name}', eq.name, qty)
    flash(f'{qty} x {eq.name} emprunte(s). Retour le {return_date.strftime("%d/%m/%Y")}.','success')
    return redirect(url_for('dashboard'))

@app.route('/return/<int:bid>', methods=['POST'])
@permission_required('return_equipment')
def return_equipment(bid):
    b = db.session.get(Borrow, bid)
    if not b or b.status not in ('active','late'): flash('Emprunt introuvable ou deja retourne.','error'); return redirect(url_for('dashboard'))
    is_admin = current_user.has_permission('manage_users')
    if b.user_id != current_user.id and not is_admin: flash('Vous ne pouvez retourner que vos propres emprunts.','error'); return redirect(url_for('dashboard'))
    b.status = 'returned'; b.actual_return_date = tunisia_now(); db.session.commit(); update_availability(b.equipment_id)
    who = current_user.full_name if b.user_id == current_user.id else f'{current_user.full_name} (admin) pour {b.user.full_name}'
    log_action('return', f'Retour de {b.quantity}x {b.equipment.name} par {who}', b.equipment.name, b.quantity)
    flash(f'{b.equipment.name} retourne avec succes.','success')
    return redirect(url_for('dashboard'))

@app.route('/equipment/add', methods=['GET','POST'])
@permission_required('manage_equipment')
def add_equipment():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        if not name: flash('Nom requis.','error'); return redirect(url_for('add_equipment'))
        ref = request.form.get('reference','').strip() or f"IM-{uuid.uuid4().hex[:8].upper()}"
        eq = Equipment(name=name, description=request.form.get('description','').strip(), reference=ref, category_id=int(request.form.get('category_id',0)) or None, total_quantity=int(request.form.get('total_quantity',1)), available_quantity=int(request.form.get('total_quantity',1)), specifications=request.form.get('specifications','').strip(), condition=request.form.get('condition','Bon etat'), location=request.form.get('location','Depot principal'))
        db.session.add(eq); db.session.flush()
        for f in request.files.getlist('images'):
            sn = save_uploaded_image(f)
            if sn: db.session.add(EquipmentImage(filename=sn, equipment_id=eq.id))
        db.session.commit()
        log_action('add_equipment', f'Ajout de {name}', name)
        flash(f'"{name}" ajoute au depot !','success')
        return redirect(url_for('equipment_detail', eid=eq.id))
    return render_template('add_equipment.html', categories=Category.query.order_by(Category.name).all())

@app.route('/equipment/<int:eid>/edit', methods=['GET','POST'])
@permission_required('manage_equipment')
def edit_equipment(eid):
    eq = db.session.get(Equipment, eid)
    if not eq: flash('Introuvable.','error'); return redirect(url_for('dashboard'))
    if request.method == 'POST':
        eq.name = request.form.get('name','').strip(); eq.description = request.form.get('description','').strip()
        ref = request.form.get('reference','').strip()
        if ref and ref != eq.reference: eq.reference = ref
        cid = request.form.get('category_id'); eq.category_id = int(cid) if cid else None
        old = eq.total_quantity; eq.total_quantity = int(request.form.get('total_quantity',eq.total_quantity))
        eq.available_quantity = max(0, eq.available_quantity + (eq.total_quantity - old))
        eq.specifications = request.form.get('specifications','').strip(); eq.condition = request.form.get('condition','Bon etat'); eq.location = request.form.get('location','Depot principal')
        for f in request.files.getlist('images'):
            sn = save_uploaded_image(f)
            if sn: db.session.add(EquipmentImage(filename=sn, equipment_id=eq.id))
        db.session.commit()
        log_action('edit_equipment', f'Modification de {eq.name}', eq.name)
        flash(f'"{eq.name}" mis a jour.','success')
        return redirect(url_for('equipment_detail', eid=eq.id))
    return render_template('edit_equipment.html', eq=eq, categories=Category.query.order_by(Category.name).all())

@app.route('/equipment/<int:eid>/delete-image/<int:iid>', methods=['POST'])
@login_required
def delete_image(eid, iid):
    img = db.session.get(EquipmentImage, iid)
    if img and img.equipment_id == eid:
        fp = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
        if os.path.exists(fp): os.remove(fp)
        db.session.delete(img); db.session.commit()
    return redirect(url_for('edit_equipment', eid=eid))

@app.route('/equipment/<int:eid>/delete', methods=['POST'])
@permission_required('manage_equipment')
def delete_equipment(eid):
    eq = db.session.get(Equipment, eid)
    if eq:
        for img in eq.images:
            fp = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
            if os.path.exists(fp): os.remove(fp)
        db.session.delete(eq); db.session.commit()
        log_action('delete_equipment', f'Suppression de {eq.name}', eq.name)
        flash(f'"{eq.name}" supprime.','info')
    return redirect(url_for('dashboard'))

@app.route('/uploads/<fn>')
@login_required
def uploaded_file(fn): return send_from_directory(app.config['UPLOAD_FOLDER'], fn)

@app.route('/change-password', methods=['GET','POST'])
@login_required
def change_password():
    if request.method == 'POST':
        cp = request.form.get('current_password',''); np = request.form.get('new_password','')
        if not current_user.check_password(cp): flash('Mot de passe actuel incorrect.','error')
        elif len(np) < 6: flash('6 caracteres minimum.','error')
        elif np != request.form.get('confirm_password',''): flash('Mots de passe differents.','error')
        else: current_user.set_password(np); db.session.commit(); log_action('change_password', f'{current_user.full_name} a change son mot de passe'); flash('Mot de passe change !','success'); return redirect(url_for('dashboard'))
    return render_template('change_password.html')

# ═══════ A D M I N   U S E R S ═══════
@app.route('/admin/users')
@permission_required('manage_users')
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('manage_users.html', users=users, all_roles=CustomRole.query.order_by(CustomRole.name).all())

@app.route('/admin/users/create', methods=['POST'])
@permission_required('manage_users')
def create_user():
    email = request.form.get('email','').strip().lower(); name = request.form.get('full_name','').strip()
    pw = request.form.get('password',''); rid = request.form.get('role_id')
    try: rid = int(rid) if rid else None
    except: rid = None
    if not email or not name or not pw: flash('Tous les champs requis.','error')
    elif len(pw) < 6: flash('6 caracteres minimum.','error')
    elif User.query.filter_by(email=email).first(): flash('Email deja utilise.','error')
    else:
        u = User(email=email, full_name=name); u.set_password(pw)
        if rid: u.role_id = rid
        db.session.add(u); db.session.commit()
        notify_user(u.id, 'Compte active', f'Votre compte a ete cree par {current_user.full_name}. Bienvenue !', '/dashboard')
        log_action('create_user', f'Compte cree par admin : {name} ({u.role_name})'); flash(f'Compte cree : {name} ({u.role_name})','success')
    return redirect(url_for('manage_users'))

@app.route('/admin/users/<int:uid>/edit', methods=['POST'])
@permission_required('manage_users')
def edit_user(uid):
    u = db.session.get(User, uid)
    if not u: flash('Introuvable.','error'); return redirect(url_for('manage_users'))
    # Allow editing yourself (just can't change your own role)
    is_self = (u.id == current_user.id)
    u.full_name = request.form.get('full_name',u.full_name).strip()
    new_email = request.form.get('email','').strip().lower()
    if new_email and new_email != u.email and User.query.filter_by(email=new_email).first():
        flash('Cet email est deja utilise.','error'); return redirect(url_for('manage_users'))
    if new_email: u.email = new_email
    if not is_self:
        rid = request.form.get('role_id')
        try: u.role_id = int(rid) if rid else None
        except: pass
    np = request.form.get('new_password','')
    if np and len(np) >= 6: u.set_password(np); flash(f'{u.full_name} mis a jour + mdp change.','success')
    elif np: flash('Mdp non change (6 car. min).','error')
    else: log_action('edit_user', f'Modification du compte de {u.full_name}'); flash(f'{u.full_name} mis a jour.','success')
    db.session.commit()
    return redirect(url_for('manage_users'))

@app.route('/admin/users/<int:uid>/delete', methods=['POST'])
@permission_required('manage_users')
def delete_user(uid):
    u = db.session.get(User, uid)
    if not u: flash('Introuvable.','error')
    elif u.id == current_user.id: flash('Impossible de se supprimer.','error')
    elif Borrow.query.filter_by(user_id=uid).filter(Borrow.status.in_(['active','late'])).first(): flash(f'{u.full_name} a des emprunts en cours.','error')
    else:
        # Nettoyer toutes les tables qui referencent cet utilisateur
        ActivityLog.query.filter_by(user_id=uid).delete()
        Notification.query.filter_by(user_id=uid).delete()
        EventAssignment.query.filter_by(user_id=uid).delete()
        Borrow.query.filter_by(user_id=uid).update({Borrow.user_id: None})
        Event.query.filter_by(created_by=uid).update({Event.created_by: None})
        db.session.delete(u); db.session.commit()
        log_action('delete_user', f'Suppression du compte de {u.full_name}'); flash(f'{u.full_name} supprime.','info')
    return redirect(url_for('manage_users'))

# ═══════ R O L E S ═══════
@app.route('/admin/roles')
@permission_required('manage_roles')
def manage_roles():
    return render_template('manage_roles.html', roles=CustomRole.query.order_by(CustomRole.name).all(), all_permissions=ALL_PERMISSIONS)

@app.route('/admin/roles/create', methods=['POST'])
@permission_required('manage_roles')
def create_role():
    name = request.form.get('name','').strip()
    if not name: flash('Nom requis.','error')
    elif CustomRole.query.filter_by(name=name).first(): flash('Ce role existe deja.','error')
    else:
        r = CustomRole(name=name, icon=request.form.get('icon','👤'), description=request.form.get('description','').strip())
        r.set_permissions(request.form.getlist('permissions')); db.session.add(r); db.session.commit()
        log_action('create_role', f'Role "{name}" cree'); flash(f'Role "{name}" cree.','success')
    return redirect(url_for('manage_roles'))

@app.route('/admin/roles/<int:rid>/edit', methods=['POST'])
@permission_required('manage_roles')
def edit_role(rid):
    r = db.session.get(CustomRole, rid)
    if not r: flash('Role introuvable.','error'); return redirect(url_for('manage_roles'))
    r.name = request.form.get('name',r.name).strip(); r.icon = request.form.get('icon',r.icon)
    r.description = request.form.get('description','').strip()
    r.set_permissions(request.form.getlist('permissions')); db.session.commit()
    log_action('edit_role', f'Role "{r.name}" modifie'); flash(f'Role "{r.name}" mis a jour.','success')
    return redirect(url_for('manage_roles'))

@app.route('/admin/roles/<int:rid>/delete', methods=['POST'])
@permission_required('manage_roles')
def delete_role(rid):
    r = db.session.get(CustomRole, rid)
    if not r: flash('Role introuvable.','error')
    elif User.query.filter_by(role_id=rid).first(): flash('Des utilisateurs utilisent ce role.','error')
    else: db.session.delete(r); db.session.commit(); log_action('delete_role', f'Role "{r.name}" supprime'); flash(f'Role "{r.name}" supprime.','info')
    return redirect(url_for('manage_roles'))

@app.route('/admin/logs/clear', methods=['POST'])
@permission_required('clear_history')
def clear_logs():
    count = ActivityLog.query.count()
    ActivityLog.query.delete()
    db.session.commit()
    db.session.add(ActivityLog(user_id=current_user.id, action='clear_history', description=f'Logs effaces ({count} entrees)'))
    db.session.commit()
    flash(f'{count} logs d\'activite effaces.','success')
    return redirect(url_for('activity_logs'))


@app.route('/admin/import-csv', methods=['GET','POST'])
@permission_required('manage_database')
def import_csv():
    if request.method == 'POST':
        pw = request.form.get('password','')
        if not current_user.check_password(pw):
            flash('Mot de passe incorrect.','error')
            return redirect(url_for('import_csv'))
        table = request.form.get('table','')
        csv_file = request.files.get('csvfile')
        if not csv_file or not table:
            flash('Selectionnez une table et un fichier CSV.','error')
            return redirect(url_for('import_csv'))
        
        # Read CSV
        import io, csv as csv_module
        stream = io.StringIO(csv_file.read().decode('utf-8-sig'))
        reader = csv_module.DictReader(stream)
        rows = list(reader)
        if not rows:
            flash('Fichier CSV vide.','error')
            return redirect(url_for('import_csv'))
        
        model_map = {
            'roles': CustomRole,
            'users': User,
            'categories': Category,
            'equipment': Equipment,
            'equipment_images': EquipmentImage,
            'borrows': Borrow,
            'events': Event,
            'event_assignments': EventAssignment,
            'activity_logs': ActivityLog,
            'notifications': Notification,
        }
        
        model = model_map.get(table)
        if not model:
            flash('Table inconnue.','error')
            return redirect(url_for('import_csv'))
        
        # Detect columns and import
        cols = list(rows[0].keys())
        count = 0
        for row in rows:
            try:
                # Check if record already exists
                existing = None
                if 'id' in cols and row.get('id','').strip():
                    existing = db.session.get(model, int(row['id'].strip()))
                
                obj = existing if existing else model()
                for col in cols:
                    val = row.get(col, '').strip()
                    if val == '' or val.lower() == 'none':
                        val = None
                        if col == 'id' and existing: continue  # dont overwrite id
                        setattr(obj, col, val)
                        continue
                    # Convert types
                    if col == 'id' and existing: continue
                    if col.endswith('_id') or col == 'id' or col.endswith('_quantity'):
                        try: val = int(val)
                        except: pass
                    # Handle date/datetime columns
                    if col in ('created_at', 'uploaded_at', 'borrow_date', 'actual_return_date', 'timestamp'):
                        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d'):
                            try: val = datetime.strptime(val, fmt); break
                            except: pass
                        else:
                            val = None  # can't parse
                    if col == 'expected_return_date' and val:
                        try: val = datetime.strptime(val, '%Y-%m-%d').date()
                        except:
                            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                                try: val = datetime.strptime(val, fmt).date(); break
                                except: pass
                            else: val = None
                    if col == 'permissions' and val and not val.startswith('['):
                        val = f'["{val}"]'  # ensure JSON format
                    setattr(obj, col, val)
                if not existing:
                    db.session.add(obj)
                count += 1
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur ligne {count+1}: {str(e)}','error')
                return redirect(url_for('import_csv'))
        
        db.session.commit()
        flash(f'{count} lignes importees dans {table}.','success')
        return redirect(url_for('import_csv'))
    
    tables = ['roles','users','categories','equipment','equipment_images','borrows','events','event_assignments','activity_logs','notifications']
    return render_template('import_csv.html', tables=tables)


@app.route('/admin/reset-tables', methods=['GET','POST'])
@permission_required('manage_database')
def reset_all_tables():
    if request.method == 'POST':
        pw = request.form.get('password','')
        if not current_user.check_password(pw):
            flash('Mot de passe incorrect.','error')
            return redirect(url_for('reset_all_tables'))
        # Keep current admin
        aid = current_user.id
        rid = current_user.role_id
        Notification.query.delete()
        EventAssignment.query.delete()
        Event.query.delete()
        ActivityLog.query.delete()
        Borrow.query.delete()
        EquipmentImage.query.delete()
        Equipment.query.delete()
        Category.query.delete()
        User.query.filter(User.id != aid).delete()
        CustomRole.query.filter(CustomRole.id != rid).delete()
        db.session.commit()
        flash('Toutes les tables videes (votre compte preserve). Base prete.','success')
        return redirect(url_for('reset_all_tables'))
    return render_template('reset_tables.html')


@app.route('/admin/clear-history', methods=['POST'])
@permission_required('clear_history')
def clear_history():
    if not current_user.check_password(request.form.get('password','')): flash('Mot de passe incorrect.','error'); return redirect(url_for('dashboard'))
    c = Borrow.query.filter_by(status='returned').count()
    Borrow.query.filter_by(status='returned').delete(); db.session.commit()
    log_action('clear_history', f'Historique global efface ({c} emprunts)')
    flash(f'{c} emprunt(s) effaces.','success')
    return redirect(url_for('dashboard'))

@app.route('/equipment/<int:eid>/clear-history', methods=['POST'])
@permission_required('clear_history')
def clear_equipment_history(eid):
    eq = db.session.get(Equipment, eid)
    if not eq: flash('Introuvable.','error'); return redirect(url_for('dashboard'))
    if not current_user.check_password(request.form.get('password','')): flash('Mot de passe incorrect.','error'); return redirect(url_for('equipment_detail', eid=eid))
    c = Borrow.query.filter_by(equipment_id=eid, status='returned').count()
    Borrow.query.filter_by(equipment_id=eid, status='returned').delete(); db.session.commit()
    log_action('clear_history', f'Historique efface pour {eq.name} ({c} emprunts)'); flash(f'{c} emprunt(s) effaces pour {eq.name}.','success')
    return redirect(url_for('equipment_detail', eid=eid))

@app.route('/admin/logs')
@permission_required('view_logs')
def activity_logs():
    page = request.args.get('page',1,type=int)
    action_filter = request.args.get('action','').strip()
    user_filter = request.args.get('user','').strip()
    q = ActivityLog.query
    if action_filter: q = q.filter_by(action=action_filter)
    if user_filter:
        # Search by user name
        matching_users = User.query.filter(User.full_name.ilike(f'%{user_filter}%')).all()
        uids = [u.id for u in matching_users]
        if uids: q = q.filter(ActivityLog.user_id.in_(uids))
        else: q = q.filter(ActivityLog.user_id == -1)  # no results
    logs = q.order_by(ActivityLog.timestamp.desc()).paginate(page=page, per_page=50, error_out=False)
    # Stats
    total_today = ActivityLog.query.filter(db.func.date(ActivityLog.timestamp) == db.func.date(tunisia_now())).count()
    total_week = ActivityLog.query.filter(ActivityLog.timestamp >= tunisia_now() - timedelta(days=7)).count()
    all_actions = [r[0] for r in db.session.query(ActivityLog.action).distinct().order_by(ActivityLog.action).all()]
    ACTION_LABELS = {
        'login':'🔑 Connexion','logout':'🚪 Deconnexion','failed_login':'⚠️ Echec connexion',
        'register':'📝 Inscription','borrow':'📤 Emprunt','return':'✅ Retour',
        'add_equipment':'➕ Ajout materiel','edit_equipment':'✏️ Modif materiel',
        'delete_equipment':'🗑️ Suppr materiel','add_category':'📂 Categorie ajoutee',
        'delete_category':'❌ Categorie supprimee','create_user':'👤 Compte cree',
        'edit_user':'✏️ Compte modifie','delete_user':'❌ Compte supprime',
        'create_role':'🔐 Role cree','edit_role':'✏️ Role modifie','delete_role':'❌ Role supprime',
        'change_password':'🔑 Mdp change','create_event':'📅 Evenement cree',
        'edit_event':'✏️ Evenement modifie','delete_event':'🗑️ Evenement supprime',
        'clear_past_events':'🧹 Evenements passes effaces','clear_history':'🧹 Effacement historique',
        'export_excel':'📊 Export Excel','permission_denied':'🚫 Acces refuse',
    }
    return render_template('activity_logs.html', logs=logs, action_filter=action_filter, user_filter=user_filter, total_today=total_today, total_week=total_week, all_actions=all_actions, ACTION_LABELS=ACTION_LABELS, all_users=User.query.order_by(User.full_name).all())

@app.route('/categories/add', methods=['POST'])
@permission_required('manage_categories')
def add_category():
    name = request.form.get('name','').strip(); icon = request.form.get('icon','📦')
    if name and not Category.query.filter_by(name=name).first():
        db.session.add(Category(name=name, icon=icon)); db.session.commit()
        log_action('add_category', f'Categorie "{name}" ajoutee'); flash(f'Categorie "{name}" ajoutee.','success')
    return redirect(url_for('dashboard'))

@app.route('/categories/<int:cid>/delete', methods=['POST'])
@permission_required('manage_categories')
def delete_category(cid):
    cat = db.session.get(Category, cid)
    if not cat: flash('Categorie introuvable.','error')
    elif Equipment.query.filter_by(category_id=cid).first(): flash(f'Des materiels utilisent la categorie {cat.name}.','error')
    else: db.session.delete(cat); db.session.commit(); log_action('delete_category', f'Categorie "{cat.name}" supprimee'); flash(f'Categorie "{cat.name}" supprimee.','info')
    return redirect(url_for('dashboard'))

# ═══════════ N E W :  E M P L O I   D U   T E M P S ═══════════
@app.route('/schedule')
@login_required
def schedule():
    if is_pending_user(): flash('Votre compte est en attente de validation.','error'); return redirect(url_for('dashboard'))
    """Main calendar/schedule view"""
    upcoming = Event.query.filter(Event.event_date >= date.today()).order_by(Event.event_date, Event.start_time).all()
    past = Event.query.filter(Event.event_date < date.today()).order_by(Event.event_date.desc()).limit(20).all()
    return render_template('schedule.html', upcoming=upcoming, past=past, today=date.today(), all_users=User.query.order_by(User.full_name).all())

@app.route('/schedule/create', methods=['POST'])
@permission_required('manage_schedule')
def create_event():
    title = request.form.get('title','').strip()
    if not title: flash('Titre requis.','error'); return redirect(url_for('schedule'))
    try: ed = datetime.strptime(request.form.get('event_date',''),'%Y-%m-%d').date()
    except: flash('Date invalide.','error'); return redirect(url_for('schedule'))
    st = request.form.get('start_time','08:00'); et = request.form.get('end_time','17:00')
    evt = Event(title=title, description=request.form.get('description','').strip(), event_date=ed, start_time=st, end_time=et, location=request.form.get('location','').strip(), created_by=current_user.id)
    db.session.add(evt); db.session.flush()
    # Assign users
    user_ids = request.form.getlist('assigned_users')
    for uid in user_ids:
        db.session.add(EventAssignment(event_id=evt.id, user_id=int(uid), role='Staff'))
    db.session.commit()
    # Notify assigned users
    for uid in user_ids:
        u = db.session.get(User, uid)
        if u:
            notify_user(u.id, f'Nouvel evenement : {title}', f'Vous etes assigne a "{title}" le {ed.strftime("%d/%m/%Y")} ({st}-{et})', url_for('schedule', _external=True))
    log_action('create_event', f'Evenement "{title}" cree le {ed.strftime("%d/%m/%Y")}'); flash(f'Evenement "{title}" cree.','success')
    return redirect(url_for('schedule'))

@app.route('/schedule/<int:evid>/edit', methods=['POST'])
@permission_required('manage_schedule')
def edit_event(evid):
    evt = db.session.get(Event, evid)
    if not evt: flash('Introuvable.','error'); return redirect(url_for('schedule'))
    evt.title = request.form.get('title','').strip(); evt.description = request.form.get('description','').strip()
    try: evt.event_date = datetime.strptime(request.form.get('event_date',''),'%Y-%m-%d').date()
    except: pass
    evt.start_time = request.form.get('start_time','08:00'); evt.end_time = request.form.get('end_time','17:00')
    evt.location = request.form.get('location','').strip(); evt.status = request.form.get('status',evt.status)
    # Update assignments
    EventAssignment.query.filter_by(event_id=evid).delete()
    for uid in request.form.getlist('assigned_users'):
        db.session.add(EventAssignment(event_id=evid, user_id=int(uid)))
    db.session.commit(); log_action('edit_event', f'Evenement "{evt.title}" modifie'); flash(f'Evenement modifie.','success')
    return redirect(url_for('schedule'))

@app.route('/schedule/<int:evid>/delete', methods=['POST'])
@permission_required('manage_schedule')
def delete_event(evid):
    evt = db.session.get(Event, evid)
    if evt: db.session.delete(evt); db.session.commit(); log_action('delete_event', f'Evenement "{evt.title}" supprime'); flash(f'Evenement "{evt.title}" supprime.','info')
    return redirect(url_for('schedule'))


@app.route('/schedule/clear-past', methods=['POST'])
@permission_required('manage_schedule')
def clear_past_events():
    count = Event.query.filter(Event.event_date < date.today()).count()
    past_ids = [e.id for e in Event.query.filter(Event.event_date < date.today()).all()]
    EventAssignment.query.filter(EventAssignment.event_id.in_(past_ids)).delete(synchronize_session='fetch')
    Event.query.filter(Event.event_date < date.today()).delete()
    db.session.commit()
    log_action('clear_past_events', f'{count} evenements passes supprimes'); flash(f'{count} evenement(s) passes supprime(s).','success')
    return redirect(url_for('schedule'))

@app.route('/schedule/<int:evid>/assign', methods=['POST'])
@permission_required('manage_schedule')
def assign_one_user(evid):
    """Quick assign one user from schedule page"""
    uid = request.form.get('user_id'); role = request.form.get('role','Staff')
    if uid and not EventAssignment.query.filter_by(event_id=evid, user_id=int(uid)).first():
        db.session.add(EventAssignment(event_id=evid, user_id=int(uid), role=role)); db.session.commit()
    return redirect(url_for('schedule'))

@app.route('/schedule/<int:evid>/unassign/<int:uid>', methods=['POST'])
@permission_required('manage_schedule')
def unassign_user(evid, uid):
    ea = EventAssignment.query.filter_by(event_id=evid, user_id=uid).first()
    if ea: db.session.delete(ea); db.session.commit()
    return redirect(url_for('schedule'))

# ═══════════ N E W :  N O T I F I C A T I O N S ═══════════
@app.route('/notifications')
@login_required
def notifications():
    if is_pending_user(): return redirect(url_for('dashboard'))
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return render_template('notifications.html', notifs=notifs)

@app.route('/notifications/read/<int:nid>', methods=['POST'])
@login_required
def mark_read(nid):
    n = Notification.query.filter_by(id=nid, user_id=current_user.id).first()
    if n: n.read = True; db.session.commit()
    return redirect(request.form.get('redirect','/notifications'))

@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, read=False).update({Notification.read: True})
    db.session.commit(); flash('Toutes les notifications lues.','success')
    return redirect(url_for('notifications'))


@app.route('/notifications/delete/<int:nid>', methods=['POST'])
@login_required
def delete_notification(nid):
    n = Notification.query.filter_by(id=nid, user_id=current_user.id).first()
    if n: db.session.delete(n); db.session.commit()
    return redirect(url_for('notifications'))


@app.route('/notifications/clear-all', methods=['POST'])
@login_required
def clear_all_notifications():
    count = Notification.query.filter_by(user_id=current_user.id).count()
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash(f'{count} notification(s) supprimees.','success')
    return redirect(url_for('notifications'))


# ═══════════ N E W :  E X P O R T S ═══════════
@app.route('/export/photos-zip')
@permission_required('manage_database')
def export_photos_zip():
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        upload_dir = app.config['UPLOAD_FOLDER']
        for fn in os.listdir(upload_dir):
            if fn == '.gitkeep': continue
            fpath = os.path.join(upload_dir, fn)
            if os.path.isfile(fpath):
                zf.write(fpath, fn)
    buf.seek(0)
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=f'photos_imagine_{date.today().strftime("%Y%m%d")}.zip')


@app.route('/admin/restore-photos', methods=['GET','POST'])
@permission_required('manage_database')
def restore_photos():
    if request.method == 'POST':
        zf = request.files.get('zipfile')
        if not zf or not zf.filename.endswith('.zip'):
            flash('Veuillez selectionner un fichier ZIP valide.','error')
            return redirect(url_for('restore_photos'))
        import zipfile, tempfile, shutil
        count = 0
        with zipfile.ZipFile(zf) as z:
            for fn in z.namelist():
                if fn.endswith('/') or fn == '.gitkeep': continue
                # Extraire le fichier dans uploads
                target = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(fn))
                if os.path.exists(target): continue  # skip duplicates
                z.extract(fn, app.config['UPLOAD_FOLDER'])
                # Renommer si extrait dans un sous-dossier
                extracted = os.path.join(app.config['UPLOAD_FOLDER'], fn)
                if extracted != target and os.path.exists(extracted):
                    os.rename(extracted, target)
                # Nettoyer le dossier parent si vide
                parent = os.path.dirname(extracted)
                if parent != app.config['UPLOAD_FOLDER'] and os.path.isdir(parent):
                    try: os.rmdir(parent)
                    except: pass
                count += 1
        flash(f'{count} photos restaurees dans le dossier uploads. Pensez a les reassocier au materiel dans Beekeeper (table equipment_images).','success')
        return redirect(url_for('restore_photos'))
    return render_template('restore_photos.html')


@app.route('/export/excel')
@permission_required('manage_equipment')
def export_excel():
    log_action('export_excel', 'Export Excel de l\'inventaire')
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Inventaire Imagine Events"
    # Styles
    header_font = Font(name='Arial', bold=True, size=11, color='FFFFFF')
    header_fill = PatternFill(start_color='0B1D3A', end_color='0B1D3A', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    cell_font = Font(name='Arial', size=10)
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    green_fill = PatternFill(start_color='DCFCE7', end_color='DCFCE7', fill_type='solid')
    red_fill = PatternFill(start_color='FDE8EC', end_color='FDE8EC', fill_type='solid')
    # Title
    ws.merge_cells('A1:I1'); ws['A1'] = 'IMAGINE EVENTS TUNISIA - Inventaire du Depot'
    ws['A1'].font = Font(name='Arial', bold=True, size=14, color='0B1D3A'); ws['A1'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A2:I2'); ws['A2'] = f'Exporte le {date.today().strftime("%d/%m/%Y")}'
    ws['A2'].font = Font(name='Arial', size=9, color='64748B'); ws['A2'].alignment = Alignment(horizontal='center')
    ws.append([])  # blank row
    # Headers
    headers = ['Reference', 'Nom', 'Categorie', 'Description', 'Qté Totale', 'Qté Dispo', 'État', 'Emplacement', 'Spécifications']
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=c, value=h)
        cell.font = header_font; cell.fill = header_fill; cell.alignment = header_alignment; cell.border = thin_border
    # Data
    for r, eq in enumerate(Equipment.query.order_by(Equipment.name).all(), 5):
        cat_name = eq.category.name if eq.category else ''
        data = [eq.reference, eq.name, cat_name, eq.description, eq.total_quantity, eq.available_quantity, eq.condition, eq.location, eq.specifications.replace('\n',' | ')[:200]]
        for c, val in enumerate(data, 1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.font = cell_font; cell.border = thin_border
            if c in (5,6): cell.alignment = Alignment(horizontal='center')
        # Color rows
        fill = green_fill if eq.available_quantity > 0 else red_fill
        for c in range(1, 10): ws.cell(row=r, column=c).fill = fill
    # Column widths
    widths = [15, 28, 18, 30, 12, 12, 14, 18, 35]
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    output = io.BytesIO()
    wb.save(output); output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'inventaire_imagine_{date.today().strftime("%Y%m%d")}.xlsx')

@app.route('/export/pdf')
@permission_required('manage_equipment')
def export_printer():
    """Page optimisee pour impression (CTRL+P -> PDF)"""
    return render_template('export_print.html', equipment=Equipment.query.order_by(Equipment.name).all(), now=tunisia_now())

# ═══════ I N I T   D B ═══════
def init_db():
    with app.app_context():
        db.create_all()
        if User.query.first(): return
        ar = CustomRole(name='Admin', icon='👑', description='Toutes les permissions'); ar.set_permissions([p['key'] for p in ALL_PERMISSIONS])
        sr = CustomRole(name='Staff', icon='👷', description='Emprunts et retours'); sr.set_permissions(['borrow_equipment','return_equipment'])
        mr = CustomRole(name='Manager', icon='🛡️', description='Gestion complete sans effacer historique'); mr.set_permissions(['manage_users','manage_equipment','borrow_equipment','return_equipment','manage_categories','view_logs','manage_schedule'])
        pr = CustomRole(name='En attente', icon='⏳', description='Nouveau compte en attente'); pr.set_permissions([])
        db.session.add_all([ar,sr,mr,pr]); db.session.flush()
        a = User(email='admin@imagine-events.com', full_name='Admin Imagine', role_id=ar.id); a.set_password('admin123')
        s = User(email='staff@imagine-events.com', full_name='Equipe Logistique', role_id=sr.id); s.set_password('staff123')
        db.session.add_all([a,s])
        cats = [Category(name=nm, icon=ic) for nm,ic in [('Ecrans & Affichage','📺'),('Sonorisation','🎤'),('Eclairage','💡'),('Scenes & Structures','🎭'),('Mobilier','🛋️'),('Cablage & Connectique','🔌')]]
        db.session.add_all(cats); db.session.commit()
        eqs = [
            Equipment(name='Ecran LED 43"',description='Ecran LED haute definition 43 pouces.',reference='IM-LED43-001',category_id=1,total_quantity=10,available_quantity=10,specifications='Taille: 43"\nResolution: Full HD\nLuminosite: 350 cd/m2\nConnectique: HDMI, VGA',condition='Excellent',location='Allee A - Etagere 1'),
            Equipment(name='Ecran LED 55"',description='Ecran LED 55 pouces pour evenements.',reference='IM-LED55-002',category_id=1,total_quantity=6,available_quantity=6,specifications='Taille: 55"\nResolution: 4K UHD',condition='Excellent',location='Allee A - Etagere 2'),
            Equipment(name='Micro Sans Fil SM58',description='Micro professionnel Shure.',reference='IM-MIC-003',category_id=2,total_quantity=12,available_quantity=12,specifications='Marque: Shure\nType: Dynamique\nPortee: 100m',condition='Bon etat',location='Allee B - Armoire 1'),
            Equipment(name='Lyre LED Beam',description='Projecteur lyre motorise a LED.',reference='IM-LYR-004',category_id=3,total_quantity=8,available_quantity=8,specifications='LED: 200W\nDMX: 16 canaux\nPrisme: 8 facettes',condition='Excellent',location='Allee C - Etagere 3'),
            Equipment(name='Canape Lounge Design',description='Canape 3 places pour receptions.',reference='IM-CAN-005',category_id=5,total_quantity=15,available_quantity=15,specifications='Places: 3\nMateriau: Velours premium',condition='Tres bon etat',location='Zone Mobilier - Rangee D'),
            Equipment(name='Barre LED RGB',description='Barre LED 144 LEDs/m pour eclairage.',reference='IM-BAR-006',category_id=3,total_quantity=20,available_quantity=20,specifications='LEDs: RGB 144/m\nAngle: 120 degres',condition='Bon etat',location='Allee C - Etagere 1'),
            Equipment(name='Enceinte Active 15"',description='Enceinte 15" 1000W pour sonorisation.',reference='IM-ENC-007',category_id=2,total_quantity=8,available_quantity=8,specifications='Puissance: 1000W\nSPL Max: 132 dB',condition='Excellent',location='Allee B - Sol'),
            Equipment(name='Scene Modulable 2x1m',description='Element de scene aluminium.',reference='IM-SCN-008',category_id=4,total_quantity=30,available_quantity=30,specifications='Dimensions: 200x100 cm\nCharge max: 750 kg/m2',condition='Bon etat',location='Zone Scenes'),
        ]
        db.session.add_all(eqs); db.session.commit()
        print("OK - admin@imagine-events.com / admin123")

init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
