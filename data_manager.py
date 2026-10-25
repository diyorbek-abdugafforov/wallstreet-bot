import json
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def read_json(filename: str, default: Any = None) -> Any:
    file_path = DATA_DIR / filename
    if not file_path.exists():
        return default if default is not None else []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Xatolik {filename} o'qishda: {e}")
        return default if default is not None else []

def write_json(filename: str, data: Any) -> bool:
    file_path = DATA_DIR / filename
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Xatolik {filename} yozishda: {e}")
        return False

# Tezkor yordamchi funksiyalar
def get_placement_test() -> List[Dict[str, Any]]:
    return read_json("placement_test.json", [])

def get_bonus_test() -> List[Dict[str, Any]]:
    return read_json("bonus_test.json", [])

def get_courses() -> List[Dict[str, Any]]:
    return read_json("courses.json", [])

def get_schedules() -> List[Dict[str, Any]]:
    return read_json("schedules.json", [])

def get_results() -> List[Dict[str, Any]]:
    return read_json("results.json", [])

def get_settings() -> Dict[str, Any]:
    return read_json("settings.json", {})
