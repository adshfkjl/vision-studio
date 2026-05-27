$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$env:VISION_STUDIO_USE_BUNDLED_DEPS = "0"
$env:PYTHONPATH = "$backend"
Set-Location $backend
conda run -n vision-studio-gpu python serve.py --reload
