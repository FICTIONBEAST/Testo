"""Self-contained SVG charts (no JavaScript, no external resources).

These render anywhere — including offline and inside sandboxed mobile file
viewers — because the output is plain SVG markup embedded directly in the page.
They are static (no hover/zoom), the trade-off for guaranteed display where an
external charting library cannot load.

Each ``build_*`` function returns an SVG string; ``write_html`` wraps one or
more of them into a standalone HTML document.
"""

from __future__ import annotations

import html

from . import data
from .model import dense_grid, fit_exponential_floor


def _esc(s):
    return html.escape(str(s), quote=True)


class Chart:
    """A minimal linear-axes SVG plotting surface working in data coordinates."""

    def __init__(self, width=900, height=520, margin=(64, 150, 78, 70),
                 title="", caption=""):
        # margin = (top, right, bottom, left)
        self.w = width
        self.h = height
        self.mt, self.mr, self.mb, self.ml = margin
        self.title = title
        self.caption = caption
        self.pl = self.ml
        self.pr = width - self.mr
        self.pt = self.mt
        self.pb = height - self.mb
        self.pw = self.pr - self.pl
        self.ph = self.pb - self.pt
        self.elems = []
        self.xmin = self.xmax = self.ymin = self.ymax = 0.0

    # -- scales -----------------------------------------------------------
    def xscale(self, xmin, xmax):
        self.xmin, self.xmax = xmin, xmax

    def yscale(self, ymin, ymax):
        self.ymin, self.ymax = ymin, ymax

    def px(self, x):
        return self.pl + (x - self.xmin) / (self.xmax - self.xmin) * self.pw

    def py(self, y):
        return self.pb - (y - self.ymin) / (self.ymax - self.ymin) * self.ph

    # -- primitives -------------------------------------------------------
    def _add(self, s):
        self.elems.append(s)

    def line_px(self, x0, y0, x1, y1, color, width=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self._add(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
                  f'stroke="{color}" stroke-width="{width}"{d} />')

    def text_px(self, x, y, s, size=12, color="#222", anchor="middle",
                italic=False, weight="normal", rotate=None):
        st = ' font-style="italic"' if italic else ""
        tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
        self._add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
                  f'text-anchor="{anchor}" font-weight="{weight}"'
                  f' font-family="system-ui,Arial,sans-serif"{st}{tr}>{_esc(s)}</text>')

    # -- composite --------------------------------------------------------
    def frame_and_grid(self, yticks, yfmt="{:g}", xticks=None, xlabels=None,
                       xtitle="", ytitle=""):
        # plot background
        self._add(f'<rect x="{self.pl:.1f}" y="{self.pt:.1f}" width="{self.pw:.1f}" '
                  f'height="{self.ph:.1f}" fill="#ffffff" stroke="#e3e3e3" />')
        # horizontal gridlines + y labels
        for yt in yticks:
            yp = self.py(yt)
            self.line_px(self.pl, yp, self.pr, yp, "#eee", 1)
            self.text_px(self.pl - 8, yp + 4, yfmt.format(yt), size=11,
                         color="#555", anchor="end")
        # x ticks + labels
        if xticks is not None:
            for i, xt in enumerate(xticks):
                xp = self.px(xt)
                self.line_px(xp, self.pb, xp, self.pb + 5, "#999", 1)
                lab = xlabels[i] if xlabels else f"{xt:g}"
                self.text_px(xp, self.pb + 20, lab, size=11, color="#555")
        # axis titles
        if xtitle:
            self.text_px((self.pl + self.pr) / 2, self.h - 34, xtitle, size=12,
                         color="#333")
        if ytitle:
            cx, cy = 18, (self.pt + self.pb) / 2
            self.text_px(cx, cy, ytitle, size=12, color="#333", rotate=-90)

    def polyline_data(self, pts, color, width=2, dash=None):
        if not pts:
            return
        coords = " ".join(f"{self.px(x):.1f},{self.py(y):.1f}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self._add(f'<polyline points="{coords}" fill="none" stroke="{color}" '
                  f'stroke-width="{width}"{d} />')

    def marker_data(self, x, y, color, r=4.5, filled=True):
        if filled:
            self._add(f'<circle cx="{self.px(x):.1f}" cy="{self.py(y):.1f}" r="{r}" '
                      f'fill="{color}" stroke="{color}" stroke-width="1.5" />')
        else:
            self._add(f'<circle cx="{self.px(x):.1f}" cy="{self.py(y):.1f}" r="{r}" '
                      f'fill="#ffffff" stroke="{color}" stroke-width="1.8" />')

    def bar_data(self, x_left, x_right, y_top, y_base, color, label=None):
        x0, x1 = self.px(x_left), self.px(x_right)
        y0, y1 = self.py(y_top), self.py(y_base)
        top = min(y0, y1)
        self._add(f'<rect x="{x0:.1f}" y="{top:.1f}" width="{(x1 - x0):.1f}" '
                  f'height="{abs(y1 - y0):.1f}" fill="{color}" />')
        if label is not None:
            ly = top - 6 if y_top >= y_base else max(y0, y1) + 16
            self.text_px((x0 + x1) / 2, ly, label, size=11, color="#333")

    def legend(self, items, x=None, y=None):
        # items: list of (label, color, dash_bool)
        x = self.pr + 16 if x is None else x
        y = self.pt + 6 if y is None else y
        for i, (label, color, dash) in enumerate(items):
            yy = y + i * 22
            da = ' stroke-dasharray="6,4"' if dash else ""
            self.line_px(x, yy, x + 24, yy, color, 3)
            if not dash:  # marker dot for series with points
                self._add(f'<circle cx="{x + 12:.1f}" cy="{yy:.1f}" r="3.5" fill="{color}" />')
            else:
                self._add(f'<line x1="{x:.1f}" y1="{yy:.1f}" x2="{x + 24:.1f}" '
                          f'y2="{yy:.1f}" stroke="{color}" stroke-width="3"{da} />')
            self.text_px(x + 30, yy + 4, label, size=11, color="#333", anchor="start")

    # -- output -----------------------------------------------------------
    def to_svg(self):
        title = ""
        if self.title:
            title = (f'<text x="{self.w / 2:.1f}" y="26" font-size="15" '
                     f'font-weight="600" text-anchor="middle" fill="#1a1a1a" '
                     f'font-family="system-ui,Arial,sans-serif">{_esc(self.title)}</text>')
        caption = ""
        if self.caption:
            caption = (f'<text x="{self.w / 2:.1f}" y="{self.h - 12}" font-size="10" '
                       f'font-style="italic" text-anchor="middle" fill="#777" '
                       f'font-family="system-ui,Arial,sans-serif">{_esc(self.caption)}</text>')
        body = "\n".join(self.elems)
        return (f'<svg viewBox="0 0 {self.w} {self.h}" '
                f'preserveAspectRatio="xMidYMid meet" '
                f'xmlns="http://www.w3.org/2000/svg" '
                f'style="width:100%;height:auto;max-width:{self.w}px;">\n'
                f'<rect width="{self.w}" height="{self.h}" fill="#ffffff" />\n'
                f'{title}\n{body}\n{caption}\n</svg>')


def _wrap_caption(text, width=95):
    words = text.split()
    lines, cur = [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > width:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def build_decay_svg():
    weeks = data.DECAY_WEEKS
    c = Chart(width=940, height=560, margin=(70, 230, 90, 70),
              title="Synthesized heartbreak recovery curves by gender and breakup type")
    c.xscale(-2, 106)
    c.yscale(0, 108)
    c.frame_and_grid(
        yticks=[0, 15, 30, 45, 60, 75, 90, 105],
        xticks=[0, 11, 26, 52, 78, 104],
        xtitle="Weeks since breakup",
        ytitle="Distress / longing intensity (0–100)",
    )

    fits = {}
    legend_items = []
    for key, curve in data.DECAY_CURVES.items():
        ys = curve["y"]
        color = curve["color"]
        gw = curve["grounded_through_week"]
        fit = fit_exponential_floor(weeks, ys)
        fits[key] = fit
        ts, fy = dense_grid(fit, t_max=weeks[-1])
        pts = list(zip(ts, fy))
        if gw >= 0:
            solid = [(x, y) for x, y in pts if x <= gw]
            dashed = [(x, y) for x, y in pts if x >= gw]
            c.polyline_data(solid, color, width=3)
            c.polyline_data(dashed, color, width=2, dash="6,4")
        else:
            c.polyline_data(pts, color, width=2, dash="6,4")
        for w, y in zip(weeks, ys):
            c.marker_data(w, y, color, filled=(gw >= 0 and w <= gw))
        legend_items.append((curve["label"], color, gw < 0))

    # threshold lines
    for name, level in data.THRESHOLDS.items():
        yp = c.py(level)
        c.line_px(c.pl, yp, c.pr, yp, "#999", 1, dash="2,3")
        c.text_px(c.pr - 4, yp - 4, name.replace("_", " ").title() + f" ({level})",
                  size=9, color="#777", anchor="end")
    # milestone lines
    for label, wk in data.MILESTONES.items():
        xp = c.px(wk)
        c.line_px(xp, c.pt, xp, c.pb, "#2f9e44", 1, dash="2,3")
        c.text_px(xp - 4, c.pt + 6, label, size=8, color="#2f9e44",
                  anchor="end", rotate=-90)

    c.legend(legend_items)
    # provenance caption (wrapped)
    for i, ln in enumerate(_wrap_caption(data.DECAY_SOURCE, width=120)):
        c.text_px(c.w / 2, c.h - 34 + i * 12, ln, size=9, italic=True, color="#888")
    return c.to_svg(), fits


def build_sbarra_svg():
    days = data.SBARRA_DAYS
    c = Chart(width=900, height=520, margin=(64, 190, 84, 70),
              title="Sbarra & Emery (2005): emotion trajectories, first 28 days (grounded)")
    c.xscale(0, 30)
    c.yscale(0, 65)
    c.frame_and_grid(
        yticks=[0, 10, 20, 30, 40, 50, 60],
        xticks=days, xtitle="Days since breakup", ytitle="Intensity (0–100)",
    )
    legend_items = []
    for emo in data.SBARRA_TRAJECTORIES.values():
        pts = list(zip(days, emo["y"]))
        c.polyline_data(pts, emo["color"], width=2)
        for x, y in pts:
            c.marker_data(x, y, emo["color"])
        legend_items.append((emo["label"], emo["color"], False))
    c.legend(legend_items)
    for i, ln in enumerate(_wrap_caption(data.SBARRA_SOURCE, width=110)):
        c.text_px(c.w / 2, c.h - 30 + i * 12, ln, size=9, italic=True, color="#888")
    return c.to_svg()


def build_morris_svg():
    genders = list(data.MORRIS_ANGUISH)
    c = Chart(width=820, height=500, margin=(64, 170, 84, 70),
              title="Peak breakup anguish by gender (Morris, Reiber & Roman 2015)")
    c.xscale(0, 2)
    c.yscale(0, 8)
    c.frame_and_grid(
        yticks=[0, 2, 4, 6, 8],
        xticks=[0.5, 1.5], xlabels=genders,
        xtitle="Gender", ytitle="Anguish (0–10)",
    )
    groups = [("emotional", "#d6336c", "Emotional anguish"),
              ("physical", "#1c7ed6", "Physical anguish")]
    bw = 0.18
    for gi, g in enumerate(genders):
        center = 0.5 + gi  # category centers
        for bi, (field, color, _lbl) in enumerate(groups):
            val = data.MORRIS_ANGUISH[g][field]
            left = center - bw + bi * bw
            c.bar_data(left, left + bw, val, 0, color, label=f"{val:.2f}")
    c.legend([(lbl, color, False) for _f, color, lbl in groups])
    for i, ln in enumerate(_wrap_caption(data.MORRIS_SOURCE, width=100)):
        c.text_px(c.w / 2, c.h - 30 + i * 12, ln, size=9, italic=True, color="#888")
    return c.to_svg()


def build_first_week_svg():
    emotions = list(data.FIRST_WEEK_DECLINES)
    colors = ["#d6336c", "#7048e8", "#e8590c"]
    c = Chart(width=820, height=500, margin=(64, 60, 84, 70),
              title="First-week decline in distress by emotion (Sbarra & Emery 2005)")
    c.xscale(0, len(emotions))
    c.yscale(-90, 10)
    c.frame_and_grid(
        yticks=[-90, -75, -60, -45, -30, -15, 0],
        xticks=[i + 0.5 for i in range(len(emotions))], xlabels=emotions,
        xtitle="Emotion", ytitle="Change over first week (%)",
    )
    # zero line
    c.line_px(c.pl, c.py(0), c.pr, c.py(0), "#888", 1)
    for i, e in enumerate(emotions):
        val = data.FIRST_WEEK_DECLINES[e]
        c.bar_data(i + 0.28, i + 0.72, val, 0, colors[i], label=f"{val}%")
    for i, ln in enumerate(_wrap_caption(data.FIRST_WEEK_SOURCE, width=100)):
        c.text_px(c.w / 2, c.h - 30 + i * 12, ln, size=9, italic=True, color="#888")
    return c.to_svg()


# ---------------------------------------------------------------------------
# HTML wrapper (fully self-contained — inline SVG, no scripts, no CDN)
# ---------------------------------------------------------------------------

def write_html(path, svgs, page_title, intro=""):
    """Write inline SVG figures into a standalone, offline HTML file."""
    blocks = "\n".join(
        f'<section style="margin:28px 0;">{svg}</section>' for svg in svgs
    )
    intro_html = f'<p style="color:#555;max-width:880px;">{_esc(intro)}</p>\n' if intro else ""
    doc = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"  <title>{_esc(page_title)}</title>\n"
        "  <style>body{font-family:system-ui,Arial,sans-serif;margin:20px;"
        "max-width:980px;} h1{font-size:1.3rem;} svg{display:block;}</style>\n"
        "</head>\n<body>\n"
        f"  <h1>{_esc(page_title)}</h1>\n{intro_html}{blocks}\n"
        "</body>\n</html>\n"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)


def write_svg(path, svg):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n' + svg + "\n")
