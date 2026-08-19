"""Dokumentweite PDF/UA-Pflichten, Sprache, Titel, XMP-Kennung, Anzeige."""

import pikepdf


def apply_metadata(pdf: pikepdf.Pdf, titel: str, sprache: str = "de-DE") -> None:
    pdf.Root.Lang = pikepdf.String(sprache)
    pdf.Root.ViewerPreferences = pikepdf.Dictionary(DisplayDocTitle=True)
    for seite in pdf.pages:
        seite.Tabs = pikepdf.Name.S
    with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
        meta["pdfuaid:part"] = "1"
        meta["dc:title"] = titel
    pdf.docinfo["/Title"] = pikepdf.String(titel)
