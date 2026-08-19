"""Font-Helfer, Textdekodierung, TTF-cmap-Parser, Breiten.

Wird vom Walker (Positions- und Textbestimmung) und von der Font-Reparatur
(ToUnicode-Erzeugung) gemeinsam genutzt.
"""

import struct
from pathlib import Path

import pikepdf

# ---------------------------------------------------------------- WinAnsi ---


def winansi_map(font) -> dict[int, str]:
    """Code → Unicode für Simple-Fonts mit WinAnsi- oder Standard-Encoding."""
    tabelle: dict[int, str] = {}
    for code in range(256):
        try:
            zeichen = bytes([code]).decode("cp1252")
        except UnicodeDecodeError:
            continue
        tabelle[code] = zeichen
    enc = font.get("/Encoding")
    if isinstance(enc, pikepdf.Dictionary) and "/Differences" in enc:
        # Differences: Zahl setzt den Code, folgende Namen belegen aufsteigend.
        code = 0
        for eintrag in enc.Differences:
            if isinstance(eintrag, (int, pikepdf.Object)) and not isinstance(
                eintrag, pikepdf.Name
            ):
                try:
                    code = int(eintrag)
                    continue
                except (TypeError, ValueError):
                    pass
            name = str(eintrag).lstrip("/")
            uni = _glyphname_to_unicode(name)
            if uni:
                tabelle[code] = uni
            code += 1
    return tabelle


def _glyphname_to_unicode(name: str) -> str | None:
    """Kleine Auflösung gängiger Glyphennamen, uniXXXX und Einzelbuchstaben."""
    if name.startswith("uni") and len(name) == 7:
        try:
            return chr(int(name[3:], 16))
        except ValueError:
            return None
    if len(name) == 1:
        return name
    haeufig = {
        "space": " ", "period": ".", "comma": ",", "hyphen": "-", "colon": ":",
        "adieresis": "ä", "odieresis": "ö", "udieresis": "ü",
        "Adieresis": "Ä", "Odieresis": "Ö", "Udieresis": "Ü",
        "germandbls": "ß", "Euro": "€", "slash": "/", "parenleft": "(",
        "parenright": ")", "plus": "+", "ampersand": "&", "at": "@",
    }
    return haeufig.get(name)


# ------------------------------------------------------------- TTF-cmap -----


def parse_ttf_cmap(fontdaten: bytes) -> dict[int, int]:
    """Liest die cmap einer TrueType-Datei, Unicode → Glyph-ID.

    Unterstützt Format 4, 6 und 12. Liefert leer, wenn keine lesbare
    Unicode-cmap vorhanden ist, es wird nie geraten.
    """
    try:
        num_tables = struct.unpack_from(">H", fontdaten, 4)[0]
        cmap_offset = None
        for i in range(num_tables):
            tag, _, offset, _ = struct.unpack_from(">4sIII", fontdaten, 12 + 16 * i)
            if tag == b"cmap":
                cmap_offset = offset
                break
        if cmap_offset is None:
            return {}
        anzahl = struct.unpack_from(">H", fontdaten, cmap_offset + 2)[0]
        kandidaten = []
        for i in range(anzahl):
            plat, enc, sub_off = struct.unpack_from(
                ">HHI", fontdaten, cmap_offset + 4 + 8 * i
            )
            kandidaten.append((plat, enc, cmap_offset + sub_off))
        # Bevorzugt Windows-BMP (3,1), dann Windows-UCS4 (3,10), dann Unicode (0,x)
        def rang(k):
            plat, enc, _ = k
            if (plat, enc) == (3, 1):
                return 0
            if (plat, enc) == (3, 10):
                return 1
            if plat == 0:
                return 2
            return 3

        for _, _, sub in sorted(kandidaten, key=rang):
            fmt = struct.unpack_from(">H", fontdaten, sub)[0]
            if fmt == 4:
                return _cmap_format4(fontdaten, sub)
            if fmt == 6:
                return _cmap_format6(fontdaten, sub)
            if fmt == 12:
                return _cmap_format12(fontdaten, sub)
        return {}
    except (struct.error, IndexError):
        return {}


def _cmap_format4(d: bytes, off: int) -> dict[int, int]:
    seg_x2 = struct.unpack_from(">H", d, off + 6)[0]
    segs = seg_x2 // 2
    end_off = off + 14
    start_off = end_off + seg_x2 + 2
    delta_off = start_off + seg_x2
    range_off = delta_off + seg_x2
    ergebnis: dict[int, int] = {}
    for i in range(segs):
        ende = struct.unpack_from(">H", d, end_off + 2 * i)[0]
        start = struct.unpack_from(">H", d, start_off + 2 * i)[0]
        delta = struct.unpack_from(">h", d, delta_off + 2 * i)[0]
        r_off = struct.unpack_from(">H", d, range_off + 2 * i)[0]
        if start == 0xFFFF:
            continue
        for c in range(start, min(ende, 0xFFFE) + 1):
            if r_off == 0:
                gid = (c + delta) & 0xFFFF
            else:
                adr = range_off + 2 * i + r_off + 2 * (c - start)
                if adr + 2 > len(d):
                    continue
                gid = struct.unpack_from(">H", d, adr)[0]
                if gid:
                    gid = (gid + delta) & 0xFFFF
            if gid:
                ergebnis[c] = gid
    return ergebnis


def _cmap_format6(d: bytes, off: int) -> dict[int, int]:
    first, count = struct.unpack_from(">HH", d, off + 6)
    return {
        first + i: struct.unpack_from(">H", d, off + 10 + 2 * i)[0]
        for i in range(count)
        if struct.unpack_from(">H", d, off + 10 + 2 * i)[0]
    }


def _cmap_format12(d: bytes, off: int) -> dict[int, int]:
    gruppen = struct.unpack_from(">I", d, off + 12)[0]
    ergebnis: dict[int, int] = {}
    for i in range(gruppen):
        start, ende, start_gid = struct.unpack_from(">III", d, off + 16 + 12 * i)
        for c in range(start, ende + 1):
            ergebnis[c] = start_gid + (c - start)
    return ergebnis


# ------------------------------------------------------ Font-Beschreibung ---


def _fontfile_bytes(font) -> bytes | None:
    desc = font.get("/FontDescriptor")
    if desc is None and font.get("/Subtype") == pikepdf.Name.Type0:
        desc = font.DescendantFonts[0].get("/FontDescriptor")
    if desc is None:
        return None
    for schluessel in ("/FontFile2", "/FontFile3", "/FontFile"):
        if schluessel in desc:
            return bytes(desc[schluessel].read_bytes())
    return None


class FontInfo:
    """Dekodierung und Breiten für einen PDF-Font, einmal aufgebaut je Font-Objekt."""

    def __init__(self, font: pikepdf.Object):
        self.font = font
        self.subtype = str(font.get("/Subtype", ""))
        self.ist_type0 = self.subtype == "/Type0"
        self._code_zu_unicode: dict[int, str] = {}
        self._breiten: dict[int, float] = {}
        self._standardbreite = 500.0
        if self.ist_type0:
            self._init_type0()
        else:
            self._init_simple()

    # -- Aufbau --

    def _init_simple(self):
        self._code_zu_unicode = winansi_map(self.font)
        first = self.font.get("/FirstChar")
        widths = self.font.get("/Widths")
        if first is not None and widths is not None:
            f = int(first)
            for i, w in enumerate(widths):
                self._breiten[f + i] = float(w)

    def _init_type0(self):
        df = self.font.DescendantFonts[0]
        dw = df.get("/DW")
        self._standardbreite = float(dw) if dw is not None else 1000.0
        w = df.get("/W")
        if w is not None:
            self._breiten = _parse_cid_widths(w)
        daten = _fontfile_bytes(self.font)
        if daten:
            uni_zu_gid = parse_ttf_cmap(daten)
            # Identity-H, CID == GID (CIDToGIDMap fehlt oder /Identity)
            gid_zu_uni: dict[int, str] = {}
            for uni, gid in uni_zu_gid.items():
                gid_zu_uni.setdefault(gid, chr(uni))
            self._code_zu_unicode = gid_zu_uni

    # -- Nutzung --

    def codes(self, raw: bytes) -> list[int]:
        if self.ist_type0:
            return [
                (raw[i] << 8) | raw[i + 1] for i in range(0, len(raw) - 1, 2)
            ]
        return list(raw)

    def decode(self, raw: bytes) -> tuple[str, bool]:
        """Bytes → Text. Zweiter Wert True, wenn Zeichen nicht dekodierbar waren."""
        luecke = False
        teile = []
        for code in self.codes(raw):
            zeichen = self._code_zu_unicode.get(code)
            if zeichen is None:
                luecke = True
            else:
                teile.append(zeichen)
        return "".join(teile), luecke

    def unicode_map(self) -> dict[int, str]:
        return dict(self._code_zu_unicode)

    def breite(self, code: int) -> float:
        return self._breiten.get(code, self._standardbreite)


def _parse_cid_widths(w) -> dict[int, float]:
    """Parst das /W-Array eines CID-Fonts, beide Schreibweisen."""
    ergebnis: dict[int, float] = {}
    eintraege = list(w)
    i = 0
    while i < len(eintraege):
        erster = int(eintraege[i])
        zweiter = eintraege[i + 1]
        if isinstance(zweiter, pikepdf.Array) or isinstance(zweiter, list):
            for j, breite in enumerate(zweiter):
                ergebnis[erster + j] = float(breite)
            i += 2
        else:
            letzter = int(zweiter)
            breite = float(eintraege[i + 2])
            for cid in range(erster, letzter + 1):
                ergebnis[cid] = breite
            i += 3
    return ergebnis


def fontinfo(font: pikepdf.Object, cache: dict | None = None) -> FontInfo:
    """FontInfo, optional mit Cache je Aufrufkontext (Schlüssel objgen)."""
    if cache is None:
        return FontInfo(font)
    try:
        objgen = font.objgen
    except AttributeError:
        return FontInfo(font)
    if objgen not in cache:
        cache[objgen] = FontInfo(font)
    return cache[objgen]


# ------------------------------------------------------------- Reparatur ----

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
LIBERATION_SANS = _ASSETS / "LiberationSans-Regular.ttf"

# Exakte BaseFont-Namen der Standard-14-Schriften und ihr metrisch
# kompatibler, frei lizenzierter Liberation-Ersatz.
STANDARD_ERSATZ: dict[str, tuple[str, str]] = {
    "Helvetica": ("LiberationSans", "LiberationSans-Regular.ttf"),
    "Helvetica-Bold": ("LiberationSans-Bold", "LiberationSans-Bold.ttf"),
    "Helvetica-Oblique": ("LiberationSans-Italic", "LiberationSans-Italic.ttf"),
    "Helvetica-BoldOblique": (
        "LiberationSans-BoldItalic",
        "LiberationSans-BoldItalic.ttf",
    ),
    "Times-Roman": ("LiberationSerif", "LiberationSerif-Regular.ttf"),
    "Times-Bold": ("LiberationSerif-Bold", "LiberationSerif-Bold.ttf"),
    "Times-Italic": ("LiberationSerif-Italic", "LiberationSerif-Italic.ttf"),
    "Times-BoldItalic": (
        "LiberationSerif-BoldItalic",
        "LiberationSerif-BoldItalic.ttf",
    ),
    "Courier": ("LiberationMono", "LiberationMono-Regular.ttf"),
    "Courier-Bold": ("LiberationMono-Bold", "LiberationMono-Bold.ttf"),
    "Courier-Oblique": ("LiberationMono-Italic", "LiberationMono-Italic.ttf"),
    "Courier-BoldOblique": (
        "LiberationMono-BoldItalic",
        "LiberationMono-BoldItalic.ttf",
    ),
}


class FontReparaturFehler(Exception):
    """Ein Font kann nicht PDF/UA-tauglich gemacht werden."""


def iter_fonts(pdf: pikepdf.Pdf):
    """Alle Fonts aus Seiten und Form-XObjects, je Objekt einmal.

    Liefert (resources, name, font).
    """
    gesehen: set[tuple] = set()

    def aus_resources(res, tiefe=6):
        if res is None or tiefe <= 0:
            return
        for name, font in (res.get("/Font") or {}).items():
            try:
                kennung = font.objgen
            except AttributeError:
                kennung = None
            if kennung == (0, 0):
                # Direkte Objekte tragen alle (0, 0), das ist keine Identität.
                kennung = None
            if kennung is not None:
                if kennung in gesehen:
                    continue
                gesehen.add(kennung)
            yield res, name, font
        for _, xobj in (res.get("/XObject") or {}).items():
            if xobj.get("/Subtype") == pikepdf.Name.Form:
                yield from aus_resources(xobj.get("/Resources"), tiefe - 1)

    for seite in pdf.pages:
        yield from aus_resources(seite.get("/Resources"))


def _cmap_daten(code_zu_unicode: dict[int, str], zwei_byte: bool) -> bytes:
    breite = 4 if zwei_byte else 2
    zeilen = [
        b"/CIDInit /ProcSet findresource begin",
        b"12 dict begin",
        b"begincmap",
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
        b"/CMapName /Adobe-Identity-UCS def",
        b"/CMapType 2 def",
        b"1 begincodespacerange",
        (
            b"<0000> <FFFF>" if zwei_byte else b"<00> <FF>"
        ),
        b"endcodespacerange",
    ]
    eintraege = sorted(code_zu_unicode.items())
    for start in range(0, len(eintraege), 100):
        block = eintraege[start : start + 100]
        zeilen.append(f"{len(block)} beginbfchar".encode())
        for code, zeichen in block:
            utf16 = zeichen.encode("utf-16-be").hex().upper()
            zeilen.append(f"<{code:0{breite}X}> <{utf16}>".encode())
        zeilen.append(b"endbfchar")
    zeilen += [
        b"endcmap",
        b"CMapName currentdict /CMap defineresource pop",
        b"end",
        b"end",
    ]
    return b"\n".join(zeilen)


def fix_cidtogid(pdf: pikepdf.Pdf) -> list[str]:
    """Setzt fehlende CIDToGIDMap-Einträge eingebetteter CIDFontType2 auf /Identity."""
    repariert = []
    for _, name, font in iter_fonts(pdf):
        if font.get("/Subtype") != pikepdf.Name.Type0:
            continue
        df = font.DescendantFonts[0]
        if df.get("/Subtype") == pikepdf.Name.CIDFontType2 and "/CIDToGIDMap" not in df:
            df.CIDToGIDMap = pikepdf.Name.Identity
            repariert.append(str(font.get("/BaseFont", name)))
    return repariert


def drop_incomplete_cidset(pdf: pikepdf.Pdf) -> list[str]:
    """Entfernt CIDSet-Streams aus FontDescriptoren.

    Die Aspose-Erzeugung liefert CIDSets, die nicht alle im Fontprogramm
    vorhandenen CIDs ausweisen, das verletzt PDF/UA-1 (ISO 14289-1, 7.21.4.2).
    Der Eintrag ist optional, ohne ihn ist die Datei konform.
    """
    entfernt = []
    for _, name, font in iter_fonts(pdf):
        beschreiber = []
        if "/FontDescriptor" in font:
            beschreiber.append(font.FontDescriptor)
        if font.get("/Subtype") == pikepdf.Name.Type0:
            df = font.DescendantFonts[0]
            if "/FontDescriptor" in df:
                beschreiber.append(df.FontDescriptor)
        for desc in beschreiber:
            if "/CIDSet" in desc:
                del desc.CIDSet
                entfernt.append(str(font.get("/BaseFont", name)))
    return entfernt


def ensure_tounicode(pdf: pikepdf.Pdf) -> list[str]:
    """Erzeugt fehlende ToUnicode-CMaps. Nicht Ableitbares löst einen Fehler aus."""
    repariert: list[str] = []
    for _, name, font in iter_fonts(pdf):
        if "/ToUnicode" in font:
            continue
        info = FontInfo(font)
        tabelle = info.unicode_map()
        if not tabelle:
            raise FontReparaturFehler(
                f"Font {font.get('/BaseFont')} ohne ableitbare Unicode-Zuordnung"
            )
        font.ToUnicode = pdf.make_stream(_cmap_daten(tabelle, info.ist_type0))
        repariert.append(str(font.get("/BaseFont", name)))
    return repariert


def _ttf_tabellen(d: bytes) -> dict[bytes, tuple[int, int]]:
    anzahl = struct.unpack_from(">H", d, 4)[0]
    return {
        struct.unpack_from(">4s", d, 12 + 16 * i)[0]: struct.unpack_from(
            ">II", d, 12 + 16 * i + 8
        )
        for i in range(anzahl)
    }


def ttf_metrics(d: bytes) -> dict:
    """Kennzahlen einer TrueType-Datei, skaliert auf 1000er-Einheiten."""
    tabellen = _ttf_tabellen(d)
    head_off = tabellen[b"head"][0]
    upem = struct.unpack_from(">H", d, head_off + 18)[0]
    bbox = struct.unpack_from(">hhhh", d, head_off + 36)
    hhea_off = tabellen[b"hhea"][0]
    ascent, descent = struct.unpack_from(">hh", d, hhea_off + 4)
    num_h = struct.unpack_from(">H", d, hhea_off + 34)[0]
    hmtx_off = tabellen[b"hmtx"][0]
    faktor = 1000.0 / upem

    def advance(gid: int) -> float:
        idx = min(gid, num_h - 1)
        return struct.unpack_from(">H", d, hmtx_off + 4 * idx)[0] * faktor

    cap_height = int(ascent * faktor)
    if b"OS/2" in tabellen:
        os2_off, os2_len = tabellen[b"OS/2"]
        version = struct.unpack_from(">H", d, os2_off)[0]
        if version >= 2 and os2_len >= 90:
            cap_height = int(struct.unpack_from(">h", d, os2_off + 88)[0] * faktor)
    return {
        "unitsPerEm": upem,
        "bbox": tuple(int(v * faktor) for v in bbox),
        "ascent": int(ascent * faktor),
        "descent": int(descent * faktor),
        "cap_height": cap_height,
        "advance": advance,
        "cmap": parse_ttf_cmap(d),
    }


def _ist_eingebettet(font) -> bool:
    desc = font.get("/FontDescriptor")
    if desc is None and font.get("/Subtype") == pikepdf.Name.Type0:
        desc = font.DescendantFonts[0].get("/FontDescriptor")
    return desc is not None and any(
        s in desc for s in ("/FontFile", "/FontFile2", "/FontFile3")
    )


def _embed_font(pdf, font, neuer_name: str, daten: bytes, metrik: dict, fontfile) -> None:
    breiten = []
    for code in range(32, 256):
        try:
            zeichen = bytes([code]).decode("cp1252")
        except UnicodeDecodeError:
            breiten.append(0)
            continue
        gid = metrik["cmap"].get(ord(zeichen))
        breiten.append(round(metrik["advance"](gid)) if gid else 0)

    fett = "Bold" in neuer_name
    kursiv = "Italic" in neuer_name
    neuer_desc = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.FontDescriptor,
            FontName=pikepdf.Name("/" + neuer_name),
            Flags=32,
            FontBBox=list(metrik["bbox"]),
            ItalicAngle=-12 if kursiv else 0,
            Ascent=metrik["ascent"],
            Descent=metrik["descent"],
            CapHeight=metrik["cap_height"],
            StemV=140 if fett else 88,
            FontFile2=fontfile,
        )
    )
    font.Subtype = pikepdf.Name.TrueType
    font.BaseFont = pikepdf.Name("/" + neuer_name)
    font.FirstChar = 32
    font.LastChar = 255
    font.Widths = breiten
    font.FontDescriptor = neuer_desc
    if "/Encoding" not in font:
        font.Encoding = pikepdf.Name.WinAnsiEncoding


def embed_standard_fonts(pdf: pikepdf.Pdf) -> list[str]:
    """Bettet nicht eingebettete Standard-14-Schriften stilgetreu als Liberation ein.

    Exakte BaseFont-Zuordnung, Helvetica-Bold wird LiberationSans-Bold, nie ein
    anderer Schnitt. Nicht zuordenbare, nicht eingebettete Fonts lösen einen
    Fehler aus, statt still falsch ersetzt zu werden.
    """
    ersetzt: list[str] = []
    geladene: dict[str, tuple[bytes, dict, object]] = {}
    for _, _, font in iter_fonts(pdf):
        if font.get("/Subtype") == pikepdf.Name.Type0 or _ist_eingebettet(font):
            continue
        base = str(font.get("/BaseFont", "")).lstrip("/")
        if "+" in base:
            base = base.split("+", 1)[1]
        if base not in STANDARD_ERSATZ:
            raise FontReparaturFehler(
                f"nicht eingebetteter Font {base} ohne bekannten Ersatz"
            )
        neuer_name, dateiname = STANDARD_ERSATZ[base]
        if neuer_name not in geladene:
            daten = (_ASSETS / dateiname).read_bytes()
            fontfile = pdf.make_stream(daten)
            fontfile.Length1 = len(daten)
            geladene[neuer_name] = (daten, ttf_metrics(daten), fontfile)
        daten, metrik, fontfile = geladene[neuer_name]
        _embed_font(pdf, font, neuer_name, daten, metrik, fontfile)
        ersetzt.append(f"{base} → {neuer_name}")
    return ersetzt
