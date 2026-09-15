#!/usr/bin/env bash
# ==============================================================================
#  MAX AI Agent — Automated One-Line Installer
#  Supported OS: Linux (Debian, Ubuntu, Arch, Fedora, Alpine), macOS, Android (Termux)
# ==============================================================================

set -e

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}   ${BOLD}${GREEN}MAX AI Agent — Automated Installer for Linux & Terminal${NC}   ${CYAN}║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── 1. Detect Environment ───────────────────────────────────────────────────
INSTALL_DIR="${HOME}/.max-ai"
BIN_DIR="${HOME}/.local/bin"
REPO_URL="https://github.com/Karanztez/MAX.git"

echo -e "${BLUE}▶ [1/5] กำลังตรวจสอบสภาพแวดล้อมระบบ...${NC}"

is_termux=false
if [ -n "$TERMUX_VERSION" ] || [ -d "/data/data/com.termux" ]; then
    is_termux=true
    BIN_DIR="${PREFIX}/bin"
    echo -e "  • ตรวจพบสภาพแวดล้อม: ${YELLOW}Android (Termux)${NC}"
else
    echo -e "  • ตรวจพบสภาพแวดล้อม: ${YELLOW}$(uname -s) ($(uname -m))${NC}"
fi

# ─── 2. Check & Install Dependencies ──────────────────────────────────────────
echo -e "${BLUE}▶ [2/5] กำลังตรวจสอบ Python และเครื่องมือจำเป็น...${NC}"

install_package() {
    local pkg=$1
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -qq && sudo apt-get install -y -qq "$pkg"
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm "$pkg"
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y -q "$pkg"
    elif command -v apk >/dev/null 2>&1; then
        sudo apk add --no-cache "$pkg"
    elif command -v pkg >/dev/null 2>&1; then
        pkg install -y "$pkg"
    elif command -v brew >/dev/null 2>&1; then
        brew install "$pkg"
    fi
}

if ! command -v git >/dev/null 2>&1; then
    echo -e "  • ${YELLOW}กำลังติดตั้ง git...${NC}"
    install_package git
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "  • ${YELLOW}กำลังติดตั้ง python3...${NC}"
    install_package python3
fi

PYTHON_CMD="python3"
if ! command -v python3 >/dev/null 2>&1 && command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

# Check for python3-venv / virtualenv
if ! $PYTHON_CMD -m venv --help >/dev/null 2>&1; then
    echo -e "  • ${YELLOW}กำลังติดตั้ง python3-venv...${NC}"
    if [ "$is_termux" = false ]; then
        install_package python3-venv || true
    fi
fi

# ─── 3. Clone or Update Repository ───────────────────────────────────────────
echo -e "${BLUE}▶ [3/5] กำลังดาวน์โหลดซอร์สโค้ด MAX AI...${NC}"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "  • พบการติดตั้งเดิม กำลังอัปเดต (git pull)..."
    cd "$INSTALL_DIR"
    git fetch --all --tags -q
    git reset --hard origin/main -q
else
    echo -e "  • กำลังโคลน Repository มาที่ ${INSTALL_DIR}..."
    rm -rf "$INSTALL_DIR"
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" -q
    cd "$INSTALL_DIR"
fi

# ─── 4. Setup Python Virtual Environment ──────────────────────────────────────
echo -e "${BLUE}▶ [4/5] กำลังสร้าง Virtual Environment และติดตั้ง Dependencies...${NC}"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [ ! -d "$INSTALL_DIR/venv" ]; then
    $PYTHON_CMD -m venv "$INSTALL_DIR/venv" || $PYTHON_CMD -m virtualenv "$INSTALL_DIR/venv" || true
fi

if [ -f "$INSTALL_DIR/venv/bin/pip" ]; then
    PIP_CMD="$INSTALL_DIR/venv/bin/pip"
    PY_EXEC="$INSTALL_DIR/venv/bin/python"
else
    PIP_CMD="pip3"
    PY_EXEC="$PYTHON_CMD"
fi

$PIP_CMD install --upgrade pip -q 2>/dev/null || true
$PIP_CMD install -r requirements.txt -q 2>/dev/null || true
$PIP_CMD install -e . -q 2>/dev/null || true

# ─── 5. Create Executable Launcher ────────────────────────────────────────────
echo -e "${BLUE}▶ [5/5] กำลังสร้างคำสั่ง 'max' สำหรับเรียกใช้งานใน Terminal...${NC}"

mkdir -p "$BIN_DIR"

LAUNCHER_SCRIPT="$BIN_DIR/max"
cat << EOF > "$LAUNCHER_SCRIPT"
#!/usr/bin/env bash
if [ -f "$INSTALL_DIR/venv/bin/python" ]; then
    exec "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/main.py" "\$@"
else
    exec python3 "$INSTALL_DIR/main.py" "\$@"
fi
EOF

chmod +x "$LAUNCHER_SCRIPT"

# Ensure PATH contains BIN_DIR in shell profiles
add_to_path() {
    local profile_file=$1
    if [ -f "$profile_file" ]; then
        if ! grep -q "$BIN_DIR" "$profile_file"; then
            echo "" >> "$profile_file"
            echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$profile_file"
            echo -e "  • เพิ่ม ${BIN_DIR} ใน ${profile_file}"
        fi
    fi
}

if [ "$is_termux" = false ]; then
    add_to_path "${HOME}/.bashrc"
    add_to_path "${HOME}/.zshrc"
    add_to_path "${HOME}/.profile"
fi

# ─── Success Banner ───────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${BOLD}${GREEN}  ✨ การติดตั้ง MAX AI Agent สำเร็จเรียบร้อยแล้ว!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo -e "คุณสามารถเปิดใช้งาน MAX ได้ทันทีด้วยคำสั่ง:"
echo -e "  ${BOLD}${CYAN}max${NC}             - เปิดโหมด Terminal Interactive CLI"
echo -e "  ${BOLD}${CYAN}max -p \"คำถาม\"${NC}   - ถามคำถามเดียว (Single-shot prompt)"
echo -e "  ${BOLD}${CYAN}max --help${NC}      - ดูคำสั่งทั้งหมด"
echo ""
if [ "$is_termux" = false ] && [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}หมายเหตุ:${NC} หากพิมพ์ 'max' แล้วไม่พบคำสั่ง กรุณารัน: ${BOLD}source ~/.bashrc${NC} หรือเปิด Terminal ใหม่"
fi
echo ""
