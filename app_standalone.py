"""
AgriChain Uganda - Blockchain Agricultural Supply Chain
Self-contained single-file version using only Flask + Werkzeug + sqlite3 (stdlib)
Run: python app_standalone.py
"""

from flask import Flask, request, session, redirect, url_for, render_template_string, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, hashlib, json, uuid, os
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = 'agrichain-kasese-uganda-2024-secret'
DB = os.path.join(os.path.dirname(__file__), 'agri_chain.db')

# ══════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            phone TEXT,
            location TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE NOT NULL,
            crop_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT DEFAULT 'kg',
            location TEXT,
            district TEXT DEFAULT 'Kasese',
            harvest_date TEXT,
            quality_grade TEXT DEFAULT 'A',
            status TEXT DEFAULT 'harvested',
            farmer_id INTEGER,
            current_owner_id INTEGER,
            blockchain_hash TEXT,
            is_flagged INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(farmer_id) REFERENCES users(id),
            FOREIGN KEY(current_owner_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id TEXT UNIQUE NOT NULL,
            product_id INTEGER,
            action TEXT NOT NULL,
            sender_id INTEGER,
            receiver_id INTEGER,
            block_index INTEGER,
            block_hash TEXT,
            previous_hash TEXT,
            payload TEXT,
            notes TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idx INTEGER UNIQUE NOT NULL,
            timestamp TEXT,
            data TEXT,
            previous_hash TEXT,
            hash TEXT UNIQUE,
            nonce INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            ip_address TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        """)
        conn.commit()

def seed_db():
    with get_db() as conn:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return
        users = [
            ('Admin User','admin@agrichain.ug', generate_password_hash('admin123'),'admin','Kampala','+256700000000'),
            ('John Muhindo','farmer@agrichain.ug', generate_password_hash('farmer123'),'farmer','Kasese','+256700000001'),
            ('Grace Birungi','buyer@agrichain.ug', generate_password_hash('buyer123'),'buyer','Kampala','+256700000002'),
            ('David Bwambale','transporter@agrichain.ug', generate_password_hash('transport123'),'transporter','Kasese','+256700000003'),
            ('Dr. Ruth Kyomugisha','regulator@agrichain.ug', generate_password_hash('regulator123'),'regulator','Kampala','+256700000004'),
            ('Peter Kato','farmer2@agrichain.ug', generate_password_hash('farmer123'),'farmer','Kasese','+256700000005'),
        ]
        conn.executemany("INSERT INTO users(name,email,password,role,location,phone) VALUES(?,?,?,?,?,?)", users)
        conn.commit()

        # Genesis block
        genesis_data = json.dumps({'genesis': True, 'message': 'AgriChain Genesis Block - Kasese District Uganda'})
        genesis_hash = _calc_hash(0, '2024-01-01T00:00:00', genesis_data, '0'*64, 0)
        conn.execute("INSERT INTO blocks(idx,timestamp,data,previous_hash,hash,nonce) VALUES(?,?,?,?,?,?)",
                     (0,'2024-01-01T00:00:00', genesis_data,'0'*64, genesis_hash, 0))
        conn.commit()

        farmers = conn.execute("SELECT id FROM users WHERE role='farmer'").fetchall()
        buyer = conn.execute("SELECT id FROM users WHERE role='buyer'").fetchone()
        products_data = [
            ('Maize',500,'Hima, Kasese','2024-03-15','A','delivered', farmers[0]['id'], buyer['id']),
            ('Coffee',200,'Kilembe, Kasese','2024-03-10','A+','approved', farmers[0]['id'], buyer['id']),
            ('Beans',150,'Bugoye, Kasese','2024-03-20','B','in_transit', farmers[1]['id'], farmers[1]['id']),
            ('Tomatoes',80,'Maliba, Kasese','2024-03-22','A','harvested', farmers[1]['id'], farmers[1]['id']),
            ('Maize',300,'Rukoki, Kasese','2024-03-18','A','transferred', farmers[0]['id'], buyer['id']),
            ('Sorghum',120,'Kisinga, Kasese','2024-03-12','B+','delivered', farmers[1]['id'], buyer['id']),
        ]
        blk_counter = conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
        prev_hash_seed = conn.execute("SELECT hash FROM blocks ORDER BY idx DESC LIMIT 1").fetchone()['hash']
        for i, (crop, qty, loc, hdate, grade, status, fid, oid) in enumerate(products_data):
            code = f'PC-2024-{str(i+1).zfill(4)}'
            ts_seed = datetime.utcnow().isoformat()
            data_str = json.dumps({'action':'harvested','crop':crop})
            nonce, block_hash = _mine(blk_counter, ts_seed, data_str, prev_hash_seed)
            conn.execute("INSERT INTO blocks(idx,timestamp,data,previous_hash,hash,nonce) VALUES(?,?,?,?,?,?)",
                         (blk_counter, ts_seed, data_str, prev_hash_seed, block_hash, nonce))
            blk_idx = blk_counter
            blk_counter += 1
            prev_hash_seed = block_hash
            is_approved = 1 if status == 'approved' else 0
            conn.execute("""INSERT INTO products(product_code,crop_type,quantity,unit,location,district,
                            harvest_date,quality_grade,status,farmer_id,current_owner_id,blockchain_hash,is_approved)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (code,crop,qty,'kg',loc,'Kasese',hdate,grade,status,fid,oid,block_hash,is_approved))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("""INSERT INTO transactions(tx_id,product_id,action,sender_id,block_index,block_hash,previous_hash,payload)
                            VALUES(?,?,?,?,?,?,?,?)""",
                         (str(uuid.uuid4()).replace('-','')[:20].upper(), pid,'harvested',fid,blk_idx,block_hash,prev_hash_seed,
                          json.dumps({'crop':crop,'qty':qty,'loc':loc})))
        conn.commit()

# ══════════════════════════════════════════════
#  BLOCKCHAIN ENGINE
# ══════════════════════════════════════════════

def _calc_hash(index, timestamp, data, previous_hash, nonce):
    s = json.dumps({'index':index,'timestamp':str(timestamp),'data':data,'previous_hash':previous_hash,'nonce':nonce}, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()

def _mine(index, timestamp, data, previous_hash, difficulty=2):
    target = '0' * difficulty
    nonce = 0
    while True:
        h = _calc_hash(index, timestamp, data, previous_hash, nonce)
        if h.startswith(target):
            return nonce, h
        nonce += 1

def add_block(data_dict):
    with get_db() as conn:
        latest = conn.execute("SELECT * FROM blocks ORDER BY idx DESC LIMIT 1").fetchone()
        prev_hash = latest['hash'] if latest else '0'*64
        new_idx = (latest['idx'] + 1) if latest else 1
        ts = datetime.utcnow().isoformat()
        data_str = json.dumps(data_dict)
        nonce, block_hash = _mine(new_idx, ts, data_str, prev_hash)
        conn.execute("INSERT INTO blocks(idx,timestamp,data,previous_hash,hash,nonce) VALUES(?,?,?,?,?,?)",
                     (new_idx, ts, data_str, prev_hash, block_hash, nonce))
        conn.commit()
        return {'index': new_idx, 'hash': block_hash, 'previous_hash': prev_hash}

def is_chain_valid():
    with get_db() as conn:
        blocks = conn.execute("SELECT * FROM blocks ORDER BY idx").fetchall()
        for i in range(1, len(blocks)):
            b = blocks[i]
            prev = blocks[i-1]
            recalc = _calc_hash(b['idx'], b['timestamp'], b['data'], b['previous_hash'], b['nonce'])
            if b['hash'] != recalc or b['previous_hash'] != prev['hash']:
                return False
        return True

# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*a, **kw)
    return dec

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def dec(*a, **kw):
            if session.get('user_role') not in roles:
                flash('Access denied.','danger')
                return redirect('/')
            return f(*a, **kw)
        return dec
    return decorator

def log_action(user_id, action, details='', ip=None):
    with get_db() as conn:
        conn.execute("INSERT INTO audit_logs(user_id,action,details,ip_address) VALUES(?,?,?,?)",
                     (user_id, action, details, ip))
        conn.commit()

def get_user(uid):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def user_name(uid):
    if not uid: return 'System'
    u = get_user(uid)
    return u['name'] if u else 'Unknown'

# ══════════════════════════════════════════════
#  TEMPLATES (inline Jinja2)
# ══════════════════════════════════════════════

BASE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{% block title %}AgriChain{% endblock %} — AgriChain Uganda</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--primary:#1a6b3c;--primary-light:#2d9e5f;--accent:#f4a820;--dark:#0d1f13;--surface:#f5f8f5;--border:#d4e4d8;--text-muted:#6b7a6e;}
*{font-family:'Space Grotesk',sans-serif;}
body{background:var(--surface);min-height:100vh;}
.navbar{background:var(--dark)!important;border-bottom:2px solid var(--primary);}
.navbar-brand{color:var(--accent)!important;font-weight:700;}
.navbar-brand span{color:#fff;font-weight:300;}
.nav-link{color:rgba(255,255,255,.8)!important;font-size:.875rem;}
.nav-link:hover{color:var(--accent)!important;}
.sidebar{background:var(--dark);min-height:calc(100vh - 57px);padding-top:1.5rem;width:230px;position:fixed;left:0;top:57px;z-index:100;}
.sidebar .nav-link{color:rgba(255,255,255,.7)!important;padding:.55rem 1.25rem;border-radius:8px;margin:2px 10px;font-size:.85rem;display:flex;align-items:center;gap:10px;}
.sidebar .nav-link:hover,.sidebar .nav-link.active{background:rgba(255,255,255,.1);color:var(--accent)!important;}
.main-content{margin-left:230px;padding:2rem;}
.card{border:1px solid var(--border);border-radius:12px;}
.card-header{background:transparent;border-bottom:1px solid var(--border);font-weight:600;padding:.75rem 1.25rem;}
.stat-card{border-radius:12px;padding:1.25rem;color:#fff;}
.stat-card.green{background:linear-gradient(135deg,#1a6b3c,#2d9e5f);}
.stat-card.amber{background:linear-gradient(135deg,#c98010,#f4a820);}
.stat-card.blue{background:linear-gradient(135deg,#0369a1,#0891b2);}
.stat-card.red{background:linear-gradient(135deg,#991b1b,#dc2626);}
.stat-num{font-size:2.2rem;font-weight:700;line-height:1;}
.stat-label{font-size:.75rem;opacity:.85;text-transform:uppercase;letter-spacing:.5px;margin-top:4px;}
.badge-status{padding:3px 10px;border-radius:20px;font-size:.72rem;font-weight:600;}
.badge-harvested{background:#ecfdf5;color:#065f46;}
.badge-transferred{background:#eff6ff;color:#1e40af;}
.badge-in_transit{background:#fffbeb;color:#92400e;}
.badge-delivered{background:#f0fdf4;color:#166534;}
.badge-approved{background:#dcfce7;color:#14532d;border:1px solid #bbf7d0;}
.badge-purchased{background:#fef3c7;color:#78350f;}
.hash-text{font-family:'JetBrains Mono',monospace;font-size:.7rem;color:var(--text-muted);word-break:break-all;}
.btn-primary{background:var(--primary);border-color:var(--primary);}
.btn-primary:hover{background:var(--primary-light);border-color:var(--primary-light);}
.timeline{position:relative;padding-left:2rem;}
.timeline::before{content:'';position:absolute;left:.5rem;top:0;bottom:0;width:2px;background:var(--border);}
.timeline-item{position:relative;margin-bottom:1.5rem;}
.timeline-item::before{content:'';position:absolute;left:-1.625rem;top:.25rem;width:14px;height:14px;border-radius:50%;background:var(--primary);border:2px solid #fff;box-shadow:0 0 0 2px var(--primary);}
.block-card{background:var(--dark);color:#e2e8f0;border-radius:10px;padding:1rem;margin-bottom:.75rem;border:1px solid rgba(255,255,255,.1);}
.block-hash{font-family:'JetBrains Mono',monospace;font-size:.7rem;color:var(--accent);}
.table th{font-size:.78rem;text-transform:uppercase;letter-spacing:.5px;color:var(--text-muted);font-weight:600;}
@media(max-width:768px){.sidebar{display:none;}.main-content{margin-left:0;padding:1rem;}}
</style>
{% block extra_css %}{% endblock %}
</head>
<body>
<nav class="navbar navbar-expand-lg sticky-top">
  <div class="container-fluid px-3">
    <a class="navbar-brand" href="/"><i class="bi bi-boxes me-2"></i>Agri<span>Chain</span></a>
    <div class="ms-auto d-flex align-items-center gap-3">
      {% if user_id %}
      <span class="text-white-50 small d-none d-md-inline"><i class="bi bi-shield-check text-success me-1"></i>Blockchain Active</span>
      <div class="dropdown">
        <button class="btn btn-sm btn-outline-light dropdown-toggle" data-bs-toggle="dropdown">
          <i class="bi bi-person-circle me-1"></i>{{ user_name }}
          <span class="badge ms-1" style="background:var(--accent);color:#0d1f13;font-size:.65rem">{{ user_role }}</span>
        </button>
        <ul class="dropdown-menu dropdown-menu-end">
          <li><a class="dropdown-item" href="/logout"><i class="bi bi-box-arrow-right me-2"></i>Logout</a></li>
        </ul>
      </div>
      {% else %}
      <a href="/login" class="btn btn-sm btn-outline-light">Login</a>
      <a href="/register" class="btn btn-sm" style="background:var(--accent);color:#0d1f13">Register</a>
      {% endif %}
    </div>
  </div>
</nav>
{% if user_id %}
<div class="sidebar">
  {% if user_role == 'farmer' %}
    <a href="/farmer/dashboard" class="nav-link"><i class="bi bi-grid"></i>Dashboard</a>
    <a href="/farmer/add_product" class="nav-link"><i class="bi bi-plus-circle"></i>Add Product</a>
  {% elif user_role == 'buyer' %}
    <a href="/buyer/dashboard" class="nav-link"><i class="bi bi-grid"></i>Dashboard</a>
  {% elif user_role == 'transporter' %}
    <a href="/transporter/dashboard" class="nav-link"><i class="bi bi-grid"></i>Dashboard</a>
  {% elif user_role == 'regulator' %}
    <a href="/regulator/dashboard" class="nav-link"><i class="bi bi-grid"></i>Dashboard</a>
    <a href="/analytics" class="nav-link"><i class="bi bi-bar-chart"></i>Analytics</a>
  {% elif user_role == 'admin' %}
    <a href="/admin/dashboard" class="nav-link"><i class="bi bi-grid"></i>Dashboard</a>
    <a href="/analytics" class="nav-link"><i class="bi bi-bar-chart"></i>Analytics</a>
  {% endif %}
  <a href="/track" class="nav-link"><i class="bi bi-search"></i>Track Product</a>
  <a href="/blockchain" class="nav-link"><i class="bi bi-link-45deg"></i>Blockchain</a>
  <div style="position:absolute;bottom:1rem;left:0;right:0;padding:0 .75rem;">
    <div style="background:rgba(244,168,32,.1);border:1px solid rgba(244,168,32,.3);border-radius:8px;padding:.6rem;font-size:.72rem;color:rgba(255,255,255,.55);">
      <i class="bi bi-geo-alt text-warning me-1"></i>Kasese District, Uganda
    </div>
  </div>
</div>
{% endif %}
<div class="{% if user_id %}main-content{% else %}container py-4{% endif %}">
  {% for cat, msg in get_flashed_messages(with_categories=true) %}
  <div class="alert alert-{{ cat if cat != 'message' else 'info' }} alert-dismissible fade show">
    {{ msg }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>
  {% endfor %}
  {% block content %}{% endblock %}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
{% block extra_js %}{% endblock %}
</body></html>"""

def render(template_str, **ctx):
    ctx.setdefault('user_id', session.get('user_id'))
    ctx.setdefault('user_name', session.get('user_name',''))
    ctx.setdefault('user_role', session.get('user_role',''))
    full = BASE.replace('{% block title %}AgriChain{% endblock %}', '{% block title %}' + ctx.pop('page_title','AgriChain') + '{% endblock %}')
    full = full.replace('{% block extra_css %}{% endblock %}', ctx.pop('extra_css',''))
    full = full.replace('{% block extra_js %}{% endblock %}', ctx.pop('extra_js',''))
    full = full.replace('{% block content %}{% endblock %}', template_str)
    from flask import render_template_string as rts
    return rts(full, **ctx)

# ══════════════════════════════════════════════
#  ROUTES — Auth
# ══════════════════════════════════════════════

@app.route('/')
def index():
    return render_template_string(LANDING_TPL)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pw = request.form['password']
        with get_db() as conn:
            u = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if u and check_password_hash(u['password'], pw):
            if not u['is_active']:
                flash('Account deactivated.','danger')
                return redirect('/login')
            session.update({'user_id':u['id'],'user_name':u['name'],'user_role':u['role'],'user_email':u['email']})
            log_action(u['id'],'LOGIN',f'Logged in from {request.remote_addr}', request.remote_addr)
            return redirect({'farmer':'/farmer/dashboard','buyer':'/buyer/dashboard',
                             'transporter':'/transporter/dashboard','regulator':'/regulator/dashboard',
                             'admin':'/admin/dashboard'}.get(u['role'],'/'))
        flash('Invalid email or password.','danger')
    return render(LOGIN_TPL, page_title='Login')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        d = request.form
        with get_db() as conn:
            if conn.execute("SELECT id FROM users WHERE email=?", (d['email'].lower(),)).fetchone():
                flash('Email already registered.','danger')
                return redirect('/register')
            conn.execute("INSERT INTO users(name,email,password,role,phone,location) VALUES(?,?,?,?,?,?)",
                         (d['name'], d['email'].lower(), generate_password_hash(d['password']),
                          d.get('role','farmer'), d.get('phone',''), d.get('location','')))
            conn.commit()
        flash('Account created! Please login.','success')
        return redirect('/login')
    return render(REGISTER_TPL, page_title='Register')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_action(session['user_id'],'LOGOUT','')
    session.clear()
    return redirect('/')

# ══════════════════════════════════════════════
#  ROUTES — Farmer
# ══════════════════════════════════════════════

@app.route('/farmer/dashboard')
@login_required
@role_required('farmer')
def farmer_dashboard():
    uid = session['user_id']
    with get_db() as conn:
        products = conn.execute("SELECT p.*,u.name as farmer_name FROM products p JOIN users u ON p.farmer_id=u.id WHERE p.farmer_id=?", (uid,)).fetchall()
        txs = conn.execute("""SELECT t.*,p.product_code FROM transactions t JOIN products p ON t.product_id=p.id
                              WHERE p.farmer_id=? ORDER BY t.timestamp DESC LIMIT 10""", (uid,)).fetchall()
        me = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return render(FARMER_DASH_TPL, page_title='Farmer Dashboard', products=products, txs=txs, me=me, user_name_fn=user_name)

@app.route('/farmer/add_product', methods=['GET','POST'])
@login_required
@role_required('farmer')
def add_product():
    if request.method == 'POST':
        d = request.form
        code = f'PC-{datetime.utcnow().strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}'
        block = add_block({'action':'harvested','crop':d['crop_type'],'farmer_id':session['user_id'],'qty':float(d['quantity']),'location':d['location']})
        with get_db() as conn:
            conn.execute("""INSERT INTO products(product_code,crop_type,quantity,unit,location,district,harvest_date,
                            quality_grade,status,farmer_id,current_owner_id,blockchain_hash,notes)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (code, d['crop_type'], float(d['quantity']), 'kg', d['location'], 'Kasese',
                          d['harvest_date'], d.get('quality_grade','A'), 'harvested',
                          session['user_id'], session['user_id'], block['hash'], d.get('notes','')))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("""INSERT INTO transactions(tx_id,product_id,action,sender_id,block_index,block_hash,previous_hash,payload)
                            VALUES(?,?,?,?,?,?,?,?)""",
                         (str(uuid.uuid4()).replace('-','')[:20].upper(), pid,'harvested',session['user_id'],
                          block['index'],block['hash'],block['previous_hash'],
                          json.dumps({'crop':d['crop_type'],'qty':d['quantity']})))
            conn.commit()
        flash(f'✓ Product {code} registered on blockchain! Block #{block["index"]}','success')
        return redirect('/farmer/dashboard')
    return render(ADD_PRODUCT_TPL, page_title='Add Product')

@app.route('/farmer/transfer/<int:pid>', methods=['POST'])
@login_required
@role_required('farmer')
def transfer_product(pid):
    receiver_email = request.form.get('receiver_email','').lower()
    with get_db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id=? AND farmer_id=?", (pid, session['user_id'])).fetchone()
        receiver = conn.execute("SELECT * FROM users WHERE email=?", (receiver_email,)).fetchone()
        if not product:
            flash('Product not found.','danger'); return redirect('/farmer/dashboard')
        if not receiver:
            flash('Receiver email not found in system.','danger'); return redirect('/farmer/dashboard')
        block = add_block({'action':'transferred','product_id':pid,'from':session['user_id'],'to':receiver['id']})
        conn.execute("UPDATE products SET current_owner_id=?,status='transferred',blockchain_hash=? WHERE id=?",
                     (receiver['id'], block['hash'], pid))
        conn.execute("""INSERT INTO transactions(tx_id,product_id,action,sender_id,receiver_id,block_index,block_hash,previous_hash)
                        VALUES(?,?,?,?,?,?,?,?)""",
                     (str(uuid.uuid4()).replace('-','')[:20].upper(), pid,'transferred',
                      session['user_id'],receiver['id'],block['index'],block['hash'],block['previous_hash']))
        conn.commit()
    flash(f'Product transferred to {receiver["name"]} · Block #{block["index"]}','success')
    return redirect('/farmer/dashboard')

# ══════════════════════════════════════════════
#  ROUTES — Buyer
# ══════════════════════════════════════════════

@app.route('/buyer/dashboard')
@login_required
@role_required('buyer')
def buyer_dashboard():
    uid = session['user_id']
    with get_db() as conn:
        available = conn.execute("""SELECT p.*,u.name as farmer_name FROM products p JOIN users u ON p.farmer_id=u.id
                                    WHERE p.status IN ('harvested','transferred')""").fetchall()
        owned = conn.execute("""SELECT p.*,u.name as farmer_name FROM products p JOIN users u ON p.farmer_id=u.id
                                WHERE p.current_owner_id=?""", (uid,)).fetchall()
        txs = conn.execute("""SELECT * FROM transactions WHERE sender_id=? OR receiver_id=?
                              ORDER BY timestamp DESC LIMIT 10""", (uid,uid)).fetchall()
    return render(BUYER_DASH_TPL, page_title='Buyer Dashboard', available=available, owned=owned, txs=txs)

@app.route('/buyer/purchase/<int:pid>', methods=['POST'])
@login_required
@role_required('buyer')
def confirm_purchase(pid):
    with get_db() as conn:
        p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        block = add_block({'action':'purchased','product_id':pid,'buyer_id':session['user_id']})
        conn.execute("UPDATE products SET current_owner_id=?,status='purchased',blockchain_hash=? WHERE id=?",
                     (session['user_id'], block['hash'], pid))
        conn.execute("""INSERT INTO transactions(tx_id,product_id,action,sender_id,receiver_id,block_index,block_hash,previous_hash)
                        VALUES(?,?,?,?,?,?,?,?)""",
                     (str(uuid.uuid4()).replace('-','')[:20].upper(), pid,'purchased',
                      p['farmer_id'],session['user_id'],block['index'],block['hash'],block['previous_hash']))
        conn.commit()
    flash(f'Purchase confirmed on blockchain! Block #{block["index"]}','success')
    return redirect('/buyer/dashboard')

# ══════════════════════════════════════════════
#  ROUTES — Transporter
# ══════════════════════════════════════════════

@app.route('/transporter/dashboard')
@login_required
@role_required('transporter')
def transporter_dashboard():
    with get_db() as conn:
        products = conn.execute("""SELECT p.*,u.name as farmer_name FROM products p JOIN users u ON p.farmer_id=u.id
                                   WHERE p.status IN ('purchased','transferred','in_transit')""").fetchall()
    return render(TRANSPORTER_DASH_TPL, page_title='Transporter Dashboard', products=products)

@app.route('/transporter/update/<int:pid>', methods=['POST'])
@login_required
@role_required('transporter')
def update_transport(pid):
    new_status = request.form.get('status')
    block = add_block({'action':new_status,'product_id':pid,'transporter_id':session['user_id']})
    with get_db() as conn:
        conn.execute("UPDATE products SET status=?,blockchain_hash=? WHERE id=?", (new_status, block['hash'], pid))
        conn.execute("""INSERT INTO transactions(tx_id,product_id,action,sender_id,block_index,block_hash,previous_hash)
                        VALUES(?,?,?,?,?,?,?)""",
                     (str(uuid.uuid4()).replace('-','')[:20].upper(), pid, new_status,
                      session['user_id'],block['index'],block['hash'],block['previous_hash']))
        conn.commit()
    flash(f'Status updated to "{new_status}" · Block #{block["index"]}','success')
    return redirect('/transporter/dashboard')

# ══════════════════════════════════════════════
#  ROUTES — Regulator
# ══════════════════════════════════════════════

@app.route('/regulator/dashboard')
@login_required
@role_required('regulator')
def regulator_dashboard():
    with get_db() as conn:
        products = conn.execute("""SELECT p.*,u.name as farmer_name FROM products p JOIN users u ON p.farmer_id=u.id""").fetchall()
        flagged = [p for p in products if p['is_flagged']]
    valid = is_chain_valid()
    return render(REGULATOR_DASH_TPL, page_title='Regulator Dashboard', products=products, flagged=flagged, chain_valid=valid)

@app.route('/regulator/approve/<int:pid>', methods=['POST'])
@login_required
@role_required('regulator')
def approve_product(pid):
    block = add_block({'action':'approved','product_id':pid,'regulator_id':session['user_id']})
    with get_db() as conn:
        conn.execute("UPDATE products SET is_approved=1,status='approved',blockchain_hash=? WHERE id=?", (block['hash'],pid))
        conn.execute("""INSERT INTO transactions(tx_id,product_id,action,sender_id,block_index,block_hash,previous_hash)
                        VALUES(?,?,?,?,?,?,?)""",
                     (str(uuid.uuid4()).replace('-','')[:20].upper(), pid,'approved_by_regulator',
                      session['user_id'],block['index'],block['hash'],block['previous_hash']))
        conn.commit()
    flash('Product approved and recorded on blockchain!','success')
    return redirect('/regulator/dashboard')

@app.route('/regulator/flag/<int:pid>', methods=['POST'])
@login_required
@role_required('regulator')
def flag_product(pid):
    with get_db() as conn:
        conn.execute("UPDATE products SET is_flagged=1 WHERE id=?", (pid,))
        conn.commit()
    flash('Product flagged for investigation.','warning')
    return redirect('/regulator/dashboard')

# ══════════════════════════════════════════════
#  ROUTES — Admin
# ══════════════════════════════════════════════

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    with get_db() as conn:
        users = conn.execute("SELECT * FROM users").fetchall()
        products = conn.execute("SELECT p.*,u.name as farmer_name FROM products p JOIN users u ON p.farmer_id=u.id").fetchall()
        txs = conn.execute("SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 20").fetchall()
        logs = conn.execute("SELECT l.*,u.name as uname FROM audit_logs l LEFT JOIN users u ON l.user_id=u.id ORDER BY timestamp DESC LIMIT 30").fetchall()
        total_blocks = conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
        flagged = conn.execute("SELECT COUNT(*) FROM products WHERE is_flagged=1").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM products WHERE is_approved=1").fetchone()[0]
    stats = {'total_users':len(users),'total_products':len(products),'total_txs':len(txs),
             'total_blocks':total_blocks,'flagged':flagged,'approved':approved,'chain_valid':is_chain_valid()}
    return render(ADMIN_DASH_TPL, page_title='Admin Dashboard', users=users, products=products, txs=txs, logs=logs, stats=stats)

@app.route('/admin/toggle_user/<int:uid>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(uid):
    with get_db() as conn:
        u = conn.execute("SELECT is_active FROM users WHERE id=?", (uid,)).fetchone()
        conn.execute("UPDATE users SET is_active=? WHERE id=?", (0 if u['is_active'] else 1, uid))
        conn.commit()
    flash('User status updated.','info')
    return redirect('/admin/dashboard')

# ══════════════════════════════════════════════
#  ROUTES — Shared
# ══════════════════════════════════════════════

@app.route('/track')
@login_required
def track_product():
    q = request.args.get('q','').strip()
    product = None; txs = []; farmer_name = ''
    if q:
        with get_db() as conn:
            product = conn.execute("""SELECT p.*,u.name as farmer_name FROM products p
                                      JOIN users u ON p.farmer_id=u.id
                                      WHERE p.product_code=? OR p.id=?""",
                                   (q, q if q.isdigit() else -1)).fetchone()
            if product:
                txs = conn.execute("SELECT * FROM transactions WHERE product_id=? ORDER BY timestamp", (product['id'],)).fetchall()
    return render(TRACK_TPL, page_title='Track Product', product=product, txs=txs, query=q, user_name_fn=user_name)

@app.route('/blockchain')
@login_required
def blockchain_explorer():
    with get_db() as conn:
        chain = conn.execute("SELECT * FROM blocks ORDER BY idx DESC").fetchall()
    valid = is_chain_valid()
    return render(BLOCKCHAIN_TPL, page_title='Blockchain Explorer', chain=chain, is_valid=valid)

@app.route('/analytics')
@login_required
def analytics():
    with get_db() as conn:
        crops = conn.execute("SELECT crop_type,COUNT(*) as cnt FROM products GROUP BY crop_type").fetchall()
        statuses = conn.execute("SELECT status,COUNT(*) as cnt FROM products GROUP BY status").fetchall()
        total_txs = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        total_p = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        verified = conn.execute("SELECT COUNT(*) FROM products WHERE is_approved=1").fetchone()[0]
        flagged = conn.execute("SELECT COUNT(*) FROM products WHERE is_flagged=1").fetchone()[0]
    crop_data = json.dumps([{'label':r['crop_type'],'value':r['cnt']} for r in crops])
    status_data = json.dumps([{'label':r['status'],'value':r['cnt']} for r in statuses])
    return render(ANALYTICS_TPL, page_title='Analytics', crop_data=crop_data, status_data=status_data,
                  total_txs=total_txs, total_p=total_p, verified=verified, flagged=flagged)

@app.route('/api/products')
@login_required
def api_products():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM products").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/chain')
@login_required
def api_chain():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM blocks ORDER BY idx").fetchall()
    return jsonify({'chain':[dict(r) for r in rows],'valid':is_chain_valid(),'length':len(rows)})

# ══════════════════════════════════════════════
#  INLINE TEMPLATES
# ══════════════════════════════════════════════

LANDING_TPL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgriChain Uganda — Blockchain Supply Chain</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{font-family:'Space Grotesk',sans-serif;margin:0;padding:0;box-sizing:border-box;}
body{background:#0d1f13;color:#e2e8f0;}
nav{padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,.1);}
.brand{color:#f4a820;font-weight:800;font-size:1.25rem;}
.brand span{color:#fff;font-weight:300;}
.hero{min-height:92vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:4rem 2rem;background:radial-gradient(ellipse at center,rgba(26,107,60,.25) 0%,transparent 70%);}
.badge-hero{background:rgba(244,168,32,.15);border:1px solid rgba(244,168,32,.3);color:#f4a820;padding:6px 16px;border-radius:20px;font-size:.8rem;font-weight:600;letter-spacing:.5px;margin-bottom:1.5rem;display:inline-block;}
h1{font-size:clamp(2.5rem,6vw,4.5rem);font-weight:800;line-height:1.1;margin-bottom:1.5rem;}
h1 span{color:#f4a820;}
.hero p{font-size:1.05rem;color:rgba(255,255,255,.6);max-width:580px;line-height:1.7;margin-bottom:2.5rem;}
.btn-cta{background:#1a6b3c;color:#fff;padding:.875rem 2.5rem;border-radius:10px;text-decoration:none;font-weight:600;border:none;margin-right:.75rem;transition:all .2s;}
.btn-cta:hover{background:#2d9e5f;color:#fff;transform:translateY(-2px);}
.btn-ghost{background:transparent;color:#fff;padding:.875rem 2.5rem;border-radius:10px;text-decoration:none;font-weight:600;border:1px solid rgba(255,255,255,.25);transition:all .2s;}
.btn-ghost:hover{background:rgba(255,255,255,.1);color:#fff;}
.stats-row{display:flex;gap:3rem;justify-content:center;margin-top:3.5rem;flex-wrap:wrap;}
.stat-item .num{font-size:1.8rem;font-weight:800;color:#f4a820;}
.stat-item .lbl{font-size:.75rem;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.5px;}
.features{padding:5rem 2rem;background:rgba(255,255,255,.02);}
.feat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1.25rem;max-width:1100px;margin:3rem auto 0;}
.feat-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:1.75rem;}
.feat-icon{width:46px;height:46px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;margin-bottom:1rem;background:rgba(26,107,60,.3);color:#f4a820;}
.feat-card h3{font-size:.95rem;font-weight:600;margin-bottom:.4rem;}
.feat-card p{font-size:.82rem;color:rgba(255,255,255,.5);line-height:1.6;}
.roles{padding:5rem 2rem;}
.role-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1rem;max-width:1100px;margin:2.5rem auto 0;}
.role-card{background:#1a6b3c;border-radius:12px;padding:1.5rem;text-align:center;cursor:pointer;transition:transform .2s;text-decoration:none;}
.role-card:hover{transform:translateY(-4px);}
.role-card i{font-size:1.75rem;color:#f4a820;display:block;margin-bottom:.6rem;}
.role-card h4{color:#fff;font-size:.9rem;font-weight:600;margin-bottom:.2rem;}
.role-card small{color:rgba(255,255,255,.55);font-size:.72rem;}
footer{text-align:center;padding:2rem;color:rgba(255,255,255,.35);font-size:.78rem;border-top:1px solid rgba(255,255,255,.1);}
.section-title{text-align:center;font-size:1.9rem;font-weight:700;}
.section-sub{text-align:center;color:rgba(255,255,255,.45);margin-top:.5rem;font-size:.9rem;}
</style></head><body>
<nav>
  <div class="brand"><i class="bi bi-boxes me-2"></i>Agri<span>Chain</span></div>
  <div>
    <a href="/login" class="btn-ghost" style="padding:.5rem 1.25rem;font-size:.875rem">Login</a>
    <a href="/register" class="btn-cta" style="padding:.5rem 1.25rem;font-size:.875rem;margin-left:.5rem">Get Started</a>
  </div>
</nav>
<section class="hero">
  <div class="badge-hero"><i class="bi bi-shield-check me-1"></i>Kasese District, Uganda · SHA-256 Blockchain</div>
  <h1>Transparent <span>Agricultural</span><br>Supply Chains</h1>
  <p>Track every crop from farm to market using immutable blockchain technology. Build trust, prevent fraud, and ensure accountability across Uganda's agricultural ecosystem.</p>
  <div>
    <a href="/register" class="btn-cta">Start Tracking &rarr;</a>
    <a href="/login" class="btn-ghost">Sign In</a>
  </div>
  <div class="stats-row">
    <div class="stat-item"><div class="num">100%</div><div class="lbl">Tamper-Resistant</div></div>
    <div class="stat-item"><div class="num">SHA-256</div><div class="lbl">Hash Algorithm</div></div>
    <div class="stat-item"><div class="num">PoW</div><div class="lbl">Proof of Work</div></div>
    <div class="stat-item"><div class="num">5</div><div class="lbl">Supply Chain Stages</div></div>
  </div>
</section>
<section class="features">
  <h2 class="section-title">How AgriChain Works</h2>
  <p class="section-sub">Every agricultural event creates a permanent, immutable blockchain record</p>
  <div class="feat-grid">
    <div class="feat-card"><div class="feat-icon"><i class="bi bi-tree"></i></div><h3>Farm Registration</h3><p>Farmers register harvests. A SHA-256 block is mined and recorded to the chain instantly.</p></div>
    <div class="feat-card"><div class="feat-icon"><i class="bi bi-arrow-left-right"></i></div><h3>Transfer & Trade</h3><p>Every ownership transfer is written as an immutable transaction on the blockchain.</p></div>
    <div class="feat-card"><div class="feat-icon"><i class="bi bi-truck"></i></div><h3>Transport Tracking</h3><p>Transporters update real-time delivery status, creating a complete movement audit trail.</p></div>
    <div class="feat-card"><div class="feat-icon"><i class="bi bi-shield-check"></i></div><h3>UNBS Regulatory Audit</h3><p>Regulators verify compliance, approve or flag products using tamper-proof blockchain logs.</p></div>
    <div class="feat-card"><div class="feat-icon"><i class="bi bi-search"></i></div><h3>Product Verification</h3><p>Search any product by code to instantly view its full verified supply chain history.</p></div>
    <div class="feat-card"><div class="feat-icon"><i class="bi bi-bar-chart-line"></i></div><h3>Analytics</h3><p>District-level insights, crop trading patterns, fraud alerts, and verification rates.</p></div>
  </div>
</section>
<section class="roles">
  <h2 class="section-title">Role-Based Access Control</h2>
  <p class="section-sub">Each stakeholder gets a purpose-built dashboard</p>
  <div class="role-grid">
    <a href="/login" class="role-card"><i class="bi bi-person-badge"></i><h4>Farmer</h4><small>Register & track harvests</small></a>
    <a href="/login" class="role-card"><i class="bi bi-bag-check"></i><h4>Buyer</h4><small>Verify & purchase produce</small></a>
    <a href="/login" class="role-card"><i class="bi bi-truck"></i><h4>Transporter</h4><small>Update delivery status</small></a>
    <a href="/login" class="role-card"><i class="bi bi-clipboard-check"></i><h4>Regulator</h4><small>Audit & approve produce</small></a>
    <a href="/login" class="role-card"><i class="bi bi-gear"></i><h4>Admin</h4><small>System management</small></a>
  </div>
</section>
<footer>
  <p>AgriChain Uganda &copy; 2024 · Final Year Project · Blockchain Agricultural Supply Chain · Kasese District</p>
  <p style="margin-top:.5rem">Built with Python Flask &middot; SQLite &middot; SHA-256 + Proof-of-Work Blockchain</p>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>"""

LOGIN_TPL = """
<div class="row justify-content-center" style="margin-top:4rem">
  <div class="col-md-5">
    <div class="text-center mb-4"><h4 class="fw-bold">Welcome back</h4><p class="text-muted small">Sign in to AgriChain</p></div>
    <div class="card p-4">
      <form method="POST" action="/login">
        <div class="mb-3"><label class="form-label fw-semibold">Email</label>
          <input type="email" name="email" class="form-control" required placeholder="you@agrichain.ug"></div>
        <div class="mb-4"><label class="form-label fw-semibold">Password</label>
          <input type="password" name="password" class="form-control" required placeholder="••••••••"></div>
        <button type="submit" class="btn btn-primary w-100 py-2">Sign In <i class="bi bi-arrow-right ms-1"></i></button>
      </form>
      <hr class="my-3">
      <div class="bg-light p-3 rounded" style="font-size:.78rem;line-height:1.8">
        <strong>Demo Credentials:</strong><br>
        <span class="badge bg-success me-1">Admin</span>admin@agrichain.ug / admin123<br>
        <span class="badge bg-primary me-1">Farmer</span>farmer@agrichain.ug / farmer123<br>
        <span class="badge bg-warning text-dark me-1">Buyer</span>buyer@agrichain.ug / buyer123<br>
        <span class="badge bg-secondary me-1">Transport</span>transporter@agrichain.ug / transport123<br>
        <span class="badge bg-dark me-1">Regulator</span>regulator@agrichain.ug / regulator123
      </div>
    </div>
    <p class="text-center mt-3 text-muted small">No account? <a href="/register" class="text-success fw-semibold">Register here</a></p>
  </div>
</div>"""

REGISTER_TPL = """
<div class="row justify-content-center" style="margin-top:3rem">
  <div class="col-md-6">
    <div class="text-center mb-4"><h4 class="fw-bold">Create Account</h4><p class="text-muted small">Join the AgriChain network</p></div>
    <div class="card p-4">
      <form method="POST" action="/register">
        <div class="row g-3">
          <div class="col-12"><label class="form-label fw-semibold">Full Name</label>
            <input type="text" name="name" class="form-control" required placeholder="John Muhindo"></div>
          <div class="col-md-6"><label class="form-label fw-semibold">Email</label>
            <input type="email" name="email" class="form-control" required></div>
          <div class="col-md-6"><label class="form-label fw-semibold">Phone</label>
            <input type="text" name="phone" class="form-control" placeholder="+256700000000"></div>
          <div class="col-md-6"><label class="form-label fw-semibold">Password</label>
            <input type="password" name="password" class="form-control" required minlength="6"></div>
          <div class="col-md-6"><label class="form-label fw-semibold">Role</label>
            <select name="role" class="form-select">
              <option value="farmer">Farmer</option>
              <option value="buyer">Buyer / Distributor</option>
              <option value="transporter">Transporter</option>
            </select></div>
          <div class="col-12"><label class="form-label fw-semibold">Location</label>
            <input type="text" name="location" class="form-control" placeholder="Kasese, Uganda"></div>
          <div class="col-12"><button type="submit" class="btn btn-primary w-100 py-2">Create Account</button></div>
        </div>
      </form>
    </div>
    <p class="text-center mt-3 text-muted small">Already registered? <a href="/login" class="text-success fw-semibold">Sign in</a></p>
  </div>
</div>"""

FARMER_DASH_TPL = """
<div class="d-flex justify-content-between align-items-center mb-4">
  <div><h4 class="fw-bold mb-0">Farmer Dashboard</h4>
    <small class="text-muted">{{ me['name'] }} &middot; {{ me['location'] or 'Kasese District' }}</small></div>
  <a href="/farmer/add_product" class="btn btn-primary"><i class="bi bi-plus-circle me-1"></i>Add Product</a>
</div>
<div class="row g-3 mb-4">
  <div class="col-6 col-md-3"><div class="stat-card green"><div class="stat-num">{{ products|length }}</div><div class="stat-label">My Products</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card amber"><div class="stat-num">{{ products|selectattr('status','equalto','harvested')|list|length }}</div><div class="stat-label">Harvested</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card blue"><div class="stat-num">{{ products|selectattr('status','equalto','transferred')|list|length }}</div><div class="stat-label">Transferred</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card green"><div class="stat-num">{{ products|selectattr('is_approved')|list|length }}</div><div class="stat-label">UNBS Approved</div></div></div>
</div>
<div class="row g-3">
  <div class="col-lg-8">
    <div class="card">
      <div class="card-header"><i class="bi bi-box-seam me-2"></i>My Products</div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light"><tr><th class="px-4">Code</th><th>Crop</th><th>Qty</th><th>Location</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {% for p in products %}
              <tr>
                <td class="px-4"><div class="fw-semibold" style="font-size:.85rem">{{ p['product_code'] }}</div>
                  <div class="hash-text">{{ p['blockchain_hash'][:22] if p['blockchain_hash'] else 'Pending' }}...</div></td>
                <td>{{ p['crop_type'] }}</td><td>{{ p['quantity'] }} kg</td>
                <td style="font-size:.82rem">{{ p['location'] }}</td>
                <td><span class="badge-status badge-{{ p['status'] }}">{{ p['status'].replace('_',' ').title() }}</span></td>
                <td>
                  <a href="/track?q={{ p['product_code'] }}" class="btn btn-sm btn-outline-secondary py-0">Track</a>
                  {% if p['status'] == 'harvested' %}
                  <button class="btn btn-sm btn-outline-success py-0 ms-1" data-bs-toggle="modal" data-bs-target="#tm{{ p['id'] }}">Transfer</button>
                  {% endif %}
                </td>
              </tr>
              <div class="modal fade" id="tm{{ p['id'] }}" tabindex="-1">
                <div class="modal-dialog modal-sm"><div class="modal-content">
                  <div class="modal-header"><h6 class="modal-title">Transfer {{ p['product_code'] }}</h6>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
                  <form method="POST" action="/farmer/transfer/{{ p['id'] }}">
                    <div class="modal-body"><label class="form-label small fw-semibold">Receiver Email</label>
                      <input type="email" name="receiver_email" class="form-control form-control-sm" required placeholder="buyer@example.com"></div>
                    <div class="modal-footer py-2">
                      <button type="submit" class="btn btn-sm btn-primary">Transfer &rarr; Blockchain</button></div>
                  </form>
                </div></div>
              </div>
              {% else %}
              <tr><td colspan="6" class="text-center py-4 text-muted">No products yet. <a href="/farmer/add_product">Add first harvest.</a></td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
  <div class="col-lg-4">
    <div class="card">
      <div class="card-header"><i class="bi bi-clock-history me-2"></i>Recent Transactions</div>
      <div class="card-body p-3">
        {% for tx in txs %}
        <div class="border-bottom pb-2 mb-2" style="font-size:.8rem">
          <div class="d-flex justify-content-between">
            <span class="fw-semibold">{{ tx['action'].replace('_',' ').title() }}</span>
            <span class="text-muted">{{ tx['timestamp'][:10] }}</span></div>
          <div class="hash-text">Block #{{ tx['block_index'] or '-' }}</div>
        </div>
        {% else %}<p class="text-muted text-center small">No transactions yet</p>{% endfor %}
      </div>
    </div>
    <div class="card mt-3">
      <div class="card-header"><i class="bi bi-info-circle me-2"></i>Account Info</div>
      <div class="card-body p-3" style="font-size:.85rem">
        <p class="mb-1"><i class="bi bi-geo-alt text-success me-2"></i>{{ me['location'] or 'Kasese District' }}</p>
        <p class="mb-1"><i class="bi bi-telephone text-success me-2"></i>{{ me['phone'] or 'Not set' }}</p>
        <p class="mb-3"><i class="bi bi-envelope text-success me-2"></i>{{ me['email'] }}</p>
        <a href="/blockchain" class="btn btn-outline-secondary btn-sm w-100"><i class="bi bi-link-45deg me-1"></i>View Blockchain</a>
      </div>
    </div>
  </div>
</div>"""

ADD_PRODUCT_TPL = """
<div class="row justify-content-center">
  <div class="col-lg-7">
    <div class="mb-4"><h4 class="fw-bold mb-0">Register New Harvest</h4>
      <small class="text-muted">Creates an immutable SHA-256 blockchain record</small></div>
    <div class="card p-4">
      <form method="POST" action="/farmer/add_product">
        <div class="row g-3">
          <div class="col-md-6"><label class="form-label fw-semibold">Crop Type *</label>
            <select name="crop_type" class="form-select" required>
              <option value="">Select...</option>
              {% for c in ['Maize','Coffee','Beans','Tomatoes','Sorghum','Cassava','Banana','Sweet Potato','Rice','Groundnuts'] %}
              <option>{{ c }}</option>{% endfor %}
            </select></div>
          <div class="col-md-6"><label class="form-label fw-semibold">Quantity (kg) *</label>
            <input type="number" name="quantity" class="form-control" min="0.1" step="0.1" required placeholder="500"></div>
          <div class="col-md-6"><label class="form-label fw-semibold">Harvest Date *</label>
            <input type="date" name="harvest_date" class="form-control" required></div>
          <div class="col-md-6"><label class="form-label fw-semibold">Quality Grade</label>
            <select name="quality_grade" class="form-select">
              <option value="A+">A+ (Premium)</option><option value="A" selected>A (Standard)</option>
              <option value="B+">B+</option><option value="B">B (Fair)</option><option value="C">C</option>
            </select></div>
          <div class="col-12"><label class="form-label fw-semibold">Farm Location *</label>
            <input type="text" name="location" class="form-control" required placeholder="e.g., Hima, Kasese District"></div>
          <div class="col-12"><label class="form-label fw-semibold">Notes</label>
            <textarea name="notes" class="form-control" rows="2" placeholder="Optional notes..."></textarea></div>
          <div class="col-12">
            <div class="alert alert-info d-flex gap-2 align-items-start" style="font-size:.84rem">
              <i class="bi bi-shield-lock fs-5"></i>
              <span>Submitting will <strong>mine a new SHA-256 blockchain block</strong>. This record is <strong>permanent and immutable</strong>.</span>
            </div>
          </div>
          <div class="col-12">
            <button type="submit" class="btn btn-primary px-4 py-2"><i class="bi bi-cpu me-2"></i>Mine Block & Register</button>
            <a href="/farmer/dashboard" class="btn btn-outline-secondary px-4 py-2 ms-2">Cancel</a>
          </div>
        </div>
      </form>
    </div>
  </div>
</div>"""

BUYER_DASH_TPL = """
<div class="d-flex justify-content-between align-items-center mb-4">
  <div><h4 class="fw-bold mb-0">Buyer Dashboard</h4></div>
  <a href="/track" class="btn btn-primary"><i class="bi bi-search me-1"></i>Verify Product</a>
</div>
<div class="row g-3 mb-4">
  <div class="col-6 col-md-3"><div class="stat-card green"><div class="stat-num">{{ available|length }}</div><div class="stat-label">Available</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card amber"><div class="stat-num">{{ owned|length }}</div><div class="stat-label">My Purchases</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card blue"><div class="stat-num">{{ txs|length }}</div><div class="stat-label">Transactions</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card green"><div class="stat-num">{{ owned|selectattr('is_approved')|list|length }}</div><div class="stat-label">UNBS Verified</div></div></div>
</div>
<div class="card">
  <div class="card-header"><i class="bi bi-shop me-2"></i>Available Products</div>
  <div class="card-body p-0">
    <div class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="table-light"><tr><th class="px-4">Code</th><th>Crop</th><th>Farmer</th><th>Qty</th><th>Grade</th><th>Location</th><th>Actions</th></tr></thead>
        <tbody>
          {% for p in available %}
          <tr>
            <td class="px-4"><div class="fw-semibold" style="font-size:.85rem">{{ p['product_code'] }}</div>
              {% if p['is_approved'] %}<span class="badge bg-success" style="font-size:.65rem">UNBS Verified</span>{% endif %}</td>
            <td>{{ p['crop_type'] }}</td><td>{{ p['farmer_name'] }}</td><td>{{ p['quantity'] }} kg</td>
            <td><span class="badge bg-light text-dark border">{{ p['quality_grade'] }}</span></td>
            <td style="font-size:.82rem">{{ p['location'] }}</td>
            <td>
              <a href="/track?q={{ p['product_code'] }}" class="btn btn-sm btn-outline-secondary py-0">History</a>
              <form method="POST" action="/buyer/purchase/{{ p['id'] }}" class="d-inline ms-1">
                <button type="submit" class="btn btn-sm btn-success py-0"
                  onclick="return confirm('Confirm blockchain purchase?')">Buy</button>
              </form>
            </td>
          </tr>
          {% else %}<tr><td colspan="7" class="text-center py-4 text-muted">No products available</td></tr>{% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>"""

TRANSPORTER_DASH_TPL = """
<div class="mb-4"><h4 class="fw-bold mb-0">Transporter Dashboard</h4>
  <small class="text-muted">Update transport & delivery status on blockchain</small></div>
<div class="card">
  <div class="card-header"><i class="bi bi-truck me-2"></i>Products for Transport</div>
  <div class="card-body p-0">
    <div class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="table-light"><tr><th class="px-4">Code</th><th>Crop</th><th>Farmer</th><th>Qty</th><th>Location</th><th>Status</th><th>Update</th></tr></thead>
        <tbody>
          {% for p in products %}
          <tr>
            <td class="px-4"><div class="fw-semibold" style="font-size:.85rem">{{ p['product_code'] }}</div>
              <div class="hash-text">{{ p['blockchain_hash'][:18] if p['blockchain_hash'] else '' }}...</div></td>
            <td>{{ p['crop_type'] }}</td><td>{{ p['farmer_name'] }}</td><td>{{ p['quantity'] }} kg</td>
            <td style="font-size:.82rem">{{ p['location'] }}</td>
            <td><span class="badge-status badge-{{ p['status'] }}">{{ p['status'].replace('_',' ').title() }}</span></td>
            <td>
              <form method="POST" action="/transporter/update/{{ p['id'] }}" class="d-flex gap-1">
                <select name="status" class="form-select form-select-sm" style="width:auto">
                  <option value="in_transit">In Transit</option>
                  <option value="delivered">Delivered</option>
                </select>
                <button type="submit" class="btn btn-sm btn-primary">Update</button>
              </form>
            </td>
          </tr>
          {% else %}<tr><td colspan="7" class="text-center py-4 text-muted">No products assigned</td></tr>{% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>"""

REGULATOR_DASH_TPL = """
<div class="d-flex justify-content-between align-items-center mb-4">
  <div><h4 class="fw-bold mb-0">Regulator / UNBS Dashboard</h4></div>
  {% if chain_valid %}<span class="badge bg-success"><i class="bi bi-shield-check me-1"></i>Chain Valid</span>
  {% else %}<span class="badge bg-danger"><i class="bi bi-exclamation-triangle me-1"></i>Chain Tampered!</span>{% endif %}
</div>
<div class="row g-3 mb-4">
  <div class="col-6 col-md-3"><div class="stat-card green"><div class="stat-num">{{ products|length }}</div><div class="stat-label">Total Products</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card blue"><div class="stat-num">{{ products|selectattr('is_approved')|list|length }}</div><div class="stat-label">Approved</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card red"><div class="stat-num">{{ flagged|length }}</div><div class="stat-label">Flagged</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card amber"><div class="stat-num">{{ products|rejectattr('is_approved')|list|length }}</div><div class="stat-label">Pending</div></div></div>
</div>
{% if flagged %}
<div class="alert alert-danger d-flex gap-2 mb-4" style="font-size:.85rem">
  <i class="bi bi-exclamation-triangle-fill fs-5"></i>
  <div><strong>{{ flagged|length }} flagged product(s)</strong> require urgent review.</div>
</div>{% endif %}
<div class="card">
  <div class="card-header"><i class="bi bi-clipboard-check me-2"></i>All Products — Audit View</div>
  <div class="card-body p-0">
    <div class="table-responsive">
      <table class="table table-hover align-middle mb-0" style="font-size:.83rem">
        <thead class="table-light"><tr><th class="px-4">Code</th><th>Crop</th><th>Farmer</th><th>Location</th><th>Grade</th><th>Status</th><th>Hash</th><th>Actions</th></tr></thead>
        <tbody>
          {% for p in products %}
          <tr class="{% if p['is_flagged'] %}table-danger{% endif %}">
            <td class="px-4"><div class="fw-semibold">{{ p['product_code'] }}</div><small class="text-muted">{{ p['harvest_date'] }}</small></td>
            <td>{{ p['crop_type'] }}</td><td>{{ p['farmer_name'] }}</td>
            <td>{{ p['location'] }}</td>
            <td><span class="badge bg-light text-dark border">{{ p['quality_grade'] }}</span></td>
            <td><span class="badge-status badge-{{ p['status'] }}">{{ p['status'].replace('_',' ').title() }}</span>
              {% if p['is_flagged'] %}<span class="badge bg-danger ms-1" style="font-size:.65rem">Flagged</span>{% endif %}</td>
            <td><div class="hash-text">{{ p['blockchain_hash'][:22] if p['blockchain_hash'] else 'N/A' }}...</div></td>
            <td>
              <a href="/track?q={{ p['product_code'] }}" class="btn btn-sm btn-outline-secondary py-0">Audit</a>
              {% if not p['is_approved'] %}
              <form method="POST" action="/regulator/approve/{{ p['id'] }}" class="d-inline ms-1">
                <button class="btn btn-sm btn-success py-0">Approve</button></form>{% endif %}
              {% if not p['is_flagged'] %}
              <form method="POST" action="/regulator/flag/{{ p['id'] }}" class="d-inline ms-1">
                <button class="btn btn-sm btn-danger py-0">Flag</button></form>{% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>"""

ADMIN_DASH_TPL = """
<div class="mb-4"><h4 class="fw-bold mb-0">System Administrator Dashboard</h4></div>
<div class="row g-3 mb-4">
  <div class="col-6 col-md-2"><div class="stat-card green"><div class="stat-num">{{ stats['total_users'] }}</div><div class="stat-label">Users</div></div></div>
  <div class="col-6 col-md-2"><div class="stat-card amber"><div class="stat-num">{{ stats['total_products'] }}</div><div class="stat-label">Products</div></div></div>
  <div class="col-6 col-md-2"><div class="stat-card blue"><div class="stat-num">{{ stats['total_txs'] }}</div><div class="stat-label">Transactions</div></div></div>
  <div class="col-6 col-md-2"><div class="stat-card green"><div class="stat-num">{{ stats['total_blocks'] }}</div><div class="stat-label">Blocks</div></div></div>
  <div class="col-6 col-md-2"><div class="stat-card red"><div class="stat-num">{{ stats['flagged'] }}</div><div class="stat-label">Flagged</div></div></div>
  <div class="col-6 col-md-2"><div class="stat-card {% if stats['chain_valid'] %}green{% else %}red{% endif %}">
    <div class="stat-num" style="font-size:1.4rem">{% if stats['chain_valid'] %}VALID{% else %}ERROR{% endif %}</div><div class="stat-label">Chain</div></div></div>
</div>
<div class="row g-3">
  <div class="col-lg-6">
    <div class="card">
      <div class="card-header"><i class="bi bi-people me-2"></i>User Management</div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0" style="font-size:.82rem">
            <thead class="table-light"><tr><th class="px-4">Name</th><th>Role</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              {% for u in users %}
              <tr>
                <td class="px-4"><div class="fw-semibold">{{ u['name'] }}</div><div class="text-muted" style="font-size:.75rem">{{ u['email'] }}</div></td>
                <td><span class="badge bg-secondary" style="font-size:.7rem">{{ u['role'] }}</span></td>
                <td>{% if u['is_active'] %}<span class="badge bg-success" style="font-size:.7rem">Active</span>
                  {% else %}<span class="badge bg-danger" style="font-size:.7rem">Inactive</span>{% endif %}</td>
                <td>{% if u['role'] != 'admin' %}
                  <form method="POST" action="/admin/toggle_user/{{ u['id'] }}" class="d-inline">
                    <button class="btn btn-sm py-0 {% if u['is_active'] %}btn-outline-danger{% else %}btn-outline-success{% endif %}">
                      {% if u['is_active'] %}Deactivate{% else %}Activate{% endif %}</button></form>{% endif %}</td>
              </tr>{% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
  <div class="col-lg-6">
    <div class="card mb-3">
      <div class="card-header"><i class="bi bi-journal-text me-2"></i>Audit Logs</div>
      <div class="card-body p-3" style="max-height:200px;overflow-y:auto">
        {% for log in logs %}
        <div class="border-bottom pb-1 mb-1" style="font-size:.76rem">
          <div class="d-flex justify-content-between"><span class="fw-semibold">{{ log['action'] }}</span>
            <span class="text-muted">{{ log['timestamp'][:16] }}</span></div>
          <div class="text-muted">{{ log['uname'] or 'System' }} &middot; {{ log['ip_address'] or 'N/A' }}</div>
        </div>{% else %}<p class="text-muted text-center small">No logs</p>{% endfor %}
      </div>
    </div>
    <div class="card">
      <div class="card-header"><i class="bi bi-link-45deg me-2"></i>Recent Blockchain Transactions</div>
      <div class="card-body p-3" style="max-height:180px;overflow-y:auto">
        {% for tx in txs %}
        <div class="border-bottom pb-1 mb-1" style="font-size:.76rem">
          <div class="d-flex justify-content-between">
            <span class="fw-semibold">{{ tx['action'].replace('_',' ').title() }}</span>
            <span class="text-muted">{{ tx['timestamp'][:10] }}</span></div>
          <div class="hash-text">Block #{{ tx['block_index'] or '-' }}: {{ tx['block_hash'][:24] if tx['block_hash'] else '' }}...</div>
        </div>{% endfor %}
      </div>
    </div>
  </div>
</div>"""

TRACK_TPL = """
<div class="mb-4"><h4 class="fw-bold mb-0">Product Verification & Tracking</h4>
  <small class="text-muted">Search by product code to view full blockchain history</small></div>
<div class="card p-3 mb-4">
  <form method="GET" action="/track" class="d-flex gap-2">
    <input type="text" name="q" class="form-control" placeholder="Product Code (e.g. PC-2024-0001)..." value="{{ query }}">
    <button type="submit" class="btn btn-primary px-4"><i class="bi bi-search me-1"></i>Search</button>
  </form>
</div>
{% if query and not product %}
<div class="alert alert-warning"><i class="bi bi-exclamation-circle me-2"></i>No product found for "{{ query }}"</div>
{% endif %}
{% if product %}
<div class="row g-3">
  <div class="col-lg-4">
    <div class="card">
      <div class="card-header"><i class="bi bi-box me-2"></i>Product Details
        {% if product['is_flagged'] %}<span class="badge bg-danger ms-2">Flagged</span>{% endif %}
        {% if product['is_approved'] %}<span class="badge bg-success ms-2">UNBS Approved</span>{% endif %}
      </div>
      <div class="card-body">
        <table class="table table-sm table-borderless mb-0" style="font-size:.84rem">
          <tr><td class="text-muted">Code</td><td class="fw-bold">{{ product['product_code'] }}</td></tr>
          <tr><td class="text-muted">Crop</td><td>{{ product['crop_type'] }}</td></tr>
          <tr><td class="text-muted">Quantity</td><td>{{ product['quantity'] }} kg</td></tr>
          <tr><td class="text-muted">Grade</td><td><span class="badge bg-light text-dark border">{{ product['quality_grade'] }}</span></td></tr>
          <tr><td class="text-muted">Farmer</td><td>{{ product['farmer_name'] }}</td></tr>
          <tr><td class="text-muted">Location</td><td>{{ product['location'] }}</td></tr>
          <tr><td class="text-muted">District</td><td>{{ product['district'] }}</td></tr>
          <tr><td class="text-muted">Harvest</td><td>{{ product['harvest_date'] }}</td></tr>
          <tr><td class="text-muted">Status</td><td><span class="badge-status badge-{{ product['status'] }}">{{ product['status'].replace('_',' ').title() }}</span></td></tr>
        </table>
        <hr>
        <div style="font-size:.72rem"><div class="text-muted fw-semibold mb-1">Blockchain Hash</div>
          <div class="hash-text bg-light p-2 rounded">{{ product['blockchain_hash'] or 'N/A' }}</div></div>
      </div>
    </div>
  </div>
  <div class="col-lg-8">
    <div class="card">
      <div class="card-header"><i class="bi bi-diagram-3 me-2"></i>Supply Chain Timeline</div>
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-4 flex-wrap" style="font-size:.8rem">
          <span class="badge bg-success">Farm</span><i class="bi bi-arrow-right text-muted"></i>
          <span class="badge bg-primary">Buyer</span><i class="bi bi-arrow-right text-muted"></i>
          <span class="badge bg-warning text-dark">Transport</span><i class="bi bi-arrow-right text-muted"></i>
          <span class="badge bg-info">Delivery</span><i class="bi bi-arrow-right text-muted"></i>
          <span class="badge bg-dark">Regulator</span>
        </div>
        <div class="timeline">
          {% for tx in txs %}
          <div class="timeline-item">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                <div class="fw-semibold">{{ tx['action'].replace('_',' ').title() }}</div>
                <div style="font-size:.82rem;color:var(--text-muted)">
                  From: {{ user_name_fn(tx['sender_id']) }}
                  {% if tx['receiver_id'] %} &rarr; To: {{ user_name_fn(tx['receiver_id']) }}{% endif %}
                </div>
                <div class="hash-text mt-1">TX: {{ tx['tx_id'] }}</div>
                <div class="hash-text">Block #{{ tx['block_index'] }} &middot; {{ tx['block_hash'][:28] if tx['block_hash'] else '' }}...</div>
              </div>
              <div class="text-end" style="font-size:.76rem;color:var(--text-muted);white-space:nowrap">
                {{ tx['timestamp'][:10] }}<br>{{ tx['timestamp'][11:19] }}</div>
            </div>
          </div>
          {% else %}<p class="text-muted">No transactions recorded.</p>{% endfor %}
        </div>
      </div>
    </div>
  </div>
</div>{% endif %}"""

BLOCKCHAIN_TPL = """
<div class="d-flex justify-content-between align-items-center mb-4">
  <div><h4 class="fw-bold mb-0">Blockchain Explorer</h4>
    <small class="text-muted">AgriChain Kasese District Node &mdash; Immutable Ledger</small></div>
  {% if is_valid %}<span class="badge bg-success fs-6"><i class="bi bi-shield-check me-1"></i>Chain VALID</span>
  {% else %}<span class="badge bg-danger fs-6"><i class="bi bi-exclamation-triangle me-1"></i>Chain COMPROMISED</span>{% endif %}
</div>
<div class="row g-3 mb-4">
  <div class="col-6 col-md-3"><div class="stat-card green"><div class="stat-num">{{ chain|length }}</div><div class="stat-label">Total Blocks</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card amber"><div class="stat-num">2</div><div class="stat-label">PoW Difficulty</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card blue"><div class="stat-num">SHA-256</div><div class="stat-label">Hash Algorithm</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card {% if is_valid %}green{% else %}red{% endif %}">
    <div class="stat-num" style="font-size:1.4rem">{% if is_valid %}VALID{% else %}ERR{% endif %}</div><div class="stat-label">Integrity</div></div></div>
</div>
<div class="card">
  <div class="card-header" style="background:var(--dark);color:#fff"><i class="bi bi-link-45deg me-2"></i>Block Chain &mdash; Kasese Agricultural Ledger</div>
  <div class="card-body p-3" style="background:#0d1117">
    {% for b in chain %}
    <div class="block-card">
      <div class="d-flex justify-content-between align-items-start mb-2">
        <div>
          <span style="background:rgba(244,168,32,.2);color:#f4a820;padding:2px 10px;border-radius:12px;font-size:.75rem;font-weight:600">Block #{{ b['idx'] }}</span>
          {% if b['idx'] == 0 %}<span style="background:rgba(255,255,255,.1);color:#94a3b8;padding:2px 8px;border-radius:10px;font-size:.68rem;margin-left:6px">Genesis</span>{% endif %}
        </div>
        <span style="font-size:.73rem;color:#64748b">{{ b['timestamp'][:19] }}</span>
      </div>
      <div style="font-size:.73rem">
        <div class="mb-1"><span style="color:#64748b">Hash: </span><span class="block-hash">{{ b['hash'] }}</span></div>
        <div class="mb-1"><span style="color:#64748b">Prev: </span><span style="font-family:'JetBrains Mono',monospace;color:#475569">{{ b['previous_hash'] }}</span></div>
        <div><span style="color:#64748b">Nonce: </span><span style="color:#e2e8f0">{{ b['nonce'] }}</span>
          <span style="color:#64748b;margin-left:1rem">Data: </span>
          <span style="font-family:'JetBrains Mono',monospace;color:#94a3b8">{{ b['data'][:70] }}{% if b['data']|length > 70 %}...{% endif %}</span></div>
      </div>
      {% if not loop.last %}<div class="text-center mt-2" style="color:#475569;font-size:.78rem"><i class="bi bi-arrow-down"></i> Linked by Hash</div>{% endif %}
    </div>
    {% endfor %}
  </div>
</div>
<div class="mt-3">
  <a href="/api/chain" class="btn btn-outline-secondary btn-sm" target="_blank"><i class="bi bi-braces me-1"></i>Raw JSON API</a>
</div>"""

ANALYTICS_TPL = """
<div class="mb-4"><h4 class="fw-bold mb-0">Analytics & Insights</h4>
  <small class="text-muted">Kasese District Agricultural Supply Chain Statistics</small></div>
<div class="row g-3 mb-4">
  <div class="col-6 col-md-3"><div class="stat-card green"><div class="stat-num">{{ total_p }}</div><div class="stat-label">Products</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card blue"><div class="stat-num">{{ total_txs }}</div><div class="stat-label">Transactions</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card amber"><div class="stat-num">{{ verified }}</div><div class="stat-label">UNBS Verified</div></div></div>
  <div class="col-6 col-md-3"><div class="stat-card red"><div class="stat-num">{{ flagged }}</div><div class="stat-label">Flagged</div></div></div>
</div>
<div class="row g-3">
  <div class="col-lg-6"><div class="card"><div class="card-header"><i class="bi bi-pie-chart me-2"></i>By Crop Type</div>
    <div class="card-body"><canvas id="cropChart" height="220"></canvas></div></div></div>
  <div class="col-lg-6"><div class="card"><div class="card-header"><i class="bi bi-bar-chart me-2"></i>By Status</div>
    <div class="card-body"><canvas id="statusChart" height="220"></canvas></div></div></div>
  <div class="col-lg-6"><div class="card"><div class="card-header"><i class="bi bi-graph-up me-2"></i>Verification Rate</div>
    <div class="card-body d-flex flex-column align-items-center justify-content-center" style="height:260px">
      <canvas id="verifyChart" style="max-width:200px;max-height:200px"></canvas>
      <div class="mt-2 text-muted" style="font-size:.84rem">{{ verified }} of {{ total_p }} verified by UNBS</div>
    </div></div></div>
</div>
<script>
const cropData={{ crop_data|safe }};const statusData={{ status_data|safe }};
const colors=['#1a6b3c','#2d9e5f','#f4a820','#c98010','#0891b2','#0369a1','#dc2626','#7c3aed'];
new Chart(document.getElementById('cropChart'),{type:'doughnut',data:{labels:cropData.map(d=>d.label),datasets:[{data:cropData.map(d=>d.value),backgroundColor:colors,borderWidth:2}]},options:{plugins:{legend:{position:'right'}},cutout:'55%'}});
new Chart(document.getElementById('statusChart'),{type:'bar',data:{labels:statusData.map(d=>d.label.replace('_',' ')),datasets:[{label:'Products',data:statusData.map(d=>d.value),backgroundColor:colors,borderRadius:6}]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{stepSize:1}}}}});
new Chart(document.getElementById('verifyChart'),{type:'doughnut',data:{labels:['Verified','Pending'],datasets:[{data:[{{ verified }},{{ total_p }}-{{ verified }}],backgroundColor:['#1a6b3c','#e5e7eb'],borderWidth:0}]},options:{cutout:'70%',plugins:{legend:{display:false}}}});
</script>"""

# ══════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════

if __name__ == '__main__':
    init_db()
    seed_db()
    print("\n" + "="*55)
    print("  AgriChain Uganda — Blockchain Supply Chain System")
    print("  Kasese District, Uganda")
    print("="*55)
    print("  URL: http://localhost:5000")
    print("\n  Test Credentials:")
    print("  Admin:       admin@agrichain.ug       / admin123")
    print("  Farmer:      farmer@agrichain.ug      / farmer123")
    print("  Buyer:       buyer@agrichain.ug       / buyer123")
    print("  Transporter: transporter@agrichain.ug / transport123")
    print("  Regulator:   regulator@agrichain.ug   / regulator123")
    print("="*55 + "\n")
    app.run(debug=True, port=5000)
