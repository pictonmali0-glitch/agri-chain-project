# AgriChain Uganda
## Blockchain-Based Agricultural Supply Chain Tracking System
### Case Study: Kasese District, Uganda
---

## Project Overview
AgriChain is a full-stack web prototype demonstrating how blockchain technology can improve transparency, traceability, trust, accountability, and fraud prevention in Uganda's agricultural supply chains.

---

## Folder Structure
```
agri_chain/
├── app.py               # Flask app factory & entry point
├── config.py            # Configuration settings
├── models.py            # SQLAlchemy database models + seed data
├── blockchain.py        # SHA-256 blockchain engine with PoW
├── auth.py              # Authentication blueprint (login/register/logout)
├── routes.py            # All route handlers (farmer/buyer/transporter/regulator/admin)
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── templates/
    ├── base.html              # Shared layout with sidebar nav
    ├── landing.html           # Public landing page
    ├── login.html             # Login page
    ├── register.html          # Registration page
    ├── farmer_dashboard.html  # Farmer role dashboard
    ├── buyer_dashboard.html   # Buyer role dashboard
    ├── transporter_dashboard.html
    ├── regulator_dashboard.html
    ├── admin_dashboard.html
    ├── add_product.html       # Product registration form
    ├── track.html             # Supply chain tracker / verifier
    ├── blockchain_explorer.html
    ├── analytics.html
    └── qr.html                # QR code display
```

---

## Installation & Setup

### Step 1: Install Python 3.10+
Make sure Python and pip are installed.

### Step 2: Create and activate virtual environment
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the application
```bash
python app.py
```

### Step 5: Open in browser
```
http://localhost:5000
```

---

## Test Credentials

| Role        | Email                        | Password      |
|-------------|------------------------------|---------------|
| Admin       | admin@agrichain.ug           | admin123      |
| Farmer      | farmer@agrichain.ug          | farmer123     |
| Farmer 2    | farmer2@agrichain.ug         | farmer123     |
| Buyer       | buyer@agrichain.ug           | buyer123      |
| Transporter | transporter@agrichain.ug     | transport123  |
| Regulator   | regulator@agrichain.ug       | regulator123  |

---

## Blockchain Implementation
- **Algorithm**: SHA-256
- **Consensus**: Proof of Work (difficulty = 2 leading zeros)
- **Storage**: SQLite (blocks table)
- **Integrity check**: Chain validation on every regulator/admin load
- **Immutability**: Each block contains the previous block's hash; tampering breaks the chain

### Block Structure
```
{
  index:         Block number
  timestamp:     UTC datetime
  data:          Transaction payload (JSON)
  previous_hash: SHA-256 of previous block
  nonce:         Proof-of-work nonce
  hash:          SHA-256 of all above fields
}
```

---

## Supply Chain Stages
1. **Harvested** – Farmer registers crop; genesis block created
2. **Transferred** – Farmer transfers ownership to buyer; new block
3. **Purchased** – Buyer confirms; new block
4. **In Transit** – Transporter marks movement; new block
5. **Delivered** – Transporter confirms arrival; new block
6. **Approved** – UNBS Regulator approves; final compliance block

---

## Key Features
- Role-based access control (5 roles)
- Immutable blockchain ledger with SHA-256 + PoW
- QR code generation per product
- Full supply chain audit timeline
- Blockchain explorer (raw block view)
- Analytics dashboard with Chart.js
- Fraud flagging system
- Audit logs for all user actions
- REST API endpoints: /api/products, /api/chain

---

## Academic Notes
This prototype simulates a permissioned blockchain on SQLite, suitable for:
- Final year project demonstrations
- Supply chain transparency research
- Comparison with Hyperledger Fabric / Ethereum in literature review
- Kasese District Uganda agricultural case studies

---

## Tech Stack
- **Backend**: Python 3.10 + Flask 3.0
- **Database**: SQLite via SQLAlchemy
- **Blockchain**: Custom SHA-256 + PoW engine
- **Frontend**: Bootstrap 5 + Chart.js + Bootstrap Icons
- **Auth**: Session-based with Werkzeug password hashing
- **QR**: qrcode + Pillow
