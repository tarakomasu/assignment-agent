$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Assert-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE" } }
function Download-Verified($Url, $Target, $Hash) {
    Invoke-WebRequest -Uri $Url -OutFile $Target
    if ((Get-FileHash $Target -Algorithm SHA256).Hash.ToLower() -ne $Hash) {
        throw "SHA256 mismatch: $Target"
    }
}

python -m PyInstaller --noconfirm --clean --onedir --name assignment-agent `
    --collect-all playwright --collect-all docx --collect-all pypdf main.py
Assert-Exit
$release = Join-Path (Get-Location) "dist/assignment-agent"
$runtime = Join-Path $release "runtime"
New-Item -ItemType Directory -Force "$runtime/node", "$runtime/gemini", "$runtime/browsers", "$release/input", "$release/licenses" | Out-Null
Copy-Item (Get-Command node).Source "$runtime/node/node.exe"
Copy-Item scripts/gemini/package*.json "$runtime/gemini/"
Push-Location "$runtime/gemini"
npm ci --omit=optional --ignore-scripts
Assert-Exit
Pop-Location
# The CLI is fully bundled and optional native terminal/keychain modules are not required.
Copy-Item "$runtime/gemini/node_modules/@google/gemini-cli/bundle/LICENSE" "$release/licenses/Gemini-CLI-LICENSE" -ErrorAction SilentlyContinue

$env:PLAYWRIGHT_BROWSERS_PATH = "$runtime/browsers"
python -m playwright install chromium
Assert-Exit

$compilerAsset = "build/w64devkit.7z.exe"
New-Item -ItemType Directory -Force build | Out-Null
Download-Verified "https://github.com/skeeto/w64devkit/releases/download/v2.10.0/w64devkit-x64-2.10.0.7z.exe" `
    $compilerAsset "18d0a4c71a166f8401ab6305781bec5882b40b5e06ba9807c61cb5f3b3c6325e"
7z x $compilerAsset "-o$runtime" -y | Out-Null
Assert-Exit
if (-not (Test-Path "$runtime/w64devkit/bin/gcc.exe")) { throw "Compiler extraction failed" }
# Distribute the exact corresponding compiler source alongside the binaries.
Download-Verified "https://github.com/skeeto/w64devkit/releases/download/v2.10.0/source.tar" `
    "dist/w64devkit-2.10.0-source.tar" "1e7a789bbc3ec58a2717b7a9069acec6a5abc58e38fa3a4dc801f22fc986e3a4"

Copy-Item README.md, LICENSE, THIRD_PARTY.md $release
Invoke-WebRequest "https://raw.githubusercontent.com/nodejs/node/$(node --version)/LICENSE" -OutFile "$release/licenses/Node-LICENSE"
Invoke-WebRequest "https://raw.githubusercontent.com/google-gemini/gemini-cli/v0.47.0/LICENSE" -OutFile "$release/licenses/Gemini-CLI-LICENSE"
$pythonVersion = python -c "import platform; print(platform.python_version())"
Invoke-WebRequest "https://raw.githubusercontent.com/python/cpython/v$pythonVersion/LICENSE" -OutFile "$release/licenses/Python-LICENSE"
python scripts/collect_licenses.py "$release/licenses"
Assert-Exit

& "$release/assignment-agent.exe" doctor
Assert-Exit
python scripts/smoke_release.py $release
Assert-Exit
Compress-Archive -Path $release -DestinationPath "dist/assignment-agent-windows-x64.zip" -Force
$hashes = Get-FileHash "dist/assignment-agent-windows-x64.zip", "dist/w64devkit-2.10.0-source.tar" -Algorithm SHA256
$hashes | ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path $_.Path -Leaf)" } | Set-Content dist/SHA256SUMS.txt
