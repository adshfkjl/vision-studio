import unittest
from unittest.mock import patch

from vision_studio.config import cors_allow_origins


class ConfigTests(unittest.TestCase):
    def test_cors_allow_origins_defaults_to_wildcard(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(cors_allow_origins(), ["*"])

    def test_cors_allow_origins_parses_comma_separated_values(self):
        with patch.dict(
            "os.environ",
            {"VISION_STUDIO_CORS_ORIGINS": "http://localhost:5174, https://demo.example.com"},
        ):
            self.assertEqual(cors_allow_origins(), ["http://localhost:5174", "https://demo.example.com"])


if __name__ == "__main__":
    unittest.main()
