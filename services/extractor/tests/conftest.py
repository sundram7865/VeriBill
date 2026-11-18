import shutil
import sys
from pathlib import Path

import pytest

# Make `tests.factories` importable regardless of how pytest is invoked.
SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


def pytest_collection_modifyitems(config, items):
    if shutil.which("tesseract"):
        return
    skip = pytest.mark.skip(reason="tesseract binary not installed")
    for item in items:
        if "ocr" in item.keywords:
            item.add_marker(skip)
