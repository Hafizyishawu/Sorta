import time
import os
from sorta.scanner import FileScanner
from sorta.dormant_detector import DormantFileDetector

def test_find_dormant_files(tmp_path):
    # Create files: one large and old, one large and recent, one small and old
    old_time = time.time() - 200 * 24 * 60 * 60  # 200 days ago
    large_size = 150 * 1024 * 1024  # 150MB
    small_size = 1 * 1024 * 1024    # 1MB
    
    f1 = tmp_path / "large_old.txt"
    f1.write_bytes(b"0" * large_size)
    f2 = tmp_path / "large_recent.txt"
    f2.write_bytes(b"0" * large_size)
    f3 = tmp_path / "small_old.txt"
    f3.write_bytes(b"0" * small_size)
    
    # Set access/modify times
    os.utime(f1, (old_time, old_time))
    os.utime(f3, (old_time, old_time))
    
    scanner = FileScanner(str(tmp_path))
    files = scanner.scan()
    detector = DormantFileDetector(files, size_threshold=100*1024*1024, days_dormant=180)
    dormant_files = detector.find_dormant_files()
    paths = [os.path.basename(f['path']) for f in dormant_files]
    assert "large_old.txt" in paths
    assert "large_recent.txt" not in paths
    assert "small_old.txt" not in paths
