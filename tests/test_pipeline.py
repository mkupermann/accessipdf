import hashlib
import json

from accessipdf.pipeline import convert
from accessipdf.testkit import mini_pdf


def _hash(pfad) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def test_unbekanntes_layout_geht_in_quarantaene(tmp_path):
    quelle = mini_pdf(tmp_path / "fremd.pdf")
    ausgang = tmp_path / "ausgang"
    quarantaene = tmp_path / "quarantaene"
    vorher = _hash(quelle)

    ergebnis = convert(str(quelle), str(ausgang), str(quarantaene))

    assert ergebnis.status == "quarantaene"
    assert "unbekanntes Layout" in (ergebnis.grund or "")
    assert _hash(quelle) == vorher, "Original wurde verändert"
    assert not list(ausgang.glob("*.pdf"))
    bericht = quarantaene / "fremd.bericht.json"
    assert bericht.exists()
    assert json.loads(bericht.read_text(encoding="utf-8"))["grund"]
