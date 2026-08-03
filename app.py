"""
Imagine Inventory — Gestion de depot evenementiel
Application Flask pour Imagine Events Tunisia
"""
import os, uuid, json
from datetime import datetime, date, timedelta, timezone
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from PIL import Image

# Fuseau horaire Tunisie (UTC+1)
TUNISIA_TZ = timezone(timedelta(hours=1))
def tunisia_now():
    return datetime.now(TUNISIA_TZ)

# ── App config ──
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

# ── Models ──
class CustomRole(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='\U0001f464')
    description = db.Column(db.String(250), default='')
    permissions = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=tunisia_now)
    users = db.relationship('User', backref='role', lazy=True)
    def get_permissions(self):
        try: return json.loads(self.permissions) if self.permissions else []
        except: return []
    def set_permissions(self, pl): self.permissions = json.dumps(pl)
    def has_permission(self, p): return p in self.get_permissions()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=tunisia_now)
    borrows = db.relationship('Borrow', backref='user', lazy=True)
    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)
    def has_permission(self, perm):
        role = db.session.get(CustomRole, self.role_id) if self.role_id else None
        return role.has_permission(perm) if role else False
    @property
    def role_name(self):
        role = db.session.get(CustomRole, self.role_id) if self.role_id else None
        return role.name if role else 'Aucun role'

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='\U0001f4e6')
    equipment = db.relationship('Equipment', backref='category', lazy=True)

class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    reference = db.Column(db.String(100), unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    total_quantity = db.Column(db.Integer, default=1)
    available_quantity = db.Column(db.Integer, default=1)
    specifications = db.Column(db.Text, default='')
    condition = db.Column(db.String(50), default='Bon etat')
    location = db.Column(db.String(100), default='Depot principal')
    created_at = db.Column(db.DateTime, default=tunisia_now)
    images = db.relationship('EquipmentImage', backref='equipment', lazy=True, cascade='all, delete-orphan')
    borrows = db.relationship('Borrow', backref='equipment', lazy=True)
    def primary_image(self):
        return self.images[0].filename if self.images else None
    def all_images(self):
        return [img.filename for img in self.images]

class EquipmentImage(db.Model):
    __tablename__ = 'equipment_images'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=tunisia_now)

class Borrow(db.Model):
    __tablename__ = 'borrows'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    borrow_date = db.Column(db.DateTime, default=tunisia_now)
    expected_return_date = db.Column(db.Date, nullable=False)
    actual_return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='active')
    notes = db.Column(db.Text, default='')
    event_name = db.Column(db.String(200), default='')

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, default='')
    equipment_name = db.Column(db.String(200), default='')
    quantity = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=tunisia_now)

# ── Login manager ──
@login_manager.user_loader
def load_user(uid): return db.session.get(User, int(uid))

@app.template_filter('get_user')
def get_user_filter(uid): return db.session.get(User, int(uid)) if uid else None

# ── Helpers ──
def allowed_file(fn): return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_image(file):
    """Enregistre une image, retourne le nom du fichier ou None."""
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        return None
    file.seek(0, 2)
    if file.tell() == 0:
        return None
    file.seek(0)
    ext = file.filename.rsplit('.', 1)[1].lower()
    uname = f"{uuid.uuid4().hex}.{ext}"
    fpath = os.path.join(app.config['UPLOAD_FOLDER'], uname)
    try:
        file.save(fpath)
        img = Image.open(fpath)
        img.thumbnail((1200, 1200))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        jpg_name = f"{uuid.uuid4().hex}.jpg"
        jpg_path = os.path.join(app.config['UPLOAD_FOLDER'], jpg_name)
        img.save(jpg_path, 'JPEG', optimize=True, quality=85)
        if ext != 'jpg':
            try: os.remove(fpath)
            except: pass
        return jpg_name
    except Exception:
        if os.path.exists(fpath):
            return uname
        return None

def update_availability(eq_id):
    eq = db.session.get(Equipment, eq_id)
    if eq:
        qty = db.session.query(db.func.sum(Borrow.quantity)).filter_by(equipment_id=eq_id, status='active').scalar() or 0
        eq.available_quantity = max(0, eq.total_quantity - qty)
        db.session.commit()

def log_action(action, description='', equipment_name='', quantity=0):
    log = ActivityLog(user_id=current_user.id, action=action, description=description, equipment_name=equipment_name, quantity=quantity)
    db.session.add(log); db.session.commit()

# ── Permissions ──
ALL_PERMISSIONS = [
    {"key":"manage_users","label":"Gerer les utilisateurs","desc":"Creer, modifier, supprimer des comptes","icon":"\U0001f465"},
    {"key":"manage_roles","label":"Gerer les roles","desc":"Creer et modifier les roles et permissions","icon":"\U0001f510"},
    {"key":"manage_equipment","label":"Gerer le materiel","desc":"Ajouter, modifier, supprimer du materiel","icon":"\U0001f4e6"},
    {"key":"borrow_equipment","label":"Emprunter","desc":"Emprunter du materiel","icon":"\U0001f4e4"},
    {"key":"return_equipment","label":"Retourner","desc":"Marquer un emprunt comme retourne","icon":"\u2705"},
    {"key":"manage_categories","label":"Gerer les categories","desc":"Ajouter des categories de materiel","icon":"\U0001f4c2"},
    {"key":"view_logs","label":"Voir les logs","desc":"Consulter l'historique d'activite","icon":"\U0001f4dc"},
    {"key":"clear_history","label":"Effacer l'historique","desc":"Supprimer l'historique des emprunts","icon":"\U0001f5d1\ufe0f"},
]

# ── Decorator ──
def permission_required(perm):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if not current_user.has_permission(perm):
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
        email = request.form.get('email','').strip().lower()
        pw = request.form.get('password','')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(pw):
            login_user(user, remember=True)
            log = ActivityLog(user_id=user.id, action='login', description=f'Connexion de {user.full_name}')
            db.session.add(log); db.session.commit()
            flash(f'Bienvenue {user.full_name} !', 'success')
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Email ou mot de passe incorrect.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        name = request.form.get('full_name','').strip()
        pw = request.form.get('password','')
        if not email or not name or not pw: flash('Tous les champs requis.','error')
        elif request.form.get('confirm_password') != pw: flash('Mots de passe differents.','error')
        elif len(pw) < 6: flash('6 caracteres minimum.','error')
        elif User.query.filter_by(email=email).first(): flash('Email deja utilise.','error')
        else:
            u = User(email=email, full_name=name); u.set_password(pw)
            # Premier inscrit = admin, les suivants = staff
            if User.query.count() == 0:
                u.role_id = 1  # Admin
            else:
                pending = CustomRole.query.filter_by(name='En attente').first()
                if pending:
                    u.role_id = pending.id
            db.session.add(u); db.session.commit()
            flash('Compte cree ! Connectez-vous.','success')
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
    search = request.args.get('search','').strip()
    cat_filter = request.args.get('category','')
    q = Equipment.query
    if search:
        q = q.filter(db.or_(Equipment.name.ilike(f'%{search}%'),Equipment.description.ilike(f'%{search}%'),Equipment.reference.ilike(f'%{search}%'),Equipment.specifications.ilike(f'%{search}%'),Equipment.location.ilike(f'%{search}%')))
    if cat_filter: q = q.filter_by(category_id=int(cat_filter))
    eqs = q.order_by(Equipment.name).all()
    cats = Category.query.order_by(Category.name).all()
    ab = Borrow.query.filter(Borrow.status.in_(['active','late'])).order_by(Borrow.expected_return_date).all()
    today = date.today()
    for b in ab:
        if b.status == 'active' and b.expected_return_date < today: b.status = 'late'
    db.session.commit()
    eq_json = json.dumps([{'id':e.id,'name':e.name,'available_quantity':e.available_quantity} for e in Equipment.query.all()])
    allc = Equipment.query.count()
    avc = Equipment.query.filter(Equipment.available_quantity>0).count()
    lc = Borrow.query.filter_by(status='late').count()
    is_pending = not current_user.has_permission('borrow_equipment') and not current_user.has_permission('manage_equipment') and not current_user.has_permission('manage_users')
    return render_template('dashboard.html', equipment=eqs, is_pending=is_pending, categories=cats, active_borrows=ab, search=search, cat_filter=cat_filter, all_count=allc, available_count=avc, late_count=lc, equipment_json=eq_json, today=today)

@app.route('/equipment/<int:eid>')
@login_required
def equipment_detail(eid):
    eq = db.session.get(Equipment, eid)
    if not eq: flash('Introuvable.','error'); return redirect(url_for('dashboard'))
    borrows = Borrow.query.filter_by(equipment_id=eid).order_by(Borrow.borrow_date.desc()).all()
    return render_template('equipment_detail.html', eq=eq, borrows=borrows, today=date.today())

@app.route('/borrow/<int:eid>', methods=['POST'])
@permission_required('borrow_equipment')
def borrow_equipment(eid):
    eq = db.session.get(Equipment, eid)
    if not eq: flash('Introuvable.','error'); return redirect(url_for('dashboard'))
    qty = int(request.form.get('quantity',1))
    rd = request.form.get('return_date','')
    try: return_date = datetime.strptime(rd,'%Y-%m-%d').date()
    except: flash('Date invalide.','error'); return redirect(url_for('dashboard'))
    if return_date < date.today(): flash('Date dans le passe.','error'); return redirect(url_for('dashboard'))
    if qty < 1 or qty > eq.available_quantity: flash(f'Quantite invalide (max {eq.available_quantity}).','error'); return redirect(url_for('dashboard'))
    b = Borrow(user_id=current_user.id, equipment_id=eid, quantity=qty, expected_return_date=return_date, event_name=request.form.get('event_name','').strip(), notes=request.form.get('notes','').strip())
    db.session.add(b); db.session.commit()
    update_availability(eid)
    log_action('borrow', f'Emprunt de {qty}x {eq.name}', eq.name, qty)
    flash(f'{qty} x {eq.name} emprunte(s). Retour le {return_date.strftime("%d/%m/%Y")}.','success')
    return redirect(url_for('dashboard'))

@app.route('/return/<int:bid>', methods=['POST'])
@permission_required('return_equipment')
def return_equipment(bid):
    b = db.session.get(Borrow, bid)
    if not b or b.status not in ('active','late'):
        flash('Emprunt introuvable ou deja retourne.', 'error')
        return redirect(url_for('dashboard'))

    # Seul l'emprunteur ou un admin peut retourner
    is_admin = current_user.has_permission('manage_users')
    if b.user_id != current_user.id and not is_admin:
        flash('Vous ne pouvez retourner que vos propres emprunts. Seul un admin peut retourner pour quelqu\'un d\'autre.', 'error')
        return redirect(url_for('dashboard'))

    b.status = 'returned'; b.actual_return_date = tunisia_now()
    db.session.commit(); update_availability(b.equipment_id)
    who = current_user.full_name if b.user_id == current_user.id else f'{current_user.full_name} (admin) pour {b.user.full_name}'
    log_action('return', f'Retour de {b.quantity}x {b.equipment.name} par {who}', b.equipment.name, b.quantity)
    flash(f'{b.equipment.name} retourne avec succes.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/equipment/add', methods=['GET','POST'])
@permission_required('manage_equipment')
def add_equipment():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        if not name: flash('Nom requis.','error'); return redirect(url_for('add_equipment'))
        ref = request.form.get('reference','').strip() or f"IM-{uuid.uuid4().hex[:8].upper()}"
        eq = Equipment(name=name, description=request.form.get('description','').strip(), reference=ref,
                        category_id=int(request.form.get('category_id',0)) or None,
                        total_quantity=int(request.form.get('total_quantity',1)),
                        available_quantity=int(request.form.get('total_quantity',1)),
                        specifications=request.form.get('specifications','').strip(),
                        condition=request.form.get('condition','Bon etat'),
                        location=request.form.get('location','Depot principal'))
        db.session.add(eq); db.session.flush()
        for f in request.files.getlist('images'):
            sn = save_uploaded_image(f)
            if sn: db.session.add(EquipmentImage(filename=sn, equipment_id=eq.id))
        db.session.commit()
        log_action('add_equipment', f'Ajout de {name}', name)
        flash(f'"{name}" ajoute au depot !','success')
        return redirect(url_for('equipment_detail', eid=eq.id))
    cats = Category.query.order_by(Category.name).all()
    return render_template('add_equipment.html', categories=cats)

@app.route('/equipment/<int:eid>/edit', methods=['GET','POST'])
@permission_required('manage_equipment')
def edit_equipment(eid):
    eq = db.session.get(Equipment, eid)
    if not eq: flash('Introuvable.','error'); return redirect(url_for('dashboard'))
    if request.method == 'POST':
        eq.name = request.form.get('name','').strip()
        eq.description = request.form.get('description','').strip()
        ref = request.form.get('reference','').strip()
        if ref and ref != eq.reference: eq.reference = ref
        cid = request.form.get('category_id'); eq.category_id = int(cid) if cid else None
        old = eq.total_quantity; eq.total_quantity = int(request.form.get('total_quantity',eq.total_quantity))
        eq.available_quantity = max(0, eq.available_quantity + (eq.total_quantity - old))
        eq.specifications = request.form.get('specifications','').strip()
        eq.condition = request.form.get('condition','Bon etat')
        eq.location = request.form.get('location','Depot principal')
        for f in request.files.getlist('images'):
            sn = save_uploaded_image(f)
            if sn: db.session.add(EquipmentImage(filename=sn, equipment_id=eq.id))
        db.session.commit()
        flash(f'"{eq.name}" mis a jour.','success')
        return redirect(url_for('equipment_detail', eid=eq.id))
    cats = Category.query.order_by(Category.name).all()
    return render_template('edit_equipment.html', eq=eq, categories=cats)

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
def uploaded_file(fn):
    return send_from_directory(app.config['UPLOAD_FOLDER'], fn)

@app.route('/change-password', methods=['GET','POST'])
@login_required
def change_password():
    if request.method == 'POST':
        cp = request.form.get('current_password','')
        np = request.form.get('new_password','')
        if not current_user.check_password(cp): flash('Mot de passe actuel incorrect.','error')
        elif len(np) < 6: flash('6 caracteres minimum.','error')
        elif np != request.form.get('confirm_password',''): flash('Mots de passe differents.','error')
        else: current_user.set_password(np); db.session.commit(); flash('Mot de passe change !','success'); return redirect(url_for('dashboard'))
    return render_template('change_password.html')

@app.route('/admin/users')
@permission_required('manage_users')
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    all_roles = CustomRole.query.order_by(CustomRole.name).all()
    return render_template('manage_users.html', users=users, all_roles=all_roles)

@app.route('/admin/users/create', methods=['POST'])
@permission_required('manage_users')
def create_user():
    email = request.form.get('email','').strip().lower()
    name = request.form.get('full_name','').strip()
    pw = request.form.get('password','')
    rid = request.form.get('role_id')
    try: rid = int(rid) if rid else None
    except: rid = None
    if not email or not name or not pw: flash('Tous les champs requis.','error')
    elif len(pw) < 6: flash('6 caracteres minimum.','error')
    elif User.query.filter_by(email=email).first(): flash('Email deja utilise.','error')
    else:
        u = User(email=email, full_name=name); u.set_password(pw)
        if rid: u.role_id = rid
        db.session.add(u); db.session.commit()
        flash(f'Compte cree : {name} ({u.role_name})','success')
    return redirect(url_for('manage_users'))

@app.route('/admin/users/<int:uid>/edit', methods=['POST'])
@permission_required('manage_users')
def edit_user(uid):
    u = db.session.get(User, uid)
    if not u: flash('Introuvable.','error'); return redirect(url_for('manage_users'))
    if u.id == current_user.id: flash('Vous ne pouvez pas modifier votre propre role.','error'); return redirect(url_for('manage_users'))
    u.full_name = request.form.get('full_name',u.full_name).strip()
    rid = request.form.get('role_id')
    try: u.role_id = int(rid) if rid else None
    except: pass
    np = request.form.get('new_password','')
    if np and len(np) >= 6: u.set_password(np); flash(f'{u.full_name} mis a jour + mdp change.','success')
    elif np: flash('Mdp non change (6 car. min).','error')
    else: flash(f'{u.full_name} mis a jour.','success')
    db.session.commit()
    return redirect(url_for('manage_users'))

@app.route('/admin/users/<int:uid>/delete', methods=['POST'])
@permission_required('manage_users')
def delete_user(uid):
    u = db.session.get(User, uid)
    if not u: flash('Introuvable.','error')
    elif u.id == current_user.id: flash('Impossible de se supprimer.','error')
    elif Borrow.query.filter_by(user_id=uid, status='active').first(): flash(f'{u.full_name} a des emprunts en cours.','error')
    else: db.session.delete(u); db.session.commit(); flash(f'{u.full_name} supprime.','info')
    return redirect(url_for('manage_users'))

@app.route('/admin/roles')
@permission_required('manage_roles')
def manage_roles():
    roles = CustomRole.query.order_by(CustomRole.name).all()
    return render_template('manage_roles.html', roles=roles, all_permissions=ALL_PERMISSIONS)

@app.route('/admin/roles/create', methods=['POST'])
@permission_required('manage_roles')
def create_role():
    name = request.form.get('name','').strip()
    if not name: flash('Nom requis.','error')
    elif CustomRole.query.filter_by(name=name).first(): flash('Ce role existe deja.','error')
    else:
        r = CustomRole(name=name, icon=request.form.get('icon','\U0001f464'), description=request.form.get('description','').strip())
        r.set_permissions(request.form.getlist('permissions'))
        db.session.add(r); db.session.commit()
        flash(f'Role "{name}" cree.','success')
    return redirect(url_for('manage_roles'))

@app.route('/admin/roles/<int:rid>/edit', methods=['POST'])
@permission_required('manage_roles')
def edit_role(rid):
    r = db.session.get(CustomRole, rid)
    if not r: flash('Role introuvable.','error'); return redirect(url_for('manage_roles'))
    r.name = request.form.get('name',r.name).strip()
    r.icon = request.form.get('icon',r.icon)
    r.description = request.form.get('description','').strip()
    r.set_permissions(request.form.getlist('permissions'))
    db.session.commit()
    flash(f'Role "{r.name}" mis a jour.','success')
    return redirect(url_for('manage_roles'))

@app.route('/admin/roles/<int:rid>/delete', methods=['POST'])
@permission_required('manage_roles')
def delete_role(rid):
    r = db.session.get(CustomRole, rid)
    if not r: flash('Role introuvable.','error')
    elif User.query.filter_by(role_id=rid).first(): flash('Des utilisateurs utilisent ce role.','error')
    else: db.session.delete(r); db.session.commit(); flash(f'Role "{r.name}" supprime.','info')
    return redirect(url_for('manage_roles'))

@app.route('/admin/clear-history', methods=['POST'])
@permission_required('clear_history')
def clear_history():
    pw = request.form.get('password','')
    if not current_user.check_password(pw): flash('Mot de passe incorrect.','error'); return redirect(url_for('dashboard'))
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
    pw = request.form.get('password','')
    if not current_user.check_password(pw): flash('Mot de passe incorrect.','error'); return redirect(url_for('equipment_detail', eid=eid))
    c = Borrow.query.filter_by(equipment_id=eid, status='returned').count()
    Borrow.query.filter_by(equipment_id=eid, status='returned').delete(); db.session.commit()
    log_action('clear_history', f'Historique efface pour {eq.name} ({c} emprunts)')
    flash(f'{c} emprunt(s) effaces pour {eq.name}.','success')
    return redirect(url_for('equipment_detail', eid=eid))

@app.route('/admin/logs')
@permission_required('view_logs')
def activity_logs():
    page = request.args.get('page',1,type=int)
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).paginate(page=page, per_page=50, error_out=False)
    return render_template('activity_logs.html', logs=logs)

@app.route('/categories/add', methods=['POST'])
@permission_required('manage_categories')
def add_category():
    name = request.form.get('name','').strip()
    icon = request.form.get('icon','\U0001f4e6')
    if name and not Category.query.filter_by(name=name).first():
        db.session.add(Category(name=name, icon=icon)); db.session.commit()
        log_action('add_category', f'Ajout de la categorie {name}')
        flash(f'Categorie "{name}" ajoutee.','success')
    return redirect(url_for('dashboard'))


@app.route('/categories/<int:cid>/delete', methods=['POST'])
@permission_required('manage_categories')
def delete_category(cid):
    cat = db.session.get(Category, cid)
    if not cat: flash('Categorie introuvable.','error')
    elif Equipment.query.filter_by(category_id=cid).first(): flash(f'Des materiels utilisent la categorie {cat.name}. Reassignez-les d\'abord.','error')
    else:
        db.session.delete(cat); db.session.commit()
        log_action('delete_category', f'Suppression de la categorie {cat.name}')
        flash(f'Categorie "{cat.name}" supprimee.','info')
    return redirect(url_for('dashboard'))

# ── Init DB ──
def init_db():
    with app.app_context():
        db.create_all()
        if User.query.first(): return
        ar = CustomRole(name='Admin', icon='\U0001f451', description='Toutes les permissions')
        ar.set_permissions([p['key'] for p in ALL_PERMISSIONS])
        sr = CustomRole(name='Staff', icon='\U0001f477', description='Emprunts et retours')
        sr.set_permissions(['borrow_equipment','return_equipment'])
        pr = CustomRole(name='En attente', icon='⏳', description='Nouveau compte en attente de validation')
        pr.set_permissions([])
        mr = CustomRole(name='Manager', icon='\U0001f6e1\ufe0f', description='Gestion complete sans effacer historique')
        mr.set_permissions(['manage_users','manage_equipment','borrow_equipment','return_equipment','manage_categories','view_logs'])
        db.session.add_all([ar,sr,mr,pr]); db.session.flush()
        a = User(email='admin@imagine-events.com', full_name='Admin Imagine', role_id=ar.id); a.set_password('admin123')
        s = User(email='staff@imagine-events.com', full_name='Equipe Logistique', role_id=sr.id); s.set_password('staff123')
        db.session.add_all([a,s])
        cats = [Category(name=nm, icon=ic) for nm,ic in [('Ecrans & Affichage','\U0001f4fa'),('Sonorisation','\U0001f3a4'),('Eclairage','\U0001f4a1'),('Scenes & Structures','\U0001f3ad'),('Mobilier','\U0001f6cb\ufe0f'),('Cablage & Connectique','\U0001f50c')]]
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
