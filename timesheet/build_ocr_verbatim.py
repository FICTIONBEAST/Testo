"""Verbatim OCR workbook: the notebook pages exactly as written, nothing computed.

Output: ocr_verbatim.xlsx  — sheets 'Page 1' and 'Page 2', same columns/headers as the notebook
Then cross-checks the verbatim text against timesheet_transcribed.csv (the structured data
behind timesheet.xlsx) and prints a per-row verification report as CSV (ocr_verification.csv).
"""
import csv
import pathlib

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HERE = pathlib.Path(__file__).parent

# Exactly as written on the page (spelling/casing kept: "Day OFF", "Day Off", "Closed").
# Non-working days are written across the Start column in the notebook, so they sit there.
PAGE1 = [
    ("22", "5:30", "11:00", "5h30m"),
    ("23", "5:30", "11:00", "5h30m"),
    ("24", "Day OFF", "", ""),
    ("25", "6:00", "10:30", "4h30m"),
    ("26", "5:30", "11:00", "~8h~ 5h30m"),   # ~x~ = struck through in the notebook
    ("27", "5:00", "10:00", "5h"),
    ("28", "Closed", "", ""),
    ("29", "5:30", "11:00", "5h30m"),
    ("30", "5:30", "11:30", "6h"),
    ("1", "5:30", "11:00", "5h30m"),
    ("2", "6:00", "11:00", "5h"),
    ("3", "5:30", "10:30", "5h"),
    ("4", "5:30", "10:30", "5h"),
    ("5", "Closed", "", ""),
    ("6", "6:00", "11:00", "5h"),
    ("7", "Day Off", "", ""),
    ("8", "5:30", "11:00", "5h30m"),
    ("9", "5:30", "11:00", "5h30m"),
]
PAGE2 = [
    ("10", "5:30", "11:30", "6h"),
    ("11", "5:11", "11:14", "6h"),
    ("12", "Closed", "", ""),
    ("13", "5:31", "11:00", "5h30m"),
    ("14", "5:31", "11:30", "6h"),
    ("15", "Day OFF", "", ""),
    ("16", "5:30", "11:00", "5h30m"),
    ("17", "6:00", "12:00", "6h"),
    ("18", "5:32", "10:30", "5h"),
    ("19", "Closed", "", ""),
    ("20", "5:30", "11:30", "6h"),
]
PAGE2_FOOTER = [("", "Total hours - 109 h", "", ""), ("", "109 x 80 → 8720B", "", "")]

F = "Arial"
ink = Font(name=F, size=12, color="1F2A5C")      # notebook-pen blue
hdr = Font(name=F, size=12, bold=True, color="1F2A5C")
ruled = Side(style="thin", color="B4C6E7")
line = Border(bottom=ruled)
paper = PatternFill("solid", fgColor="FAFAFF")
mid = Alignment(horizontal="center", vertical="center")


def strike_text(s):
    if "~" not in s:
        return s
    _, struck, rest = s.split("~")
    return CellRichText(TextBlock(InlineFont(rFont=F, sz=12, color="1F2A5C", strike=True), struck),
                        TextBlock(InlineFont(rFont=F, sz=12, color="1F2A5C"), rest))


def write_page(ws, rows, footer=(), page_no=None):
    ws.sheet_view.showGridLines = False
    if page_no:
        ws["D1"] = page_no
        ws["D1"].font, ws["D1"].alignment = hdr, mid
    for j, h in enumerate(["Date", "Start", "Finished", "Total"], 1):
        c = ws.cell(2, j, h)
        c.font, c.alignment, c.border, c.fill = hdr, mid, line, paper
    for i, row in enumerate(list(rows) + list(footer)):
        n = 3 + i
        for j, v in enumerate(row, 1):
            c = ws.cell(n, j, strike_text(v) if v else None)
            c.font, c.border, c.fill = ink, line, paper
            # text left-aligned when it spans (Day off / Closed / footer), else centred like the page
            c.alignment = Alignment(horizontal="left", vertical="center") if (j == 2 and not row[2]) else mid
            c.number_format = "@"   # keep "5:30" as text, never let Excel turn it into a time
        ws.row_dimensions[n].height = 24
    ws.row_dimensions[2].height = 26
    for col, w in zip("ABCD", (9, 22, 16, 16)):
        ws.column_dimensions[col].width = w
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = f"A1:D{2 + len(rows) + len(footer)}"


wb = Workbook()
write_page(wb.active, PAGE1)
wb.active.title = "Page 1"
write_page(wb.create_sheet("Page 2"), PAGE2, PAGE2_FOOTER, page_no="103")
wb.save(HERE / "ocr_verbatim.xlsx")

# ---------------------------------------------------------------- cross-check vs structured data
def hm_minutes(s):
    s = s.split()[-1]  # drop struck-through prefix
    h, _, m = s.partition("h")
    return int(h) * 60 + int(m.rstrip("m") or 0)


def clock_minutes(s):
    h, m = map(int, s.split(":"))
    return h * 60 + m


structured = list(csv.DictReader(open(HERE / "timesheet_transcribed.csv")))
verbatim = PAGE1 + PAGE2
assert len(structured) == len(verbatim)

report, problems = [], 0
for (page, (d, start, fin, tot)), s in zip([(1, r) for r in PAGE1] + [(2, r) for r in PAGE2], structured):
    worked = bool(fin)
    same = (d == s["day"] and
            (start == s["start"] and fin == s["finish"] and tot.split()[-1] == s["written_total"]
             if worked else start.lower() == s["status"].lower()))
    if worked:
        clock = clock_minutes(fin) - clock_minutes(start)
        diff = hm_minutes(tot) - clock
        arith = "exact" if diff == 0 else f"rounded ({diff:+d} min)"
    else:
        arith = "n/a"
    problems += not same
    report.append({"page": page, "date": d, "start": start, "finished": fin, "total": tot.replace("~", ""),
                   "matches_timesheet_xlsx": "yes" if same else "NO",
                   "finish_minus_start_vs_total": arith})

written_sum = sum(hm_minutes(t) for _, _, f, t in verbatim if f) / 60
with open(HERE / "ocr_verification.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=report[0].keys())
    w.writeheader()
    w.writerows(report)

print(f"rows={len(report)} mismatches_vs_timesheet={problems} "
      f"rounded_rows={sum('rounded' in r['finish_minus_start_vs_total'] for r in report)} "
      f"sum_of_written_totals={written_sum:g}h notebook_says=109h")
