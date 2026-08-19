"""Kommandozeile, accessipdf convert | identify | check."""

import argparse
import sys
from pathlib import Path

import pikepdf

from accessipdf.pipeline import convert
from accessipdf.tagging.walker import walk_page
from accessipdf.templates.loader import identify as identify_template
from accessipdf.templates.loader import load_templates
from accessipdf.validate.verapdf import validate_ua1


def _cmd_convert(args) -> int:
    eingang = Path(args.eingang)
    dateien = sorted(eingang.glob("*.pdf")) if eingang.is_dir() else [eingang]
    if not dateien:
        print(f"keine PDF-Dateien in {eingang}")
        return 2
    quarantaene_getroffen = False
    for datei in dateien:
        ergebnis = convert(str(datei), args.ausgang, args.quarantaene)
        zusatz = f" ({ergebnis.grund})" if ergebnis.grund else ""
        print(f"{datei.name}: {ergebnis.status}{zusatz}")
        if ergebnis.status == "quarantaene":
            quarantaene_getroffen = True
        elif ergebnis.status == "fehler":
            return 2
    return 1 if quarantaene_getroffen else 0


def _cmd_identify(args) -> int:
    with pikepdf.open(args.datei) as pdf:
        seiten_textops = [walk_page(pdf, seite) for seite in pdf.pages]
    template = identify_template(seiten_textops, load_templates())
    if template is None:
        print("Layout: unbekannt")
        return 1
    print(f"Layout: {template.name}")
    return 0


def _cmd_check(args) -> int:
    ergebnis = validate_ua1(args.datei)
    print(f"PDF/UA-1: {'PASS' if ergebnis.passed else 'FAIL'}")
    for regel in ergebnis.failed_rules:
        print(f"  - {regel}")
    return 0 if ergebnis.passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="accessipdf",
        description="Wandelt Rechnungs-PDFs bekannter Layouts in barrierefreie "
        "PDFs nach PDF/UA-1 um, Erscheinungsbild 1 zu 1.",
    )
    unter = parser.add_subparsers(dest="befehl", required=True)

    p_convert = unter.add_parser("convert", help="Datei oder Verzeichnis umwandeln")
    p_convert.add_argument("eingang", help="PDF-Datei oder Verzeichnis")
    p_convert.add_argument("ausgang", help="Zielverzeichnis")
    p_convert.add_argument(
        "--quarantaene",
        default="quarantaene",
        help="Verzeichnis für nicht umwandelbare Dateien (Standard: quarantaene)",
    )
    p_convert.set_defaults(func=_cmd_convert)

    p_identify = unter.add_parser("identify", help="Layout einer Datei bestimmen")
    p_identify.add_argument("datei")
    p_identify.set_defaults(func=_cmd_identify)

    p_check = unter.add_parser("check", help="Datei gegen PDF/UA-1 prüfen")
    p_check.add_argument("datei")
    p_check.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
