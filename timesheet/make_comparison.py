"""Side-by-side: original notebook photo (left) vs rendered OCR workbook (right), one panel per page."""
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFont

photos, renders, out = sys.argv[1:3], sys.argv[3:5], sys.argv[5]
H = 1500
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
except OSError:
    font = ImageFont.load_default()

def trim(im):
    bg = Image.new(im.mode, im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).getbbox()
    return im.crop((box[0] - 30, box[1] - 30, box[2] + 30, box[3] + 30))

def fit(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)

panels = []
for i, (p, r) in enumerate(zip(photos, renders), 1):
    a = fit(Image.open(p).convert("RGB"), H)
    b = trim(Image.open(r).convert("RGB"))
    b = fit(b, min(H, round(b.height * 1.9)))
    w = a.width + b.width + 90
    canvas = Image.new("RGB", (w, H + 80), "white")
    d = ImageDraw.Draw(canvas)
    d.text((20, 20), f"Page {i} — ORIGINAL photo", fill="#222", font=font)
    d.text((a.width + 70, 20), f"Page {i} — OCR spreadsheet (ocr_verbatim.xlsx)", fill="#1F2A5C", font=font)
    canvas.paste(a, (20, 70))
    canvas.paste(b, (a.width + 70, 70))
    d.line([(a.width + 45, 70), (a.width + 45, H + 70)], fill="#999", width=3)
    panels.append(canvas)

W = max(p.width for p in panels)
sheet = Image.new("RGB", (W, sum(p.height for p in panels) + 40), "white")
y = 0
for p in panels:
    sheet.paste(p, (0, y)); y += p.height + 40
sheet.save(out, optimize=True)
print(out, sheet.size)
