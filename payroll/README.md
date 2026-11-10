# Notebook timesheet → verified payroll

Photograph the handwritten hours book, get a checked spreadsheet and a signable PDF.

## Each pay period

1. Make a folder, e.g. `periods/2026-10-21/`, and put the page photos in it.
2. Copy `period.json` from the last period and change the start date, photo names, staff name and (if needed) rate.
3. Run:

```
python payroll.py read  periods/2026-10-21     # AI reads each photo twice → read_a.csv, read_b.csv
python payroll.py build periods/2026-10-21     # checks everything → payroll.xlsx, report.html, report.pdf
```

`build` prints PASS/FAIL for each check and says VERIFIED or NOT VERIFIED. If a check fails it names the
row; look at the photo, correct that cell in **both** CSV files, and run `build` again.

## What is checked

| Check | Catches |
|---|---|
| Two independent readings agree | a digit misread by the AI |
| Finish − start = written total (5 min rounding allowed) | a misread time or total, or a slip by whoever wrote it |
| Dates run in order, no gaps | a skipped or doubled row |
| Closed days are exactly the Mondays | rows shifted by a day, wrong start date |
| Shifts are 1–12 hours and readable | garbage values |
| Notebook's own grand total vs the sum | adding-up mistakes in the book (reported as a finding) |

Pay is shown two ways, clearly labelled: **A** hours as written (rounded by staff) and **B** exact clock time.

## Setup (once)

`pip install openpyxl pillow anthropic`, and set `ANTHROPIC_API_KEY`. Chrome or Chromium on the machine
gives you `report.pdf`; without it, open `report.html` and print to PDF.

`python test_payroll.py` plants six kinds of error and confirms each one is caught.

## Limits

The record proves the spreadsheet matches the notebook and the notebook's arithmetic holds. It cannot prove
the hours were worked — that is what the two signature lines are for.
