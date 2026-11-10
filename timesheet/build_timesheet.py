"""Build a timesheet workbook + weekday-average chart from the OCR'd notebook pages.

Input : timesheet_transcribed.csv  (hand transcription of the two notebook photos)
Output: timesheet.xlsx             (live formulas, native Excel line chart)
        weekday_average.png        (same chart as an image)

The notebook only records day-of-month numbers. PERIOD_START anchors them to real
dates so weekdays can be derived; change it in the workbook (cell C3) and every
weekday, average and chart point recalculates.
"""
import csv
import datetime as dt
import pathlib
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = pathlib.Path(__file__).parent
PERIOD_START = dt.date(2026, 9, 22)  # assumption: 22 Sep -> 20 Oct 2026 (28th = Monday "Closed")
HOURLY_RATE = 80                     # from notebook: "109 x 80 -> 8720 B"
NOTEBOOK_TOTAL = 109                 # total as written in the notebook
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_hm(s):
    """'5h30m' -> 5.5"""
    if not s:
        return None
    m = re.fullmatch(r"(\d+)h(?:(\d+)m)?", s.strip())
    return int(m.group(1)) + int(m.group(2) or 0) / 60


def parse_clock(s):
    if not s:
        return None
    h, m = map(int, s.split(":"))
    return dt.time(h, m)


rows = list(csv.DictReader(open(HERE / "timesheet_transcribed.csv")))
for i, r in enumerate(rows):
    r["date"] = PERIOD_START + dt.timedelta(days=i)
    assert r["date"].day == int(r["day"]), f"date mismatch at {r['day']}"  # sanity: rollover lands right
    r["start_t"], r["finish_t"] = parse_clock(r["start"]), parse_clock(r["finish"])
    r["written_h"] = parse_hm(r["written_total"])

# ---------------------------------------------------------------- workbook
F = "Arial"
font = Font(name=F, size=10)
bold = Font(name=F, size=10, bold=True)
blue = Font(name=F, size=10, color="0000FF")
title = Font(name=F, size=14, bold=True)
grey = Font(name=F, size=9, italic=True, color="666666")
head_fill = PatternFill("solid", fgColor="1F3864")
head_font = Font(name=F, size=10, bold=True, color="FFFFFF")
yellow = PatternFill("solid", fgColor="FFFF00")
off_fill = PatternFill("solid", fgColor="EDEDED")
flag_fill = PatternFill("solid", fgColor="FCE4D6")
total_fill = PatternFill("solid", fgColor="D9E1F2")
thin = Side(style="thin", color="BFBFBF")
box = Border(top=thin, bottom=thin, left=thin, right=thin)
center = Alignment(horizontal="center", vertical="center")

wb = Workbook()
ws = wb.active
ws.title = "Timesheet"

ws["A1"] = "Working Hours Timesheet (transcribed from handwritten notebook)"
ws["A1"].font = title
ws["A3"], ws["A4"] = "Period start date", "Hourly rate (THB)"
ws["C3"], ws["C4"] = PERIOD_START, HOURLY_RATE
for c in ("A3", "A4"):
    ws[c].font = bold
for c in ("C3", "C4"):
    ws[c].font = blue
    ws[c].fill = yellow
    ws[c].border = box
ws["C3"].number_format = "dd mmm yyyy"
ws["D3"] = "Assumption: notebook gives only day numbers 22 → 20; 22 Sep 2026 chosen because the 30→1 rollover needs a 30-day month and it makes every 'Closed' day a Monday. Edit if wrong."
ws["D4"] = "Source: notebook, '109 x 80 → 8720 B'."
ws["D3"].font = ws["D4"].font = grey
ws["A5"] = "Legend: blue text on yellow = editable input · blue text = transcribed value · black = formula · orange rows = written total differs from clock time"
ws["A5"].font = grey

headers = ["Date", "Weekday", "Status", "Start", "Finish", "Hours (clock)",
           "Hours (as written)", "Written − clock (min)", "Cumulative hours", "OCR note"]
HR = 7
for j, h in enumerate(headers, 1):
    c = ws.cell(row=HR, column=j, value=h)
    c.font, c.fill, c.alignment, c.border = head_font, head_fill, Alignment(horizontal="center", vertical="center", wrap_text=True), box
ws.row_dimensions[HR].height = 30

first = HR + 1
for i, r in enumerate(rows):
    n = first + i
    worked = r["status"] == "Worked"
    ws.cell(n, 1, f"=$C$3+{i}").number_format = "ddd dd mmm"
    ws.cell(n, 2, f'=CHOOSE(WEEKDAY(A{n},2),"Mon","Tue","Wed","Thu","Fri","Sat","Sun")')
    ws.cell(n, 3, r["status"]).font = blue
    if worked:
        ws.cell(n, 4, r["start_t"]).font = blue
        ws.cell(n, 5, r["finish_t"]).font = blue
        ws.cell(n, 7, r["written_h"]).font = blue
    for col in (4, 5):
        ws.cell(n, col).number_format = "h:mm"
    ws.cell(n, 6, f'=IF(C{n}="Worked",(E{n}-D{n})*24,0)').number_format = "0.00"
    ws.cell(n, 7).number_format = "0.00"
    ws.cell(n, 8, f'=IF(C{n}="Worked",ROUND((G{n}-F{n})*60,0),0)').number_format = "0;-0;-"
    ws.cell(n, 9, f"=G{n}" if i == 0 else f"=I{n-1}+N(G{n})").number_format = "0.00"
    ws.cell(n, 10, r["ocr_note"] or None)
    clock_h = (dt.datetime.combine(dt.date.min, r["finish_t"]) - dt.datetime.combine(dt.date.min, r["start_t"])).seconds / 3600 if worked else 0
    mismatch = worked and abs(clock_h - r["written_h"]) > 1e-9
    for col in range(1, 11):
        c = ws.cell(n, col)
        c.border = box
        if c.font != blue:
            c.font = font
        if col <= 9:
            c.alignment = center
        if not worked:
            c.fill = off_fill
        elif mismatch:
            c.fill = flag_fill
last = first + len(rows) - 1

t = last + 2
ws.cell(t, 1, "TOTAL")
ws.cell(t, 3, f'=COUNTIF(C{first}:C{last},"Worked")&" days worked"')
ws.cell(t, 6, f"=SUM(F{first}:F{last})")
ws.cell(t, 7, f"=SUM(G{first}:G{last})")
ws.cell(t, 8, f"=SUM(H{first}:H{last})")
ws.cell(t, 9, f"=I{last}")
for col in range(1, 11):
    c = ws.cell(t, col)
    c.font, c.fill, c.border, c.alignment = bold, total_fill, box, center
    if col in (6, 7, 9):
        c.number_format = "0.00"

# reconciliation block
rec = t + 2
ws.cell(rec, 1, "Pay reconciliation").font = Font(name=F, size=11, bold=True)
recon = [
    ("Hours as written (sum of daily totals)", f"=G{t}", "0.00"),
    ("Hours from clock times", f"=F{t}", "0.00"),
    ("Hours stated in notebook", NOTEBOOK_TOTAL, "0.00"),
    ("Hours missing from notebook total", f"=B{rec+1}-B{rec+3}", "0.00"),
    ("Pay on written hours (THB)", f"=B{rec+1}*$C$4", "#,##0"),
    ("Pay stated in notebook (THB)", f"=B{rec+3}*$C$4", "#,##0"),
    ("Shortfall (THB)", f"=B{rec+5}-B{rec+6}", "#,##0"),
]
for k, (label, val, fmt) in enumerate(recon, 1):
    a = ws.cell(rec + k, 1, label)
    b = ws.cell(rec + k, 2, val)
    a.font, b.number_format, b.border, a.border = font, fmt, box, box
    b.font = blue if isinstance(val, (int, float)) else font
    b.alignment = center
ws.cell(rec + 3, 2).comment = Comment("Source: notebook page 2, 'Total hours - 109 h'.", "OCR")
for k in (4, 7):
    ws.cell(rec + k, 1).font = ws.cell(rec + k, 2).font = Font(name=F, size=10, bold=True, color="C00000")
ws.merge_cells(start_row=rec, start_column=1, end_row=rec, end_column=1)

widths = [14, 10, 10, 9, 9, 12, 12, 13, 13, 46]
for j, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(j)].width = w
ws.column_dimensions["A"].width = 38
ws.freeze_panes = ws.cell(first, 1)

# ---------------------------------------------------------------- weekday averages
wa = wb.create_sheet("Weekday Average")
wa["A1"] = "Average hours by day of week"
wa["A1"].font = title
wa["A2"] = "Based on 'Hours (as written)'. 'Per shift' ignores days not worked; 'per calendar day' counts Day off / Closed as 0 h."
wa["A2"].font = grey
hdr = ["Weekday", "Shifts worked", "Calendar days", "Total hours", "Avg per shift worked", "Avg per calendar day"]
for j, h in enumerate(hdr, 1):
    c = wa.cell(4, j, h)
    c.font, c.fill, c.alignment, c.border = head_font, head_fill, Alignment(horizontal="center", wrap_text=True), box
wa.row_dimensions[4].height = 30
B = f"Timesheet!$B${first}:$B${last}"
C = f"Timesheet!$C${first}:$C${last}"
G = f"Timesheet!$G${first}:$G${last}"
for k, d in enumerate(DAYS):
    n = 5 + k
    wa.cell(n, 1, d)
    wa.cell(n, 2, f'=COUNTIFS({B},A{n},{C},"Worked")')
    wa.cell(n, 3, f"=COUNTIF({B},A{n})")
    wa.cell(n, 4, f"=SUMIFS({G},{B},A{n})")
    wa.cell(n, 5, f"=IF(B{n}=0,0,D{n}/B{n})")
    wa.cell(n, 6, f"=IF(C{n}=0,0,D{n}/C{n})")
    for col in range(1, 7):
        c = wa.cell(n, col)
        c.font, c.border, c.alignment = font, box, center
        if col >= 4:
            c.number_format = "0.00"
for col in "ABCDEF":
    wa.column_dimensions[col].width = 15

ch = LineChart()
ch.title = "Average hours worked by day of week"
ch.y_axis.title = "Average hours"
ch.x_axis.title = "Day of week"
ch.y_axis.scaling.min = 0
ch.y_axis.scaling.max = 7
ch.y_axis.majorUnit = 1
ch.x_axis.delete = False
ch.y_axis.delete = False
ch.add_data(Reference(wa, min_col=5, max_col=6, min_row=4, max_row=11), titles_from_data=True)
ch.set_categories(Reference(wa, min_col=1, min_row=5, max_row=11))
for s, color in zip(ch.series, ("1F77B4", "FF7F0E")):
    s.graphicalProperties.line.solidFill = color
    s.graphicalProperties.line.width = 28000
    s.marker.symbol = "circle"
    s.marker.size = 7
    s.marker.graphicalProperties.solidFill = color
    s.marker.graphicalProperties.line.solidFill = color
    s.smooth = False
ch.height, ch.width = 9, 18
wa.add_chart(ch, "H4")

out = HERE / "timesheet.xlsx"
wb.save(out)

# ---------------------------------------------------------------- python mirror (for PNG + checks)
worked = [r for r in rows if r["status"] == "Worked"]
total_written = sum(r["written_h"] for r in worked)
per_shift, per_cal = [], []
for k, d in enumerate(DAYS):
    days_k = [r for r in rows if r["date"].weekday() == k]
    w = [r["written_h"] for r in days_k if r["status"] == "Worked"]
    per_shift.append(sum(w) / len(w) if w else 0)
    per_cal.append(sum(w) / len(days_k) if days_k else 0)

fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150)
ax.plot(DAYS, per_shift, marker="o", lw=2.2, color="#1F77B4", label="Avg per shift worked")
ax.plot(DAYS, per_cal, marker="o", lw=2.2, color="#FF7F0E", label="Avg per calendar day (off/closed = 0)")
for x, y in enumerate(per_shift):
    ax.annotate("Closed" if y == 0 else f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=9, color="#1F77B4")
ax.set_ylim(0, 7)
ax.set_ylabel("Average hours")
ax.set_title(f"Average hours by weekday · {rows[0]['date']:%d %b} – {rows[-1]['date']:%d %b %Y}", loc="left")
ax.grid(axis="y", alpha=0.3)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, loc="lower right")
fig.tight_layout()
fig.savefig(HERE / "weekday_average.png")

print(f"days worked={len(worked)} written={total_written:.2f}h notebook={NOTEBOOK_TOTAL}h "
      f"missing={total_written-NOTEBOOK_TOTAL:.2f}h shortfall={(total_written-NOTEBOOK_TOTAL)*HOURLY_RATE:.0f} THB")
for d, a, b in zip(DAYS, per_shift, per_cal):
    print(f"  {d}: per shift {a:.2f}  per calendar day {b:.2f}")
