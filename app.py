"""
Imagine Inventory — Gestion de dépôt événementiel
Application Flask pour la digitalisation du dépôt Imagine Events Tunisia
"""
import os
import uuid
from datetime import datetime, date, timedelta, timezone
from functools import wraps

# Fuseau horaire Tunisie (UTC+1)
TUNISIA_TZ = timezone(timedelta(hours=1))

def tunisia_now():
    return datetime.now(TUNISIA_TZ)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user, UserMixin
)
from PIL import Image

# ── App config ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'imagine-events-tunisia-secret-key-2026')

# Base de données : PostgreSQL en production, SQLite en développement
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # PostgreSQL (Render, Railway, Heroku...)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
else:
    # SQLite local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'


# ── Models ──────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=tunisia_now)
    borrows = db.relationship('Borrow', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, perm):
        role = db.session.get(CustomRole, self.role_id) if self.role_id else None
        if not role:
            return False
        return role.has_permission(perm)

    @property
    def role_name(self):
        role = db.session.get(CustomRole, self.role_id) if self.role_id else None
        return role.name if role else 'Aucun role'


class CustomRole(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='👤')
    description = db.Column(db.String(250), default='')
    permissions = db.Column(db.Text, default='')  # JSON list
    created_at = db.Column(db.DateTime, default=tunisia_now)
    users = db.relationship('User', backref='role', lazy=True)

    def get_permissions(self):
        import json
        try:
            return json.loads(self.permissions) if self.permissions else []
        except:
            return []

    def set_permissions(self, perms_list):
        import json
        self.permissions = json.dumps(perms_list)

    def has_permission(self, perm):
        return perm in self.get_permissions()


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='📦')
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
    specifications = db.Column(db.Text, default='')  # JSON-like string
    condition = db.Column(db.String(50), default='Bon état')
    location = db.Column(db.String(100), default='Dépôt principal')
    created_at = db.Column(db.DateTime, default=tunisia_now)
    images = db.relationship('EquipmentImage', backref='equipment', lazy=True, cascade='all, delete-orphan')
    borrows = db.relationship('Borrow', backref='equipment', lazy=True)

    def primary_image(self):
        if self.images:
            return self.images[0].filename
        return None

    def all_images(self):
        return [img.filename for img in self.images]

    def is_available(self):
        return self.available_quantity > 0


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
    status = db.Column(db.String(50), default='active')  # active / returned / late
    notes = db.Column(db.Text, default='')
    event_name = db.Column(db.String(200), default='')


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # login, borrow, return, delete, create_user, delete_borrow, clear_history
    description = db.Column(db.Text, default='')
    equipment_name = db.Column(db.String(200), default='')
    quantity = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=tunisia_now)


# ── Login manager ───────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.template_filter('get_user')
def get_user_filter(user_id):
    return db.session.get(User, int(user_id)) if user_id else None


# ── Helpers ─────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file):
    """Save uploaded image, return filename or None."""
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(full_path)
        # Create thumbnail / resize if needed
        try:
            img = Image.open(full_path)
            img.thumbnail((1200, 1200))
            img.save(full_path, optimize=True, quality=85)
        except Exception:
            pass
        return unique_name
    return None


def update_availability(equipment_id):
    """Recalculate available quantity for an equipment."""
    equipment = db.session.get(Equipment, equipment_id)
    if not equipment:
        return
    active_qty = db.session.query(db.func.sum(Borrow.quantity)).filter_by(
        equipment_id=equipment_id, status='active'
    ).scalar() or 0
    equipment.available_quantity = max(0, equipment.total_quantity - active_qty)
    db.session.commit()


def log_action(action, description='', equipment_name='', quantity=0):
    """Record an activity in the logs."""
    log = ActivityLog(
        user_id=current_user.id,
        action=action,
        description=description,
        equipment_name=equipment_name,
        quantity=quantity
    )
    db.session.add(log)
    db.session.commit()


# ── Decorator for permissions ──────────────────────────────

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


# ── Routes: Auth ────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=request.form.get('remember'))
            next_page = request.args.get('next')
            # Log it
            log = ActivityLog(user_id=user.id, action='login', description=f'Connexion de {user.full_name}')
            db.session.add(log); db.session.commit()
            flash(f'Bienvenue {user.full_name} !', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Email ou mot de passe incorrect.', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not email or not full_name or not password:
            flash('Tous les champs sont requis.', 'error')
        elif password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'error')
        elif len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'error')
        else:
            user = User(email=email, full_name=full_name)
            user.set_password(password)
            # First user is admin
            if User.query.count() == 0:
                user.role = 'admin'
            db.session.add(user)
            db.session.commit()
            flash('Compte créé avec succès ! Connectez-vous.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    log_action('logout', f'Deconnexion de {current_user.full_name}')
    logout_user()
    flash('Vous etes deconnecte.', 'info')
    return redirect(url_for('login'))


# ── Routes: Dashboard ───────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '')

    query = Equipment.query

    if search:
        query = query.filter(
            db.or_(
                Equipment.name.ilike(f'%{search}%'),
                Equipment.description.ilike(f'%{search}%'),
                Equipment.reference.ilike(f'%{search}%'),
                Equipment.specifications.ilike(f'%{search}%'),
                Equipment.location.ilike(f'%{search}%'),
            )
        )

    if category_filter:
        query = query.filter_by(category_id=int(category_filter))

    equipment_list = query.order_by(Equipment.name).all()
    categories = Category.query.order_by(Category.name).all()

    # Active borrows
    active_borrows = Borrow.query.filter_by(
        status='active'
    ).order_by(Borrow.expected_return_date).all()

    # Late returns
    today = date.today()
    for b in active_borrows:
        if b.expected_return_date < today and b.status == 'active':
            b.status = 'late'
    db.session.commit()

    return render_template(
        'dashboard.html',
        equipment_list=equipment_list,
        categories=categories,
        active_borrows=active_borrows,
        search=search,
        category_filter=category_filter,
        today=today
    )


# ── Routes: Equipment detail ────────────────────────────────

@app.route('/equipment/<int:equipment_id>')
@login_required
def equipment_detail(equipment_id):
    equipment = db.session.get(Equipment, equipment_id)
    if not equipment:
        flash('Matériel introuvable.', 'error')
        return redirect(url_for('dashboard'))

    borrows = Borrow.query.filter_by(
        equipment_id=equipment_id
    ).order_by(Borrow.borrow_date.desc()).all()

    return render_template(
        'equipment_detail.html',
        equipment=equipment,
        borrows=borrows,
        today=date.today()
    )


# ── Routes: Borrow ──────────────────────────────────────────

@permission_required("borrow_equipment")
@app.route('/borrow/<int:equipment_id>', methods=['POST'])
@login_required
def borrow_equipment(equipment_id):
    equipment = db.session.get(Equipment, equipment_id)
    if not equipment:
        return jsonify({'success': False, 'message': 'Matériel introuvable.'}), 404

    qty = int(request.form.get('quantity', 1))
    return_date_str = request.form.get('return_date', '')
    event_name = request.form.get('event_name', '').strip()
    notes = request.form.get('notes', '').strip()

    # Validate
    if not return_date_str:
        return jsonify({'success': False, 'message': 'Date de retour requise.'}), 400

    try:
        return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'message': 'Format de date invalide.'}), 400

    if return_date < date.today():
        return jsonify({'success': False, 'message': 'La date de retour ne peut pas etre dans le passe.'}), 400

    if qty < 1 or qty > equipment.available_quantity:
        return jsonify({
            'success': False,
            'message': f'Quantité invalide. Disponible: {equipment.available_quantity}'
        }), 400

    # Create borrow
    borrow = Borrow(
        user_id=current_user.id,
        equipment_id=equipment_id,
        quantity=qty,
        expected_return_date=return_date,
        event_name=event_name,
        notes=notes
    )
    db.session.add(borrow)
    db.session.commit()
    update_availability(equipment_id)

    log_action('borrow', f'Emprunt de {qty}x {equipment.name}', equipment.name, qty)

    flash(f'{qty} × {equipment.name} emprunté(s) jusqu\'au {return_date.strftime("%d/%m/%Y")}.', 'success')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Emprunt enregistré.'})

    return redirect(url_for('dashboard'))


@permission_required("return_equipment")
@app.route('/return/<int:borrow_id>', methods=['POST'])
@login_required
def return_equipment(borrow_id):
    borrow = db.session.get(Borrow, borrow_id)
    if not borrow:
        flash('Emprunt introuvable.', 'error')
        return redirect(url_for('dashboard'))

    borrow.status = 'returned'
    borrow.actual_return_date = tunisia_now()
    db.session.commit()
    update_availability(borrow.equipment_id)

    log_action('return', f'Retour de {borrow.quantity}x {borrow.equipment.name}', borrow.equipment.name, borrow.quantity)

    flash(f'{borrow.equipment.name} retourné avec succès.', 'success')
    return redirect(url_for('dashboard'))


# ── Routes: Add / Edit equipment ────────────────────────────
@permission_required("manage_equipment")

@app.route('/equipment/add', methods=['GET', 'POST'])
@login_required
def add_equipment():
    categories = Category.query.order_by(Category.name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        reference = request.form.get('reference', '').strip()
        category_id = request.form.get('category_id')
        total_quantity = int(request.form.get('total_quantity', 1))
        specifications = request.form.get('specifications', '').strip()
        condition = request.form.get('condition', 'Bon état')
        location = request.form.get('location', 'Dépôt principal')

        if not name:
            flash('Le nom du matériel est requis.', 'error')
            return render_template('add_equipment.html', categories=categories)

        if reference and Equipment.query.filter_by(reference=reference).first():
            flash('Cette référence existe déjà.', 'error')
            return render_template('add_equipment.html', categories=categories)

        if not reference:
            reference = f"IM-{uuid.uuid4().hex[:8].upper()}"

        equipment = Equipment(
            name=name,
            description=description,
            reference=reference,
            category_id=int(category_id) if category_id else None,
            total_quantity=total_quantity,
            available_quantity=total_quantity,
            specifications=specifications,
            condition=condition,
            location=location
        )
        db.session.add(equipment)
        db.session.flush()  # get equipment.id

        # Handle image uploads
        images = request.files.getlist('images')
        for img_file in images:
            saved_name = save_uploaded_image(img_file)
            if saved_name:
                db.session.add(EquipmentImage(filename=saved_name, equipment_id=equipment.id))

        db.session.commit()
        flash(f'"{name}" ajouté au dépôt !', 'success')
        return redirect(url_for('equipment_detail', equipment_id=equipment.id))

    return render_template('add_equipment.html', categories=categories)

@permission_required("manage_equipment")

@app.route('/equipment/<int:equipment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_equipment(equipment_id):
    equipment = db.session.get(Equipment, equipment_id)
    if not equipment:
        flash('Matériel introuvable.', 'error')
        return redirect(url_for('dashboard'))

    categories = Category.query.order_by(Category.name).all()

    if request.method == 'POST':
        equipment.name = request.form.get('name', '').strip()
        equipment.description = request.form.get('description', '').strip()
        new_ref = request.form.get('reference', '').strip()

        if new_ref and new_ref != equipment.reference:
            if Equipment.query.filter_by(reference=new_ref).first():
                flash('Cette référence existe déjà.', 'error')
                return render_template('edit_equipment.html', equipment=equipment, categories=categories)
            equipment.reference = new_ref

        cat_id = request.form.get('category_id')
        equipment.category_id = int(cat_id) if cat_id else None

        new_total = int(request.form.get('total_quantity', equipment.total_quantity))
        diff = new_total - equipment.total_quantity
        equipment.total_quantity = new_total
        equipment.available_quantity = max(0, equipment.available_quantity + diff)

        equipment.specifications = request.form.get('specifications', '').strip()
        equipment.condition = request.form.get('condition', 'Bon état')
        equipment.location = request.form.get('location', 'Dépôt principal')

        # New images
        images = request.files.getlist('images')
        for img_file in images:
            saved_name = save_uploaded_image(img_file)
            if saved_name:
                db.session.add(EquipmentImage(filename=saved_name, equipment_id=equipment.id))

        db.session.commit()
        flash(f'"{equipment.name}" mis à jour.', 'success')
        return redirect(url_for('equipment_detail', equipment_id=equipment.id))

    return render_template('edit_equipment.html', equipment=equipment, categories=categories)


@app.route('/equipment/<int:equipment_id>/delete-image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(equipment_id, image_id):
    img = db.session.get(EquipmentImage, image_id)
    if img and img.equipment_id == equipment_id:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(img)
        db.session.commit()
        flash('Image supprimée.', 'info')
    return redirect(url_for('edit_equipment', equipment_id=equipment_id))
@permission_required("manage_equipment")


@app.route('/equipment/<int:equipment_id>/delete', methods=['POST'])
@login_required
def delete_equipment(equipment_id):
    equipment = db.session.get(Equipment, equipment_id)
    if not equipment:
        flash('Matériel introuvable.', 'error')
        return redirect(url_for('dashboard'))

    # Delete image files
    for img in equipment.images:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.session.delete(equipment)
    db.session.commit()
    flash(f'"{equipment.name}" supprimé du dépôt.', 'info')
    return redirect(url_for('dashboard'))


# ── Routes: Uploads ─────────────────────────────────────────

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ── Routes: Change Password ─────────────────────────────────

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        if not current_user.check_password(current_pw):
            flash('Mot de passe actuel incorrect.', 'error')
        elif len(new_pw) < 6:
            flash('Le nouveau mot de passe doit contenir au moins 6 caractères.', 'error')
        elif new_pw != confirm:
            flash('Les mots de passe ne correspondent pas.', 'error')
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash('Mot de passe changé avec succès !', 'success')
            return redirect(url_for('dashboard'))

    return render_template('change_password.html')


# ── Routes: User Management (admin only) ─────────────────────

@app.route('/admin/users')
@permission_required("manage_users")
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    all_roles = CustomRole.query.order_by(CustomRole.name).all()
    return render_template('manage_users.html', users=users, all_roles=all_roles)


@app.route('/admin/users/create', methods=['POST'])
@permission_required("manage_users")
def create_user():
    email = request.form.get('email', '').strip().lower()
    full_name = request.form.get('full_name', '').strip()
    password = request.form.get('password', '')
    role_id = request.form.get('role_id')
    if role_id:
        try: role_id = int(role_id)
        except: role_id = None

    if not email or not full_name or not password:
        flash('Tous les champs sont requis.', 'error')
    elif len(password) < 6:
        flash('Mot de passe : 6 caracteres minimum.', 'error')
    elif User.query.filter_by(email=email).first():
        flash('Cet email est deja utilise.', 'error')
    else:
        user = User(email=email, full_name=full_name)
        if role_id: user.role_id = role_id
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        rolename = user.role_name
        flash(f'Compte cree : {full_name} ({rolename})', 'success')

    return redirect(url_for('manage_users'))


@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@permission_required("manage_users")
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('manage_users'))

    if user.id == current_user.id:
        flash('Vous ne pouvez pas modifier votre propre role.', 'error')
        return redirect(url_for('manage_users'))

    user.full_name = request.form.get('full_name', user.full_name).strip()
    role_id = request.form.get('role_id')
    if role_id:
        try: user.role_id = int(role_id)
        except: pass

    new_pw = request.form.get('new_password', '')
    if new_pw and len(new_pw) >= 6:
        user.set_password(new_pw)
        flash(f'{user.full_name} mis a jour + mot de passe change.', 'success')
    elif new_pw:
        flash('Mot de passe non change (6 caracteres minimum).', 'error')
    else:
        flash(f'{user.full_name} mis a jour.', 'success')

    db.session.commit()
    return redirect(url_for('manage_users'))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@permission_required("manage_users")
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('Utilisateur introuvable.', 'error')
    elif user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'error')
    elif Borrow.query.filter_by(user_id=user_id, status='active').first():
        flash(f'{user.full_name} a des emprunts en cours.', 'error')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'{user.full_name} supprime.', 'info')

    return redirect(url_for('manage_users'))


# ── Routes: Delete borrow history (admin only, password required) ──

@app.route('/admin/clear-history', methods=['POST'])
@permission_required("clear_history")
def clear_history():
    password = request.form.get('password', '')
    if not current_user.check_password(password):
        flash('Mot de passe administrateur incorrect.', 'error')
        return redirect(url_for('dashboard'))

    count = Borrow.query.filter_by(status='returned').count()
    Borrow.query.filter_by(status='returned').delete()
    db.session.commit()

    log_action('clear_history', f'Historique global efface ({count} emprunts termines)')
    flash(f'{count} emprunt(s) termines effaces de l\'historique.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/equipment/<int:equipment_id>/clear-history', methods=['POST'])
@permission_required("clear_history")
def clear_equipment_history(equipment_id):
    eq = db.session.get(Equipment, equipment_id)
    if not eq:
        flash('Materiel introuvable.', 'error')
        return redirect(url_for('dashboard'))

    password = request.form.get('password', '')
    if not current_user.check_password(password):
        flash('Mot de passe administrateur incorrect.', 'error')
        return redirect(url_for('equipment_detail', equipment_id=equipment_id))

    count = Borrow.query.filter_by(equipment_id=equipment_id, status='returned').count()
    Borrow.query.filter_by(equipment_id=equipment_id, status='returned').delete()
    db.session.commit()

    log_action('clear_history', f'Historique efface pour {eq.name} ({count} emprunts)')
    flash(f'{count} emprunt(s) termines effaces pour {eq.name}.', 'success')
    return redirect(url_for('equipment_detail', equipment_id=equipment_id))


# ── Routes: Activity Logs (admin only) ──────────────────────

@app.route('/admin/logs')
@permission_required("view_logs")
def activity_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('activity_logs.html', logs=logs)

@permission_required("manage_categories")

# ── Routes: Categories ──────────────────────────────────────

@app.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', '📦')
    if name and not Category.query.filter_by(name=name).first():
        db.session.add(Category(name=name, icon=icon))
        db.session.commit()
        flash(f'Catégorie "{name}" ajoutée.', 'success')
    return redirect(url_for('dashboard'))


# ── Init DB & seed ──────────────────────────────────────────

def init_db():
    """Create tables and seed with sample data."""
    with app.app_context():
        db.create_all()

        # Skip if already seeded
        if User.query.first():
            return

        # Create default roles
        admin_role = CustomRole(name='Admin', icon='👑',
                               description='Toutes les permissions')
        admin_role.set_permissions([p['key'] for p in ALL_PERMISSIONS])

        staff_role = CustomRole(name='Staff', icon='👷',
                               description='Emprunts et retours uniquement')
        staff_role.set_permissions(['borrow_equipment', 'return_equipment'])

        manager_role = CustomRole(name='Manager', icon='🛡️',
                                 description='Gestion complete sans supprimer l\'historique')
        manager_role.set_permissions(['manage_users', 'manage_equipment', 'borrow_equipment',
                                       'return_equipment', 'manage_categories', 'view_logs'])

        db.session.add_all([admin_role, staff_role, manager_role])
        db.session.flush()

        # Admin user
        admin = User(email='admin@imagine-events.com', full_name='Admin Imagine', role_id=admin_role.id)
        admin.set_password('admin123')
        db.session.add(admin)

        # Staff user
        staff = User(email='staff@imagine-events.com', full_name='Equipe Logistique', role_id=staff_role.id)
        staff.set_password('staff123')
        db.session.add(staff)

        # Categories
        cats = [
            Category(name='Écrans & Affichage', icon='📺'),
            Category(name='Sonorisation', icon='🎤'),
            Category(name='Éclairage', icon='💡'),
            Category(name='Scènes & Structures', icon='🎭'),
            Category(name='Mobilier', icon='🛋️'),
            Category(name='Câblage & Connectique', icon='🔌'),
        ]
        db.session.add_all(cats)
        db.session.commit()

        # Sample equipment
        samples = [
            Equipment(name='Écran LED 43"', description='Écran LED haute définition 43 pouces, idéal pour affichage et présentations.', reference='IM-LED43-001', category_id=1, total_quantity=10, available_quantity=10, specifications='Taille: 43" (109 cm)\nRésolution: 1920×1080 Full HD\nLuminosité: 350 cd/m²\nConnectique: HDMI, VGA, USB', condition='Excellent', location='Allée A - Étagère 1'),
            Equipment(name='Écran LED 55"', description='Écran LED grande taille 55 pouces pour événements professionnels.', reference='IM-LED55-002', category_id=1, total_quantity=6, available_quantity=6, specifications='Taille: 55" (140 cm)\nRésolution: 3840×2160 4K UHD\nLuminosité: 400 cd/m²\nConnectique: HDMI 2.1, DisplayPort', condition='Excellent', location='Allée A - Étagère 2'),
            Equipment(name='Micro Sans Fil SM58', description='Microphone sans fil professionnel Shure, qualité broadcast.', reference='IM-MIC-003', category_id=2, total_quantity=12, available_quantity=12, specifications='Marque: Shure\nType: Dynamique\nPortée: 100m\nFréquence: UHF', condition='Bon état', location='Allée B - Armoire 1'),
            Equipment(name='Lyre LED Beam', description='Projecteur lyre motorisé à LED pour effets dynamiques.', reference='IM-LYR-004', category_id=3, total_quantity=8, available_quantity=8, specifications='LED: 200W\nDMX: 16 canaux\nZoom: 8° - 40°\nPrisme: 8 facettes', condition='Excellent', location='Allée C - Étagère 3'),
            Equipment(name='Canapé Lounge Design', description='Canapé élégant 3 places pour espaces lounge et réceptions.', reference='IM-CAN-005', category_id=5, total_quantity=15, available_quantity=15, specifications='Places: 3\nCouleurs: Noir, Blanc, Gris\nMatériau: Velours premium\nStructure: Bois massif', condition='Très bon état', location='Zone Mobilier - Rangée D'),
            Equipment(name='Barre LED RGB', description='Barre LED linéaire 144 LEDs/m pour éclairage architectural et scénique.', reference='IM-BAR-006', category_id=3, total_quantity=20, available_quantity=20, specifications='LEDs: RGB 144 LEDs/m\nAngle: 120°\nLongueur: 1m\nContrôle: DMX/Art-Net', condition='Bon état', location='Allée C - Étagère 1'),
            Equipment(name='Enceinte Active 15"', description='Enceinte amplifiée 15 pouces 1000W pour sonorisation événementielle.', reference='IM-ENC-007', category_id=2, total_quantity=8, available_quantity=8, specifications='Puissance: 1000W Peak\nHP: 15" + driver 1.4"\nSPL Max: 132 dB\nPoids: 28 kg', condition='Excellent', location='Allée B - Sol'),
            Equipment(name='Scène Modulable 2×1m', description='Élément de scène modulable 2m × 1m, structure aluminium.', reference='IM-SCN-008', category_id=4, total_quantity=30, available_quantity=30, specifications='Dimensions: 200×100 cm\nHauteur réglable: 40-100 cm\nCharge max: 750 kg/m²\nMatériau: Aluminium + contreplaqué', condition='Bon état', location='Zone Scènes - Extérieur'),
        ]
        db.session.add_all(samples)
        db.session.commit()

        print("✅ Base de données initialisée avec succès !")
        print("   Comptes : admin@imagine-events.com / admin123 (admin)")
        print("             staff@imagine-events.com / staff123 (staff)")


# ⚡ Auto-init DB au démarrage (pour Render / production)
init_db()


# ── Main ────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
