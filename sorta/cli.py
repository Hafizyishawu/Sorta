import argparse
import os
from sorta.scanner import FileScanner
from sorta.duplicate_finder import DuplicateFinder
from sorta.dormant_detector import DormantFileDetector
from sorta.organizer import FileOrganizer
from sorta.trash_manager import TrashManager
from sorta.recommendations import get_recommendations
from sorta.scheduler import Scheduler, ScheduleError, SAFE_COMMANDS


def prompt_yes_no(question):
    while True:
        try:
            ans = input(f"{question} [y/n]: ").strip().lower()
        except EOFError:
            # No interactive input available. Default to the safe answer for
            # destructive prompts rather than crashing with a traceback.
            print("no (no input)")
            return False
        if ans in ('y', 'yes'):
            return True
        if ans in ('n', 'no'):
            return False
        print("Please enter 'y' or 'n'.")

def show_duplicates(files, apply=False, strict_names=False, base_dir=None, trash_manager=None, include_empty=False):
    finder = DuplicateFinder(files, strict_names=strict_names, include_empty=include_empty)
    duplicates = finder.find_duplicates()
    if not duplicates:
        print("No duplicate files found.")
        return
    print(f"Found {sum(len(group)-1 for group in duplicates)} duplicate files in {len(duplicates)} groups:")
    deleted = 0
    for i, group in enumerate(duplicates, 1):
        print(f"  Group {i}:")
        for idx, file in enumerate(group):
            print(f"    [{idx}] {file['path']} ({file['size']} bytes)")
        if apply:
            keep_idx = 0
            print("Select the file to keep (default 0): ", end='')
            try:
                keep_idx = int(input().strip() or '0')
            except Exception:
                keep_idx = 0
            for idx, file in enumerate(group):
                if idx != keep_idx:
                    if prompt_yes_no(f"Delete {file['path']}?"):
                        try:
                            if trash_manager:
                                trash_manager.move_to_trash(file['path'])
                                print(f"Moved {file['path']} to trash")
                            else:
                                os.remove(file['path'])
                                print(f"Deleted {file['path']}")
                            deleted += 1
                        except Exception as e:
                            print(f"Error deleting {file['path']}: {e}")
    if apply:
        print(f"Deleted {deleted} duplicate files (moved to trash if enabled).")


def show_dormant(files, size_threshold, days_dormant, apply=False, trash_manager=None):
    detector = DormantFileDetector(files, size_threshold=size_threshold, days_dormant=days_dormant)
    dormant_files = detector.find_dormant_files()
    if not dormant_files:
        print("No large dormant files found.")
        return
    print(f"Found {len(dormant_files)} large dormant files:")
    deleted = 0
    for file in dormant_files:
        print(f"  {file['path']} | {file['size']//(1024*1024)} MB | Last accessed: {file['last_accessed']}")
        if apply:
            if prompt_yes_no(f"Delete {file['path']}?"):
                try:
                    if trash_manager:
                        trash_manager.move_to_trash(file['path'])
                        print(f"Moved {file['path']} to trash")
                    else:
                        os.remove(file['path'])
                        print(f"Deleted {file['path']}")
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting {file['path']}: {e}")
    if apply:
        print(f"Deleted {deleted} dormant files (moved to trash if enabled).")


def show_organization(files, base_dir, apply=False):
    organizer = FileOrganizer(files, base_dir)
    suggestions = organizer.get_organization_suggestions()
    if not suggestions:
        print("No files to organize.")
        return
    print(f"Suggest moving {len(suggestions)} files:")
    moved = 0
    for s in suggestions:
        print(f"  {s['source']} -> {s['target']}  [{s['category']}]" )
        if apply:
            if prompt_yes_no(f"Move {s['source']} to {s['target']}?"):
                try:
                    if os.path.exists(s['target']):
                        # os.rename overwrites the destination silently. Refuse
                        # rather than destroy an existing file at the target.
                        print(f"Skipped {s['source']}: target already exists ({s['target']})")
                        continue
                    os.makedirs(os.path.dirname(s['target']), exist_ok=True)
                    os.rename(s['source'], s['target'])
                    print(f"Moved {s['source']} -> {s['target']}")
                    moved += 1
                except OSError as e:
                    print(f"Error moving {s['source']}: {e}")
    if apply:
        print(f"Moved {moved} files.")


def handle_schedule(args):
    scheduler = Scheduler()
    try:
        if args.list_jobs:
            jobs = scheduler.list_scheduled()
            if not jobs:
                print("No scheduled sorta entries.")
            else:
                print("Scheduled sorta entries:")
                for job in jobs:
                    print(f"  {job}")
            return
        if args.remove:
            count = scheduler.remove(dry_run=args.dry_run)
            if args.dry_run:
                print(f"Would remove {count} scheduled sorta entr{'y' if count == 1 else 'ies'}.")
            else:
                print(f"Removed {count} scheduled sorta entr{'y' if count == 1 else 'ies'}.")
            return
        if not args.cron:
            print("Specify --cron to install a schedule, --list to view, or --remove to delete.")
            return
        line = scheduler.install(args.cron, args.directory, args.run, dry_run=args.dry_run)
        if args.dry_run:
            print("Would install crontab entry:")
            print(f"  {line}")
        else:
            print("Installed crontab entry:")
            print(f"  {line}")
    except ScheduleError as e:
        print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description='Sorta - Smart Filesystem Manager')
    parser.add_argument('directory', help='Directory to scan')
    parser.add_argument('--hidden', action='store_true', help='Include hidden files (default: false)')
    parser.add_argument('--ignore', action='append', default=[], help='Glob pattern to ignore files or directories (can be used multiple times)')
    subparsers = parser.add_subparsers(dest='command', required=False)

    subparsers.add_parser('scan', help='Scan and show file count')
    dup_parser = subparsers.add_parser('show-duplicates', help='Show duplicate files')
    dup_parser.add_argument('--apply', action='store_true', help='Delete duplicates interactively (moved to trash)')
    dup_parser.add_argument('--strict-names', action='store_true', help='Only consider files as duplicates if both names and content match')
    dup_parser.add_argument('--include-empty', action='store_true', help='Also treat empty (zero-byte) files as duplicates of each other')
    dormant_parser = subparsers.add_parser('show-dormant', help='Show large dormant files')
    dormant_parser.add_argument('--size', type=int, default=100, help='Min size in MB (default: 100)')
    dormant_parser.add_argument('--days', type=int, default=180, help='Dormant days (default: 180)')
    dormant_parser.add_argument('--apply', action='store_true', help='Delete dormant files interactively (moved to trash)')
    org_parser = subparsers.add_parser('show-organization', help='Show file organization suggestions')
    org_parser.add_argument('--apply', action='store_true', help='Move files interactively (moved to trash)')
    restore_parser = subparsers.add_parser('restore', help='List and restore files from trash')
    restore_parser.add_argument('--list', action='store_true', help='List files in trash')
    restore_parser.add_argument('--file', type=str, help='Restore a specific trashed file by trash name')
    subparsers.add_parser('empty-trash', help='Permanently delete all files in trash')
    subparsers.add_parser('recommend', help='Show recommendations and insights')
    schedule_parser = subparsers.add_parser('schedule', help='Manage a scheduled sorta run via cron')
    schedule_parser.add_argument('--cron', type=str, help="Cron expression, e.g. '0 9 * * 1' for Mondays at 09:00")
    schedule_parser.add_argument('--run', type=str, default='recommend', choices=SAFE_COMMANDS,
                                 help='Command to run on schedule (read-only only; default: recommend)')
    schedule_parser.add_argument('--remove', action='store_true', help='Remove the scheduled sorta entry')
    schedule_parser.add_argument('--list', action='store_true', dest='list_jobs', help='List scheduled sorta entries')
    schedule_parser.add_argument('--dry-run', action='store_true', help='Show what would change without modifying crontab')

    args = parser.parse_args()
    scanner = FileScanner(args.directory, include_hidden=getattr(args, 'hidden', False), ignore_patterns=getattr(args, 'ignore', []))
    files = scanner.scan()
    if scanner.skipped:
        print(f"Warning: skipped {len(scanner.skipped)} unreadable path(s) (permission denied or unavailable). Results may be incomplete.")
    trash_manager = TrashManager(args.directory)

    if args.command == 'show-duplicates':
        show_duplicates(files, apply=getattr(args, 'apply', False), strict_names=getattr(args, 'strict_names', False), trash_manager=trash_manager, include_empty=getattr(args, 'include_empty', False))
    elif args.command == 'show-dormant':
        show_dormant(files, size_threshold=args.size*1024*1024, days_dormant=args.days, apply=getattr(args, 'apply', False), trash_manager=trash_manager)
    elif args.command == 'show-organization':
        show_organization(files, args.directory, apply=getattr(args, 'apply', False))
    elif args.command == 'restore':
        if args.list:
            idx = trash_manager.list_trash()
            if not idx:
                print("Trash is empty.")
            else:
                print("Files in trash:")
                for name, meta in idx.items():
                    print(f"  {name}: {meta['original_path']} (trashed at {meta['trashed_at']})")
        elif args.file:
            try:
                orig = trash_manager.restore(args.file)
                print(f"Restored {args.file} to {orig}")
            except Exception as e:
                print(f"Error restoring: {e}")
        else:
            print("Specify --list to view or --file to restore.")
    elif args.command == 'empty-trash':
        trash_manager.empty_trash()
        print("Trash emptied.")
    elif args.command == 'recommend':
        recs = get_recommendations(files)
        for rec in recs:
            if rec['type'] == 'largest_files':
                print("Largest files:")
                for f in rec['files']:
                    print(f"  {f['path']} ({f['size']} bytes)")
            elif rec['type'] == 'file_type_breakdown':
                print("File type breakdown:")
                for ext, count in rec['breakdown']:
                    print(f"  .{ext}: {count}")
            elif rec['type'] == 'dormant_files':
                print("Dormant files (>180d, >50MB):")
                for f in rec['files']:
                    print(f"  {f['path']} ({f['size']} bytes)")
            elif rec['type'] == 'duplicate_groups':
                print(f"Duplicate groups: {len(rec['groups'])}")
                for group in rec['groups']:
                    print("  Group:")
                    for f in group:
                        print(f"    {f['path']} ({f['size']} bytes)")
            elif rec['type'] == 'largest_folders':
                print("Largest folders:")
                for folder, size in rec['folders']:
                    print(f"  {folder}: {size} bytes")
    elif args.command == 'schedule':
        handle_schedule(args)
    else:
        print(f"Scanned {len(files)} files.")
        for f in files[:10]:
            print(f)

if __name__ == '__main__':
    main()
