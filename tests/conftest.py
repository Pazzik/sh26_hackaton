from pathlib import Path
import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "meridian_dwh"

@pytest.fixture(scope="session")
def data_dir() -> Path:
    assert DATA_DIR.exists(), f"нет каталога данных: {DATA_DIR}"
    return DATA_DIR
