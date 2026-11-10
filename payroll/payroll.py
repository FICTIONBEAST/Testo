#!/usr/bin/env python3
"""Handwritten timesheet -> verified payroll record.

    python payroll.py read  periods/2026-09-22     # photos -> read_a.csv, read_b.csv (two independent AI readings)
    python payroll.py build periods/2026-09-22     # readings -> checks -> payroll.xlsx + report.html (+ report.pdf)

The notebook checks itself: every row has a start, a finish AND a written total, so a
misread digit breaks  finish - start = total.  `build` uses that, plus a second reading,
plus the calendar (closed day), and refuses to call a period VERIFIED unless all agree.
"""
import base64
import csv
import datetime as dt
import html
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FIELDS = ["page", "day", "status", "start", "finish", "total", "note"]
ROUNDING_TOLERANCE_MIN = 5      # written total may be rounded by up to this much
MODEL = "claude-opus-5-5"

READ_PROMPT = """This is a photo of a handwritten staff timesheet with columns Date, Start, Finished, Total.
Transcribe every row exactly as written, top to bottom. Do not correct, round or calculate anything.
- day: the day-of-month number in the Date column.
- status: "Worked" if the row has times; "Day off" or "Closed" if that is written instead.
- start / finish: as written, H:MM. Empty if not worked.
- total: as written, like 5h30m or 6h. If a figure is crossed out, ignore it and say so in note.
- note: only for something a payroll clerk must know (crossed-out text, a digit you are unsure of). Otherwise empty.
Also return stated_total_hours if the page has a grand total written on it (e.g. "Total hours - 109 h"), else null."""


# ------------------------------------------------------------------ step 1: read the photos
def read(folder):
    """Two independent readings per photo: the original, and a sharpened 2x enlargement."""
    import anthropic                       # pip install anthropic ; needs ANTHROPIC_API_KEY
    from PIL import Image, ImageOps
    from pydantic import BaseModel

    class Row(BaseModel):
        day: int
        status: str
        start: str
        finish: str
        total: str
        note: str

    class Page(BaseModel):
        rows: list[Row]
        stated_total_hours: float | None

    import os
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        sys.exit("No API key found. Set ANTHROPIC_API_KEY, then run this again. Nothing was changed.")
    client = anthropic.Anthropic()
    period = json.loads((folder / "period.json").read_text())

    def ask(jpeg_bytes):
        response = client.messages.parse(
            model=MODEL, max_tokens=16000, output_format=Page,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.standard_b64encode(jpeg_bytes).decode()}},
                {"type": "text", "text": READ_PROMPT}]}])
        if response.stop_reason != "end_turn":
            sys.exit(f"Reading stopped early ({response.stop_reason}); nothing written.")
        return response.parsed_output

    def enhanced(path):
        im = ImageOps.autocontrast(ImageOps.grayscale(Image.open(path)))
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90)
        return buf.getvalue()

    for name, prepare in (("read_a.csv", lambda p: p.read_bytes()), ("read_b.csv", enhanced)):
        rows = []
        for n, photo in enumerate(period["photos"], 1):
            page = ask(prepare(folder / photo))
            rows += [{"page": n, **r.model_dump()} for r in page.rows]
            if name == "read_a.csv" and page.stated_total_hours is not None:
                period["notebook_total_hours"] = page.stated_total_hours
        with open(folder / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, FIELDS)
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {name}: {len(rows)} rows")
    (folder / "period.json").write_text(json.dumps(period, indent=2) + "\n")


# ------------------------------------------------------------------ step 2: verify + build
def clock_min(s):
    h, m = map(int, s.split(":"))
    return h * 60 + m


def total_min(s):
    m = re.fullmatch(r"(\d+)h\s*(?:(\d+)m)?", s.strip())
    return int(m.group(1)) * 60 + int(m.group(2) or 0)


def hm(minutes):
    return f"{minutes // 60}h {minutes % 60:02d}m"


def load(path):
    return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(open(path))]


def verify(folder):
    period = json.loads((folder / "period.json").read_text())
    a, b = load(folder / "read_a.csv"), load(folder / "read_b.csv")
    start = dt.date.fromisoformat(period["start_date"])
    closed = period["closed_weekday"]
    checks, rows = [], []

    def check(name, problems, ok_text):
        checks.append({"name": name, "ok": not problems, "detail": "; ".join(problems) or ok_text})

    cells = ["day", "status", "start", "finish", "total"]
    diffs = [f"row {i+1} {c}: '{x[c]}' vs '{y[c]}'" for i, (x, y) in enumerate(zip(a, b)) for c in cells if x[c] != y[c]]
    if len(a) != len(b):
        diffs.append(f"reading A has {len(a)} rows, reading B has {len(b)}")
    check("Two independent readings agree", diffs, f"{len(a)} rows x {len(cells)} cells identical")

    cal, shut, arith, shape = [], [], [], []
    for i, r in enumerate(a):
        date = start + dt.timedelta(days=i)
        wd = DAYS[date.weekday()]
        worked = r["status"] == "Worked"
        if int(r["day"]) != date.day:
            cal.append(f"expected day {date.day}, notebook says {r['day']}")
        if (r["status"] == "Closed") != (wd == closed):
            shut.append(f"{date:%d %b} is a {wd} but is marked '{r['status']}'")
        written = clock = 0
        if worked:
            try:
                clock = clock_min(r["finish"]) - clock_min(r["start"])
                written = total_min(r["total"])
            except (ValueError, AttributeError):
                shape.append(f"{date:%d %b}: cannot read '{r['start']}' / '{r['finish']}' / '{r['total']}'")
            if abs(written - clock) > ROUNDING_TOLERANCE_MIN:
                arith.append(f"{date:%d %b}: {r['start']}-{r['finish']} is {hm(clock)}, written {r['total']}")
            if not 60 <= clock <= 12 * 60:
                shape.append(f"{date:%d %b}: shift of {hm(clock)} is outside 1-12 h")
        rows.append({**r, "date": date, "weekday": wd, "worked": worked, "written": written, "clock": clock})

    rounded = [r for r in rows if r["worked"] and r["written"] != r["clock"]]
    check("Dates run in order with no gaps", cal, f"{rows[0]['date']:%d %b} to {rows[-1]['date']:%d %b %Y}, {len(rows)} days")
    check(f"Closed days are exactly the {closed}days", shut, f"all {sum(r['status']=='Closed' for r in rows)} closed days fall on {closed}")
    check("Finish minus start equals the written total", arith,
          f"{sum(r['worked'] for r in rows) - len(rounded)} exact, {len(rounded)} rounded by {ROUNDING_TOLERANCE_MIN} min or less")
    check("Every shift is a readable, plausible length", shape, "all shifts between 1 and 12 hours")

    written = sum(r["written"] for r in rows)
    clock = sum(r["clock"] for r in rows)
    rate = period["hourly_rate"]
    stated = period.get("notebook_total_hours")
    finding = None
    if stated is not None and abs(stated * 60 - written) > 0.5:
        cum, upto = 0, None
        for r in rows:
            cum += r["written"]
            if r["worked"] and cum == stated * 60:
                upto = r["date"]
        finding = {"stated_h": stated, "gap_h": (written - stated * 60) / 60, "gap_pay": (written - stated * 60) / 60 * rate,
                   "upto": upto, "missed": [r for r in rows if upto and r["worked"] and r["date"] > upto]}
    return {"period": period, "rows": rows, "checks": checks, "verified": all(c["ok"] for c in checks),
            "written": written, "clock": clock, "pay_written": written / 60 * rate, "pay_clock": round(clock / 60 * rate, 2),
            "days_worked": sum(r["worked"] for r in rows), "finding": finding, "rounded": rounded}


def write_xlsx(v, path):
    from openpyxl import Workbook
    from openpyxl.chart import LineChart, Reference
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    p, rows = v["period"], v["rows"]
    cur = p["currency"]
    F = "Arial"
    f, bold, blue = Font(name=F, size=10), Font(name=F, size=10, bold=True), Font(name=F, size=10, color="0000FF")
    head = dict(font=Font(name=F, size=10, bold=True, color="FFFFFF"), fill=PatternFill("solid", fgColor="1F3864"))
    grey, amber, band = (PatternFill("solid", fgColor=c) for c in ("EDEDED", "FFF2CC", "D9E1F2"))
    thin = Side(style="thin", color="BFBFBF")
    box, mid = Border(top=thin, bottom=thin, left=thin, right=thin), Alignment(horizontal="center", vertical="center", wrap_text=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Payroll"
    ws["A1"] = "Staff hours and pay record"
    ws["A1"].font = Font(name=F, size=14, bold=True)
    ws["A2"] = ("VERIFIED" if v["verified"] else "NOT VERIFIED") + " against the handwritten notebook - see Checks tab"
    ws["A2"].font = Font(name=F, size=10, bold=True, color="00703C" if v["verified"] else "C00000")
    for n, (label, val) in enumerate([("Staff name", p["staff"] or None), ("Period start", dt.date.fromisoformat(p["start_date"])),
                                      (f"Hourly rate ({cur})", p["hourly_rate"])], 3):
        ws.cell(n, 1, label).font = bold
        c = ws.cell(n, 2, val)
        c.font, c.fill, c.border = blue, PatternFill("solid", fgColor="FFFF00"), box
    ws["B4"].number_format = "dd mmm yyyy"
    ws["C3"] = "Yellow cells are inputs. Blue text is copied from the notebook. Everything else is a formula."
    ws["C3"].font = Font(name=F, size=9, italic=True, color="666666")

    H = 7
    cols = ["Date", "Day", "Status", "Start", "Finish", "Hours AS WRITTEN", "Hours BY CLOCK",
            "Written minus clock (min)", "Running total AS WRITTEN", "Running total BY CLOCK", "Note"]
    for j, t in enumerate(cols, 1):
        c = ws.cell(H, j, t)
        c.font, c.fill, c.alignment, c.border = head["font"], head["fill"], mid, box
    ws.row_dimensions[H].height = 42
    r0 = H + 1
    for i, r in enumerate(rows):
        n = r0 + i
        ws.cell(n, 1, f"=$B$4+{i}").number_format = "dd mmm"
        ws.cell(n, 2, f'=CHOOSE(WEEKDAY(A{n},2),"Mon","Tue","Wed","Thu","Fri","Sat","Sun")')
        ws.cell(n, 3, r["status"])
        if r["worked"]:
            ws.cell(n, 4, dt.time(*map(int, r["start"].split(":")))).number_format = "h:mm"
            ws.cell(n, 5, dt.time(*map(int, r["finish"].split(":")))).number_format = "h:mm"
            ws.cell(n, 6, r["written"] / 60)
        ws.cell(n, 7, f'=IF(C{n}="Worked",(E{n}-D{n})*24,0)')
        ws.cell(n, 8, f'=IF(C{n}="Worked",ROUND((F{n}-G{n})*60,0),0)').number_format = "+0;-0;-"
        ws.cell(n, 9, f"=N(F{n})" if i == 0 else f"=I{n-1}+N(F{n})")
        ws.cell(n, 10, f"=G{n}" if i == 0 else f"=J{n-1}+G{n}")
        ws.cell(n, 11, r["note"] or None)
        for j in range(1, 12):
            c = ws.cell(n, j)
            c.font, c.border = (blue if j in (3, 4, 5, 6) else f), box
            c.alignment = Alignment(vertical="center") if j == 11 else mid
            if j in (6, 7, 9, 10):
                c.number_format = "0.00"
            if not r["worked"]:
                c.fill = grey
            elif r["written"] != r["clock"]:
                c.fill = amber
    r1 = r0 + len(rows) - 1
    T = r1 + 1
    ws.cell(T, 1, "TOTAL")
    ws.cell(T, 3, f'=COUNTIF(C{r0}:C{r1},"Worked")&" shifts"')
    for j, col in ((6, "F"), (7, "G"), (8, "H")):
        ws.cell(T, j, f"=SUM({col}{r0}:{col}{r1})")
    ws.cell(T, 9, f"=I{r1}")
    ws.cell(T, 10, f"=J{r1}")
    for j in range(1, 12):
        c = ws.cell(T, j)
        c.font, c.fill, c.border, c.alignment = bold, band, box, mid
        if j in (6, 7, 9, 10):
            c.number_format = "0.00"

    P = T + 2
    for j, t in enumerate(["PAY", "Hours", f"Pay ({cur})"], 1):
        c = ws.cell(P, j, t)
        c.font, c.fill, c.border, c.alignment = head["font"], head["fill"], box, mid
    lines = [("A  Hours AS WRITTEN by staff (rounded)", f"=F{T}", f"=B{P+1}*$B$5"),
             ("B  Hours BY CLOCK (finish minus start, exact)", f"=G{T}", f"=ROUND(B{P+2}*$B$5,2)"),
             ("Difference A minus B", f"=B{P+1}-B{P+2}", f"=C{P+1}-C{P+2}")]
    if p.get("notebook_total_hours") is not None:
        lines += [("Total written at the foot of the notebook", p["notebook_total_hours"], f"=B{P+4}*$B$5"),
                  ("Notebook total is short of A by", f"=B{P+1}-B{P+4}", f"=C{P+1}-C{P+4}")]
    for k, (label, hours, pay) in enumerate(lines, 1):
        for j, val in enumerate((label, hours, pay), 1):
            c = ws.cell(P + k, j, val)
            c.font, c.border = (bold if k in (1, 2, 5) else f), box
            if j > 1:
                c.number_format, c.alignment = ("0.00" if j == 2 else "#,##0.00"), mid
        if k == 4:
            ws.cell(P + k, 2).font = blue
    S = P + len(lines) + 3
    ws.cell(S, 1, "Staff signature: ______________________   Date: __________").font = f
    ws.cell(S + 2, 1, "Owner signature: ______________________   Date: __________").font = f
    for col, w in zip("ABCDEFGHIJK", (44, 10, 12, 9, 9, 12, 12, 13, 13, 13, 40)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = ws.cell(r0, 1)
    ws.page_setup.orientation, ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = "landscape", 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    cs = wb.create_sheet("Checks")
    for j, t in enumerate(["Check", "Result", "Detail"], 1):
        c = cs.cell(1, j, t)
        c.font, c.fill, c.border = head["font"], head["fill"], box
    for n, c in enumerate(v["checks"], 2):
        cs.cell(n, 1, c["name"]).font = f
        k = cs.cell(n, 2, "PASS" if c["ok"] else "FAIL")
        k.font = Font(name=F, size=10, bold=True, color="00703C" if c["ok"] else "C00000")
        cs.cell(n, 3, c["detail"]).font = f
    for col, w in zip("ABC", (46, 9, 90)):
        cs.column_dimensions[col].width = w

    wa = wb.create_sheet("Weekday average")
    for j, t in enumerate(["Day", "Shifts worked", "Hours (as written)", "Average hours per shift"], 1):
        c = wa.cell(1, j, t)
        c.font, c.fill, c.border, c.alignment = head["font"], head["fill"], box, mid
    for k, d in enumerate(DAYS, 2):
        rng = lambda col: f"Payroll!${col}${r0}:${col}${r1}"
        wa.cell(k, 1, d)
        wa.cell(k, 2, f'=COUNTIFS({rng("B")},A{k},{rng("C")},"Worked")')
        wa.cell(k, 3, f'=SUMIFS({rng("F")},{rng("B")},A{k})')
        wa.cell(k, 4, f"=IF(B{k}=0,0,C{k}/B{k})")
        for j in range(1, 5):
            c = wa.cell(k, j)
            c.font, c.border, c.alignment = f, box, mid
            if j > 2:
                c.number_format = "0.00"
    for col in "ABCD":
        wa.column_dimensions[col].width = 18
    ch = LineChart()
    ch.title, ch.y_axis.title, ch.x_axis.title = "Average hours per shift, by day of week", "Average hours", "Day of week"
    ch.y_axis.scaling.min, ch.y_axis.scaling.max, ch.y_axis.majorUnit = 0, 7, 1
    ch.x_axis.delete = ch.y_axis.delete = False
    ch.legend = None
    ch.add_data(Reference(wa, min_col=4, min_row=1, max_row=8), titles_from_data=True)
    ch.set_categories(Reference(wa, min_col=1, min_row=2, max_row=8))
    ch.series[0].marker.symbol = "circle"
    ch.series[0].smooth = False
    ch.height, ch.width = 8, 16
    wa.add_chart(ch, "F1")
    wb.save(path)


def photo_data_uri(path, width=900):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


CSS = """
@page { size: A4; margin: 14mm; }
* { box-sizing: border-box; }
body { font: 10.5pt/1.4 Arial, Helvetica, sans-serif; color: #1a1a1a; margin: 0; }
h1 { font-size: 19pt; margin: 0 0 2mm; } h2 { font-size: 12pt; margin: 6mm 0 2mm; }
.meta { color: #555; margin-bottom: 4mm; }
.verdict { padding: 3mm 4mm; border-radius: 2mm; font-weight: bold; color: #fff; background: #00703c; }
.verdict.bad { background: #c00000; }
.pay { display: flex; gap: 4mm; margin: 4mm 0; }
.pay div { flex: 1; border: 0.4mm solid #1f3864; border-radius: 2mm; padding: 3mm 4mm; }
.pay small { display: block; color: #555; } .pay b { font-size: 17pt; display: block; }
.finding { border-left: 1.2mm solid #c00000; background: #fdf1f0; padding: 3mm 4mm; margin: 4mm 0; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; }
th { background: #1f3864; color: #fff; padding: 1.2mm 1.5mm; text-align: center; }
td { border-bottom: 0.2mm solid #cfcfcf; padding: 0.9mm 1.5mm; text-align: center; }
td.l { text-align: left; } tr.off td { background: #efefef; color: #666; } tr.rnd td { background: #fff5d6; }
tr.tot td { font-weight: bold; background: #d9e1f2; border-top: 0.4mm solid #1f3864; }
.ok { color: #00703c; font-weight: bold; } .no { color: #c00000; font-weight: bold; }
.sign { display: flex; gap: 12mm; margin-top: 12mm; } .sign div { flex: 1; border-top: 0.3mm solid #000; padding-top: 1mm; color: #555; }
.page { page-break-before: always; } .ev { display: flex; gap: 5mm; align-items: flex-start; }
.ev img { width: 92mm; border: 0.2mm solid #999; } .ev table { font-size: 8.5pt; }
.foot { color: #777; font-size: 8pt; margin-top: 4mm; }
"""


def write_report(v, folder):
    p, rows, cur = v["period"], v["rows"], v["period"]["currency"]
    e = html.escape
    money = lambda x: f"{x:,.2f} {cur}"
    out = [f"<!doctype html><meta charset='utf-8'><title>Payroll record</title><style>{CSS}</style>",
           "<h1>Staff hours and pay record</h1>",
           f"<div class='meta'>Staff: <b>{e(p['staff']) or '______________________'}</b> &nbsp;·&nbsp; "
           f"Period: <b>{rows[0]['date']:%d %b %Y} – {rows[-1]['date']:%d %b %Y}</b> &nbsp;·&nbsp; "
           f"Rate: <b>{p['hourly_rate']} {cur}/hour</b> &nbsp;·&nbsp; {v['days_worked']} shifts</div>"]
    out.append(f"<div class='verdict'>VERIFIED — the spreadsheet matches the handwritten notebook; all {len(v['checks'])} checks passed.</div>"
               if v["verified"] else "<div class='verdict bad'>NOT VERIFIED — fix the failed checks below before paying from this record.</div>")
    out.append(f"<div class='pay'><div><small>A · Hours AS WRITTEN by staff (rounded)</small><b>{hm(v['written'])}</b>{money(v['pay_written'])}</div>"
               f"<div><small>B · Hours BY CLOCK (finish minus start, exact)</small><b>{hm(v['clock'])}</b>{money(v['pay_clock'])}</div></div>")
    fd = v["finding"]
    if fd:
        why = ""
        if fd["upto"]:
            missed = " and ".join(f"{r['date']:%d %b} ({r['total']})" for r in fd["missed"])
            why = f" The running total is exactly {fd['stated_h']:g} h on {fd['upto']:%d %b}, so the notebook total appears to leave out {missed}."
        out.append(f"<div class='finding'><b>Finding:</b> the notebook's own total says <b>{fd['stated_h']:g} h</b> "
                   f"({money(fd['stated_h'] * p['hourly_rate'])}), but its daily totals add up to <b>{hm(v['written'])}</b>. "
                   f"The notebook total is <b>{fd['gap_h']:g} h / {money(fd['gap_pay'])}</b> short.{why}</div>")
    out.append("<h2>Checks</h2><table><tr><th>Check</th><th>Result</th><th>Detail</th></tr>")
    for c in v["checks"]:
        out.append(f"<tr><td class='l'>{e(c['name'])}</td><td class='{'ok' if c['ok'] else 'no'}'>{'PASS' if c['ok'] else 'FAIL'}</td><td class='l'>{e(c['detail'])}</td></tr>")
    out.append("</table>")

    def table(subset, cumulative=True):
        t = ["<table><tr><th>Date</th><th>Day</th><th>Start</th><th>Finish</th><th>As written</th><th>By clock</th>"
             + ("<th>Running total<br>as written</th><th>Running total<br>by clock</th>" if cumulative else "") + "</tr>"]
        for r in subset:
            if not r["worked"]:
                t.append(f"<tr class='off'><td>{r['date']:%d %b}</td><td>{r['weekday']}</td><td colspan='{6 if cumulative else 4}'>{e(r['status'])}</td></tr>")
                continue
            cum = f"<td>{hm(r['cw'])}</td><td>{hm(r['cc'])}</td>" if cumulative else ""
            t.append(f"<tr class='{'rnd' if r['written'] != r['clock'] else ''}'><td>{r['date']:%d %b}</td><td>{r['weekday']}</td>"
                     f"<td>{r['start']}</td><td>{r['finish']}</td><td>{e(r['total'])}</td><td>{hm(r['clock'])}</td>{cum}</tr>")
        return t

    cw = cc = 0
    for r in rows:
        cw, cc = cw + r["written"], cc + r["clock"]
        r["cw"], r["cc"] = cw, cc
    out.append("<div class='page'></div><h2>Daily record</h2>")
    out += table(rows)
    out.append(f"<tr class='tot'><td colspan='4'>TOTAL · {v['days_worked']} shifts</td><td>{hm(v['written'])}</td><td>{hm(v['clock'])}</td>"
               f"<td>{money(v['pay_written'])}</td><td>{money(v['pay_clock'])}</td></tr></table>")
    out.append("<div class='foot'>Yellow rows: the written total was rounded from the clock times. Grey rows: not worked.</div>")
    out.append("<div class='sign'><div>Staff signature / date</div><div>Owner signature / date</div></div>")
    for n, photo in enumerate(p["photos"], 1):
        out.append(f"<div class='page'></div><h2>Evidence · notebook page {n} beside what was read from it</h2><div class='ev'>"
                   f"<img src='{photo_data_uri(folder / photo)}'><div style='flex:1'>")
        out += table([r for r in rows if r["page"] == str(n)], cumulative=False)
        out.append("</table></div></div>")
    out.append("<div class='foot'>This record proves the spreadsheet matches the notebook and that the notebook's arithmetic holds. "
               "It cannot prove the hours were worked; the two signatures do that.</div>")
    (folder / "report.html").write_text("\n".join(out))
    chrome = next((c for c in ("chromium", "google-chrome", "chrome", "chromium-browser") if shutil.which(c)), None)
    if chrome:
        subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={folder / 'report.pdf'}", (folder / "report.html").resolve().as_uri()],
                       check=True, capture_output=True)
    return bool(chrome)


def build(folder):
    v = verify(folder)
    write_xlsx(v, folder / "payroll.xlsx")
    pdf = write_report(v, folder)
    cur = v["period"]["currency"]
    for c in v["checks"]:
        print(f"  {'PASS' if c['ok'] else 'FAIL'}  {c['name']}: {c['detail']}")
    print(f"  A as written : {hm(v['written'])}  = {v['pay_written']:,.2f} {cur}")
    print(f"  B by clock   : {hm(v['clock'])}  = {v['pay_clock']:,.2f} {cur}")
    if v["finding"]:
        print(f"  FINDING      : notebook total {v['finding']['stated_h']:g} h is {v['finding']['gap_h']:g} h / {v['finding']['gap_pay']:,.2f} {cur} short")
    print(("VERIFIED" if v["verified"] else "NOT VERIFIED") + f" -> payroll.xlsx, report.html" + (", report.pdf" if pdf else " (open in a browser and print to PDF)"))
    return 0 if v["verified"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("read", "build"):
        sys.exit(__doc__)
    target = pathlib.Path(sys.argv[2])
    sys.exit(read(target) if sys.argv[1] == "read" else build(target))
