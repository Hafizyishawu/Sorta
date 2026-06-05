import os
import mimetypes
import json
from typing import List, Dict

import fnmatch

class FileScanner:
    """
    Recursively scans directories and collects metadata about files.
    """
    def __init__(self, root_dir: str, include_hidden: bool = False, ignore_patterns=None, config_path=None):
        self.root_dir = root_dir
        self.include_hidden = include_hidden
        # Config is loaded from a caller-controlled location, never from inside
        # the directory being scanned. Reading config from the scan target would
        # let an untrusted tree dictate its own ignore rules and hide files.
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'default_config.json')
        config_patterns = []
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    config_patterns = config.get('ignore_patterns', [])
            except (OSError, ValueError) as e:
                print(f"Warning: could not load config {config_path}: {e}")
        self.ignore_patterns = (ignore_patterns or []) + config_patterns
        self.skipped = []

    def is_hidden(self, path: str) -> bool:
        # Hidden if any part of the path (file or folder) starts with a dot
        for part in os.path.normpath(path).split(os.sep):
            if part.startswith('.'):
                return True
        return False

    def is_ignored(self, path: str) -> bool:
        # Patterns are matched against both the full path and the basename, so a
        # basename pattern like '~$*' or '*.tmp' matches regardless of how deep
        # the file sits in the tree.
        basename = os.path.basename(path)
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(basename, pattern):
                return True
        return False

    def scan(self) -> List[Dict]:
        files_metadata = []
        # os.walk swallows directory-level errors by default, so a directory the
        # process cannot read (e.g. macOS privacy restrictions) would silently
        # produce no results. Record them instead so callers can surface it.
        def on_walk_error(error):
            self.skipped.append((getattr(error, 'filename', self.root_dir), str(error)))
        for dirpath, _, filenames in os.walk(self.root_dir, onerror=on_walk_error):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if not self.include_hidden and self.is_hidden(filepath):
                    continue
                if self.is_ignored(filepath):
                    continue
                try:
                    stat = os.stat(filepath)
                    size = stat.st_size
                    last_accessed = stat.st_atime
                    last_modified = stat.st_mtime
                    mime_type, _ = mimetypes.guess_type(filepath)
                    ext = os.path.splitext(filename)[1].lower()
                    files_metadata.append({
                        'path': filepath,
                        'size': size,
                        'last_accessed': last_accessed,
                        'last_modified': last_modified,
                        'extension': ext,
                        'mime_type': mime_type,
                    })
                except OSError as e:
                    # Unreadable files (permissions, broken symlinks, races) are
                    # skipped but reported rather than swallowed silently.
                    self.skipped.append((filepath, str(e)))
                    continue
        return files_metadata
