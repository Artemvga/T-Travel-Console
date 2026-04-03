import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

USERS_FILE = Path(__file__).resolve().parent / "data" / "users" / "users_db.json"
FAVORITES_FILE = Path(__file__).resolve().parent / "data" / "users" / "favorites_db.json"


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    if not username:
        return False, "Логин не может быть пустым."
    if username.lower() == "adm":
        return False, "Этот логин зарезервирован."
    data = _load_json(USERS_FILE, {"users": []})
    for u in data["users"]:
        if u["username"].lower() == username.lower():
            return False, "Такой пользователь уже есть."
    data["users"].append(
        {"username": username, "password_hash": _hash_password(password), "role": "user"}
    )
    _save_json(USERS_FILE, data)
    return True, "Регистрация успешна."


def verify_login(username: str, password: str) -> bool:
    username = username.strip()
    data = _load_json(USERS_FILE, {"users": []})
    h = _hash_password(password)
    for u in data["users"]:
        if u["username"].lower() == username.lower() and u["password_hash"] == h:
            return True
    return False


def canonical_username(username: str) -> str:
    data = _load_json(USERS_FILE, {"users": []})
    un = username.strip()
    for u in data["users"]:
        if u["username"].lower() == un.lower():
            return u["username"]
    return un


def add_favorite_route(username: str, route_dict: dict) -> str:
    data = _load_json(FAVORITES_FILE, {"by_user": {}})
    if "by_user" not in data:
        data["by_user"] = {}
    if username not in data["by_user"]:
        data["by_user"][username] = []
    fav_id = str(uuid.uuid4())
    entry = {
        "id": fav_id,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "route": route_dict,
    }
    data["by_user"][username].append(entry)
    _save_json(FAVORITES_FILE, data)
    return fav_id


def list_favorites(username: str) -> list[dict]:
    data = _load_json(FAVORITES_FILE, {"by_user": {}})
    return list(data.get("by_user", {}).get(username, []))


def is_admin(username: str) -> bool:
    canon = canonical_username(username)
    data = _load_json(USERS_FILE, {"users": []})
    for u in data["users"]:
        if u["username"] == canon:
            return u.get("role", "user") == "admin"
    return False


def list_all_user_accounts() -> list[dict]:
    """Для админа: логины и роли, без паролей."""
    data = _load_json(USERS_FILE, {"users": []})
    return [
        {"username": u["username"], "role": u.get("role", "user")}
        for u in data["users"]
    ]


def remove_favorite(username: str, fav_id: str) -> bool:
    data = _load_json(FAVORITES_FILE, {"by_user": {}})
    items = data.get("by_user", {}).get(username)
    if not items:
        return False
    new_items = [x for x in items if x.get("id") != fav_id]
    if len(new_items) == len(items):
        return False
    data["by_user"][username] = new_items
    _save_json(FAVORITES_FILE, data)
    return True
