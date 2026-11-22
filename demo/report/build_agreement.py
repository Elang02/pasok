"""Build the one-page explanation of the 89.5% agreement figure.

Every number comes from data/sap/rpt_summary.json, which records the run of 15 October:
600 query rows, 0 predicted stockouts, 577 predicted expiry risks, 89.5% agreement, and
zero SKUs flagged by both models.
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT = Path(__file__).resolve().parent / "Pasok_sap_agreement.docx"
INK = RGBColor(0x1D, 0x1D, 0x1F)
GREY = RGBColor(0x5F, 0x5F, 0x5F)
ACCENT = RGBColor(0x4B, 0x2E, 0x83)


def head(doc, text, size=15, space_before=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    r.font.color.rgb = INK
    r.font.name = "Arial"
    return p


def body(doc, text, size=10.5, after=4, italic=False, colour=INK):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.18
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.italic = italic
    r.font.color.rgb = colour
    r.font.name = "Arial"
    return p


def numbered(doc, items, size=10.5):
    for i, text in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.28)
        p.paragraph_format.first_line_indent = Inches(-0.28)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.12
        r = p.add_run(f"{i}.  {text}")
        r.font.size = Pt(size)
        r.font.name = "Arial"
        r.font.color.rgb = INK


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def cell_text(cell, text, bold=False, size=9.5, colour=INK, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.space_before = Pt(1)
    if align:
        p.alignment = align
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.name = "Arial"
    r.font.color.rgb = colour


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.27)      # A4, like the other Pasok documents
    sec.page_height = Inches(11.69)
    sec.top_margin = Inches(0.45)
    sec.bottom_margin = Inches(0.45)
    sec.left_margin = Inches(0.8)
    sec.right_margin = Inches(0.8)

    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10)

    title = doc.add_paragraph()
    title.paragraph_format.space_after = Pt(2)
    r = title.add_run("Apa arti angka 89,5%")
    r.bold = True
    r.font.size = Pt(19)
    r.font.name = "Arial"
    r.font.color.rgb = INK

    body(doc, "Catatan untuk halaman 10, SAP dan AWS. Semua angka di halaman ini berasal dari "
              "satu kali pemanggilan SAP RPT-1.6 pada 15 Oktober 2026.", 10, 10, italic=True,
         colour=GREY)

    body(doc, "Angka 89,5% mengukur seberapa sering dua penilai memberi jawaban yang sama pada 600 SKU. "
              "Ia bukan akurasi, dan bukan bukti bahwa model kita benar. Tabel di bawah membuka isinya.", 10, 6)

    head(doc, "Dulu, 600 SKU itu apa", 12, 4)
    body(doc, "600 adalah seluruh katalog, satu alam yang sama, bukan 600 percobaan terpisah. "
              "Kelas ABC hanya membagi katalog menurut porsi volumenya: A 260 SKU, B 188 SKU, C 152 SKU. "
              "Kelas tidak menentukan apakah stok sedang tipis; ia menentukan seberapa ketat aturannya.", 10, 3)
    body(doc, "Status “di bawah reorder” adalah keadaan pada satu hari, bukan kelas: hari cover stok lebih "
              "pendek dari lead time ditambah tujuh hari cadangan. Pada 15 Oktober ada 63 SKU dalam keadaan "
              "itu, dan 537 SKU tidak. Pesanan tetap dibuat jauh sebelum garis itu tersentuh: pada putaran "
              "28 Oktober, 325 SKU butuh pesanan walau tidak satu pun berada di bawah reorder.", 10, 6)

    head(doc, "Tabel kebenaran, 600 SKU", 12, 4)

    t = doc.add_table(rows=3, cols=4)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.style = "Table Grid"
    widths = [Inches(2.05), Inches(1.35), Inches(1.15), Inches(0.95)]
    rows = [
        ["", "SAP: stok akan habis", "SAP: aman", "Jumlah"],
        ["Aturan kita: di bawah reorder", "0 SKU", "63 SKU", "63"],
        ["Aturan kita: aman", "0 SKU", "537 SKU", "537"],
    ]
    for ri, row in enumerate(rows):
        for ci, text in enumerate(row):
            cell = t.cell(ri, ci)
            cell.width = widths[ci]
            bold = ri == 0 or ci == 3 or (ci == 0 and ri > 0)
            cell_text(cell, text, bold=bold,
                      align=None if ci == 0 else WD_ALIGN_PARAGRAPH.CENTER)
            if ri == 0:
                shade(cell, "F3F0FA")
            elif ri == 2 and ci == 2:
                shade(cell, "EDF3EA")
            elif ci == 1:
                shade(cell, "FBF7F4")

    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    body(doc, "Baris dan kolom terakhir: 537 SKU di mana kedua penilai sama-sama berkata aman, "
              "ditambah 63 SKU di mana hanya aturan kita yang khawatir. 537 dari 600 sama dengan 89,5%.", 9.5, 8,
         italic=True, colour=GREY)

    head(doc, "Cara membacanya", 12, 5)
    numbered(doc, [
        "Kedua sel nol di kolom kiri adalah intinya. SAP tidak menandai satu pun SKU akan habis, "
        "dan tidak ada satu SKU pun yang kami tandai bersama. Ringkasnya, kedua model tidak pernah "
        "menunjuk barang yang sama.",
        "Jadi seluruh 89,5% berasal dari sisi tenang: SKU yang dua-duanya dianggap beres. Angka itu "
        "mengukur kesepakatan, bukan kemampuan menemukan masalah.",
        "63 SKU yang kami khawatirkan tidak dianggap masalah oleh SAP karena jendelanya 14 hari dan "
        "ia tidak membaca kalender event maupun umur simpan. Aturan kita membaca keduanya.",
    ])

    head(doc, "Yang justru SAP tambahkan", 12, 5)
    body(doc, "Dua hal yang tidak kami hitung dengan cara yang sama:", 10, 2)
    numbered(doc, [
        "577 dari 600 SKU ditandai mendekati kedaluwarsa, angka yang tidak muncul dari aturan reorder kami.",
        "Median sisa umur cover 13,8 hari dari model regresinya, sebagai pembanding independen atas "
        "hitungan cover kami sendiri.",
    ])

    head(doc, "Kalimat untuk panggung", 12, 5)
    quote = doc.add_paragraph()
    quote.paragraph_format.left_indent = Inches(0.25)
    quote.paragraph_format.right_indent = Inches(0.25)
    quote.paragraph_format.space_before = Pt(2)
    quote.paragraph_format.space_after = Pt(8)
    quote.paragraph_format.line_spacing = 1.2
    r = quote.add_run("“SAP and our rule land on the same answer for 89.5 percent of SKUs, but that "
                      "agreement is all on the quiet side: on the SKUs where we expect trouble, SAP sees "
                      "nothing, because its horizon is fourteen days and it does not read the calendar. "
                      "What it does add is expiry: 577 SKUs this week.”")
    r.italic = True
    r.font.size = Pt(10.5)
    r.font.name = "Arial"
    r.font.color.rgb = ACCENT

    body(doc, "Yang jangan diucapkan: “jadi model kami tervalidasi oleh SAP”. Angka ini tidak "
              "memvalidasi apa pun.", 9.5, 6, colour=GREY)

    body(doc, "Ringkasnya: 600 adalah seluruh katalog, 63 adalah yang sedang di bawah titik reorder pada "
              "15 Oktober, 537 adalah sisanya, dan 89,5% hanya mengukur seberapa sering dua penilai memberi "
              "jawaban yang sama pada satu hari.", 10, 8)
    body(doc, "Sumber: data/sap/rpt_summary.json (0 stok habis, 577 kedaluwarsa, agreement 0,895, "
              "both_flag_same_sku 0) dan data/sap/rpt_request_meta.json (10,73 detik). Angka 63 memakai "
              "snapshot 15 Oktober, jadi tidak akan sama bila dihitung ulang hari ini.", 8, 0, italic=True, colour=GREY)

    doc.save(OUT)
    print("wrote", OUT.name)


if __name__ == "__main__":
    main()
