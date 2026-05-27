import unittest

from vision_studio.devices import devices_from_torch
from vision_studio.train_runner import resolve_training_device


class FakeCuda:
    def __init__(self, available: bool) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def device_count(self) -> int:
        return 2 if self.available else 0

    def get_device_name(self, index: int) -> str:
        return f"GPU-{index}"


class FakeTorch:
    def __init__(self, available: bool) -> None:
        self.cuda = FakeCuda(available)


class DeviceTests(unittest.TestCase):
    def test_devices_recommend_first_gpu_when_cuda_is_available(self) -> None:
        info = devices_from_torch(FakeTorch(True))

        self.assertTrue(info["cuda_available"])
        self.assertEqual(info["recommended"], "0")
        self.assertEqual(info["devices"][1]["name"], "GPU-0")

    def test_auto_training_device_resolves_to_recommended_gpu(self) -> None:
        self.assertEqual(resolve_training_device({"device": "auto"}, {"recommended": "0"}), "0")
        self.assertEqual(resolve_training_device({"device": ""}, {"recommended": "cpu"}), "cpu")
        self.assertEqual(resolve_training_device({"device": "cpu"}, {"recommended": "0"}), "cpu")


if __name__ == "__main__":
    unittest.main()
