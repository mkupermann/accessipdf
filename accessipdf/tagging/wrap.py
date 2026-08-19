"""Klammert Seiteninhalte in Marked Content, echte Inhalte mit MCID, Deko als Artefakt.

Arbeitsweise auf dem Seitenstream:

- Zugewiesene Textoperatoren bekommen ``role BDC ... EMC`` mit fortlaufender MCID.
- Zuweisungen mit Rolle "Artifact" werden als Artefakt geklammert.
- Pfadobjekte (Konstruktion bis Maloperator) ohne Zuweisung werden als Ganzes
  Artefakt, ebenso XObject-Aufrufe (Do). Ein als Artefakt geklammertes Form-Do
  macht den gesamten Inhalt des XObjects zum Artefakt, deshalb müssen geteilte
  Briefkopf-Formen nicht umgeschrieben werden.
- Zustandsoperatoren bleiben unberührt. BDC/EMC umschließen immer genau eine
  Einheit und überspannen nie q/Q, die Schachtelung bleibt sauber.
"""

from dataclasses import dataclass

import pikepdf

from accessipdf.tagging.tokenizer import parse_ops, write_ops

PATH_CONSTRUCT = {"m", "l", "c", "v", "y", "re", "h"}
PATH_PAINT = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"}
CLIP = {"W", "W*"}
SHOW = {"Tj", "TJ", "'", '"'}


@dataclass
class Assignment:
    seq: int
    stream: str
    role: str
    alt: str | None = None


def _bdc(role: str, mcid: int) -> tuple:
    return (
        [pikepdf.Name("/" + role), pikepdf.Dictionary(MCID=mcid)],
        pikepdf.Operator("BDC"),
    )


def _artifact_bdc(art_typ: str) -> tuple:
    return (
        [
            pikepdf.Name("/Artifact"),
            pikepdf.Dictionary(Type=pikepdf.Name("/" + art_typ)),
        ],
        pikepdf.Operator("BDC"),
    )


_EMC: tuple[list, pikepdf.Operator] = ([], pikepdf.Operator("EMC"))


def wrap_page(pdf: pikepdf.Pdf, page, assignments: list[Assignment]) -> dict[int, int]:
    """Klammert den Seitenstream und liefert die vergebene MCID je Operator-seq.

    Zuweisungen gelten nur für den Stream "page". Inhalte in Form-XObjects werden
    über das artefakt-geklammerte Do erfasst.
    """
    zuweisung_je_seq = {a.seq: a for a in assignments if a.stream == "page"}
    ops = parse_ops(page)
    neu: list = []
    pfad_puffer: list = []
    mcid = 0
    mcid_je_seq: dict[int, int] = {}

    def flush_pfad_als_artefakt():
        nonlocal neu
        if not pfad_puffer:
            return
        neu.append(_artifact_bdc("Layout"))
        neu.extend(pfad_puffer)
        neu.append(_EMC)
        pfad_puffer.clear()

    for seq, instr in enumerate(ops):
        try:
            operanden, op = instr
            name = str(op)
        except (TypeError, ValueError):
            # Inline-Bild, als Ganzes Artefakt
            neu.append(_artifact_bdc("Layout"))
            neu.append(instr)
            neu.append(_EMC)
            continue

        if name in PATH_CONSTRUCT or name in CLIP:
            pfad_puffer.append(instr)
            continue
        if name in PATH_PAINT:
            pfad_puffer.append(instr)
            flush_pfad_als_artefakt()
            continue

        if name in SHOW:
            zu = zuweisung_je_seq.get(seq)
            if zu is None or zu.role == "Artifact":
                neu.append(_artifact_bdc("Layout"))
                neu.append(instr)
                neu.append(_EMC)
            else:
                neu.append(_bdc(zu.role, mcid))
                neu.append(instr)
                neu.append(_EMC)
                mcid_je_seq[seq] = mcid
                mcid += 1
            continue

        if name in {"Do", "sh"}:
            zu = zuweisung_je_seq.get(seq)
            if zu is not None and zu.role not in ("Artifact",):
                neu.append(_bdc(zu.role, mcid))
                neu.append(instr)
                neu.append(_EMC)
                mcid_je_seq[seq] = mcid
                mcid += 1
            else:
                neu.append(_artifact_bdc("Pagination"))
                neu.append(instr)
                neu.append(_EMC)
            continue

        neu.append(instr)

    # Ein offener Pfadpuffer ohne Maloperator wäre kaputter Inhalt, unverändert anhängen.
    neu.extend(pfad_puffer)

    write_ops(pdf, page, neu)
    return mcid_je_seq
