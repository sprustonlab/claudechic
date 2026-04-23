#!/bin/bash
set -euo pipefail

# =============================================================================
# claudechic -- setup (Linux / macOS)
#
# One-liner install:
#   curl -fsSL https://raw.githubusercontent.com/sprustonlab/claudechic/main/install.sh | bash
# =============================================================================

echo ""
echo "==================================================="
echo "  claudechic -- setup"
echo "==================================================="
echo ""

# ─── Step 1: Check git ──────────────────────────────────────────────────────
if ! command -v git &> /dev/null; then
    echo "git is required but not found."
    echo ""

    # Determine install method
    _git_install_cmd=""
    _git_manual_hint=""
    case "$(uname -s)" in
        Darwin*)
            if command -v brew &> /dev/null; then
                _git_install_cmd="brew install git"
            else
                _git_manual_hint="  Install via Homebrew (brew install git) or Xcode (xcode-select --install)"
            fi
            ;;
        Linux*)
            if command -v module &> /dev/null; then
                # HPC environment -- don't offer auto-install
                echo "  HPC environment detected. Load git with your module system:"
                echo "    module load git"
                echo ""
                echo "Then re-run this installer."
                exit 1
            elif command -v apt-get &> /dev/null; then
                _git_install_cmd="sudo apt-get install -y git"
            elif command -v dnf &> /dev/null; then
                _git_install_cmd="sudo dnf install -y git"
            else
                _git_manual_hint="  Install from: https://git-scm.com/downloads"
            fi
            ;;
    esac

    if [[ -n "$_git_install_cmd" ]]; then
        echo "  Will run: $_git_install_cmd"
        read -rp "Install git? [Y/n] " _answer < /dev/tty
        _answer="${_answer:-Y}"
        if [[ "$_answer" =~ ^[Yy] ]]; then
            $_git_install_cmd || {
                echo ""
                echo "Error: git installation failed."
                echo "  Install manually: https://git-scm.com/downloads"
                exit 1
            }
        else
            echo ""
            echo "  Install git manually:"
            echo "    $_git_install_cmd"
            echo "    -- or --"
            echo "    https://git-scm.com/downloads"
            echo ""
            echo "Then re-run this installer."
            exit 1
        fi
    else
        echo "$_git_manual_hint"
        echo ""
        echo "Then re-run this installer."
        exit 1
    fi
fi

# ─── Step 2: Check / install uv ─────────────────────────────────────────────
if ! command -v uv &> /dev/null; then
    echo "uv (Python package manager) is required but not found."
    echo ""
    echo "  Will run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    read -rp "Install uv? [Y/n] " _answer < /dev/tty
    _answer="${_answer:-Y}"
    if [[ "$_answer" =~ ^[Yy] ]]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh || {
            echo ""
            echo "Error: uv installation failed."
            echo "  Install manually: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        }
        # uv installer puts binary in ~/.local/bin (or ~/.cargo/bin on some systems)
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        echo ""
    else
        echo ""
        echo "  Install uv manually:"
        echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "    -- or --"
        echo "    https://docs.astral.sh/uv/getting-started/installation/"
        echo ""
        echo "Then re-run this installer."
        exit 1
    fi
fi

if ! command -v uv &> /dev/null; then
    echo "Error: uv was installed but not found on PATH."
    echo ""
    echo "  Add to your shell profile:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "  Then restart your shell and re-run this installer."
    exit 1
fi

echo "  uv $(uv --version 2>/dev/null || echo '(version unknown)')"

# ─── Step 3: Install claudechic ─────────────────────────────────────────────
echo ""
echo "Installing claudechic..."
uv tool install git+https://github.com/sprustonlab/claudechic || {
    echo ""
    echo "Error: failed to install claudechic."
    echo "  Try manually: uv tool install git+https://github.com/sprustonlab/claudechic"
    exit 1
}

# ─── Step 4: Verify installation ────────────────────────────────────────────
echo ""
if command -v claudechic &> /dev/null; then
    echo "  claudechic $(claudechic --version 2>/dev/null || echo '(installed)')"
else
    # uv tool bin dir may not be on PATH yet
    UV_TOOL_BIN="$(uv tool dir 2>/dev/null)/../bin"
    if [[ -x "$UV_TOOL_BIN/claudechic" ]]; then
        echo "  claudechic installed, but not on PATH."
    else
        echo "  claudechic installed, but the binary was not found on PATH."
    fi
    echo ""
    echo "  Add the uv tool directory to your PATH:"
    echo ""
    SHELL_NAME="$(basename "${SHELL:-/bin/bash}")"
    case "$SHELL_NAME" in
        zsh)
            echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
            echo "    source ~/.zshrc"
            ;;
        fish)
            echo "    fish_add_path ~/.local/bin"
            ;;
        *)
            echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
            echo "    source ~/.bashrc"
            ;;
    esac
    echo ""
    echo "  Then verify with: claudechic --version"
    echo ""
fi

# ─── Step 5: Check Claude Code CLI ──────────────────────────────────────────
echo ""
if ! command -v claude &> /dev/null; then
    echo "Claude Code is not installed."
    echo ""
    if ! command -v npm &> /dev/null; then
        echo "  Step 1 -- Install Node.js (needed for npm):"
        case "$(uname -s)" in
            Darwin*)
                echo "    brew install node"
                ;;
            Linux*)
                if command -v apt-get &> /dev/null; then
                    echo "    sudo apt-get install nodejs npm"
                elif command -v dnf &> /dev/null; then
                    echo "    sudo dnf install nodejs npm"
                elif command -v module &> /dev/null; then
                    echo "    module load nodejs"
                else
                    echo "    See https://nodejs.org/en/download"
                fi
                ;;
        esac
        echo ""
        echo "  Step 2 -- Install Claude Code:"
    fi
    echo "    npm install -g @anthropic-ai/claude-code"
    echo "    claude /login"
else
    # Claude is installed -- check version and auth
    CLAUDE_VERSION="$(claude --version 2>/dev/null || echo '')"
    if [[ -n "$CLAUDE_VERSION" ]]; then
        echo "  Claude Code $CLAUDE_VERSION"
        # Warn if version looks old (pre-1.x)
        MAJOR="$(echo "$CLAUDE_VERSION" | grep -oP '^\d+' || echo '')"
        if [[ -n "$MAJOR" && "$MAJOR" -lt 1 ]]; then
            echo "  Warning: your Claude Code version may be outdated."
            echo "    Update with: npm update -g @anthropic-ai/claude-code"
        fi
    fi

    CLAUDE_AUTH="$(claude auth status 2>/dev/null || echo '{"loggedIn": false}')"
    if echo "$CLAUDE_AUTH" | grep -q '"loggedIn": false'; then
        echo ""
        echo "  Claude Code is installed but not logged in."
        echo "    claude /login"
    fi
fi

# ─── Step 6: Done ───────────────────────────────────────────────────────────
echo ""
echo "==================================================="
echo "  Setup complete!"
echo "==================================================="
echo ""
echo "  Next steps:"
echo "    cd your-project"
echo "    claudechic"
echo ""
