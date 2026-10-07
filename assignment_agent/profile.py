import json

from .gemini import state_root
from .models import AgentError


def save_profile(name, student_id):
    if not name.strip() or len(name) > 100 or not student_id.strip() or len(student_id) > 50:
        raise AgentError("氏名と学籍番号を入力してください。")
    root = state_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "profile.json"
    path.write_text(json.dumps({"name": name.strip(), "student_id": student_id.strip()}, ensure_ascii=False), encoding="utf-8")


def load_profile():
    path = state_root() / "profile.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or any(not isinstance(value.get(k), str) for k in ("name", "student_id")):
            raise ValueError()
        return {"name": value["name"], "student_id": value["student_id"]}
    except (ValueError, OSError) as exc:
        raise AgentError("提出者情報を読み取れません。profileコマンドで設定し直してください。") from exc
