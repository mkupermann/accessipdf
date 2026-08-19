from accessipdf.cli import main
from accessipdf.testkit import mini_pdf


def test_identify_nennt_layout(demo_pdf, capsys):
    rc = main(["identify", str(demo_pdf)])
    assert rc == 0
    assert "acme-demo" in capsys.readouterr().out


def test_identify_fremdes_pdf(tmp_path, capsys):
    pfad = mini_pdf(tmp_path / "fremd.pdf")
    rc = main(["identify", str(pfad)])
    assert rc == 1
    assert "unbekannt" in capsys.readouterr().out


def test_check_unbehandelte_datei_faellt_durch(demo_pdf):
    assert main(["check", str(demo_pdf)]) == 1


def test_convert_ganzer_ordner(demo_pdf, tmp_path, capsys):
    rc = main(
        ["convert", str(demo_pdf.parent), str(tmp_path / "aus"),
         "--quarantaene", str(tmp_path / "quar")]
    )
    assert rc == 0
    assert "ok" in capsys.readouterr().out
