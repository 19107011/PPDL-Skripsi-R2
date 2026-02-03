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
Logging Specification

Version: 1.0.1
Created: December 2025
"""

"""Guard & helper untuk PPDL LOGGING SPEC V1.1.

Sumber: docs/Doc_for_Ex_Plan-5.md.
"""

LVL1_ALLOWED: set[str] = {"DEBUG", "INIT", "INFO", "GEN", "WARN", "FAIL", "ERROR", "SUCCESS"}
LVL2_ALLOWED: set[str] = {"MAIN", "HOME", "INITIAL", "DATABASE", "SQL", "RESUME"}
LVL3_ALLOWED: set[str] = {"BASE", "CAL", "RPT"}
LVL4_ALLOWED: set[str] = {"FTS", "ANN", "ARIMA", "GENERAL"}

# Separator kontrak (Doc_for_Ex_Plan-5.md)
FIELD_SEP = " | "
CAUSE_SEP = "\x1a"  # tampil sebagai '' pada beberapa editor
RESULT_SEP = "\x1b"  # tampil sebagai '' pada beberapa editor

# Larangan mutlak (Doc_for_Ex_Plan-5.md: 4.5)
FORBIDDEN_WORDS = ("contoh", "misalnya", "kayak gini")


def contains_forbidden(text: str) -> str | None:
	low = str(text).lower()
	for w in FORBIDDEN_WORDS:
		if w in low:
			return w
	return None


def normalize_tag(value: str) -> str:
	return str(value).strip().upper()


def validate_tag(value: str, allowed: set[str], tag_name: str) -> str:
	normalized = normalize_tag(value)
	if normalized not in allowed:
		raise ValueError(f"{tag_name} invalid: {value!r}")
	return normalized


def format_route(actor: str, targets: list[str] | None) -> str:
	actor_norm = normalize_tag(actor)
	target_list = targets or [actor_norm]
	targets_norm = ",".join(normalize_tag(t) for t in target_list if str(t).strip())
	if not targets_norm:
		targets_norm = actor_norm
	return f"ROUTE: {actor_norm} {CAUSE_SEP} {targets_norm}"

