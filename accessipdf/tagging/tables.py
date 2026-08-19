"""Tabellenplan aus Textoperatoren einer Tabellen-Zone."""

import statistics

from accessipdf.core.model import Tabelle, TextOp, Zeile, Zelle


def cluster_zeilen(ops: list[TextOp], toleranz_faktor: float = 0.6) -> list[list[TextOp]]:
    """Gruppiert Operatoren nach Grundlinie zu Zeilen, oben nach unten."""
    if not ops:
        return []
    sortiert = sorted(ops, key=lambda op: (-op.bbox[1], op.bbox[0]))
    zeilen: list[list[TextOp]] = []
    for op in sortiert:
        if zeilen:
            referenz = zeilen[-1][0]
            toleranz = toleranz_faktor * max(referenz.size, op.size, 1.0)
            if abs(op.bbox[1] - referenz.bbox[1]) <= toleranz:
                zeilen[-1].append(op)
                continue
        zeilen.append([op])
    for zeile in zeilen:
        zeile.sort(key=lambda op: op.bbox[0])
    return zeilen


def _spalte(op: TextOp, spalten: list[float]) -> int:
    mitte = (op.bbox[0] + op.bbox[2]) / 2
    index = 0
    for grenze in spalten:
        if mitte >= grenze:
            index += 1
    return index


def plan_table(
    ops: list[TextOp], spalten: list[float], kopf_anker: list[str], name: str
) -> Tabelle:
    """Baut den Tabellenplan, Zeilen über Grundlinien-Cluster, Zellen über Spaltengrenzen.

    Kopfzeilen sind die Zeilen, die einen Kopf-Anker enthalten, plus Unterzeilen
    unmittelbar darunter (weniger als 1,5 Zeilenhöhen Abstand zur untersten
    Anker-Zeile, für Zusätze wie "(netto)").
    """
    zeilen_ops = cluster_zeilen(ops)
    anker_grundlinien = [
        zeile[0].bbox[1]
        for zeile in zeilen_ops
        if any(any(a in op.text for a in kopf_anker) for op in zeile)
    ]
    kopf_grenze = None
    if anker_grundlinien:
        groesse = statistics.median(op.size for op in ops)
        kopf_grenze = min(anker_grundlinien) - 1.5 * groesse

    tabelle = Tabelle(name=name, n_spalten=len(spalten) + 1)
    for zeile_ops in zeilen_ops:
        ist_kopf = kopf_grenze is not None and zeile_ops[0].bbox[1] >= kopf_grenze
        zellen: dict[int, Zelle] = {}
        for op in zeile_ops:
            index = _spalte(op, spalten)
            zellen.setdefault(index, Zelle(spalte=index, kopf=ist_kopf)).seqs.append(
                op.seq
            )
        tabelle.zeilen.append(
            Zeile(kopf=ist_kopf, zellen=[zellen[i] for i in sorted(zellen)])
        )
    return tabelle
