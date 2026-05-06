#!/bin/bash
# AgriChain Backend Setup Script
# Run from the agrichain/backend/ directory

echo "🌿 AgriChain Backend Setup"
echo "=========================="

# Create virtual environment
python3 -m venv venv
echo "✅ Virtual environment created"

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Create .env if not exists
if [ ! -f .env ]; then
  cat > .env << 'EOF'
SECRET_KEY=agrichain-change-this-secret-2024
JWT_SECRET_KEY=agrichain-jwt-change-this-2024
DATABASE_URL=sqlite:///agrichain.db

# Email (configure for production)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@agrichain.app
EOF
  echo "✅ .env template created – update with real values!"
fi

# Create uploads folder
mkdir -p uploads/qrcodes uploads/products uploads/profiles
echo "✅ Upload directories created"

echo ""
echo "🚀 Starting AgriChain Backend..."
echo "   Admin: admin@agrichain.app / Admin@123"
echo ""

python app.py
