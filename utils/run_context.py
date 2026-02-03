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
Runtime Context Manager

Version: 1.0.1
Created: December 2025
"""

import datetime
import secrets
import string
from dataclasses import dataclass


APP_VERSION = "1.0"


_GUID_ALPHABET = string.ascii_uppercase + string.digits


def generate_run_guid(length: int = 10) -> str:
	"""Generate GUID pendek (10-12 char) untuk identitas run."""

	n = int(length)
	if n < 10:
		n = 10
	if n > 12:
		n = 12
	return "".join(secrets.choice(_GUID_ALPHABET) for _ in range(n))


@dataclass(frozen=True)
class RunContext:
	guid: str
	started_at: datetime.datetime
	app_version: str

	@classmethod
	def new(cls, *, guid_length: int = 10, app_version: str | None = None) -> "RunContext":
		version = str(app_version).strip() if app_version else APP_VERSION
		return cls(
			guid=generate_run_guid(guid_length),
			started_at=datetime.datetime.now(),
			app_version=version,
		)

	def identity_lines(self) -> list[str]:
		start_text = self.started_at.strftime("%Y-%m-%d %H:%M:%S")
		return [
			f"RUN_GUID={self.guid}",
			f"RUN_START={start_text}",
			f"APP_VERSION={self.app_version}",
		]

