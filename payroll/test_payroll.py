"""Plant one error at a time in a copy of a good period and confirm the tool refuses to verify it.
    python test_payroll.py
"""
import pathlib, shutil, tempfile
import payroll

GOOD = pathlib.Path(__file__).parent / "periods" / "2026-09-22"


def run(edit_a=None, edit_b=None):
    with tempfile.TemporaryDirectory() as tmp:
        folder = pathlib.Path(tmp) / "p"
        shutil.copytree(GOOD, folder)
        for name, edit in (("read_a.csv", edit_a), ("read_b.csv", edit_b)):
            if edit:
                path = folder / name
                lines = path.read_text().splitlines()
                path.write_text("\n".join(edit(lines)) + "\n")
        return payroll.verify(folder)


def swap(old, new):
    return lambda lines: [l.replace(old, new) if l.startswith(old.split(",")[0] + "," + old.split(",")[1] + ",") else l for l in lines]


def failed(v):
    return [c["name"] for c in v["checks"] if not c["ok"]]


good = run()
assert good["verified"] and good["written"] == 120 * 60 and good["clock"] == 120 * 60 - 1
assert good["pay_written"] == 9600 and good["pay_clock"] == 9598.67
assert good["finding"]["gap_h"] == 11 and good["finding"]["upto"].day == 17
assert [r["date"].day for r in good["finding"]["missed"]] == [18, 20]

cases = {
    "one reading misreads a digit": (None, swap("1,22,Worked,5:30", "1,22,Worked,6:30"), "Two independent readings agree"),
    "both readings misread the same finish time": (swap("1,23,Worked,5:30,11:00", "1,23,Worked,5:30,11:30"),) * 2 + ("Finish minus start equals the written total",),
    "both readings misread a written total (5h read as 6h)": (swap("1,27,Worked,5:00,10:00,5h", "1,27,Worked,5:00,10:00,6h"),) * 2 + ("Finish minus start equals the written total",),
    "a row is skipped": (lambda l: [x for x in l if not x.startswith("1,25,")],) * 2 + ("Dates run in order with no gaps",),
    "a Closed day is read as a Day off": (swap("1,28,Closed", "1,28,Day off"),) * 2 + ("Closed days are exactly the Mondays",),
    "an unreadable total": (swap("2,16,Worked,5:30,11:00,5h30m", "2,16,Worked,5:30,11:00,5h3?"),) * 2 + ("Every shift is a readable, plausible length",),
}
for name, (ea, eb, expected) in cases.items():
    v = run(ea, eb)
    assert not v["verified"] and expected in failed(v), (name, failed(v))
    print(f"caught: {name}  ->  FAIL '{expected}'")
print(f"all {len(cases)} planted errors caught; clean period verifies")
