$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$deps = Join-Path $backend ".deps"
$gpuEnv = if ($env:VISION_STUDIO_GPU_CONDA_ENV) { $env:VISION_STUDIO_GPU_CONDA_ENV } else { "vision-studio-gpu" }
$forceCpu = $env:VISION_STUDIO_FORCE_CPU -eq "1"

function Test-VisionStudioGpuEnv {
    param(
        [string]$EnvName
    )

    if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
        Write-Host "[Vision Studio] conda not found; falling back to bundled CPU dependencies."
        return $false
    }

    $probe = @'
import sys
try:
    import torch
    ok = bool(torch.cuda.is_available())
    print("CUDA_AVAILABLE=" + ("1" if ok else "0"))
    print("TORCH=" + getattr(torch, "__version__", "unknown"))
    print("PYTHON=" + sys.executable)
    print("CUDA_DEVICE=" + (torch.cuda.get_device_name(0) if ok else "none"))
except Exception as exc:
    print("CUDA_AVAILABLE=0")
    print("ERROR=" + repr(exc))
'@
    $probeFile = Join-Path $env:TEMP "vision-studio-gpu-probe.py"
    Set-Content -LiteralPath $probeFile -Value $probe -Encoding UTF8

    $output = conda run -n $EnvName python $probeFile 2>&1
    Remove-Item -LiteralPath $probeFile -Force -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Vision Studio] GPU env '$EnvName' probe failed; falling back to bundled CPU dependencies."
        $output | ForEach-Object { Write-Host "[Vision Studio] $_" }
        return $false
    }

    $output | ForEach-Object { Write-Host "[Vision Studio] $_" }
    return [bool]($output -match "CUDA_AVAILABLE=1")
}

Set-Location $backend

if (-not $forceCpu -and (Test-VisionStudioGpuEnv -EnvName $gpuEnv)) {
    Write-Host "[Vision Studio] Starting backend with GPU conda env '$gpuEnv'."
    $env:VISION_STUDIO_USE_BUNDLED_DEPS = "0"
    $env:PYTHONPATH = "$backend"
    conda run -n $gpuEnv python serve.py --reload
} else {
    if ($forceCpu) {
        Write-Host "[Vision Studio] VISION_STUDIO_FORCE_CPU=1; starting backend with bundled CPU dependencies."
    } else {
        Write-Host "[Vision Studio] Starting backend with bundled CPU dependencies."
    }
    $env:VISION_STUDIO_USE_BUNDLED_DEPS = "1"
    $env:PYTHONPATH = "$backend;$deps"
    python serve.py --reload
}
