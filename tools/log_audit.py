"""

PPDL - Prediksi Pemakaian Daya Listrik
PPDL - Electrical Power Consumption Prediction

Academic Project Title:
Prediksi Pemakaian Daya Listrik Pada Rumah Tangga di Jakarta Berbasis IoT
dengan Menggunakan Metode Fuzzy Time Series

Prediction of Household Electrical Power Consumption in Jakarta
Using the Fuzzy Time Series Method

Property of:
Universitas Trilogi | Teknik Informatika | Program Sarjana (Strata 1)
Trilogi University | Informatics Engineering | Bachelor Degree

Author:
Alma Zannuba Arifah | 19107011

Supervisors:
Ir. Yaddarabulah, M.Kom., Ph.D.
Opitasari, S.Si., M.Kom.

Module:
Logging Audit Tool

Version: 1.0.1
Created: December 2025
"""

"""PPDL Logging Spec V1.1 audit tool.

RUN-5 target: quick validation for:
- 4-level header format
- EVT catalog usage (no unknown EVT)
- ROUTE presence and actor/targets validity
- forbidden words in log text
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))


from utils.logging_events import ALL_EVENTS  # noqa: E402
from utils.logging_spec import (  # noqa: E402
	CAUSE_SEP,
	LVL1_ALLOWED,
	LVL2_ALLOWED,
	LVL3_ALLOWED,
	LVL4_ALLOWED,
	contains_forbidden,
)


HEADER_RE = re.compile(
	r"^\[(\d{2}:\d{2}:\d{2})\]\[([A-Z]+)\]\[([A-Z]+)\]\[([A-Z]+)\]\[([A-Z]+)\]\s+(.*)$"
)
EVT_RE = re.compile(r"\bEVT=([A-Z0-9_]+)\b")
EVT_DOT_RE = re.compile(r"\bEVT\.([A-Z0-9_]+)\b")

# Accept both literal CAUSE_SEP (control char) and its common rendered form ()
ROUTE_RE = re.compile(r"ROUTE:\s*([A-Z]+)\s*(?:\x1a|)\s*([A-Z,]+)")


@dataclass(frozen=True)
class Issue:
	kind: str
	line_no: int
	detail: str
	line: str


def _iter_python_files(base: Path, rel_paths: list[str]) -> list[Path]:
	paths: list[Path] = []
	for rel in rel_paths:
		p = (base / rel).resolve()
		if not p.exists():
			continue
		if p.is_file() and p.suffix.lower() == ".py":
			paths.append(p)
			continue
		if p.is_dir():
			for f in p.rglob("*.py"):
				if "venv" in f.parts:
					continue
				paths.append(f)
	return sorted(set(paths))


def audit_source(rel_paths: list[str]) -> int:
	py_files = _iter_python_files(PROJECT_ROOT, rel_paths)
	used: dict[str, list[str]] = {}
	for path in py_files:
		try:
			text = path.read_text(encoding="utf-8")
		except UnicodeDecodeError:
			text = path.read_text(encoding="utf-8", errors="replace")
		for name in EVT_DOT_RE.findall(text):
			used.setdefault(name, []).append(str(path.relative_to(PROJECT_ROOT)))

	unknown = sorted([name for name in used.keys() if name not in ALL_EVENTS])
	unused = sorted([evt for evt in ALL_EVENTS if evt not in used])

	print(f"[source] scanned_files={len(py_files)}")
	print(f"[source] catalog_events={len(ALL_EVENTS)} used={len(used)} unknown={len(unknown)} unused={len(unused)}")

	if unknown:
		print("[source] ERROR unknown EVT usage:")
		for name in unknown:
			files = ", ".join(sorted(set(used.get(name, []))))
			print(f"  - EVT.{name} in {files}")

	# unused tidak dianggap error; ini bisa jadi backlog migrasi.
	if unused:
		print("[source] INFO unused catalog EVT (not emitted yet):")
		for name in unused:
			print(f"  - {name}")

	return 1 if unknown else 0


def audit_log(
	log_path: Path,
	*,
	only_evt: bool,
	require_evt: bool,
	require_route: bool,
	check_route_actor_matches_header: bool,
	max_errors: int,
) -> int:
	if not log_path.exists():
		print(f"[log] ERROR path not found: {log_path}")
		return 2

	try:
		lines = log_path.read_text(encoding="utf-8").splitlines()
	except UnicodeDecodeError:
		lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()

	issues: list[Issue] = []
	checked = 0

	for idx, line in enumerate(lines, start=1):
		if not line.strip():
			continue
		if line.startswith("--- "):
			# AppLogger header marker
			continue

		m = HEADER_RE.match(line)
		if not m:
			issues.append(Issue("bad_header", idx, "Header not match 4-level format", line, line))
			if len(issues) >= max_errors:
				break
			continue

		_time, lvl1, lvl2, lvl3, lvl4, body = m.groups()

		if lvl1 not in LVL1_ALLOWED:
			issues.append(Issue("bad_lvl1", idx, f"LVL-1 invalid: {lvl1}", line, line))
		if lvl2 not in LVL2_ALLOWED:
			issues.append(Issue("bad_lvl2", idx, f"LVL-2 invalid: {lvl2}", line, line))
		if lvl3 not in LVL3_ALLOWED:
			issues.append(Issue("bad_lvl3", idx, f"LVL-3 invalid: {lvl3}", line, line))
		if lvl4 not in LVL4_ALLOWED:
			issues.append(Issue("bad_lvl4", idx, f"LVL-4 invalid: {lvl4}", line, line))

		has_evt = bool(EVT_RE.search(body))
		if only_evt and not has_evt:
			# skip lines without EVT= (legacy/transitional)
			continue

		checked += 1

		if require_evt and not has_evt:
			issues.append(Issue("missing_evt", idx, "Missing EVT= in log body", line, line))
		if has_evt:
			evt_code = EVT_RE.search(body).group(1)  # type: ignore[union-attr]
			if evt_code not in ALL_EVENTS:
				issues.append(Issue("unknown_evt", idx, f"EVT not in catalog: {evt_code}", line, line))

		route_match = ROUTE_RE.search(body)
		if require_route and not route_match:
			issues.append(Issue("missing_route", idx, "Missing ROUTE: in log body", line, line))
		if route_match:
			route_actor = route_match.group(1)
			targets = route_match.group(2)
			if route_actor not in LVL2_ALLOWED:
				issues.append(Issue("bad_route_actor", idx, f"ROUTE actor invalid: {route_actor}", line, line))
			if not targets:
				issues.append(Issue("bad_route_targets", idx, "ROUTE targets empty", line, line))
			if check_route_actor_matches_header and route_actor != lvl2:
				issues.append(
					Issue(
						"route_actor_mismatch",
						idx,
						f"ROUTE actor != header LVL-2: route={route_actor} header={lvl2}",
						line,
						line,
					)
				)

		forbidden = contains_forbidden(body)
		if forbidden:
			issues.append(Issue("forbidden_word", idx, f"Forbidden word: {forbidden}", line, line))

		if len(issues) >= max_errors:
			break

	print(f"[log] file={log_path}")
	print(f"[log] total_lines={len(lines)} checked_lines={checked} errors={len(issues)}")

	if issues:
		print("[log] FAIL (first errors):")
		for it in issues[:max_errors]:
			# Print the line to make debugging fast; avoid printing extremely long lines.
			preview = it.line
			if len(preview) > 400:
				preview = preview[:400] + "..."
			print(f"  - L{it.line_no} {it.kind}: {it.detail}")
			print(f"    {preview}")
		return 1

	print("[log] PASS")
	return 0


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(prog="log_audit.py", description="PPDL Logging Spec V1.1 audit tool")
	sub = parser.add_subparsers(dest="cmd", required=True)

	p_src = sub.add_parser("source", help="Audit EVT catalog usage in source code")
	p_src.add_argument(
		"--paths",
		nargs="*",
		default=["ui", "workers", "database", "logic", "utils"],
		help="Relative paths under project root to scan (default: ui workers database logic utils)",
	)

	p_log = sub.add_parser("log", help="Audit a produced log file (session_full.log or exported log)")
	p_log.add_argument("path", type=str, help="Path to log file")
	p_log.add_argument("--only-evt", action="store_true", help="Only validate lines that contain EVT=")
	p_log.add_argument("--require-evt", action="store_true", help="Require EVT= on validated lines")
	p_log.add_argument("--require-route", action="store_true", help="Require ROUTE: on validated lines")
	p_log.add_argument(
		"--no-check-route-actor",
		action="store_true",
		help="Do not require ROUTE actor to match header LVL-2",
	)
	p_log.add_argument("--max-errors", type=int, default=30, help="Stop after N errors (default: 30)")

	# Tail/framing audit (RUN-1/2)
	p_tail = sub.add_parser("tail", help="Audit START/END framing and metadata tails in log(s) or a run directory")
	p_tail.add_argument("path", type=str, help="Run directory containing logs, or a single .log file")

	args = parser.parse_args(argv)

	if args.cmd == "source":
		return audit_source(list(args.paths))

	if args.cmd == "log":
		# Default mode: practical for current repo state (legacy logs still exist).
		# - If only-evt=false: all lines are checked for header validity.
		# - If require-evt/require-route=true: enforce contract for validated lines.
		return audit_log(
			Path(args.path),
			only_evt=bool(args.only_evt),
			require_evt=bool(args.require_evt),
			require_route=bool(args.require_route),
			check_route_actor_matches_header=not bool(args.no_check_route_actor),
			max_errors=int(args.max_errors),
		)

	if args.cmd == "tail":
		def _audit_tail_file(path: str) -> tuple[bool, list[str]]:
			try:
				text = Path(path).read_text(encoding="utf-8")
			except Exception as e:
				return False, [f"READ_FAIL: {e}"]
			start_ok = bool(re.search(r"^===== START (?:Export|Calculation)\\b.*=====$", text, re.M))
			end_ok = bool(re.search(r"^===== END (?:Export|Calculation)\\b.*=====$", text, re.M))
			tail_ok = bool(re.search(r"^----- METADATA TAIL -----$", text, re.M))
			guid_ok = bool(re.search(r"^RUN_GUID=.+$", text, re.M))
			app_ok = bool(re.search(r"^APP_NAME=PPDL$", text, re.M))
			ver_ok = bool(re.search(r"^APP_VERSION=.+$", text, re.M))
			out_ok = bool(re.search(r"^OUTPUT_PATH=.+$", text, re.M))
			issues: list[str] = []
			if not start_ok:
				issues.append("MISSING_START_FRAME")
			if not end_ok:
				issues.append("MISSING_END_FRAME")
			if not tail_ok:
				issues.append("MISSING_TAIL_MARK")
			if not guid_ok:
				issues.append("MISSING_RUN_GUID")
			if not app_ok:
				issues.append("MISSING_APP_NAME")
			if not ver_ok:
				issues.append("MISSING_APP_VERSION")
			if not out_ok:
				issues.append("MISSING_OUTPUT_PATH")
			return len(issues) == 0, issues

		path = args.path
		targets: list[str] = []
		if os.path.isdir(path):
			for name in os.listdir(path):
				if name.endswith(".log") and name.startswith("["):
					targets.append(os.path.join(path, name))
		else:
			targets.append(path)

		if not targets:
			print(f"No logs found under: {path}")
			return 2

		ok_all = True
		for fp in sorted(targets):
			ok, issues = _audit_tail_file(fp)
			status = "OK" if ok else "FAIL"
			print(f"[tail] {status} {fp}")
			for i in issues:
				print(f"  - {i}")
			ok_all = ok_all and ok
		return 0 if ok_all else 1

	return 2


if __name__ == "__main__":
	raise SystemExit(main())

