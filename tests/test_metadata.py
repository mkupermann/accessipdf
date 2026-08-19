import pikepdf

from accessipdf.tagging.metadata import apply_metadata


def _leeres_pdf(pfad):
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(595, 842))
    pdf.save(pfad)
    return pfad


def test_apply_metadata_setzt_ua_kennung(tmp_path):
    quelle = _leeres_pdf(tmp_path / "leer.pdf")
    ziel = tmp_path / "meta.pdf"
    with pikepdf.open(quelle) as pdf:
        apply_metadata(pdf, titel="Rechnung F100 Juni 2026")
        pdf.save(ziel)

    with pikepdf.open(ziel) as pdf:
        assert str(pdf.Root.Lang) == "de-DE"
        assert bool(pdf.Root.ViewerPreferences.DisplayDocTitle) is True
        assert str(pdf.pages[0].Tabs) == "/S"
        with pdf.open_metadata() as meta:
            assert meta.get("pdfuaid:part") in (1, "1")
            assert meta.get("dc:title") == "Rechnung F100 Juni 2026"
        assert str(pdf.docinfo["/Title"]) == "Rechnung F100 Juni 2026"
