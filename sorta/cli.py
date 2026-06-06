import argparse
import os
from sorta.scanner import FileScanner
from sorta.duplicate_finder import DuplicateFinder
from sorta.dormant_detector import DormantFileDetector
from sorta.organizer import FileOrganizer
from sorta.trash_manager import TrashManager, SEND2TRASH_AVAILABLE
from sorta.recommendations import get_recommendations
from sorta.scheduler import Scheduler, ScheduleError, SAFE_COMMANDS
from sorta import render


def prompt_yes_no(question, assume_yes=False):
    if assume_yes:
        # Echo the auto-confirmed action so -y still leaves an audit trail of
        # what was acted on rather than silently destroying.
        print(f"{question} [y/n]: y (auto)")
        return True
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

def show_duplicates(files, apply=False, strict_names=False, base_dir=None, trash_manager=None, include_empty=False, assume_yes=False, as_json=False, plain=False, dry_run=False):
    finder = DuplicateFinder(files, strict_names=strict_names, include_empty=include_empty)
    duplicates = finder.find_duplicates()
    render.render_duplicates(duplicates, plain=plain, as_json=as_json)
    if as_json or not duplicates:
        return
    if dry_run:
        # Keeps index 0 in each group, would delete the rest (same rule as -y).
        rows = [(file['path'],) for group in duplicates for file in group[1:]]
        render.render_apply_summary(
            f"[dry-run] Would delete {len(rows)} duplicate file(s) (to trash).",
            items=rows, columns=[("Would delete", "left")], plain=plain, border_style="yellow",
        )
        return
    if not apply:
        return
    deleted_rows = []
    for i, group in enumerate(duplicates, 1):
        keep_idx = 0
        if assume_yes:
            # Keep the first file in each group, delete the rest to trash.
            print(f"Group {i}: keeping index 0 (auto)")
        else:
            print(f"Group {i}: select the file to keep (default 0): ", end='')
            try:
                keep_idx = int(input().strip() or '0')
            except Exception:
                keep_idx = 0
        for idx, file in enumerate(group):
            if idx != keep_idx:
                if prompt_yes_no(f"Delete {file['path']}?", assume_yes=assume_yes):
                    try:
                        if trash_manager:
                            trash_manager.move_to_trash(file['path'])
                        else:
                            os.remove(file['path'])
                        deleted_rows.append((file['path'],))
                    except Exception as e:
                        print(f"Error deleting {file['path']}: {e}")
    render.render_apply_summary(
        f"Deleted {len(deleted_rows)} duplicate file(s) (to trash).",
        items=deleted_rows,
        columns=[("Trashed", "left")],
        plain=plain,
    )


def show_dormant(files, size_threshold, days_dormant, apply=False, trash_manager=None, assume_yes=False, as_json=False, plain=False, dry_run=False):
    detector = DormantFileDetector(files, size_threshold=size_threshold, days_dormant=days_dormant)
    dormant_files = detector.find_dormant_files()
    render.render_dormant(dormant_files, plain=plain, as_json=as_json)
    if as_json or not dormant_files:
        return
    if dry_run:
        # The findings table above already lists every dormant file that would
        # go, so just show the summary panel.
        render.render_apply_summary(
            f"[dry-run] Would delete {len(dormant_files)} dormant file(s) (to trash).",
            plain=plain, border_style="yellow",
        )
        return
    if not apply:
        return
    deleted_rows = []
    for file in dormant_files:
        if prompt_yes_no(f"Delete {file['path']}?", assume_yes=assume_yes):
            try:
                if trash_manager:
                    trash_manager.move_to_trash(file['path'])
                else:
                    os.remove(file['path'])
                deleted_rows.append((file['path'],))
            except Exception as e:
                print(f"Error deleting {file['path']}: {e}")
    render.render_apply_summary(
        f"Deleted {len(deleted_rows)} dormant file(s) (to trash).",
        items=deleted_rows,
        columns=[("Trashed", "left")],
        plain=plain,
    )


def show_organization(files, base_dir, apply=False, assume_yes=False, as_json=False, plain=False, dry_run=False):
    organizer = FileOrganizer(files, base_dir)
    suggestions = organizer.get_organization_suggestions()
    render.render_organization(suggestions, plain=plain, as_json=as_json)
    if as_json or not suggestions:
        return
    if dry_run:
        move_rows = []
        for s in suggestions:
            if os.path.exists(s['target']):
                print(f"[dry-run] Would skip {s['source']}: target exists ({s['target']})")
            else:
                move_rows.append((s['source'], s['target']))
        render.render_apply_summary(
            f"[dry-run] Would move {len(move_rows)} file(s).",
            items=move_rows, columns=[("From", "left"), ("To", "left")], plain=plain, border_style="yellow",
        )
        return
    if not apply:
        return
    moved_rows = []
    for s in suggestions:
        if prompt_yes_no(f"Move {s['source']} to {s['target']}?", assume_yes=assume_yes):
            try:
                if os.path.exists(s['target']):
                    # os.rename overwrites the destination silently. Refuse
                    # rather than destroy an existing file at the target.
                    print(f"Skipped {s['source']}: target already exists ({s['target']})")
                    continue
                os.makedirs(os.path.dirname(s['target']), exist_ok=True)
                os.rename(s['source'], s['target'])
                moved_rows.append((s['source'], s['target']))
            except OSError as e:
                print(f"Error moving {s['source']}: {e}")
    render.render_apply_summary(
        f"Moved {len(moved_rows)} file(s).",
        items=moved_rows,
        columns=[("From", "left"), ("To", "left")],
        plain=plain,
    )


def show_delete(files, keywords, apply=False, trash_manager=None, assume_yes=False, dry_run=False, plain=False):
    # Refuse to act without a filter: an empty keyword list would otherwise match
    # and delete every scanned file. This is the guardrail against a fat-finger
    # `delete --apply` wiping a directory.
    keywords = [k for k in (keywords or []) if k]
    if not keywords:
        print("Specify at least one --match keyword. Refusing to delete without a filter.")
        return
    lowered = [k.lower() for k in keywords]
    matches = [
        f for f in files
        if any(k in os.path.basename(f['path']).lower() for k in lowered)
    ]
    quoted = ', '.join(repr(k) for k in keywords)
    if not matches:
        print(f"No files match {quoted}.")
        return
    total = sum(f['size'] for f in matches)
    print(f"{len(matches)} file(s) match {quoted} ({total} bytes):")
    for f in matches:
        print(f"  {f['path']} ({f['size']} bytes)")
    if dry_run:
        # The match list above already enumerates everything that would go.
        render.render_apply_summary(
            f"[dry-run] Would delete {len(matches)} file(s) (to trash).",
            plain=plain, border_style="yellow",
        )
        return
    if not apply:
        print("Preview only. Re-run with --apply to delete (to trash).")
        return
    deleted_rows = []
    for f in matches:
        if prompt_yes_no(f"Delete {f['path']}?", assume_yes=assume_yes):
            try:
                if trash_manager:
                    trash_manager.move_to_trash(f['path'])
                else:
                    os.remove(f['path'])
                deleted_rows.append((f['path'],))
            except OSError as e:
                print(f"Error deleting {f['path']}: {e}")
    render.render_apply_summary(
        f"Deleted {len(deleted_rows)} file(s) (to trash).",
        items=deleted_rows,
        columns=[("Trashed", "left")],
        plain=plain,
    )


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
        line = scheduler.install(args.cron, args.directory, args.run, dry_run=args.dry_run, report=getattr(args, 'report', None))
        if args.dry_run:
            print("Would install crontab entry:")
            print(f"  {line}")
        else:
            print("Installed crontab entry:")
            print(f"  {line}")
    except ScheduleError as e:
        print(f"Error: {e}")


def main():
    # Global options live on a shared parent so they are accepted both before
    # and after the subcommand (argparse otherwise routes post-subcommand flags
    # to the subparser, which would reject them). SUPPRESS defaults stop the
    # subparser's copy from overwriting a value already set at the top level.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--hidden', action='store_true', default=argparse.SUPPRESS, help='Include hidden files (default: false)')
    common.add_argument('--ignore', action='append', default=argparse.SUPPRESS, help='Glob pattern to ignore files or directories (can be used multiple times)')
    common.add_argument('--json', action='store_true', default=argparse.SUPPRESS, help='Emit machine-readable JSON instead of formatted output')
    common.add_argument('--plain', action='store_true', default=argparse.SUPPRESS, help='Force plain-text output, disabling rich formatting')
    common.add_argument('--limit', type=int, default=argparse.SUPPRESS, help='Max files to list in scan output (default: 10; ignored with --all)')
    common.add_argument('--all', action='store_true', dest='show_all', default=argparse.SUPPRESS, help='List every file in scan output, no cap')
    common.add_argument('-y', '--yes', action='store_true', dest='assume_yes', default=argparse.SUPPRESS, help='Assume yes to all prompts (deletions still go to trash; does not affect empty-trash)')
    common.add_argument('--sorta-trash', action='store_true', dest='sorta_trash', default=argparse.SUPPRESS, help="Use sorta's recoverable internal trash instead of the native OS Trash")

    parser = argparse.ArgumentParser(description='Sorta - Smart Filesystem Manager', parents=[common])
    parser.add_argument('directory', help='Directory to scan')
    subparsers = parser.add_subparsers(dest='command', required=False)

    subparsers.add_parser('scan', parents=[common], help='Scan and show file count')
    dup_parser = subparsers.add_parser('show-duplicates', parents=[common], help='Show duplicate files')
    dup_parser.add_argument('--apply', action='store_true', help='Delete duplicates interactively (moved to trash)')
    dup_parser.add_argument('--strict-names', action='store_true', help='Only consider files as duplicates if both names and content match')
    dup_parser.add_argument('--include-empty', action='store_true', help='Also treat empty (zero-byte) files as duplicates of each other')
    dup_parser.add_argument('--dry-run', action='store_true', help='Show what --apply would delete, without doing it')
    dormant_parser = subparsers.add_parser('show-dormant', parents=[common], help='Show large dormant files')
    dormant_parser.add_argument('--size', type=int, default=100, help='Min size in MB (default: 100)')
    dormant_parser.add_argument('--days', type=int, default=180, help='Dormant days (default: 180)')
    dormant_parser.add_argument('--apply', action='store_true', help='Delete dormant files interactively (moved to trash)')
    dormant_parser.add_argument('--dry-run', action='store_true', help='Show what --apply would delete, without doing it')
    org_parser = subparsers.add_parser('show-organization', parents=[common], help='Show file organization suggestions')
    org_parser.add_argument('--apply', action='store_true', help='Move files interactively (moved to trash)')
    org_parser.add_argument('--dry-run', action='store_true', help='Show what --apply would move, without doing it')
    delete_parser = subparsers.add_parser('delete', parents=[common], help='Delete files whose name matches a keyword (to trash)')
    delete_parser.add_argument('--match', action='append', default=[], help='Keyword to match in the filename (repeatable; matches any). Case-insensitive substring.')
    delete_parser.add_argument('--apply', action='store_true', help='Actually delete matches to trash; without it, only previews')
    delete_parser.add_argument('--dry-run', action='store_true', help='Show what --apply would delete, without doing it')
    restore_parser = subparsers.add_parser('restore', parents=[common], help='List and restore files from trash')
    restore_parser.add_argument('--list', action='store_true', help='List files in trash')
    restore_parser.add_argument('--file', type=str, help='Restore a specific trashed file by trash name')
    subparsers.add_parser('empty-trash', parents=[common], help='Permanently delete all files in trash')
    subparsers.add_parser('recommend', parents=[common], help='Show recommendations and insights')
    schedule_parser = subparsers.add_parser('schedule', parents=[common], help='Manage a scheduled sorta run via cron')
    schedule_parser.add_argument('--cron', type=str, help="Cron expression, e.g. '0 9 * * 1' for Mondays at 09:00")
    schedule_parser.add_argument('--run', type=str, default='recommend', choices=SAFE_COMMANDS,
                                 help='Command to run on schedule (read-only only; default: recommend)')
    schedule_parser.add_argument('--report', type=str, help='Append each run\'s JSON output to this log file (audit trail)')
    schedule_parser.add_argument('--remove', action='store_true', help='Remove the scheduled sorta entry')
    schedule_parser.add_argument('--list', action='store_true', dest='list_jobs', help='List scheduled sorta entries')
    schedule_parser.add_argument('--dry-run', action='store_true', help='Show what would change without modifying crontab')

    args = parser.parse_args()
    scanner = FileScanner(args.directory, include_hidden=getattr(args, 'hidden', False), ignore_patterns=getattr(args, 'ignore', []))
    with render.scan_progress() as progress:
        files = scanner.scan(progress_callback=progress.update)
    if scanner.skipped:
        print(f"Warning: skipped {len(scanner.skipped)} unreadable path(s) (permission denied or unavailable). Results may be incomplete.")
    want_os_trash = not getattr(args, 'sorta_trash', False)
    destructive = {'show-duplicates', 'show-dormant', 'show-organization', 'delete'}
    if want_os_trash and not SEND2TRASH_AVAILABLE and args.command in destructive:
        print("Note: 'send2trash' not installed - using sorta's internal trash. "
              "Install requirements-optional.txt for native macOS Trash, or pass --sorta-trash to silence this.")
    trash_manager = TrashManager(args.directory, use_os_trash=want_os_trash)

    assume_yes = getattr(args, 'assume_yes', False)
    as_json = getattr(args, 'json', False)
    plain = getattr(args, 'plain', False)
    dry_run = getattr(args, 'dry_run', False)
    if args.command == 'show-duplicates':
        show_duplicates(files, apply=getattr(args, 'apply', False), strict_names=getattr(args, 'strict_names', False), trash_manager=trash_manager, include_empty=getattr(args, 'include_empty', False), assume_yes=assume_yes, as_json=as_json, plain=plain, dry_run=dry_run)
    elif args.command == 'show-dormant':
        show_dormant(files, size_threshold=args.size*1024*1024, days_dormant=args.days, apply=getattr(args, 'apply', False), trash_manager=trash_manager, assume_yes=assume_yes, as_json=as_json, plain=plain, dry_run=dry_run)
    elif args.command == 'show-organization':
        show_organization(files, args.directory, apply=getattr(args, 'apply', False), assume_yes=assume_yes, as_json=as_json, plain=plain, dry_run=dry_run)
    elif args.command == 'delete':
        show_delete(files, keywords=getattr(args, 'match', []), apply=getattr(args, 'apply', False), trash_manager=trash_manager, assume_yes=assume_yes, dry_run=dry_run, plain=plain)
    elif args.command == 'restore':
        if args.list:
            idx = trash_manager.list_trash()
            if not idx:
                if trash_manager.use_os_trash:
                    print("Trash is empty. Native macOS Trash is in use; recover deleted files from Finder's Trash with Put Back.")
                else:
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
        render.render_recommendations(get_recommendations(files), plain=plain, as_json=as_json)
    elif args.command == 'schedule':
        handle_schedule(args)
    else:
        render.render_scan(
            files,
            limit=getattr(args, 'limit', None),
            show_all=getattr(args, 'show_all', False),
            plain=plain,
            as_json=as_json,
        )

if __name__ == '__main__':
    main()
