$ErrorActionPreference = "Stop"

$projectRoot = (Get-Location).Path

function Invoke-Step {
    param(
        [string]$Label,
        [string[]]$Arguments
    )

    Write-Host "==> $Label"
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Label"
    }
}

Push-Location $projectRoot
try {
    Invoke-Step "Merge Markdown from src/ via main.md" @((Join-Path $PSScriptRoot "merge_md.py"))
    Invoke-Step "Number merged Markdown" @((Join-Path $PSScriptRoot "number_md.py"))
    Invoke-Step "Export DOCX" @((Join-Path $PSScriptRoot "export_docx.py"))
    Write-Host ""
    Write-Host "Word export complete: build/docx/paper.docx"
}
finally {
    Pop-Location
}
