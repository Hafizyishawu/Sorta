import os
import hashlib
from typing import List, Dict, DefaultDict
from collections import defaultdict

class DuplicateFinder:
    """
    Finds duplicate files in the given list of file metadata using hash comparison.
    """
    def __init__(self, files_metadata: List[Dict], strict_names: bool = False, include_empty: bool = False):
        self.files_metadata = files_metadata
        self.strict_names = strict_names
        self.include_empty = include_empty

    @staticmethod
    def hash_file(filepath: str, chunk_size: int = 8192) -> str:
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def find_duplicates(self) -> List[List[Dict]]:
        size_map: DefaultDict[int, List[Dict]] = defaultdict(list)
        for file in self.files_metadata:
            # Empty files all share the same hash, so unrelated zero-byte files
            # would be reported as duplicates of each other. Excluded by default.
            if file['size'] == 0 and not self.include_empty:
                continue
            size_map[file['size']].append(file)
        # Only check files with same size
        if self.strict_names:
            # Group by (hash, basename)
            hash_map: DefaultDict[tuple, List[Dict]] = defaultdict(list)
            for files in size_map.values():
                if len(files) < 2:
                    continue
                for file in files:
                    file_hash = self.hash_file(file['path'])
                    if file_hash:
                        key = (file_hash, os.path.basename(file['path']))
                        hash_map[key].append(file)
            return [group for group in hash_map.values() if len(group) > 1]
        else:
            hash_map: DefaultDict[str, List[Dict]] = defaultdict(list)
            for files in size_map.values():
                if len(files) < 2:
                    continue
                for file in files:
                    file_hash = self.hash_file(file['path'])
                    if file_hash:
                        hash_map[file_hash].append(file)
            return [group for group in hash_map.values() if len(group) > 1]
