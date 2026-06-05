import os
from collections import Counter, defaultdict

def get_recommendations(files_metadata):
    recs = []
    # Largest files
    largest = sorted(files_metadata, key=lambda x: x['size'], reverse=True)[:5]
    if largest:
        recs.append({
            'type': 'largest_files',
            'files': largest
        })
    # File type breakdown
    ext_counter = Counter([f['extension'] for f in files_metadata])
    recs.append({
        'type': 'file_type_breakdown',
        'breakdown': ext_counter.most_common()
    })
    # Dormant files
    import time
    now = time.time()
    dormant = [f for f in files_metadata if (now - f['last_accessed']) > 180*24*3600 and f['size'] > 50*1024*1024]
    if dormant:
        recs.append({
            'type': 'dormant_files',
            'files': dormant
        })
    # Duplicates by hash
    from sorta.duplicate_finder import DuplicateFinder
    dups = DuplicateFinder(files_metadata).find_duplicates()
    if dups:
        recs.append({
            'type': 'duplicate_groups',
            'groups': dups
        })
    # Largest folders
    folder_sizes = defaultdict(int)
    for f in files_metadata:
        folder = os.path.dirname(f['path'])
        folder_sizes[folder] += f['size']
    largest_folders = sorted(folder_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
    recs.append({
        'type': 'largest_folders',
        'folders': largest_folders
    })
    return recs
