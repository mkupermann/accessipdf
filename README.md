# accessipdf

**Make existing PDFs accessible.** accessipdf converts PDFs from known layouts
(invoices, statements, any template-generated documents) into fully tagged,
**PDF/UA-1 conformant accessible PDFs** — while keeping the visual appearance
pixel-identical. No commercial SDK, no AI guessing: deterministic rules per
layout, validated by [veraPDF](https://verapdf.org/) on every single file.

![Demo](docs/media/demo.gif)

https://github.com/mkupermann/accessipdf/raw/main/docs/media/demo.mp4

*(Full video with timing: [docs/media/demo.mp4](docs/media/demo.mp4))*

## Why

Millions of archived and freshly generated PDFs fail screen readers: no tag
structure, no Unicode mappings, fonts not embedded. Accessibility laws (EU
European Accessibility Act, German BFSG, US Section 508) increasingly require
accessible documents — including the ones you already have. Re-generating them
is often impossible; retrofitting them must not change a single pixel.

accessipdf retrofits. The original file is never touched; the output is a new,
byte-for-byte visually identical PDF that carries the full invisible
accessibility layer.

## What it does

For every PDF, five stages:

1. **Extract** — parse content streams, track the graphics state, recover every
   text operator with its position and decoded text (pikepdf + pypdfium2).
2. **Identify** — match the file against registered YAML layout templates via
   anchor texts. Unknown layouts are quarantined with a machine-readable
   report, never guessed.
3. **Assign semantics** — the template maps zones to roles: headings,
   paragraphs, real tables with header cells (`TR`/`TH`/`TD` incl. multi-page
   tables), decorative content as artifacts, plus reading order.
4. **Tag & repair** — rewrite content streams with marked content (`BDC`/`EMC`
   + MCIDs), build the structure tree, set language/title/XMP PDF/UA
   identifier, and **repair fonts**: generate missing `ToUnicode` CMaps, embed
   non-embedded standard fonts with metric-compatible Liberation faces
   (bold stays bold), fix `CIDToGIDMap`, drop broken `CIDSet`s.
5. **Gate** — veraPDF validates the result against PDF/UA-1. Green goes to the
   output directory (atomic move), red goes to quarantine with the full rule
   report. No silent green, ever.

Processing is idempotent (SHA-256 registry) and fast: ~0.1–0.15 s per invoice
for the engine itself; the per-file veraPDF JVM start dominates wall time
(~0.7 s).

## Quickstart

Requirements: Python ≥ 3.12, veraPDF CLI on the PATH (`brew install verapdf`
on macOS, or the [installer](https://verapdf.org/software/)).

```bash
git clone https://github.com/mkupermann/accessipdf
cd accessipdf
make setup

# generate the synthetic, deliberately inaccessible demo invoice
.venv/bin/python -m accessipdf.demo demo_invoice.pdf

.venv/bin/accessipdf check demo_invoice.pdf        # FAIL — untagged, broken fonts
.venv/bin/accessipdf identify demo_invoice.pdf     # Layout: acme-demo
.venv/bin/accessipdf convert demo_invoice.pdf out/ # tag, repair, validate
.venv/bin/accessipdf check out/demo_invoice.pdf    # PASS — PDF/UA-1
```

Exit codes of `convert`: `0` all green, `1` at least one file quarantined,
`2` hard error.

## Adding your own layout

One YAML per layout under `accessipdf/templates/vorlagen/` — see
[`acme-demo.yaml`](accessipdf/templates/vorlagen/acme-demo.yaml) as the
reference. Zone order defines the reading order; table zones only apply on
pages where their header anchors are found:

```yaml
name: my-layout
sprache: en-US
titel_muster: "Invoice {invoice_no}"
erkennung:
  - { text: "My Company Ltd.", seite: 1, bbox: [50, 770, 300, 800] }
zonen:
  - { name: subject, seiten: "1", bbox: [50, 590, 400, 620], rolle: H1 }
  - name: items
    seiten: alle
    bbox: [50, 420, 560, 575]
    rolle: Table
    kopf_anker: ["Item", "Unit price"]
    spalten: [290, 370, 460]
unbekannt_als: P
```

`scripts/zonen_dump.py your.pdf 1 2` prints every text operator with its
coordinates so you can measure the zones.

## How it is verified

Every conversion has to pass three independent gates — this is enforced by the
pipeline and by the test suite (`make test`):

1. **veraPDF, zero errors** against the PDF/UA-1 profile, per file.
2. **Pixel-identical rendering**: every page is rendered before and after and
   compared pixel by pixel. The single allowed exception is glyph-edge
   anti-aliasing noise after a font had to be embedded — and even then an
   erosion mask (9×9 kernel) proves the difference contains no solid area,
   i.e. nothing moved and nothing is missing.
3. **Lossless text extraction**: no line of previously extractable text may be
   lost. (It may get *better*: generating missing ToUnicode maps typically
   fixes previously garbled extraction — that is the point of PDF/UA.)

The test suite builds a synthetic, deliberately broken demo invoice (untagged,
no ToUnicode, non-embedded Helvetica/Helvetica-Bold) and drives it through the
full pipeline including the veraPDF gate. In its original production setting,
the engine converts real telecom invoices from two different layout families
with 13/13 files passing all three gates; those documents contain customer
data and are not part of this repository.

Machine-green is not the whole truth: for production use, run a manual
acceptance per layout with PAC 2024 and a screen reader (NVDA/VoiceOver).

## Limitations (by design)

- **Known layouts only.** Unknown PDFs are quarantined, not guessed at. This
  is not a generic AI auto-tagger — for uniform template-generated documents,
  deterministic rules beat guessing.
- **No scanned PDFs** (no OCR) and **no signed PDFs** (tagging breaks
  signatures — tag before signing).
- Zones are measured per layout; a redesigned layout needs a template update.
- Code identifiers and comments are currently German (the project originated
  in a German accessibility context). Contributions — including translation —
  are welcome.

## License

MIT (see [LICENSE](LICENSE)). The bundled Liberation fonts used for embedding
substitutes are licensed under the SIL Open Font License, see
[`accessipdf/assets/LIZENZ-LiberationSans.txt`](accessipdf/assets/LIZENZ-LiberationSans.txt).
veraPDF is invoked as an external tool and is not part of this distribution.
