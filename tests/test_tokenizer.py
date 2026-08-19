import pikepdf

from accessipdf.tagging.tokenizer import parse_ops, write_ops
from accessipdf.testkit import extract_text, pixel_diff, render_pages


def test_round_trip_ohne_aenderung_ist_pixelgleich(demo_pdf, tmp_path):
    ziel = tmp_path / "roundtrip.pdf"
    with pikepdf.open(demo_pdf) as pdf:
        for seite in pdf.pages:
            ops = parse_ops(seite)
            assert ops, "leerer Operatorstrom"
            write_ops(pdf, seite, ops)
        pdf.save(ziel)

    vorher = render_pages(str(demo_pdf))
    nachher = render_pages(str(ziel))
    assert len(vorher) == len(nachher)
    for i, (a, b) in enumerate(zip(vorher, nachher)):
        assert pixel_diff(a, b) == 0, f"Seite {i + 1} weicht ab"
    assert extract_text(str(demo_pdf)) == extract_text(str(ziel))
