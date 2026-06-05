import os
import shlex
import shutil
import subprocess  # nosec B404 - fixed argv, no shell; see read_crontab/write_crontab
import sys
from typing import List, Optional

CRON_MARKER = "# sorta-scheduled"

SAFE_COMMANDS = ("scan", "recommend", "show-duplicates", "show-dormant", "show-organization")


class ScheduleError(Exception):
    pass


class Scheduler:
    """
    Manages a single sorta entry in the user's crontab.

    Only the current user's crontab is touched, and every managed line carries
    CRON_MARKER so install/remove are idempotent and never disturb unrelated
    entries. Scheduled commands are restricted to read-only actions: an
    unattended job must not delete files without a human to confirm the prompt.
    """

    def __init__(self, python_executable: Optional[str] = None, module: str = "sorta.cli"):
        self.python_executable = python_executable or sys.executable
        self.module = module

    def _crontab_bin(self) -> str:
        # Resolve to an absolute path so the binary is not taken from a
        # potentially attacker-controlled PATH.
        path = shutil.which("crontab")
        if not path:
            raise ScheduleError("crontab executable not found on PATH")
        return path

    def validate_cron(self, cron_expr: str) -> str:
        fields = cron_expr.split()
        if len(fields) != 5:
            raise ScheduleError(
                f"cron expression must have 5 fields (min hour day month weekday), got {len(fields)}: '{cron_expr}'"
            )
        return " ".join(fields)

    def build_line(self, cron_expr: str, directory: str, command: str) -> str:
        if command not in SAFE_COMMANDS:
            raise ScheduleError(
                f"'{command}' is not schedulable. Choose one of: {', '.join(SAFE_COMMANDS)}. "
                "Destructive actions are excluded because a scheduled run has no one to confirm prompts."
            )
        cron_expr = self.validate_cron(cron_expr)
        directory = os.path.abspath(directory)
        # A newline in the path would break out of this crontab line and inject
        # a second entry. shlex.quote does not neutralise newlines for crontab,
        # which is line-oriented, so reject them outright.
        if "\n" in directory or "\r" in directory:
            raise ScheduleError("directory path must not contain newline characters")
        invocation = (
            f"{shlex.quote(self.python_executable)} -m {self.module} "
            f"{shlex.quote(directory)} {command}"
        )
        return f"{cron_expr} {invocation} {CRON_MARKER}"

    def _strip_managed(self, lines: List[str]) -> List[str]:
        return [line for line in lines if CRON_MARKER not in line]

    def merge(self, existing_lines: List[str], new_line: str) -> List[str]:
        kept = self._strip_managed(existing_lines)
        kept.append(new_line)
        return kept

    def read_crontab(self) -> List[str]:
        result = subprocess.run(  # nosec B603 B607 - absolute path, fixed args, no shell, no user input in argv
            [self._crontab_bin(), "-l"], capture_output=True, text=True
        )
        if result.returncode != 0:
            # No crontab yet for this user is not an error.
            if "no crontab" in (result.stderr or "").lower():
                return []
            raise ScheduleError(f"could not read crontab: {result.stderr.strip()}")
        return [line for line in result.stdout.splitlines() if line.strip()]

    def write_crontab(self, lines: List[str]) -> None:
        payload = "\n".join(lines) + "\n" if lines else ""
        result = subprocess.run(  # nosec B603 B607 - absolute path, fixed args, no shell; cron content passed via stdin
            [self._crontab_bin(), "-"], input=payload, text=True, capture_output=True
        )
        if result.returncode != 0:
            raise ScheduleError(f"could not write crontab: {result.stderr.strip()}")

    def install(self, cron_expr: str, directory: str, command: str, dry_run: bool = False) -> str:
        line = self.build_line(cron_expr, directory, command)
        if dry_run:
            return line
        merged = self.merge(self.read_crontab(), line)
        self.write_crontab(merged)
        return line

    def remove(self, dry_run: bool = False) -> int:
        existing = self.read_crontab()
        managed = [line for line in existing if CRON_MARKER in line]
        if dry_run:
            return len(managed)
        if managed:
            self.write_crontab(self._strip_managed(existing))
        return len(managed)

    def list_scheduled(self) -> List[str]:
        return [line for line in self.read_crontab() if CRON_MARKER in line]
