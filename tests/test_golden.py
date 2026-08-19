"""Golden-Test, die Demo-Rechnung muss die volle Pipeline grün durchlaufen."""

from accessipdf.pipeline import convert
from accessipdf.testkit import (
    extract_text,
    pixel_diff,
    render_pages,
    solid_diff_area,
)


def test_demo_rechnung_wird_barrierefrei(demo_pdf, tmp_path):
    ausgang = tmp_path / "ausgang"
    quarantaene = tmp_path / "quarantaene"

    ergebnis = convert(str(demo_pdf), str(ausgang), str(quarantaene))
    assert ergebnis.status == "ok", f"{ergebnis.status}: {ergebnis.grund}"
    assert ergebnis.report["verapdf"]["passed"] is True
    assert ergebnis.report["layout"] == "acme-demo"

    ziel = ausgang / demo_pdf.name
    vorher = render_pages(str(demo_pdf))
    nachher = render_pages(str(ziel))
    assert len(vorher) == len(nachher)
    for i, (a, b) in enumerate(zip(vorher, nachher)):
        anteil = pixel_diff(a, b) / (a.width * a.height)
        if anteil >= 0.005:
            # Erlaubt: Glyphenkanten-Rauschen der eingebetteten Ersatzschrift.
            assert ergebnis.report["font_reparaturen"]["eingebettet"]
            assert anteil < 0.25, f"Seite {i + 1}: {anteil:.4%} ist zu viel"
            assert solid_diff_area(a, b, kern=9) == 0, f"Seite {i + 1}: flächige Abweichung"

    # Kein sauber dekodierter Text darf verloren gehen.
    for seite_vorher, seite_nachher in zip(extract_text(str(demo_pdf)), extract_text(str(ziel))):
        for zeile in seite_vorher.splitlines():
            if zeile.strip():
                assert zeile in seite_nachher, f"Zeile verloren: {zeile!r}"

    # Idempotenz, zweiter Lauf überspringt.
    zweiter = convert(str(demo_pdf), str(ausgang), str(quarantaene))
    assert zweiter.status == "ok"
    assert "bereits verarbeitet" in (zweiter.grund or "")
