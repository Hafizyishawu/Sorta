import pytest
from sorta.scheduler import Scheduler, ScheduleError, CRON_MARKER


@pytest.fixture
def scheduler():
    return Scheduler(python_executable="/usr/bin/python3")


def test_validate_cron_accepts_five_fields(scheduler):
    assert scheduler.validate_cron("0 9 * * 1") == "0 9 * * 1"


def test_validate_cron_rejects_wrong_field_count(scheduler):
    with pytest.raises(ScheduleError):
        scheduler.validate_cron("0 9 * *")


def test_build_line_includes_marker_and_command(scheduler, tmp_path):
    line = scheduler.build_line("0 9 * * 1", str(tmp_path), "recommend")
    assert line.startswith("0 9 * * 1 ")
    assert line.endswith(CRON_MARKER)
    assert "-m sorta.cli" in line
    assert "recommend" in line


def test_build_line_rejects_destructive_command(scheduler, tmp_path):
    with pytest.raises(ScheduleError):
        scheduler.build_line("0 9 * * 1", str(tmp_path), "empty-trash")


def test_build_line_with_report_appends_json_log(scheduler, tmp_path):
    log = tmp_path / "sorta.log"
    line = scheduler.build_line("0 9 * * 1", str(tmp_path), "recommend", report=str(log))
    assert "--json" in line
    assert ">>" in line and "sorta.log" in line
    assert "2>&1" in line
    assert line.endswith(CRON_MARKER)


def test_build_line_rejects_newline_in_report(scheduler, tmp_path):
    with pytest.raises(ScheduleError):
        scheduler.build_line("0 9 * * 1", str(tmp_path), "recommend", report="/tmp/evil\n0 0 * * * x")


def test_build_line_quotes_directory_with_spaces(scheduler, tmp_path):
    spaced = tmp_path / "my files"
    spaced.mkdir()
    line = scheduler.build_line("0 9 * * 1", str(spaced), "scan")
    assert "'" in line and "my files" in line


def test_build_line_rejects_newline_in_directory(scheduler):
    with pytest.raises(ScheduleError):
        scheduler.build_line("0 9 * * 1", "/tmp/evil\n0 0 * * * rm -rf ~", "scan")


def test_merge_replaces_existing_managed_line(scheduler):
    existing = [
        "0 0 * * * /other/job",
        f"0 8 * * * old sorta {CRON_MARKER}",
    ]
    new_line = f"0 9 * * 1 new sorta {CRON_MARKER}"
    merged = scheduler.merge(existing, new_line)

    assert "0 0 * * * /other/job" in merged
    assert new_line in merged
    assert sum(1 for line in merged if CRON_MARKER in line) == 1


def test_merge_preserves_unrelated_entries(scheduler):
    existing = ["* * * * * unrelated_one", "@daily unrelated_two"]
    new_line = f"0 9 * * 1 sorta {CRON_MARKER}"
    merged = scheduler.merge(existing, new_line)

    assert "* * * * * unrelated_one" in merged
    assert "@daily unrelated_two" in merged
    assert new_line in merged
