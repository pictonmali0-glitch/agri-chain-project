# AgriChain – Complete Deployment Guide
**Agricultural Blockchain Supply Chain Tracking System**
*Kasese District, Uganda*

---

## 📁 Project Structure

```
agrichain/
├── backend/                     ← Flask REST API
│   ├── app.py                   ← App factory & entry point
│   ├── requirements.txt         ← Python dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              ← User & OTPCode models
│   │   ├── product.py           ← Product model
│   │   └── blockchain.py        ← Transfer & BlockchainBlock models
│   ├── routes/
│   │   ├── auth_routes.py       ← Register, login, OTP, profile
│   │   ├── product_routes.py    ← CRUD, QR, search, history
│   │   ├── transfer_routes.py   ← Transfer, acknowledge, reject
│   │   ├── blockchain_routes.py ← Chain explorer, verify
│   │   ├── admin_routes.py      ← Dashboard, movements, suspicious
│   │   └── receiver_routes.py   ← Scan QR, pending, track
│   └── utils/
│       ├── auth_utils.py        ← OTP generation & email
│       ├── qr_utils.py          ← QR code generation & images
│       └── suspicious.py        ← Fraud detection logic
│
└── flutter_frontend/            ← Flutter mobile app
    ├── pubspec.yaml
    └── lib/
        ├── main.dart            ← Entry point
        ├── router.dart          ← GoRouter navigation
        ├── utils/
        │   └── constants.dart   ← Theme, colors, helpers
        ├── services/
        │   ├── api_service.dart ← HTTP client (all API calls)
        │   └── auth_provider.dart ← Auth state management
        ├── widgets/
        │   └── common_widgets.dart ← Reusable UI components
        └── screens/
            ├── auth/
            │   ├── splash_screen.dart
            │   ├── login_screen.dart
            │   └── register_screen.dart
            ├── farmer/
            │   ├── farmer_dashboard.dart
            │   ├── add_product_screen.dart
            │   └── transfer_screen.dart
            ├── receiver/
            │   └── receiver_dashboard.dart
            ├── admin/
            │   └── admin_dashboard.dart
            └── shared/
                ├── product_tracking_screen.dart
                └── profile_screen.dart
```

---

## 🗄️ Database Schema

### users
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(36) PK | UUID |
| name | VARCHAR(120) | |
| email | VARCHAR(120) UNIQUE | |
| phone | VARCHAR(20) | |
| password_hash | VARCHAR(256) | bcrypt |
| role | VARCHAR(20) | farmer \| receiver \| admin |
| is_verified | BOOLEAN | Email OTP verified |
| profile_pic | VARCHAR(300) | File path |
| location | VARCHAR(200) | |
| fingerprint_enabled | BOOLEAN | |
| created_at | DATETIME | |
| last_login | DATETIME | |

### otp_codes
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| email | VARCHAR(120) | |
| code | VARCHAR(6) | 6-digit numeric |
| purpose | VARCHAR(30) | registration \| login \| reset |
| is_used | BOOLEAN | |
| attempts | INTEGER | Max 5 |
| created_at | DATETIME | |
| expires_at | DATETIME | 5 min TTL |

### products
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(36) PK | UUID |
| name | VARCHAR(120) | |
| batch_number | VARCHAR(50) UNIQUE | e.g. MAIZE-1234-2024 |
| category | VARCHAR(60) | |
| quantity | FLOAT | |
| unit | VARCHAR(20) | kg, tonnes, bags |
| description | TEXT | |
| origin | VARCHAR(200) | Farm location |
| harvest_date | DATE | |
| qr_code_path | VARCHAR(300) | |
| images | TEXT | JSON array of paths |
| current_location | VARCHAR(200) | |
| current_holder_id | FK → users.id | |
| farmer_id | FK → users.id | |
| status | VARCHAR(30) | pending \| in_transit \| delivered \| acknowledged |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### transfers
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(36) PK | UUID |
| product_id | FK → products.id | |
| sender_id | FK → users.id | |
| receiver_id | FK → users.id | nullable |
| from_location | VARCHAR(200) | |
| to_location | VARCHAR(200) | |
| quantity_sent | FLOAT | |
| quantity_received | FLOAT | nullable |
| unit | VARCHAR(20) | |
| status | VARCHAR(30) | pending \| in_transit \| delivered \| acknowledged \| rejected |
| transfer_type | VARCHAR(40) | transfer \| collection \| warehouse \| final_delivery |
| note | TEXT | |
| acknowledgement_note | TEXT | |
| acknowledged_at | DATETIME | |
| is_suspicious | BOOLEAN | |
| suspicious_reason | VARCHAR(300) | |
| block_hash | VARCHAR(64) | SHA-256 hash |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### blockchain_blocks
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| block_index | INTEGER UNIQUE | Sequential |
| transaction_id | FK → transfers.id | |
| previous_hash | VARCHAR(64) | SHA-256 of previous block |
| current_hash | VARCHAR(64) | SHA-256 of this block |
| data | TEXT | JSON payload |
| nonce | INTEGER | |
| timestamp | DATETIME | |
| is_genesis | BOOLEAN | Block #0 flag |

---

## 🚀 Backend Setup (Flask)

### 1. Prerequisites
- Python 3.11+
- pip

### 2. Install dependencies
```bash
cd agrichain/backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment variables
Create a `.env` file in `backend/`:
```env
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DATABASE_URL=sqlite:///agrichain.db

# Email (Gmail example)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@agrichain.app
```

> 💡 For Gmail: enable 2FA, then generate an App Password at myaccount.google.com

### 4. Run the backend
```bash
python app.py
# → Running on http://0.0.0.0:5000
```

**Default Admin Account (auto-created):**
- Email: `admin@agrichain.app`
- Password: `Admin@123`

### 5. Production deployment
```bash
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

---

## 📱 Flutter Frontend Setup

### 1. Prerequisites
- Flutter SDK 3.22+
- Android Studio or VS Code
- Android SDK (for Android) or Xcode (for iOS)

### 2. Install dependencies
```bash
cd agrichain/flutter_frontend
flutter pub get
```

### 3. Configure API URL
Edit `lib/utils/constants.dart`:
```dart
// For Android emulator:
const String kBaseUrl = 'http://10.0.2.2:5000/api';

// For physical device (use your PC's local IP):
const String kBaseUrl = 'http://192.168.x.x:5000/api';

// For production:
const String kBaseUrl = 'https://api.agrichain.app/api';
```

### 4. Android permissions
Add to `android/app/src/main/AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.USE_BIOMETRIC"/>
<uses-permission android:name="android.permission.USE_FINGERPRINT"/>
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
```

For biometric auth, add to `<activity>` in AndroidManifest:
```xml
android:launchMode="singleTop"
```

### 5. Run the app
```bash
flutter run                    # Debug mode
flutter run --release          # Release mode
flutter build apk              # Build APK
flutter build appbundle        # Build for Play Store
```

### 6. iOS setup (additional)
```bash
cd ios && pod install && cd ..
open ios/Runner.xcworkspace
```
Add to `ios/Runner/Info.plist`:
```xml
<key>NSCameraUsageDescription</key>
<string>AgriChain uses camera to scan QR codes</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>AgriChain needs photo access to upload product images</string>
<key>NSFaceIDUsageDescription</key>
<string>AgriChain uses Face ID for secure login</string>
```

---

## 🔌 Full API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/request-otp | Send OTP to email |
| POST | /api/auth/verify-otp | Verify OTP code |
| POST | /api/auth/register | Create account |
| POST | /api/auth/login | Login with email/password |
| POST | /api/auth/reset-password | Reset password via OTP |
| GET | /api/auth/me | Get current user |
| PUT | /api/auth/profile | Update profile |
| POST | /api/auth/profile/picture | Upload profile pic |
| POST | /api/auth/refresh | Refresh JWT |

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/products/ | Create product |
| GET | /api/products/ | List products |
| GET | /api/products/search?q= | Search products |
| GET | /api/products/:id | Get product |
| GET | /api/products/:id/history | Product timeline |
| GET | /api/products/:id/qr | Get QR code |
| POST | /api/products/:id/images | Upload images |

### Transfers
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/transfers/ | Create transfer |
| GET | /api/transfers/ | List transfers |
| GET | /api/transfers/:id | Get transfer |
| POST | /api/transfers/:id/acknowledge | Acknowledge receipt |
| POST | /api/transfers/:id/reject | Reject transfer |

### Blockchain
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/blockchain/chain | Full blockchain |
| GET | /api/blockchain/verify | Verify chain integrity |
| GET | /api/blockchain/block/:index | Get single block |
| GET | /api/blockchain/product/:id | Product chain |
| GET | /api/blockchain/stats | Chain statistics |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/admin/dashboard | Dashboard data |
| GET | /api/admin/movements | Product movements |
| GET | /api/admin/suspicious | Suspicious transactions |
| PUT | /api/admin/suspicious/:id | Flag/unflag transaction |
| GET | /api/admin/users | All users |
| POST | /api/admin/transfers/:id/approve | Approve/reject transfer |

### Receiver
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/receiver/scan | Scan QR code |
| GET | /api/receiver/pending | Pending transfers |
| GET | /api/receiver/track/:id | Track product |

---

## 🔐 Security Features

1. **JWT Authentication** – All protected routes require Bearer token
2. **Email OTP Verification** – 6-digit code, 5-min TTL, max 5 attempts
3. **Password Requirements** – Min 8 chars, uppercase + digit required
4. **Blockchain Integrity** – SHA-256 chained hashes, tamper detection
5. **Suspicious Detection** – Auto-flags: quantity anomalies, rapid duplicates, self-transfers
6. **QR Abuse Detection** – Flags repeated QR scans (5+ per hour)
7. **Fingerprint Auth** – Local biometric via Flutter local_auth
8. **Role-Based Access** – Farmer/Receiver/Admin isolation

---

## 🌿 Suspicious Transaction Rules

| Rule | Trigger |
|------|---------|
| Quantity anomaly | Received > sent by 5% |
| Rapid duplicate | Same product transferred within 60s |
| Self-transfer | Sender == Receiver |
| Status conflict | Transfer on acknowledged product |
| QR abuse | 5+ scans by same user in 1 hour |
| Qty discrepancy | Acknowledged qty < sent qty by 5% |

---

## 📊 Supply Chain Flow

```
Farmer (registers product + QR)
  ↓ transfer
Collection Center
  ↓ transfer
Transporter / Truck
  ↓ transfer
Warehouse
  ↓ transfer
Buyer / Receiver (scans QR → acknowledges receipt)

Each step → New Transfer record → New Blockchain Block
```

**Status Lifecycle:**
```
pending → in_transit → delivered → acknowledged
                    ↘ rejected
```

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| `No internet` on emulator | Use `10.0.2.2` instead of `localhost` |
| OTP not received | Check console (DEV mode prints OTP), verify SMTP config |
| QR scanner black screen | Grant camera permission in device settings |
| Fingerprint not working | Enable biometrics on device first |
| CORS errors | Check Flask-CORS is installed, API URL is correct |
| DB errors | Delete `agrichain.db` and restart (re-seeds admin) |

---

## 🎓 Academic Notes

This system demonstrates:
- **Blockchain fundamentals**: Genesis block, SHA-256 chaining, tamper detection
- **Merkle-like integrity**: Each block contains previous hash
- **Supply chain transparency**: Full audit trail from farm to buyer
- **Smart fraud detection**: Automated suspicious transaction flagging
- **QR-based authentication**: Product identity via encrypted QR payloads
- **Role-based access control**: Farmer, Receiver, Admin isolation
- **OTP-based email verification**: Prevents fake registrations

*Built for Kasese District Agricultural Supply Chain – Uganda, 2024*
