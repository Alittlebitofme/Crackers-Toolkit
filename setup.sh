#!/usr/bin/env bash
# ============================================================
# Cracker's Toolkit — Dependency Setup (Debian/Ubuntu)
# ============================================================
# Run this script ONCE after extracting the release archive.
# It downloads and sets up all external tools automatically.
# Requires: Debian/Ubuntu (apt), internet connection.
# Usage:  chmod +x setup.sh && ./setup.sh
# ============================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

BASE="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "============================================================"
echo "  Cracker's Toolkit - Dependency Setup (Debian/Ubuntu)"
echo "============================================================"
echo ""
echo "Install location: $BASE"
echo ""

# Helper: check if a command exists
has_cmd() { command -v "$1" &>/dev/null; }

# Helper: install an apt package if missing
ensure_apt() {
    local pkg="$1"
    if dpkg -s "$pkg" &>/dev/null; then
        return 0
    fi
    echo -e "       Installing ${BOLD}$pkg${NC} via apt..."
    sudo apt-get install -y "$pkg" >/dev/null 2>&1
}

# -------------------------------------------------------
# 0. Ensure basic build tools are available
# -------------------------------------------------------
echo -e "[0/6] Checking system prerequisites..."
if ! has_cmd sudo; then
    echo -e "  ${RED}✗${NC} sudo not found. Run this as root or install sudo."
    exit 1
fi
sudo apt-get update -qq >/dev/null 2>&1
ensure_apt curl
ensure_apt wget
ensure_apt p7zip-full
echo -e "  ${GREEN}✓${NC} curl, wget, p7zip-full ready."

# -------------------------------------------------------
# 1. Check / Install Python 3
# -------------------------------------------------------
echo ""
echo -e "[1/6] Checking Python 3..."
if has_cmd python3; then
    PYVER=$(python3 --version 2>&1)
    echo -e "  ${GREEN}✓${NC} Found $PYVER"
else
    echo "  Installing python3..."
    sudo apt-get install -y python3 python3-pip python3-venv >/dev/null 2>&1
    echo -e "  ${GREEN}✓${NC} Python 3 installed."
fi

# -------------------------------------------------------
# 2. Download / install hashcat
# -------------------------------------------------------
echo ""
echo -e "[2/6] Checking hashcat..."
if [ -d "$BASE/hashcat-7.1.2" ] && [ -f "$BASE/hashcat-7.1.2/hashcat.bin" -o -f "$BASE/hashcat-7.1.2/hashcat" ]; then
    echo -e "  ${GREEN}✓${NC} Found hashcat in $BASE/hashcat-7.1.2/"
elif has_cmd hashcat; then
    echo -e "  ${GREEN}✓${NC} Found hashcat on PATH: $(which hashcat)"
else
    echo "  Downloading hashcat 7.1.2..."
    HC_URL="https://hashcat.net/files/hashcat-7.1.2.7z"
    HC_TMP="/tmp/hashcat-7.1.2.7z"
    if curl -L -o "$HC_TMP" "$HC_URL" 2>/dev/null; then
        echo "  Extracting..."
        7z x "$HC_TMP" -o"$BASE" -y >/dev/null 2>&1
        # Make binary executable
        chmod +x "$BASE/hashcat-7.1.2/hashcat.bin" 2>/dev/null || true
        chmod +x "$BASE/hashcat-7.1.2/hashcat" 2>/dev/null || true
        if [ -d "$BASE/hashcat-7.1.2" ]; then
            echo -e "  ${GREEN}✓${NC} hashcat installed."
        else
            echo -e "  ${RED}✗${NC} Extraction failed. Install manually:"
            echo "       sudo apt install hashcat"
            echo "       or download from https://hashcat.net/hashcat/"
        fi
        rm -f "$HC_TMP"
    else
        echo -e "  ${YELLOW}!${NC} Download failed. You can install via apt instead:"
        echo "       sudo apt install hashcat"
    fi
fi

# -------------------------------------------------------
# 3. Download / install John the Ripper
# -------------------------------------------------------
echo ""
echo -e "[3/6] Checking John the Ripper..."
JTR_FOUND=0
for d in "$BASE"/john-*/; do
    [ -d "$d/run" ] && JTR_FOUND=1 && break
done
if [ "$JTR_FOUND" -eq 1 ]; then
    echo -e "  ${GREEN}✓${NC} Found John the Ripper."
elif has_cmd john; then
    echo -e "  ${GREEN}✓${NC} Found john on PATH: $(which john)"
else
    echo "  Installing John the Ripper via snap (Jumbo edition)..."
    if has_cmd snap; then
        sudo snap install john-the-ripper >/dev/null 2>&1 && \
            echo -e "  ${GREEN}✓${NC} john-the-ripper installed via snap." || \
            echo -e "  ${YELLOW}!${NC} snap install failed. Try: sudo apt install john"
    else
        echo "  snap not available. Installing basic john via apt..."
        sudo apt-get install -y john >/dev/null 2>&1
        echo -e "  ${GREEN}✓${NC} john installed via apt (basic, not Jumbo)."
        echo -e "  ${YELLOW}!${NC} For full Jumbo features, install snap and run:"
        echo "       sudo snap install john-the-ripper"
    fi
fi

# -------------------------------------------------------
# 4. Download PRINCE Processor
# -------------------------------------------------------
echo ""
echo -e "[4/6] Checking PRINCE Processor..."
PP_FOUND=0
[ -d "$BASE/Scripts_to_use/princeprocessor-master" ] && PP_FOUND=1
has_cmd pp64 && PP_FOUND=1
if [ "$PP_FOUND" -eq 1 ]; then
    echo -e "  ${GREEN}✓${NC} Found PRINCE Processor."
else
    echo "  Downloading PRINCE Processor..."
    PP_URL="https://github.com/hashcat/princeprocessor/releases/download/v0.22/princeprocessor-0.22.7z"
    PP_TMP="/tmp/princeprocessor.7z"
    if curl -L -o "$PP_TMP" "$PP_URL" 2>/dev/null; then
        mkdir -p "$BASE/Scripts_to_use/princeprocessor-master"
        7z x "$PP_TMP" -o"$BASE/Scripts_to_use/princeprocessor-master" -y >/dev/null 2>&1
        # Make binaries executable
        find "$BASE/Scripts_to_use/princeprocessor-master" -name 'pp64*' -exec chmod +x {} \; 2>/dev/null
        find "$BASE/Scripts_to_use/princeprocessor-master" -name 'pp.*' -exec chmod +x {} \; 2>/dev/null
        echo -e "  ${GREEN}✓${NC} PRINCE Processor installed."
        rm -f "$PP_TMP"
    else
        echo -e "  ${RED}✗${NC} Download failed. Get it from:"
        echo "       https://github.com/hashcat/princeprocessor/releases"
    fi
fi

# -------------------------------------------------------
# 5. Download PCFG Cracker + demeuk
# -------------------------------------------------------
echo ""
echo -e "[5/6] Checking PCFG Cracker and demeuk..."

if [ -d "$BASE/Scripts_to_use/pcfg_cracker-master" ]; then
    echo -e "  ${GREEN}✓${NC} Found PCFG Cracker."
else
    echo "  Downloading PCFG Cracker..."
    PCFG_URL="https://github.com/lakiw/pcfg_cracker/archive/refs/heads/master.zip"
    PCFG_TMP="/tmp/pcfg_cracker.zip"
    if curl -L -o "$PCFG_TMP" "$PCFG_URL" 2>/dev/null; then
        mkdir -p "$BASE/Scripts_to_use"
        unzip -qo "$PCFG_TMP" -d "$BASE/Scripts_to_use" 2>/dev/null
        echo -e "  ${GREEN}✓${NC} PCFG Cracker installed."
        rm -f "$PCFG_TMP"
    else
        echo -e "  ${RED}✗${NC} Download failed. Get it from:"
        echo "       https://github.com/lakiw/pcfg_cracker"
    fi
fi

if [ -d "$BASE/Scripts_to_use/demeuk-master" ]; then
    echo -e "  ${GREEN}✓${NC} Found demeuk."
else
    echo "  Downloading demeuk..."
    DM_URL="https://github.com/roeldev/demeuk/archive/refs/heads/master.zip"
    DM_TMP="/tmp/demeuk.zip"
    if curl -L -o "$DM_TMP" "$DM_URL" 2>/dev/null; then
        mkdir -p "$BASE/Scripts_to_use"
        unzip -qo "$DM_TMP" -d "$BASE/Scripts_to_use" 2>/dev/null
        echo -e "  ${GREEN}✓${NC} demeuk installed."
        rm -f "$DM_TMP"
    else
        echo -e "  ${RED}✗${NC} Download failed. Get it from:"
        echo "       https://github.com/roeldev/demeuk"
    fi
fi

# -------------------------------------------------------
# 6. Check Perl (usually pre-installed on Debian/Ubuntu)
# -------------------------------------------------------
echo ""
echo -e "[6/6] Checking Perl..."
if has_cmd perl; then
    echo -e "  ${GREEN}✓${NC} Found Perl: $(perl -v 2>&1 | head -2 | tail -1 | sed 's/^[[:space:]]*//')"
else
    echo "  Installing perl..."
    sudo apt-get install -y perl >/dev/null 2>&1
    echo -e "  ${GREEN}✓${NC} Perl installed."
fi

# -------------------------------------------------------
# Summary
# -------------------------------------------------------
echo ""
echo "============================================================"
echo "  Setup Complete!"
echo "============================================================"
echo ""
echo "  Run the toolkit:"
echo "    ./CrackersToolkit"
echo ""
echo "  Or from source:"
echo "    pip install PyQt6"
echo "    python3 crackers_toolkit/main.py"
echo ""
echo "  The app will auto-detect tools on startup."
echo "  Use Settings to manually configure paths if needed."
echo ""
