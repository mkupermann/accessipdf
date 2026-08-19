import pikepdf

from accessipdf.core.model import Absatz
from accessipdf.tagging.structure import build_structure, fuelle_mcids
from accessipdf.tagging.walker import walk_page
from accessipdf.tagging.wrap import Assignment, wrap_page
from accessipdf.testkit import extract_text, mini_pdf, pixel_diff, render_pages


def test_wrap_und_struktur_auf_mini_pdf(tmp_path):
    quelle = mini_pdf(tmp_path / "mini.pdf")
    ziel = tmp_path / "mini_getaggt.pdf"

    with pikepdf.open(quelle) as pdf:
        seite = pdf.pages[0]
        textops = [op for op in walk_page(pdf, seite) if op.stream == "page"]
        assert len(textops) == 2
        zuweisungen = [
            Assignment(seq=op.seq, stream="page", role="P") for op in textops
        ]
        bausteine = [Absatz(role="P", seqs=[op.seq]) for op in textops]
        mcids = wrap_page(pdf, seite, zuweisungen)
        fuelle_mcids(bausteine, mcids)
        build_structure(pdf, [(seite, bausteine)])
        pdf.save(ziel)

    with pikepdf.open(ziel) as pdf:
        root = pdf.Root
        assert "/StructTreeRoot" in root
        assert bool(root.MarkInfo.Marked) is True
        dokument = root.StructTreeRoot.K
        assert str(dokument.S) == "/Document"
        assert len(list(dokument.K)) == 2
        inhalt = pdf.pages[0].Contents.read_bytes()
        assert b"BDC" in inhalt and b"EMC" in inhalt
        assert b"/MCID" in inhalt
        assert b"/Artifact" in inhalt  # das Rechteck ist Deko

    vorher = render_pages(str(quelle))
    nachher = render_pages(str(ziel))
    assert pixel_diff(vorher[0], nachher[0]) == 0


def test_wrap_demo_rechnung_pixelgleich(demo_pdf, tmp_path):
    ziel = tmp_path / "getaggt.pdf"
    with pikepdf.open(demo_pdf) as pdf:
        seiten = []
        for seite in pdf.pages:
            textops = [op for op in walk_page(pdf, seite) if op.stream == "page"]
            zuweisungen = [
                Assignment(seq=op.seq, stream="page", role="P") for op in textops
            ]
            bausteine = [Absatz(role="P", seqs=[op.seq for op in textops])]
            mcids = wrap_page(pdf, seite, zuweisungen)
            fuelle_mcids(bausteine, mcids)
            seiten.append((seite, bausteine))
        build_structure(pdf, seiten)
        pdf.save(ziel)

    vorher = render_pages(str(demo_pdf))
    nachher = render_pages(str(ziel))
    for i, (a, b) in enumerate(zip(vorher, nachher)):
        assert pixel_diff(a, b) == 0, f"Seite {i + 1} weicht ab"
    assert extract_text(str(demo_pdf)) == extract_text(str(ziel))
