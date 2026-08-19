import pikepdf

from accessipdf.tagging.walker import walk_page
from accessipdf.templates.loader import identify, load_templates
from accessipdf.testkit import mini_pdf


def _textops(pfad):
    with pikepdf.open(pfad) as pdf:
        return [walk_page(pdf, seite) for seite in pdf.pages]


def test_templates_laden():
    templates = load_templates()
    assert "acme-demo" in {t.name for t in templates}
    for t in templates:
        assert t.zonen and t.erkennung


def test_identify_demo(demo_pdf):
    t = identify(_textops(demo_pdf), load_templates())
    assert t is not None and t.name == "acme-demo"


def test_identify_fremdes_pdf_ist_none(tmp_path):
    pfad = mini_pdf(tmp_path / "fremd.pdf")
    assert identify(_textops(pfad), load_templates()) is None
