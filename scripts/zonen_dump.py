"""Listet Textoperatoren mit Koordinaten, Hilfsmittel zum Ausmessen der Templates."""

import sys

import pikepdf

from accessipdf.tagging.walker import walk_page


def main() -> None:
    pfad = sys.argv[1]
    seiten = [int(s) for s in sys.argv[2:]] or [1]
    with pikepdf.open(pfad) as pdf:
        for nummer in seiten:
            seite = pdf.pages[nummer - 1]
            print(f"--- Seite {nummer} ({float(seite.MediaBox[2])}x{float(seite.MediaBox[3])}) ---")
            for op in walk_page(pdf, seite):
                x0, y0, x1, y1 = (round(v) for v in op.bbox)
                kurz = op.text[:60].replace("\n", " ")
                print(f"{op.stream:14} seq={op.seq:4} ({x0:4},{y0:4})-({x1:4},{y1:4}) {op.size:4.1f} {kurz}")


if __name__ == "__main__":
    main()
