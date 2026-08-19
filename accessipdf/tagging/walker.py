"""Grafikzustands-Verfolgung, liefert Textoperatoren mit Position und Text.

Verfolgt cm/q/Q und die Textmatrix, steigt in Form-XObjects ab und dekodiert
den Text über die Font-Helfer. Was nicht sicher dekodierbar ist, bekommt
undecoded=True, es wird nie geraten.
"""

import pikepdf

from accessipdf.core.model import TextOp
from accessipdf.tagging.fonts import fontinfo
from accessipdf.tagging.tokenizer import parse_ops

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mmul(m1, m2):
    """Erst m1, dann m2 anwenden (Zeilenvektor-Konvention)."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + b1 * c2,
        a1 * b2 + b1 * d2,
        c1 * a2 + d1 * c2,
        c1 * b2 + d1 * d2,
        e1 * a2 + f1 * c2 + e2,
        e1 * b2 + f1 * d2 + f2,
    )


def tpoint(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def _translate(tx, ty):
    return (1.0, 0.0, 0.0, 1.0, tx, ty)


class _TextState:
    def __init__(self):
        self.tm = IDENT
        self.tlm = IDENT
        self.font_name = ""
        self.font = None
        self.size = 0.0
        self.leading = 0.0
        self.char_spacing = 0.0
        self.word_spacing = 0.0
        self.h_scale = 1.0
        self.rise = 0.0


def walk_page(pdf: pikepdf.Pdf, page, max_tiefe: int = 6) -> list[TextOp]:
    """Alle Textoperatoren der Seite inklusive Form-XObjects, in Streamreihenfolge."""
    ergebnis: list[TextOp] = []
    cache: dict = {}
    _walk_stream(
        pdf, page, page.get("/Resources"), IDENT, "page", ergebnis, max_tiefe, cache
    )
    return ergebnis


def _walk_stream(pdf, owner, resources, basis_ctm, stream_id, out, tiefe, cache):
    if tiefe <= 0:
        return
    ctm = basis_ctm
    stack: list[tuple] = []
    ts = _TextState()

    def show(seq, raw_bytes, ts):
        if ts.font is None:
            return
        info = fontinfo(ts.font, cache)
        text, luecke = info.decode(raw_bytes)
        vorschub = 0.0
        for code in info.codes(raw_bytes):
            breite = info.breite(code) / 1000.0 * ts.size + ts.char_spacing
            if not info.ist_type0 and code == 32:
                breite += ts.word_spacing
            vorschub += breite * ts.h_scale
        m = mmul(ts.tm, ctm)
        ecken = [
            tpoint(m, 0, -0.25 * ts.size + ts.rise),
            tpoint(m, 0, 0.85 * ts.size + ts.rise),
            tpoint(m, vorschub, -0.25 * ts.size + ts.rise),
            tpoint(m, vorschub, 0.85 * ts.size + ts.rise),
        ]
        xs = [p[0] for p in ecken]
        ys = [p[1] for p in ecken]
        out.append(
            TextOp(
                seq=seq,
                stream=stream_id,
                bbox=(min(xs), min(ys), max(xs), max(ys)),
                text=text,
                font=ts.font_name,
                size=ts.size,
                undecoded=luecke,
            )
        )
        ts.tm = mmul(_translate(vorschub, 0), ts.tm)

    for seq, (operanden, op) in enumerate(parse_ops(owner)):
        name = str(op)
        if name == "q":
            stack.append(ctm)
        elif name == "Q":
            if stack:
                ctm = stack.pop()
        elif name == "cm":
            ctm = mmul(tuple(float(x) for x in operanden), ctm)
        elif name == "BT":
            ts.tm = ts.tlm = IDENT
        elif name == "ET":
            pass
        elif name == "Tf":
            ts.font_name = str(operanden[0])
            ts.size = float(operanden[1])
            schriften = (resources or {}).get("/Font", {})
            ts.font = schriften.get(ts.font_name)
        elif name == "TL":
            ts.leading = float(operanden[0])
        elif name == "Tc":
            ts.char_spacing = float(operanden[0])
        elif name == "Tw":
            ts.word_spacing = float(operanden[0])
        elif name == "Tz":
            ts.h_scale = float(operanden[0]) / 100.0
        elif name == "Ts":
            ts.rise = float(operanden[0])
        elif name == "Td":
            ts.tlm = mmul(_translate(float(operanden[0]), float(operanden[1])), ts.tlm)
            ts.tm = ts.tlm
        elif name == "TD":
            ts.leading = -float(operanden[1])
            ts.tlm = mmul(_translate(float(operanden[0]), float(operanden[1])), ts.tlm)
            ts.tm = ts.tlm
        elif name == "Tm":
            ts.tlm = tuple(float(x) for x in operanden)
            ts.tm = ts.tlm
        elif name == "T*":
            ts.tlm = mmul(_translate(0, -ts.leading), ts.tlm)
            ts.tm = ts.tlm
        elif name == "Tj":
            show(seq, bytes(operanden[0]), ts)
        elif name == "'":
            ts.tlm = mmul(_translate(0, -ts.leading), ts.tlm)
            ts.tm = ts.tlm
            show(seq, bytes(operanden[0]), ts)
        elif name == '"':
            ts.word_spacing = float(operanden[0])
            ts.char_spacing = float(operanden[1])
            ts.tlm = mmul(_translate(0, -ts.leading), ts.tlm)
            ts.tm = ts.tlm
            show(seq, bytes(operanden[2]), ts)
        elif name == "TJ":
            for element in operanden[0]:
                if isinstance(element, (pikepdf.String, bytes)):
                    show(seq, bytes(element), ts)
                else:
                    versatz = -float(element) / 1000.0 * ts.size * ts.h_scale
                    ts.tm = mmul(_translate(versatz, 0), ts.tm)
        elif name == "Do":
            xobjekte = (resources or {}).get("/XObject", {})
            xobj = xobjekte.get(str(operanden[0]))
            if xobj is not None and xobj.get("/Subtype") == pikepdf.Name.Form:
                matrix = xobj.get("/Matrix")
                form_m = (
                    tuple(float(x) for x in matrix) if matrix is not None else IDENT
                )
                _walk_stream(
                    pdf,
                    xobj,
                    xobj.get("/Resources") or resources,
                    mmul(form_m, ctm),
                    f"{stream_id}/{str(operanden[0])}",
                    out,
                    tiefe - 1,
                    cache,
                )
