"""Hilfen für Tests und Nachweise, Rendern, Pixel-Vergleich, Textextraktion.

Eigene, nicht versionierte Test-PDFs lassen sich über die Umgebungsvariable
ACCESSIPDF_SAMPLES einbinden. Tests darauf überspringen sich sauber, wenn sie
nicht gesetzt ist.
"""

from pathlib import Path

import pypdfium2 as pdfium
import pytest
from PIL import Image, ImageChops

import os

_samples_env = os.environ.get("ACCESSIPDF_SAMPLES")
SAMPLES_DIR = Path(_samples_env) if _samples_env else None


def require_samples():
    """pytest-Marker, überspringt Tests ohne lokales Beispielverzeichnis.

    Eigene, nicht versionierte PDFs über die Umgebungsvariable
    ACCESSIPDF_SAMPLES einbinden.
    """
    return pytest.mark.skipif(
        SAMPLES_DIR is None
        or not SAMPLES_DIR.is_dir()
        or not any(SAMPLES_DIR.glob("*.pdf")),
        reason="ACCESSIPDF_SAMPLES zeigt auf kein PDF-Verzeichnis",
    )


def sample_paths() -> list[Path]:
    if SAMPLES_DIR is None:
        return []
    return sorted(SAMPLES_DIR.glob("*.pdf"))


def mini_pdf(pfad):
    """Synthetisches Ein-Seiten-PDF mit zwei Textzeilen Helvetica und einer Deko-Fläche."""
    import pikepdf

    pdf = pikepdf.new()
    seite = pikepdf.Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=[0, 0, 595, 842],
        Resources=pikepdf.Dictionary(
            Font=pikepdf.Dictionary(
                F1=pikepdf.Dictionary(
                    Type=pikepdf.Name.Font,
                    Subtype=pikepdf.Name.Type1,
                    BaseFont=pikepdf.Name.Helvetica,
                    Encoding=pikepdf.Name.WinAnsiEncoding,
                )
            )
        ),
    )
    inhalt = b"""BT /F1 12 Tf 72 700 Td (Erste Zeile) Tj ET
BT /F1 12 Tf 72 680 Td (Zweite Zeile) Tj ET
q 1 0 0 1 0 0 cm 72 600 100 2 re f Q"""
    seite = pdf.make_indirect(seite)
    seite.Contents = pdf.make_stream(inhalt)
    pdf.pages.append(pikepdf.Page(seite))
    pdf.save(pfad)
    return pfad


def render_pages(pdf_path: str, scale: float = 2.0) -> list[Image.Image]:
    """Rendert alle Seiten als PIL-Bilder."""
    doc = pdfium.PdfDocument(pdf_path)
    try:
        return [seite.render(scale=scale).to_pil() for seite in doc]
    finally:
        doc.close()


def pixel_diff(a: Image.Image, b: Image.Image) -> int:
    """Anzahl der Pixel, die sich zwischen zwei Bildern unterscheiden."""
    if a.size != b.size:
        return a.size[0] * a.size[1]
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    histogramm = diff.convert("L").histogram()
    return sum(histogramm[1:])


def solid_diff_area(a: Image.Image, b: Image.Image, kern: int = 5) -> int:
    """Anzahl der Diff-Pixel, die in einem voll abweichenden kern-x-kern-Block liegen.

    Glyphenkanten-Rauschen nach einer Schrift-Einbettung ist 1 bis 2 Pixel dünn
    und verschwindet bei der Erosion. Flächige Abweichungen (verschobener oder
    fehlender Inhalt) überleben sie und zählen.
    """
    from PIL import ImageFilter

    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L")
    binaer = diff.point(lambda v: 255 if v else 0)
    erodiert = binaer.filter(ImageFilter.MinFilter(kern))
    return sum(erodiert.histogram()[1:])


def extract_text(pdf_path: str) -> list[str]:
    """Extrahiert den Text jeder Seite über pypdfium2."""
    doc = pdfium.PdfDocument(pdf_path)
    try:
        return [seite.get_textpage().get_text_bounded() for seite in doc]
    finally:
        doc.close()
