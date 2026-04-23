# =============================================================================
# claudechic -- setup (Windows)
#
# One-liner install:
#   irm https://raw.githubusercontent.com/sprustonlab/claudechic/main/install.ps1 | iex
# =============================================================================

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force 2>$null
$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==================================================="
Write-Host "  claudechic -- setup"
Write-Host "==================================================="
Write-Host ""

# --- Step 1: Check git ---------------------------------------------------------
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "git is required but not found." -ForegroundColor Yellow
    Write-Host ""
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  Will run: winget install --id Git.Git -e --source winget"
        $answer = Read-Host "Install git? [Y/n]"
        if (-not $answer) { $answer = "Y" }
        if ($answer -match '^[Yy]') {
            winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
            # Refresh PATH so git is available in this session
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
            if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
                Write-Host ""
                Write-Host "Error: git was installed but not found in PATH." -ForegroundColor Red
                Write-Host "  Restart PowerShell and re-run this installer."
                return
            }
            Write-Host "  git installed successfully." -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "  Install git manually:" -ForegroundColor Yellow
            Write-Host "    winget install --id Git.Git -e --source winget"
            Write-Host "    -- or --"
            Write-Host "    https://git-scm.com/downloads"
            Write-Host ""
            Write-Host "Then restart PowerShell and re-run this installer."
            return
        }
    } else {
        Write-Host "  Install from: https://git-scm.com/downloads" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Then restart PowerShell and re-run this installer."
        return
    }
}

# --- Step 2: Check / install uv ------------------------------------------------
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv (Python package manager) is required but not found." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Will run: irm https://astral.sh/uv/install.ps1 | iex"
    $answer = Read-Host "Install uv? [Y/n]"
    if (-not $answer) { $answer = "Y" }
    if ($answer -match '^[Yy]') {
        try {
            $uvInstaller = (Invoke-RestMethod https://astral.sh/uv/install.ps1)
            Invoke-Expression $uvInstaller
        } catch {
            Write-Host ""
            Write-Host "Error: uv installation failed." -ForegroundColor Red
            Write-Host "  Install manually: https://docs.astral.sh/uv/getting-started/installation/"
            return
        }
        # Refresh PATH to pick up newly installed uv
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "  Install uv manually:" -ForegroundColor Yellow
        Write-Host "    irm https://astral.sh/uv/install.ps1 | iex"
        Write-Host "    -- or --"
        Write-Host "    https://docs.astral.sh/uv/getting-started/installation/"
        Write-Host ""
        Write-Host "Then re-run this installer."
        return
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Error: uv was installed but not found on PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Restart PowerShell and re-run this installer."
    return
}

$uvVersion = try { uv --version 2>$null } catch { "(version unknown)" }
Write-Host "  uv $uvVersion"

# --- Step 3: Install claudechic ------------------------------------------------
Write-Host ""
Write-Host "Installing claudechic..."
uv tool install git+https://github.com/sprustonlab/claudechic
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Error: failed to install claudechic." -ForegroundColor Red
    Write-Host "  Try manually: uv tool install git+https://github.com/sprustonlab/claudechic"
    return
}

# --- Step 4: Verify installation ------------------------------------------------
Write-Host ""
$chicCmd = Get-Command claudechic -ErrorAction SilentlyContinue
if ($chicCmd) {
    $chicVersion = try { claudechic --version 2>$null } catch { "(installed)" }
    Write-Host "  claudechic $chicVersion"
} else {
    Write-Host "  claudechic installed, but not found on PATH." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  The uv tool directory may not be on your PATH."
    Write-Host "  Try restarting PowerShell, or add the directory manually:"
    Write-Host ""
    $uvToolBin = try { uv tool dir 2>$null | Split-Path -Parent } catch { "$env:USERPROFILE\.local\bin" }
    Write-Host "    `$env:PATH = `"$uvToolBin;`$env:PATH`""
    Write-Host ""
    Write-Host "  Then verify with: claudechic --version"
}

# --- Step 5: Check Claude Code CLI ----------------------------------------------
Write-Host ""
$claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claudeCmd) {
    Write-Host "Claude Code is not installed."
    Write-Host ""
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-Host "  Step 1 -- Install Node.js (needed for npm):" -ForegroundColor Yellow
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "    winget install OpenJS.NodeJS.LTS"
        } else {
            Write-Host "    Download from: https://nodejs.org/en/download"
        }
        Write-Host ""
        Write-Host "  Step 2 -- Restart PowerShell, then install Claude Code:" -ForegroundColor Yellow
    }
    Write-Host "    npm install -g @anthropic-ai/claude-code"
    Write-Host "    claude /login"
} else {
    # Claude is installed -- check version and auth
    $claudeVersion = try { claude --version 2>$null } catch { "" }
    if ($claudeVersion) {
        Write-Host "  Claude Code $claudeVersion"
        # Warn if version looks old (pre-1.x)
        if ($claudeVersion -match '^(\d+)') {
            $major = [int]$Matches[1]
            if ($major -lt 1) {
                Write-Host "  Warning: your Claude Code version may be outdated." -ForegroundColor Yellow
                Write-Host "    Update with: npm update -g @anthropic-ai/claude-code"
            }
        }
    }

    $claudeAuth = try { claude auth status 2>&1 | Out-String } catch { '{"loggedIn": false}' }
    if ($claudeAuth -match '"loggedIn":\s*false') {
        Write-Host ""
        Write-Host "  Claude Code is installed but not logged in."
        Write-Host "    claude /login"
    }
}

# --- Step 6: Done ---------------------------------------------------------------
Write-Host ""
Write-Host "==================================================="
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "==================================================="
Write-Host ""
Write-Host "  Next steps:"
Write-Host "    cd your-project"
Write-Host "    claudechic"
Write-Host ""
