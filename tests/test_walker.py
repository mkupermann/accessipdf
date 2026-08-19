from collections import Counter

import pikepdf

from accessipdf.tagging.walker import walk_page
from accessipdf.testkit import extract_text


def test_walker_findet_anker_mit_position(demo_pdf):
    with pikepdf.open(demo_pdf) as pdf:
        seite = pdf.pages[0]
        hoehe = float(seite.MediaBox[3])
        ops = walk_page(pdf, seite)
    treffer = [op for op in ops if "ACME Utilities Ltd." in op.text]
    assert treffer, "Anker nicht gefunden"
    op = treffer[0]
    assert op.bbox[1] > hoehe * 0.75, f"Briefkopf unerwartet tief: {op.bbox}"
    assert op.bbox[2] > op.bbox[0]
    assert op.font and op.size > 0


def test_walker_deckt_text_ab(demo_pdf):
    with pikepdf.open(demo_pdf) as pdf:
        ops = walk_page(pdf, pdf.pages[0])
    walker_text = "".join("".join(op.text.split()) for op in ops)
    referenz = "".join(extract_text(str(demo_pdf))[0].split())
    cw, cr = Counter(walker_text), Counter(referenz)
    gefunden = sum(min(cw[z], n) for z, n in cr.items())
    assert gefunden / len(referenz) >= 0.9
