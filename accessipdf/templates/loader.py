"""Template-Format, Lader und deterministische Layout-Erkennung.

Ein Template je Rechnungslayout, als YAML unter templates/vorlagen/. Die
Zonen-Reihenfolge im Template ist die Leseordnung. Eine Tabellen-Zone gilt auf
einer Seite nur, wenn ihre Kopf-Anker dort gefunden werden, sonst fällt ihr
Inhalt an die nachfolgenden Zonen bzw. an unbekannt_als.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

VORLAGEN_DIR = Path(__file__).resolve().parent / "vorlagen"


@dataclass
class Zone:
    name: str
    seiten: str  # "alle", "1", "ab2", "letzte"
    bbox: tuple[float, float, float, float]
    rolle: str
    alt: str | None = None
    kopf_anker: list[str] = field(default_factory=list)
    spalten: list[float] = field(default_factory=list)

    def gilt_fuer(self, seite_nr: int, n_seiten: int) -> bool:
        if self.seiten == "alle":
            return True
        if self.seiten == "letzte":
            return seite_nr == n_seiten
        if self.seiten.startswith("ab"):
            return seite_nr >= int(self.seiten[2:])
        return seite_nr == int(self.seiten)

    def enthaelt(self, bbox: tuple[float, float, float, float]) -> bool:
        mx = (bbox[0] + bbox[2]) / 2
        my = (bbox[1] + bbox[3]) / 2
        x0, y0, x1, y1 = self.bbox
        return x0 <= mx <= x1 and y0 <= my <= y1


@dataclass
class Anker:
    text: str
    seite: int
    bbox: tuple[float, float, float, float]


@dataclass
class Feld:
    name: str
    seite: int
    bbox: tuple[float, float, float, float]


@dataclass
class Template:
    name: str
    sprache: str
    titel_muster: str
    erkennung: list[Anker]
    zonen: list[Zone]
    felder: list[Feld]
    unbekannt_als: str = "P"


def _zone(daten: dict) -> Zone:
    bbox_data = daten["bbox"]
    bbox: tuple[float, float, float, float] = (
        float(bbox_data[0]),
        float(bbox_data[1]),
        float(bbox_data[2]),
        float(bbox_data[3]),
    )
    return Zone(
        name=daten["name"],
        seiten=str(daten.get("seiten", "alle")),
        bbox=bbox,
        rolle=daten["rolle"],
        alt=daten.get("alt"),
        kopf_anker=list(daten.get("kopf_anker", [])),
        spalten=[float(v) for v in daten.get("spalten", [])],
    )


def load_templates(verzeichnis: Path = VORLAGEN_DIR) -> list["Template"]:
    templates = []
    for pfad in sorted(verzeichnis.glob("*.yaml")):
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
        templates.append(
            Template(
                name=daten["name"],
                sprache=daten.get("sprache", "de-DE"),
                titel_muster=daten.get("titel_muster", "Rechnung"),
                erkennung=[
                    Anker(
                        text=a["text"],
                        seite=int(a.get("seite", 1)),
                        bbox=(
                            float(a["bbox"][0]),
                            float(a["bbox"][1]),
                            float(a["bbox"][2]),
                            float(a["bbox"][3]),
                        ),
                    )
                    for a in daten["erkennung"]
                ],
                zonen=[_zone(z) for z in daten["zonen"]],
                felder=[
                    Feld(
                        name=name,
                        seite=int(f.get("seite", 1)),
                        bbox=(
                            float(f["bbox"][0]),
                            float(f["bbox"][1]),
                            float(f["bbox"][2]),
                            float(f["bbox"][3]),
                        ),
                    )
                    for name, f in daten.get("felder", {}).items()
                ],
                unbekannt_als=daten.get("unbekannt_als", "P"),
            )
        )
    return templates


def _anker_gefunden(anker: Anker, seiten_textops: list[list]) -> bool:
    if anker.seite > len(seiten_textops):
        return False
    x0, y0, x1, y1 = anker.bbox
    for op in seiten_textops[anker.seite - 1]:
        mx = (op.bbox[0] + op.bbox[2]) / 2
        my = (op.bbox[1] + op.bbox[3]) / 2
        if anker.text in op.text and x0 <= mx <= x1 and y0 <= my <= y1:
            return True
    return False


def identify(seiten_textops: list[list], templates: list[Template]) -> Template | None:
    """Layout-Erkennung, Treffer nur wenn alle Anker eines Templates sitzen."""
    for template in templates:
        if all(_anker_gefunden(a, seiten_textops) for a in template.erkennung):
            return template
    return None


def extrahiere_felder(template: Template, seiten_textops: list[list]) -> dict[str, str]:
    """Feldwerte für den Dokumenttitel aus den definierten Bereichen ziehen."""
    werte = {}
    for feld in template.felder:
        if feld.seite > len(seiten_textops):
            continue
        x0, y0, x1, y1 = feld.bbox
        teile = [
            op.text.strip()
            for op in seiten_textops[feld.seite - 1]
            if x0 <= (op.bbox[0] + op.bbox[2]) / 2 <= x1
            and y0 <= (op.bbox[1] + op.bbox[3]) / 2 <= y1
            and op.text.strip()
        ]
        werte[feld.name] = " ".join(teile)
    return werte
