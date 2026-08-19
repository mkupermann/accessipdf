"""Semantik-Zuordnung, Template-Zonen auf Textoperatoren einer Seite anwenden.

Liefert die Zuweisungen in Leseordnung (Zonen-Reihenfolge des Templates, darin
Zeilen oben nach unten) und die Strukturbaum-Bausteine (Absätze, Tabellen).
Zonenloser Text fällt an unbekannt_als, es geht nie stumm etwas verloren.
"""

import statistics

from accessipdf.core.model import Absatz, PageSemantik, TextOp
from accessipdf.tagging.tables import cluster_zeilen, plan_table
from accessipdf.tagging.wrap import Assignment
from accessipdf.templates.loader import Template, Zone


def _absaetze(ops: list[TextOp], rolle: str, alt: str | None) -> list[Absatz]:
    """Zeilen clustern und an Leerraum-Sprüngen in Absätze teilen."""
    zeilen = cluster_zeilen(ops)
    if not zeilen:
        return []
    groesse = statistics.median(op.size for op in ops)
    absaetze = [Absatz(role=rolle, alt=alt)]
    letzte_grundlinie = None
    for zeile in zeilen:
        grundlinie = zeile[0].bbox[1]
        if (
            letzte_grundlinie is not None
            and letzte_grundlinie - grundlinie > 1.8 * groesse
            and absaetze[-1].seqs
        ):
            absaetze.append(Absatz(role=rolle, alt=alt))
        absaetze[-1].seqs.extend(op.seq for op in zeile)
        letzte_grundlinie = grundlinie
    return [a for a in absaetze if a.seqs]


def _tabellen_zone_aktiv(zone: Zone, ops_in_zone: list[TextOp]) -> bool:
    text = " ".join(op.text for op in ops_in_zone)
    return all(anker in text for anker in zone.kopf_anker)


def assign(
    textops: list[TextOp], template: Template, seite_nr: int, n_seiten: int
) -> PageSemantik:
    # Leere Textoperatoren (reine Platzhalter ohne Inhalt) bleiben unzugewiesen
    # und werden beim Klammern Artefakt. Undekodierte Operatoren bleiben drin,
    # ihr Inhalt darf nicht stumm verschwinden.
    page_ops = [
        op
        for op in textops
        if op.stream == "page" and (op.text.strip() or op.undecoded)
    ]
    zonen = [z for z in template.zonen if z.gilt_fuer(seite_nr, n_seiten)]

    ops_je_zone: dict[int, list[TextOp]] = {id(z): [] for z in zonen}
    rest: list[TextOp] = []
    for op in page_ops:
        for zone in zonen:
            if zone.enthaelt(op.bbox):
                ops_je_zone[id(zone)].append(op)
                break
        else:
            rest.append(op)

    # Inaktive Tabellen-Zonen (Kopf-Anker fehlen) geben ihre Operatoren frei.
    aktive_zonen = []
    for zone in zonen:
        ops = ops_je_zone[id(zone)]
        if zone.rolle == "Table" and zone.kopf_anker and not _tabellen_zone_aktiv(zone, ops):
            rest.extend(ops)
            continue
        aktive_zonen.append(zone)

    semantik = PageSemantik()

    def absatz_bausteine(ops: list[TextOp], rolle: str, alt: str | None):
        for absatz in _absaetze(ops, rolle, alt):
            semantik.bausteine.append(absatz)
            semantik.assignments.extend(
                Assignment(seq=seq, stream="page", role=rolle, alt=alt)
                for seq in absatz.seqs
            )

    for zone in aktive_zonen:
        ops = ops_je_zone[id(zone)]
        if not ops:
            continue
        if zone.rolle == "Artifact":
            semantik.assignments.extend(
                Assignment(seq=op.seq, stream="page", role="Artifact") for op in ops
            )
        elif zone.rolle == "Table":
            tabelle = plan_table(ops, zone.spalten, zone.kopf_anker, name=zone.name)
            semantik.bausteine.append(tabelle)
            for zeile in tabelle.zeilen:
                for zelle in zeile.zellen:
                    rolle = "TH" if zelle.kopf else "TD"
                    semantik.assignments.extend(
                        Assignment(seq=seq, stream="page", role=rolle)
                        for seq in zelle.seqs
                    )
        else:
            absatz_bausteine(ops, zone.rolle, zone.alt)

    if rest:
        # Zonenloser Text in natürlicher Leseordnung ans Ende.
        absatz_bausteine(rest, template.unbekannt_als, None)

    return semantik
