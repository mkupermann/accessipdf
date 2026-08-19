from accessipdf.validate.verapdf import validate_ua1


def test_unbehandelte_datei_faellt_durch(demo_pdf):
    ergebnis = validate_ua1(str(demo_pdf))
    assert ergebnis.passed is False
    assert ergebnis.failed_rules
    assert any("14289" in regel for regel in ergebnis.failed_rules)
