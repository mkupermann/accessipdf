"""Zerlegen und Zusammensetzen von Content-Streams, byte-treu bis auf gewollte Einfügungen."""

import pikepdf


def parse_ops(stream_owner) -> list:
    """Zerlegt den Content-Stream einer Seite oder eines Form-XObjects in Instruktionen."""
    return list(pikepdf.parse_content_stream(stream_owner))


def write_ops(pdf: pikepdf.Pdf, stream_owner, ops: list) -> None:
    """Ersetzt den Content-Stream durch die gegebenen Instruktionen.

    Für Seiten wird /Contents als ein einzelner Stream neu gesetzt, für
    Form-XObjects der Stream-Inhalt selbst.
    """
    daten = pikepdf.unparse_content_stream(ops)
    if "/Type" in stream_owner and stream_owner.Type == pikepdf.Name.Page:
        stream_owner.Contents = pdf.make_stream(daten)
    else:
        stream_owner.write(daten)
