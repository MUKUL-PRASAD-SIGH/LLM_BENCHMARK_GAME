import json
import os

DB_FILE = "avatar_db.json"

class AvatarDB:
    """
    Handles persisting user avatars to a simple local JSON file.
    No need for external databases for the MVP.
    """
    def __init__(self):
        self.db_path = DB_FILE
        if not os.path.exists(self.db_path):
            self._save_disk({})
            
    def _load_disk(self):
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_disk(self, data):
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=4)
            
    def save_avatar(self, user_id: int, config: dict):
        data = self._load_disk()
        data[str(user_id)] = config
        self._save_disk(data)
            
    def get_avatar(self, user_id: int):
        data = self._load_disk()
        return data.get(str(user_id))

db = AvatarDB()
