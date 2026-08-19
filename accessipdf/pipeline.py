"""Die Umwandlungs-Pipeline, eine Rechnung rein, eine geprüfte PDF/UA-Datei raus.

Grundsätze:
- Das Original wird nie verändert oder gelöscht.
- Die Ausgabe entsteht als Temp-Datei und wird erst nach grünem veraPDF-Gate
  atomar ins Ausgangsverzeichnis verschoben.
- Alles Nicht-Grüne geht begründet in die Quarantäne, mit JSON-Bericht.
- Idempotent über den SHA256 des Originals.
"""

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pikepdf

from accessipdf.semantics import assign
from accessipdf.tagging.fonts import (
    FontReparaturFehler,
    drop_incomplete_cidset,
    embed_standard_fonts,
    ensure_tounicode,
    fix_cidtogid,
)
from accessipdf.tagging.metadata import apply_metadata
from accessipdf.tagging.structure import build_structure, fuelle_mcids
from accessipdf.tagging.walker import walk_page
from accessipdf.tagging.wrap import wrap_page
from accessipdf.templates.loader import extrahiere_felder, identify, load_templates
from accessipdf.validate.verapdf import validate_ua1

REGISTRY_NAME = ".verarbeitet.json"


@dataclass
class ConvertResult:
    status: Literal["ok", "quarantaene", "fehler"]
    grund: str | None = None
    report: dict = field(default_factory=dict)


def _sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _registry_lesen(ausgang: Path) -> dict:
    pfad = ausgang / REGISTRY_NAME
    if pfad.exists():
        return json.loads(pfad.read_text(encoding="utf-8"))
    return {}


def _registry_schreiben(ausgang: Path, registry: dict) -> None:
    pfad = ausgang / REGISTRY_NAME
    tmp = pfad.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(registry, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, pfad)


def _quarantaene(quelle: Path, quarantaene_dir: Path, grund: str, report: dict) -> ConvertResult:
    quarantaene_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(quelle, quarantaene_dir / quelle.name)
    bericht = dict(report)
    bericht["grund"] = grund
    bericht["datei"] = quelle.name
    (quarantaene_dir / f"{quelle.stem}.bericht.json").write_text(
        json.dumps(bericht, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    return ConvertResult(status="quarantaene", grund=grund, report=bericht)


def convert(in_path: str, out_dir: str, quarantaene_dir: str) -> ConvertResult:
    quelle = Path(in_path)
    ausgang = Path(out_dir)
    quarantaene = Path(quarantaene_dir)
    ausgang.mkdir(parents=True, exist_ok=True)

    report: dict = {"datei": quelle.name}
    fingerabdruck = _sha256(quelle)
    registry = _registry_lesen(ausgang)
    if fingerabdruck in registry:
        return ConvertResult(
            status="ok",
            grund=f"bereits verarbeitet als {registry[fingerabdruck]}",
            report=report,
        )

    temp = None
    try:
        with pikepdf.open(quelle) as pdf:
            seiten_textops = [walk_page(pdf, seite) for seite in pdf.pages]
            template = identify(seiten_textops, load_templates())
            if template is None:
                return _quarantaene(quelle, quarantaene, "unbekanntes Layout", report)
            report["layout"] = template.name
            report["seiten"] = len(pdf.pages)

            felder = extrahiere_felder(template, seiten_textops)
            seiten = []
            for nummer, (seite, textops) in enumerate(zip(pdf.pages, seiten_textops), start=1):
                semantik = assign(textops, template, seite_nr=nummer, n_seiten=len(pdf.pages))
                mcids = wrap_page(pdf, seite, semantik.assignments)
                fuelle_mcids(semantik.bausteine, mcids)
                seiten.append((seite, semantik.bausteine))
            build_structure(pdf, seiten)

            report["font_reparaturen"] = {
                "cidtogid": fix_cidtogid(pdf),
                "cidset_entfernt": drop_incomplete_cidset(pdf),
                "tounicode": ensure_tounicode(pdf),
                "eingebettet": embed_standard_fonts(pdf),
            }

            titel = template.titel_muster.format_map(_MitLuecken(felder))
            apply_metadata(pdf, titel=titel, sprache=template.sprache)

            fd, temp_name = tempfile.mkstemp(suffix=".pdf", dir=ausgang)
            os.close(fd)
            temp = Path(temp_name)
            pdf.save(temp)
    except FontReparaturFehler as fehler:
        if temp and temp.exists():
            temp.unlink()
        return _quarantaene(quelle, quarantaene, f"Font-Reparatur: {fehler}", report)

    pruefung = validate_ua1(str(temp))
    report["verapdf"] = {
        "passed": pruefung.passed,
        "failed_rules": pruefung.failed_rules,
    }
    if not pruefung.passed:
        quarantaene.mkdir(parents=True, exist_ok=True)
        os.replace(temp, quarantaene / quelle.name)
        bericht = dict(report)
        bericht["grund"] = "veraPDF rot"
        (quarantaene / f"{quelle.stem}.bericht.json").write_text(
            json.dumps(bericht, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        return ConvertResult(status="quarantaene", grund="veraPDF rot", report=bericht)

    ziel = ausgang / quelle.name
    os.replace(temp, ziel)
    registry[fingerabdruck] = quelle.name
    _registry_schreiben(ausgang, registry)
    return ConvertResult(status="ok", report=report)


class _MitLuecken(dict):
    """format_map-Hilfe, unbekannte Felder bleiben als Platzhalter sichtbar."""

    def __missing__(self, schluessel):
        return f"{{{schluessel}}}"
