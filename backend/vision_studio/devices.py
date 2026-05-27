from __future__ import annotations

from typing import Any


def devices_from_torch(torch_module: Any | None) -> dict[str, Any]:
    devices = [{"id": "auto", "name": "Auto (GPU first)", "kind": "auto"}]
    cuda_available = False
    if torch_module is not None:
        try:
            cuda_available = bool(torch_module.cuda.is_available())
        except Exception:
            cuda_available = False
    if cuda_available:
        count = int(torch_module.cuda.device_count())
        for index in range(count):
            try:
                name = str(torch_module.cuda.get_device_name(index))
            except Exception:
                name = f"CUDA {index}"
            devices.append({"id": str(index), "name": name, "kind": "cuda"})
    devices.append({"id": "cpu", "name": "CPU", "kind": "cpu"})
    return {
        "cuda_available": cuda_available,
        "recommended": "0" if cuda_available else "cpu",
        "devices": devices,
    }


def available_devices() -> dict[str, Any]:
    try:
        import torch
    except Exception:
        torch = None
    return devices_from_torch(torch)
