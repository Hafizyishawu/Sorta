import os
import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, DefaultDict
from collections import defaultdict


class DuplicateFinder:
    """
    Finds duplicate files in the given list of file metadata using hash comparison.

    Two optimisations keep this fast on large directories without changing which
    files are reported:
      1. A first-chunk "quick hash" pre-filter. Files that share a size but
         differ in their first chunk cannot be identical, so they are never
         fully hashed. This avoids reading large files end-to-end just to rule
         them out.
      2. Hashing is run across a thread pool. Hashing is dominated by file I/O,
         which releases the GIL, so threads give real parallelism here.
    """

    def __init__(self, files_metadata: List[Dict], strict_names: bool = False,
                 include_empty: bool = False, max_workers: int = None):
        self.files_metadata = files_metadata
        self.strict_names = strict_names
        self.include_empty = include_empty
        self.max_workers = max_workers

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

    @staticmethod
    def quick_hash(filepath: str, chunk_size: int = 8192) -> str:
        # Hash only the first chunk. A cheap necessary-but-not-sufficient test:
        # if two same-size files differ here, they are definitely not duplicates.
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                hasher.update(f.read(chunk_size))
            return hasher.hexdigest()
        except Exception:
            return None

    def _hash_many(self, files: List[Dict], hash_fn) -> Dict[str, str]:
        paths = [f['path'] for f in files]
        if not paths:
            return {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            return dict(zip(paths, executor.map(hash_fn, paths)))

    def find_duplicates(self) -> List[List[Dict]]:
        size_map: DefaultDict[int, List[Dict]] = defaultdict(list)
        for file in self.files_metadata:
            # Empty files all share the same hash, so unrelated zero-byte files
            # would be reported as duplicates of each other. Excluded by default.
            if file['size'] == 0 and not self.include_empty:
                continue
            size_map[file['size']].append(file)

        # Only files that share a size with at least one other file can be dupes.
        candidates = [f for files in size_map.values() if len(files) >= 2 for f in files]
        if not candidates:
            return []

        # Stage 1: quick (first-chunk) hash, keyed with size to stay within
        # same-size groups. Only buckets with a collision proceed.
        quick = self._hash_many(candidates, self.quick_hash)
        prelim: DefaultDict[tuple, List[Dict]] = defaultdict(list)
        for f in candidates:
            qh = quick.get(f['path'])
            if qh is not None:
                prelim[(f['size'], qh)].append(f)

        to_full = [f for group in prelim.values() if len(group) >= 2 for f in group]
        if not to_full:
            return []

        # Stage 2: full hash only the files that survived the pre-filter.
        full = self._hash_many(to_full, self.hash_file)
        result_map: DefaultDict = defaultdict(list)
        for f in to_full:
            file_hash = full.get(f['path'])
            if file_hash is None:
                continue
            # strict_names also requires identical basenames to be a duplicate.
            key = (file_hash, os.path.basename(f['path'])) if self.strict_names else file_hash
            result_map[key].append(f)
        return [group for group in result_map.values() if len(group) > 1]
