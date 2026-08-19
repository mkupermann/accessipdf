"""Anbindung des externen veraPDF-Prüfwerkzeugs."""

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


def verapdf_cmd() -> list[str]:
    """Findet die veraPDF-CLI, zuerst im PATH, dann unter ~/.local/verapdf."""
    im_pfad = shutil.which("verapdf")
    if im_pfad:
        return [im_pfad]
    lokal = Path.home() / ".local" / "verapdf" / "verapdf"
    if lokal.exists():
        return [str(lokal)]
    raise FileNotFoundError(
        "veraPDF nicht gefunden. Installation über 'brew install verapdf' "
        "oder Greenfield-CLI nach ~/.local/verapdf."
    )


@dataclass
class ValidationResult:
    passed: bool
    failed_rules: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def validate_ua1(pdf_path: str, timeout: int = 300) -> ValidationResult:
    """Prüft eine Datei gegen PDF/UA-1 und fasst die gescheiterten Regeln zusammen."""
    lauf = subprocess.run(
        verapdf_cmd() + ["--flavour", "ua1", "--format", "json", pdf_path],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if not lauf.stdout.strip():
        raise RuntimeError(f"veraPDF ohne Ausgabe, stderr: {lauf.stderr[:500]}")
    bericht = json.loads(lauf.stdout)
    jobs = bericht.get("report", {}).get("jobs", [])
    if not jobs or not jobs[0].get("validationResult"):
        raise RuntimeError(f"veraPDF ohne Validierungsergebnis: {lauf.stderr[:500]}")
    ergebnis = jobs[0]["validationResult"][0]
    regeln = []
    for regel in ergebnis.get("details", {}).get("ruleSummaries", []):
        if regel.get("ruleStatus") == "FAILED":
            regeln.append(
                f"{regel.get('specification')} {regel.get('clause')}"
                f"-{regel.get('testNumber')} ({regel.get('failedChecks')}x): "
                f"{regel.get('description', '')[:160]}"
            )
    return ValidationResult(
        passed=bool(ergebnis.get("compliant")), failed_rules=regeln, raw=ergebnis
    )
