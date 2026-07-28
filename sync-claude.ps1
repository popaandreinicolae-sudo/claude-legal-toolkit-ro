<#
.SYNOPSIS
  Re-sincronizeaza in ~/.claude selectia curata de skill-uri si subagenti.

.DESCRIPTION
  De rulat dupa fiecare `git pull`.

  hooks/ NU apare aici: ~/.claude/scripts este un junction catre hooks/, deci
  cele doua cai arata acelasi director si nu pot derapa una fata de alta.

  skills/ si agents/ sunt copii reale, fiindca repo-ul contine si material care
  nu are ce cauta in configul global, 160 de subagenti fara legatura cu practica
  juridica (Roblox, Unity, marketing) si bundle-uri _official_* care dubleaza
  skill-uri deja integrate in Claude Code. Copierea in bloc din INSTALL.md le-ar
  aduce pe toate in contextul fiecarei sesiuni, asa ca lista de mai jos ramane
  explicita. Adauga aici orice skill sau subagent nou pe care il vrei instalat.

  Subagentii se reimprospateaza dupa ce e DEJA instalat in ~/.claude/agents, deci
  scriptul nu adauga nimic nou de capul lui. Un fisier prezent local dar absent
  din repo (scris de tine) se pastreaza si se raporteaza.
#>

$ErrorActionPreference = 'Stop'

$Toolkit = $PSScriptRoot
$Dest = Join-Path $env:USERPROFILE '.claude'

$Skills = @(
    'anti-hallucination-document'
    'anti-hallucination-energetic'
    'constitutional-law-ro'
    'cyber-law-ro'
    'docx-track-changes-review'
    'source-pack-grounding'
    'task-contract'
    'ub-drept-citation'
    'verificare-citari-gate'
)

Write-Host "`n=== SKILL-URI ===" -ForegroundColor Cyan
foreach ($s in $Skills) {
    $src = Join-Path $Toolkit "skills\$s"
    if (-not (Test-Path $src)) { Write-Host "  lipseste in repo: $s" -ForegroundColor Yellow; continue }
    Copy-Item -Recurse -Force $src (Join-Path $Dest 'skills\')
    Write-Host "  ok  $s"
}

Write-Host "`n=== SUBAGENTI (doar cei deja instalati) ===" -ForegroundColor Cyan
Get-ChildItem (Join-Path $Dest 'agents') -Filter *.md | ForEach-Object {
    $src = Join-Path $Toolkit "agents\$($_.Name)"
    if (Test-Path $src) {
        Copy-Item -Force $src $_.FullName
        Write-Host "  ok  $($_.Name)"
    } else {
        Write-Host "  local, absent din repo, pastrat: $($_.Name)" -ForegroundColor Yellow
    }
}

Write-Host "`n=== HOOKS ===" -ForegroundColor Cyan
$scripts = Join-Path $Dest 'scripts'
$item = Get-Item $scripts -ErrorAction SilentlyContinue
if ($item -and $item.LinkType -eq 'Junction') {
    Write-Host "  junction catre $($item.Target -join ', '), nimic de copiat"
} else {
    Write-Host "  ATENTIE: $scripts nu mai e junction, hook-urile pot derapa" -ForegroundColor Red
}

Write-Host "`nGata. Reporneste Claude Desktop ca serverele MCP sa reincarce codul.`n" -ForegroundColor Green
