import pytest

from accessipdf.demo import build_demo_invoice


@pytest.fixture(scope="session")
def demo_pdf(tmp_path_factory):
    """Die synthetische ACME-Demo-Rechnung, einmal je Testlauf erzeugt."""
    pfad = tmp_path_factory.mktemp("demo") / "demo_invoice.pdf"
    build_demo_invoice(str(pfad))
    return pfad
