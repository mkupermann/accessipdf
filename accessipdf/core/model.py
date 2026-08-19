"""Internes Dokumentmodell."""

from dataclasses import dataclass, field


@dataclass
class TextOp:
    """Ein textzeigender Operator mit Position und dekodiertem Text.

    seq ist der Index in der Operatorliste des jeweiligen Streams,
    stream kennzeichnet den Stream ("page" oder der XObject-Pfad wie
    "page//Fm0"). bbox in PDF-Nutzerkoordinaten der Seite, (x0, y0, x1, y1).
    """

    seq: int
    stream: str
    bbox: tuple[float, float, float, float]
    text: str
    font: str
    size: float
    undecoded: bool = False


@dataclass
class Absatz:
    """Ein Strukturbaum-Blatt, mehrere Marked-Content-Sequenzen unter einer Rolle."""

    role: str
    seqs: list[int] = field(default_factory=list)
    alt: str | None = None
    mcids: list[int] = field(default_factory=list)


@dataclass
class Zelle:
    spalte: int
    kopf: bool
    seqs: list[int] = field(default_factory=list)
    mcids: list[int] = field(default_factory=list)


@dataclass
class Zeile:
    kopf: bool
    zellen: list[Zelle] = field(default_factory=list)


@dataclass
class Tabelle:
    name: str
    n_spalten: int = 0
    zeilen: list[Zeile] = field(default_factory=list)


@dataclass
class PageSemantik:
    """Ergebnis der Semantik-Zuordnung einer Seite.

    assignments in Leseordnung (Eingabe für wrap_page), bausteine als
    geordnete Strukturbaum-Knoten (Absätze und Tabellen).
    """

    assignments: list = field(default_factory=list)
    bausteine: list = field(default_factory=list)
