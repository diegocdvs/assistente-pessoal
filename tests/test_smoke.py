from __future__ import annotations

from scripts.smoke import find_report, strip_log_prefix, strip_log_prefixes


def test_strip_log_prefix_removes_timestamp_and_stream_prefix():
    line = '2026-07-08T14:30:01.123456Z stdout F   "finished_at": "2026-07-08T14:30:01Z",'

    assert strip_log_prefix(line) == '"finished_at": "2026-07-08T14:30:01Z",'


def test_find_report_from_prefixed_fragmented_cloud_logs():
    logs = """
2026-07-08T14:30:00.000000Z stdout F 2026-07-08 14:30:00 INFO Gmail retornou 10 mensagens para conta pessoal_google
2026-07-08T14:30:01.000000Z stderr F Regional Access Boundary HTTP request failed...
2026-07-08T14:30:01.000001Z stderr F Gaia id not found...
2026-07-08T14:30:02.000000Z stdout F {
2026-07-08T14:30:02.000001Z stdout F   "finished_at": "2026-07-08T14:30:02Z",
2026-07-08T14:30:02.000002Z stdout F   "dry_run": true,
2026-07-08T14:30:02.000003Z stdout F   "report": {
2026-07-08T14:30:02.000004Z stdout F     "total": 10,
2026-07-08T14:30:02.000005Z stdout F     "errors": [],
2026-07-08T14:30:02.000006Z stdout F     "total_by_category": {
2026-07-08T14:30:02.000007Z stdout F       "financeiro": 1,
2026-07-08T14:30:02.000008Z stdout F       "outros": 9
2026-07-08T14:30:02.000009Z stdout F     },
2026-07-08T14:30:02.000010Z stdout F     "total_by_priority": {
2026-07-08T14:30:02.000011Z stdout F       "normal": 9,
2026-07-08T14:30:02.000012Z stdout F       "alta": 1
2026-07-08T14:30:02.000013Z stdout F     },
2026-07-08T14:30:02.000014Z stdout F     "planned_actions": [
2026-07-08T14:30:02.000015Z stdout F       {"type": "review_financial", "dry_run": true}
2026-07-08T14:30:02.000016Z stdout F     ]
2026-07-08T14:30:02.000017Z stdout F   }
2026-07-08T14:30:02.000018Z stdout F }
"""

    report = find_report(logs)

    assert report is not None
    assert report["total"] == 10
    assert report["errors"] == []
    assert report["total_by_category"] == {"financeiro": 1, "outros": 9}
    assert report["planned_actions"] == [{"type": "review_financial", "dry_run": True}]


def test_find_report_accepts_empty_planned_actions():
    logs = """
2026-07-08T14:30:02Z stdout F {
2026-07-08T14:30:02Z stdout F   "finished_at": "2026-07-08T14:30:02Z",
2026-07-08T14:30:02Z stdout F   "dry_run": true,
2026-07-08T14:30:02Z stdout F   "report": {
2026-07-08T14:30:02Z stdout F     "total": 10,
2026-07-08T14:30:02Z stdout F     "errors": [],
2026-07-08T14:30:02Z stdout F     "total_by_category": {},
2026-07-08T14:30:02Z stdout F     "total_by_priority": {"normal": 10},
2026-07-08T14:30:02Z stdout F     "planned_actions": []
2026-07-08T14:30:02Z stdout F   }
2026-07-08T14:30:02Z stdout F }
"""

    report = find_report(logs)

    assert report is not None
    assert report["planned_actions"] == []
    assert report["total_by_priority"] == {"normal": 10}


def test_find_report_keeps_working_with_plain_json():
    logs = '{\n  "finished_at": "now",\n  "dry_run": true,\n  "report": {"total": 1, "errors": []}\n}'

    assert find_report(strip_log_prefixes(logs)) == {"total": 1, "errors": []}
