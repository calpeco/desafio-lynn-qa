<#
.SYNOPSIS
  Cria o .venv, instala as dependências (app + test) e o Chromium do Playwright, no Windows.
  Equivalente ao setup.sh (Linux, macOS, Git Bash, WSL). Funciona no Windows PowerShell 5.1 e no PowerShell 7+.

.EXAMPLE
  .\setup.ps1
  .\setup.ps1 -SkipBrowser
  .\setup.ps1 -Recreate
  # Se a política de execução bloquear scripts:  setup.cmd   (ou)
  powershell -ExecutionPolicy Bypass -File .\setup.ps1
#>
[CmdletBinding()]
param(
  [switch]$SkipBrowser,          # não baixa o Chromium (só testes unitários, API e segurança)
  [switch]$Recreate,             # apaga e recria o .venv
  [switch]$SystemSitePackages,   # o .venv enxerga os pacotes do Python do sistema (ambiente sem rede)
  [switch]$WithDeps,             # aceito por simetria com o setup.sh; no Windows não há libs de sistema a instalar
  [string]$Python = $env:PYTHON  # força o interpretador (ex.: C:\Python312\python.exe)
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot   # raiz do repositório
$Venv = '.venv'

function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
  & $Exe @Arguments
  if ($LASTEXITCODE -ne 0) { throw "Falhou ($LASTEXITCODE): $Exe $($Arguments -join ' ')" }
}

# Um candidato vale se executar de verdade e for 3.11+. O "python.exe" da pasta WindowsApps
# é o atalho da Microsoft Store: só abre a loja, por isso é testado e não apenas localizado.
function Test-Python([string]$Exe, [string[]]$Prefix) {
  if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { return $false }
  try {
    & $Exe @Prefix -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)' 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
  } catch { return $false }
}

$candidates = @()
if ($Python) { $candidates += , @($Python) } else { $candidates += , @('py', '-3'); $candidates += , @('python'); $candidates += , @('python3') }
$py = $null
foreach ($c in $candidates) {
  $exe = $c[0]; $prefix = @($c | Select-Object -Skip 1)
  if (Test-Python $exe $prefix) { $py = @{ Exe = $exe; Prefix = $prefix }; break }
}
if (-not $py) {
  if ($Python) { throw "PYTHON=$Python não é Python 3.11+." }
  throw 'Python 3.11+ não encontrado. Instale em https://www.python.org/downloads/ (marque "Add python.exe to PATH") ou use: .\setup.ps1 -Python C:\caminho\python.exe'
}
$info = & $py.Exe @($py.Prefix) -c 'import sys; print(sys.version.split()[0], sys.executable)'
Write-Host "Sistema: windows · Python: $info"

# ---------------------------------------------------------------- .venv
$VenvPython = Join-Path $Venv 'Scripts\python.exe'
if ($Recreate -and (Test-Path $Venv)) { Write-Host "Removendo $Venv"; Remove-Item -Recurse -Force $Venv }
# Um .venv criado no Linux/WSL (.venv/bin) não serve no Windows: recria.
if ((Test-Path $Venv) -and -not (Test-Path $VenvPython)) {
  Write-Host "$Venv existente é de outro sistema ou está quebrado: recriando"; Remove-Item -Recurse -Force $Venv
}
if (-not (Test-Path $Venv)) {
  Write-Host "Criando $Venv"
  $venvArgs = @($py.Prefix) + @('-m', 'venv')
  if ($SystemSitePackages) { $venvArgs += '--system-site-packages' }
  Invoke-Checked $py.Exe ($venvArgs + @($Venv))
}

# ---------------------------------------------------------------- dependências
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Write-Warning 'Não foi possível atualizar o pip; seguindo com a versão atual.' }
Invoke-Checked $VenvPython @('-m', 'pip', 'install', '-r', 'requirements.txt')

if ($SkipBrowser) {
  Write-Host 'Chromium não instalado (-SkipBrowser): os cenários @ui não vão rodar.'
} else {
  Invoke-Checked $VenvPython @('-m', 'playwright', 'install', 'chromium')
}

Write-Host ''
Write-Host 'Pronto. Ative o ambiente com:'
Write-Host '  .venv\Scripts\Activate.ps1   (PowerShell)  ·  .venv\Scripts\activate.bat (cmd)'
Write-Host '  Se o PowerShell bloquear: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned'
Write-Host 'Depois: pytest  ·  behave --tags=@api  ·  python test\scripts\run_parallel.py'
