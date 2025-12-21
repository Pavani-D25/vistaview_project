#!/usr/bin/env bash
set -euo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏠 VistaView Vendor Catalog Setup"
echo "   Automated PDF ingestion + Next.js frontend"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PDF="$BACKEND/input/catalog.pdf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Python
echo -e "${BLUE}Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

# Check Node.js
echo -e "${BLUE}Checking Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js found ($(node --version))${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npm found ($(npm --version))${NC}"
echo ""

# Check for PDF
echo -e "${BLUE}Checking for catalog PDF...${NC}"
if [ ! -f "$PDF" ]; then
    echo -e "${YELLOW}⚠️  Warning: No catalog.pdf found${NC}"
    echo "   Expected location: $PDF"
    echo "   Please add your PDF before running ingestion"
    echo ""
else
    PDF_SIZE=$(du -h "$PDF" | cut -f1)
    echo -e "${GREEN}✓ Found catalog.pdf (${PDF_SIZE})${NC}"
    echo ""
fi

# Setup Backend
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}📦 Setting up Backend...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$BACKEND"

# Create directories
mkdir -p input data/images data/collages

# Setup Python virtual environment
echo "Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate venv
source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# Setup Frontend
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}🎨 Setting up Frontend...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$FRONTEND"

# Create directories
mkdir -p public/images public/collages

# Install npm dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies (this may take a minute)..."
    npm install --silent
    echo -e "${GREEN}✓ npm dependencies installed${NC}"
else
    echo -e "${GREEN}✓ npm dependencies already installed${NC}"
fi
echo ""

# Run ingestion if PDF exists
if [ -f "$PDF" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}🔄 Running PDF Ingestion...${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    cd "$BACKEND"
    source .venv/bin/activate
    python3 ingest_vendor_pdf.py
    echo ""
fi

# Final instructions
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -f "$PDF" ]; then
    echo -e "${GREEN}🚀 Starting Frontend...${NC}"
    cd "$FRONTEND"
    
    # Kill any existing process on port 3000
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}✓ Frontend starting on http://localhost:3000${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    npm run dev
else
    echo -e "${YELLOW}📝 Next Steps:${NC}"
    echo ""
    echo "1. Add your PDF catalog:"
    echo "   ${BLUE}cp your_catalog.pdf backend/input/catalog.pdf${NC}"
    echo ""
    echo "2. Run ingestion:"
    echo "   ${BLUE}cd backend && source .venv/bin/activate && python3 ingest_vendor_pdf.py${NC}"
    echo ""
    echo "3. Start frontend:"
    echo "   ${BLUE}cd frontend && npm run dev${NC}"
    echo ""
    echo "4. Open browser:"
    echo "   ${BLUE}http://localhost:3000${NC}"
    echo ""
fi