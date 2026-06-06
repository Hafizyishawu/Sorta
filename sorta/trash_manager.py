import os
import shutil
import json
from datetime import datetime

try:
    from send2trash import send2trash as _os_send2trash
    SEND2TRASH_AVAILABLE = True
except ImportError:
    # send2trash is optional. Without it, deletions fall back to the internal
    # recoverable trash so a delete always has an undo path. The name is still
    # defined so use_os_trash gating (and tests) can reference it.
    _os_send2trash = None
    SEND2TRASH_AVAILABLE = False

TRASH_DIR_NAME = ".sorta_trash"
TRASH_INDEX = "index.json"

class TrashManager:
    def __init__(self, base_dir, use_os_trash=True):
        self.base_dir = base_dir
        # Native OS trash (Finder on macOS) is the default so deleted files land
        # in the system Trash where users expect them. It is only active when the
        # optional send2trash dependency is installed; otherwise we silently use
        # the internal trash, which is always recoverable via `restore`.
        self.use_os_trash = use_os_trash and SEND2TRASH_AVAILABLE
        self.trash_dir = os.path.join(base_dir, TRASH_DIR_NAME)
        self.index_path = os.path.join(self.trash_dir, TRASH_INDEX)
        if not self.use_os_trash:
            os.makedirs(self.trash_dir, exist_ok=True)
            if not os.path.exists(self.index_path):
                with open(self.index_path, 'w') as f:
                    json.dump({}, f)

    def _load_index(self):
        # The internal index may not exist when OS trash is in use. Treat a
        # missing index as an empty trash rather than raising.
        if not os.path.exists(self.index_path):
            return {}
        with open(self.index_path, 'r') as f:
            return json.load(f)

    def _save_index(self, idx):
        with open(self.index_path, 'w') as f:
            json.dump(idx, f, indent=2)

    def move_to_trash(self, file_path):
        if self.use_os_trash:
            # Finder then owns the file (recover via Put Back), so there is no
            # internal index entry to track. abspath because send2trash resolves
            # relative paths against the process cwd, not the scanned directory.
            _os_send2trash(os.path.abspath(file_path))
            return None
        fname = os.path.basename(file_path)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        idx = self._load_index()
        # The timestamp has one-second resolution, so two files with the same
        # basename trashed in the same second would collide. A colliding name
        # would overwrite both the trashed bytes and the index entry, making the
        # first file unrecoverable. Guarantee a unique name before moving.
        trash_name = f"{timestamp}_{fname}"
        suffix = 1
        while trash_name in idx or os.path.exists(os.path.join(self.trash_dir, trash_name)):
            trash_name = f"{timestamp}_{suffix}_{fname}"
            suffix += 1
        trash_path = os.path.join(self.trash_dir, trash_name)
        shutil.move(file_path, trash_path)
        idx[trash_name] = {
            'original_path': file_path,
            'trashed_at': timestamp
        }
        self._save_index(idx)
        return trash_path

    def list_trash(self):
        idx = self._load_index()
        return idx

    def restore(self, trash_name):
        idx = self._load_index()
        if trash_name not in idx:
            raise ValueError("File not found in trash.")
        trash_path = os.path.join(self.trash_dir, trash_name)
        orig_path = idx[trash_name]['original_path']
        if os.path.exists(orig_path):
            # shutil.move would overwrite whatever now occupies the original
            # path. Refuse so a restore never destroys a newer file.
            raise ValueError(f"cannot restore: a file already exists at {orig_path}")
        os.makedirs(os.path.dirname(orig_path), exist_ok=True)
        shutil.move(trash_path, orig_path)
        del idx[trash_name]
        self._save_index(idx)
        return orig_path

    def empty_trash(self):
        idx = self._load_index()
        for trash_name in list(idx.keys()):
            trash_path = os.path.join(self.trash_dir, trash_name)
            if os.path.exists(trash_path):
                os.remove(trash_path)
            del idx[trash_name]
        self._save_index(idx)
