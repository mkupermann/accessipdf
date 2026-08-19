"""Synthetic demo invoice for examples and tests.

Builds a deliberately inaccessible, fictional invoice PDF (no tags, no
ToUnicode maps, non-embedded standard fonts) so the full pipeline can be
demonstrated without any real customer data.

Usage:
    python -m accessipdf.demo demo_invoice.pdf
"""

import sys

import pikepdf


def build_demo_invoice(path: str) -> str:
    pdf = pikepdf.new()
    fonts = pikepdf.Dictionary(
        F1=pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name.Helvetica,
            Encoding=pikepdf.Name.WinAnsiEncoding,
        ),
        F2=pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name("/Type1"),
            BaseFont=pikepdf.Name("/Helvetica-Bold"),
            Encoding=pikepdf.Name.WinAnsiEncoding,
        ),
    )
    page = pikepdf.Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=[0, 0, 595, 842],
        Resources=pikepdf.Dictionary(Font=fonts),
    )

    def line(font: str, size: int, x: int, y: int, text: str) -> bytes:
        return f"BT /{font} {size} Tf {x} {y} Td ({text}) Tj ET\n".encode("latin-1")

    content = b""
    # Letterhead
    content += line("F2", 16, 60, 780, "ACME Utilities Ltd.")
    content += b"q 0.2 0.4 0.8 rg 60 770 475 2 re f Q\n"  # decorative rule
    # Recipient
    content += line("F1", 11, 60, 700, "Jane Doe")
    content += line("F1", 11, 60, 685, "42 Sample Street")
    content += line("F1", 11, 60, 670, "12345 Springfield")
    # Invoice metadata
    content += line("F1", 10, 350, 700, "Invoice no: INV-2026-001")
    content += line("F1", 10, 350, 685, "Date: 19 August 2026")
    content += line("F1", 10, 350, 670, "Customer: C-1007")
    # Heading
    content += line("F2", 14, 60, 600, "Your invoice for July 2026")
    # Items table
    content += line("F2", 10, 60, 560, "Item")
    content += line("F2", 10, 300, 560, "Qty")
    content += line("F2", 10, 380, 560, "Unit price")
    content += line("F2", 10, 470, 560, "Total")
    content += line("F1", 10, 60, 535, "Internet flat 100 Mbit")
    content += line("F1", 10, 300, 535, "1")
    content += line("F1", 10, 380, 535, "39.90")
    content += line("F1", 10, 470, 535, "39.90")
    content += line("F1", 10, 60, 510, "Phone minutes")
    content += line("F1", 10, 300, 510, "120")
    content += line("F1", 10, 380, 510, "0.02")
    content += line("F1", 10, 470, 510, "2.40")
    content += line("F2", 10, 60, 480, "Total (net)")
    content += line("F2", 10, 470, 480, "42.30")
    content += line("F1", 10, 60, 455, "VAT 19%")
    content += line("F1", 10, 470, 455, "8.04")
    content += line("F2", 10, 60, 430, "Amount due")
    content += line("F2", 10, 470, 430, "50.34")
    # Closing paragraph
    content += line("F1", 10, 60, 370, "Payment is due within 14 days. We will collect the amount by")
    content += line("F1", 10, 60, 355, "direct debit from your registered bank account.")
    content += line("F1", 10, 60, 320, "Thank you for choosing ACME Utilities.")
    # Small print footer (running content, will be tagged as artifact)
    content += line("F1", 7, 60, 50, "ACME Utilities Ltd. - 1 Demo Road - Springfield - Registered: HRB 00000")

    page = pdf.make_indirect(page)
    page.Contents = pdf.make_stream(content)
    pdf.pages.append(pikepdf.Page(page))
    pdf.save(path)
    return path


if __name__ == "__main__":
    ziel = sys.argv[1] if len(sys.argv) > 1 else "demo_invoice.pdf"
    build_demo_invoice(ziel)
    print(f"demo invoice written to {ziel}")
