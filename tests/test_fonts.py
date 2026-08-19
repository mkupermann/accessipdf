import pikepdf

from accessipdf.tagging.fonts import embed_standard_fonts, ensure_tounicode, iter_fonts
from accessipdf.testkit import extract_text, pixel_diff, render_pages, solid_diff_area


def test_ensure_tounicode(demo_pdf, tmp_path):
    ziel = tmp_path / "tounicode.pdf"
    with pikepdf.open(demo_pdf) as pdf:
        repariert = ensure_tounicode(pdf)
        assert repariert, "es gab nichts zu reparieren, unerwartet"
        pdf.save(ziel)
    with pikepdf.open(ziel) as pdf:
        for _, _, font in iter_fonts(pdf):
            assert "/ToUnicode" in font, f"Font ohne ToUnicode: {font.get('/BaseFont')}"
    assert extract_text(str(demo_pdf)) == extract_text(str(ziel))
    for a, b in zip(render_pages(str(demo_pdf)), render_pages(str(ziel))):
        assert pixel_diff(a, b) == 0


def test_embed_standard_fonts(demo_pdf, tmp_path):
    ziel = tmp_path / "eingebettet.pdf"
    with pikepdf.open(demo_pdf) as pdf:
        ersetzt = embed_standard_fonts(pdf)
        assert ersetzt, "keine nicht eingebettete Standardschrift gefunden"
        assert any("Bold" in e for e in ersetzt), "Bold-Schnitt muss stilgetreu ersetzt werden"
        pdf.save(ziel)

    with pikepdf.open(ziel) as pdf:
        for _, _, font in iter_fonts(pdf):
            desc = font.get("/FontDescriptor")
            if desc is None and font.get("/Subtype") == pikepdf.Name.Type0:
                desc = font.DescendantFonts[0].get("/FontDescriptor")
            assert desc is not None
            assert any(s in desc for s in ("/FontFile", "/FontFile2", "/FontFile3")), (
                f"nicht eingebettet: {font.get('/BaseFont')}"
            )

    # Erlaubt ist Glyphenkanten-Rauschen der Ersatzschrift, keine flächige Abweichung.
    for a, b in zip(render_pages(str(demo_pdf)), render_pages(str(ziel))):
        assert solid_diff_area(a, b, kern=9) == 0
    assert extract_text(str(demo_pdf)) == extract_text(str(ziel))
