"""Baut den Strukturbaum aus den Bausteinen (Absätze, Tabellen)."""

import pikepdf

from accessipdf.core.model import Absatz, Tabelle


def fuelle_mcids(bausteine: list, mcid_je_seq: dict[int, int]) -> None:
    """Überträgt die von wrap_page vergebenen MCIDs in die Bausteine."""
    for baustein in bausteine:
        if isinstance(baustein, Absatz):
            baustein.mcids = [
                mcid_je_seq[s] for s in baustein.seqs if s in mcid_je_seq
            ]
        elif isinstance(baustein, Tabelle):
            for zeile in baustein.zeilen:
                for zelle in zeile.zellen:
                    zelle.mcids = [
                        mcid_je_seq[s] for s in zelle.seqs if s in mcid_je_seq
                    ]


def build_structure(pdf: pikepdf.Pdf, seiten: list[tuple]) -> None:
    """Erzeugt StructTreeRoot, ParentTree und MarkInfo.

    seiten: Liste von (Seite, Bausteine) in Leseordnung. Tabellen gleichen
    Namens auf aufeinanderfolgenden Seiten werden zu einem Table-Element
    zusammengeführt (mehrseitige Positionslisten).
    """
    struct_root = pdf.make_indirect(
        pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot)
    )
    dokument = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.StructElem,
            S=pikepdf.Name.Document,
            P=struct_root,
            K=pikepdf.Array(),
        )
    )
    struct_root.K = dokument

    def elem(rolle: str, parent, seite, kinder=None, alt: str | None = None):
        e = pikepdf.Dictionary(
            Type=pikepdf.Name.StructElem,
            S=pikepdf.Name("/" + rolle),
            P=parent,
            Pg=seite.obj,
        )
        if kinder is not None:
            e.K = kinder
        if alt:
            e.Alt = pikepdf.String(alt)
        return pdf.make_indirect(e)

    nums = pikepdf.Array()
    offene_tabellen: dict[str, pikepdf.Object] = {}

    for schluessel, (seite, bausteine) in enumerate(seiten):
        mcid_zu_elem: dict[int, pikepdf.Object] = {}
        tabellen_dieser_seite: set[str] = set()

        for baustein in bausteine:
            if isinstance(baustein, Absatz):
                if not baustein.mcids:
                    continue
                blatt = elem(
                    baustein.role,
                    dokument,
                    seite,
                    kinder=pikepdf.Array(baustein.mcids),
                    alt=baustein.alt,
                )
                dokument.K.append(blatt)
                for mcid in baustein.mcids:
                    mcid_zu_elem[mcid] = blatt
            elif isinstance(baustein, Tabelle):
                tabellen_dieser_seite.add(baustein.name)
                tabelle_elem = offene_tabellen.get(baustein.name)
                if tabelle_elem is None:
                    tabelle_elem = elem("Table", dokument, seite, kinder=pikepdf.Array())
                    dokument.K.append(tabelle_elem)
                    offene_tabellen[baustein.name] = tabelle_elem
                for zeile in baustein.zeilen:
                    if not any(zelle.mcids for zelle in zeile.zellen):
                        continue
                    zeile_elem = elem("TR", tabelle_elem, seite, kinder=pikepdf.Array())
                    tabelle_elem.K.append(zeile_elem)
                    zellen_je_spalte = {z.spalte: z for z in zeile.zellen}
                    # PDF/UA verlangt gleich viele Spalten je Zeile, fehlende
                    # Zellen werden als leere Elemente aufgefüllt.
                    for spalte in range(baustein.n_spalten):
                        zelle = zellen_je_spalte.get(spalte)
                        rolle = "TH" if zeile.kopf else "TD"
                        kinder = (
                            pikepdf.Array(zelle.mcids)
                            if zelle is not None and zelle.mcids
                            else None
                        )
                        zelle_elem = elem(rolle, zeile_elem, seite, kinder=kinder)
                        if zeile.kopf:
                            zelle_elem.A = pikepdf.Dictionary(
                                O=pikepdf.Name.Table, Scope=pikepdf.Name.Column
                            )
                        zeile_elem.K.append(zelle_elem)
                        if zelle is not None:
                            for mcid in zelle.mcids:
                                mcid_zu_elem[mcid] = zelle_elem

        # Tabellen, die auf dieser Seite nicht weitergehen, sind abgeschlossen.
        for name in list(offene_tabellen):
            if name not in tabellen_dieser_seite:
                del offene_tabellen[name]

        seite.StructParents = schluessel
        rueckverweise = pikepdf.Array()
        hoechste = max(mcid_zu_elem, default=-1)
        for mcid in range(hoechste + 1):
            eintrag = mcid_zu_elem.get(mcid)
            rueckverweise.append(eintrag if eintrag is not None else None)
        nums.append(schluessel)
        nums.append(pdf.make_indirect(rueckverweise))

    struct_root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=nums))
    struct_root.ParentTreeNextKey = len(seiten)
    pdf.Root.StructTreeRoot = struct_root
    pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True)
