import subprocess

import accessipdf
from accessipdf.validate.verapdf import verapdf_cmd


def test_paket_importierbar():
    assert accessipdf.__version__


def test_verapdf_erreichbar():
    ergebnis = subprocess.run(
        verapdf_cmd() + ["--version"], capture_output=True, text=True, timeout=120
    )
    assert ergebnis.returncode == 0
    assert "veraPDF" in ergebnis.stdout
