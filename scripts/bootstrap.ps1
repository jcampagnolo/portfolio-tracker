param(
  [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
  Write-Host "`n==> $msg"
}

function Test-Command([string]$cmd) {
  return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

Write-Step "Bootstrapping virtual environment (.venv)"

if (-not (Test-Command $PythonCommand)) {
  Write-Host "Não encontrei '$PythonCommand' no PATH."
  Write-Host "Instale o Python 3.12+ e/ou habilite o alias no PATH, depois rode novamente:"
  Write-Host "  scripts\\bootstrap.ps1"
  Write-Host ""
  Write-Host "Dica (Windows): instale pelo python.org e marque 'Add python.exe to PATH'."
  exit 1
}

if (-not (Test-Path ".venv")) {
  Write-Step "Criando .venv"
  & $PythonCommand -m venv .venv
}

Write-Step "Ativando .venv"
& ".\\.venv\\Scripts\\Activate.ps1"

Write-Step "Atualizando pip"
python -m pip install --upgrade pip

if (Test-Path "requirements.txt") {
  Write-Step "Instalando dependências (requirements.txt)"
  pip install -r requirements.txt
}

Write-Step "Pronto"
python -c "import sys; print('Python:', sys.version); print('Executable:', sys.executable)"
