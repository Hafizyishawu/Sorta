import time
from typing import List, Dict

class DormantFileDetector:
    """
    Detects large, dormant files (not accessed for a long time).
    """
    def __init__(self, files_metadata: List[Dict], size_threshold: int = 100 * 1024 * 1024, days_dormant: int = 180):
        """
        :param files_metadata: List of file metadata dicts
        :param size_threshold: Minimum size in bytes (default 100MB)
        :param days_dormant: Number of days since last access (default 180 days)
        """
        self.files_metadata = files_metadata
        self.size_threshold = size_threshold
        self.days_dormant = days_dormant

    def find_dormant_files(self) -> List[Dict]:
        now = time.time()
        dormant_files = []
        for file in self.files_metadata:
            if file['size'] >= self.size_threshold:
                days_since_access = (now - file['last_accessed']) / (60 * 60 * 24)
                if days_since_access >= self.days_dormant:
                    dormant_files.append(file)
        return dormant_files
