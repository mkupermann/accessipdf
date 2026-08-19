import pikepdf

from accessipdf.core.model import Absatz, Tabelle
from accessipdf.semantics import assign
from accessipdf.tagging.walker import walk_page
from accessipdf.templates.loader import load_templates


def _semantik(demo_pdf):
    template = [t for t in load_templates() if t.name == "acme-demo"][0]
    with pikepdf.open(demo_pdf) as pdf:
        textops = walk_page(pdf, pdf.pages[0])
    return textops, assign(textops, template, seite_nr=1, n_seiten=1)


def test_tabelle_mit_kopf_und_daten(demo_pdf):
    _, semantik = _semantik(demo_pdf)
    tabellen = [b for b in semantik.bausteine if isinstance(b, Tabelle)]
    assert len(tabellen) == 1
    kopf = [z for z in tabellen[0].zeilen if z.kopf]
    daten = [z for z in tabellen[0].zeilen if not z.kopf]
    assert kopf and daten
    assert tabellen[0].n_spalten == 4


def test_ueberschrift_und_artefakt(demo_pdf):
    textops, semantik = _semantik(demo_pdf)
    h1 = [b for b in semantik.bausteine if isinstance(b, Absatz) and b.role == "H1"]
    assert len(h1) == 1

    fussnote = [op for op in textops if "1 Demo Road" in op.text]
    assert fussnote, "Kleinformat-Fußzeile nicht gefunden"
    inhalts_seqs = {s for b in semantik.bausteine if isinstance(b, Absatz) for s in b.seqs} | {
        s
        for b in semantik.bausteine
        if isinstance(b, Tabelle)
        for z in b.zeilen
        for zelle in z.zellen
        for s in zelle.seqs
    }
    assert fussnote[0].seq not in inhalts_seqs, "Fußzeile muss Artefakt sein"


def test_kein_inhalt_geht_verloren(demo_pdf):
    textops, semantik = _semantik(demo_pdf)
    page_ops = [op for op in textops if op.stream == "page" and (op.text.strip() or op.undecoded)]
    behandelt = {a.seq for a in semantik.assignments}
    assert {op.seq for op in page_ops} <= behandelt
