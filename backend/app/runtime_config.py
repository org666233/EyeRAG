"""运行时配置覆盖（进程存活期内有效，重启后从文件恢复）"""
import json
from pathlib import Path

_overrides: dict = {}
_persist_path = Path("data/runtime_config.json")


def _apply_to_settings():
    if not _overrides:
        return
    try:
        from app.config import get_settings
        s = get_settings()
        for k, v in _overrides.items():
            if hasattr(s, k):
                object.__setattr__(s, k, v)
    except Exception:
        pass


def _load():
    global _overrides
    if _persist_path.exists():
        try:
            _overrides = json.loads(_persist_path.read_text(encoding="utf-8"))
            _apply_to_settings()
        except Exception:
            _overrides = {}


def set_values(updates: dict):
    _overrides.update(updates)
    _persist_path.parent.mkdir(parents=True, exist_ok=True)
    _persist_path.write_text(json.dumps(_overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    _apply_to_settings()


def get_all() -> dict:
    return dict(_overrides)


_load()
