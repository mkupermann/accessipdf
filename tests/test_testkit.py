import pikepdf

from accessipdf.testkit import extract_text, pixel_diff, render_pages


def test_render_pages_liefert_alle_seiten(demo_pdf):
    with pikepdf.open(demo_pdf) as pdf:
        seitenzahl = len(pdf.pages)
    bilder = render_pages(str(demo_pdf))
    assert len(bilder) == seitenzahl
    assert bilder[0].width > 500


def test_pixel_diff_identisch_ist_null(demo_pdf):
    bilder = render_pages(str(demo_pdf))
    assert pixel_diff(bilder[0], bilder[0]) == 0


def test_extract_text_findet_anker(demo_pdf):
    assert "ACME Utilities Ltd." in extract_text(str(demo_pdf))[0]
