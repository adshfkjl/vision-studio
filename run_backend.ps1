$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$deps = Join-Path $backend ".deps"
$env:PYTHONPATH = "$backend;$deps;$env:PYTHONPATH"
Set-Location $backend
python serve.py --reload
