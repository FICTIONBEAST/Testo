#!/usr/bin/env python3
"""
visualize.py  --  Deliverable 4.4
Offline visualization of the parser CSV (Deliverable 4.1).

================================================================================
WHAT THIS DOES
  * Reads the CSV produced by marauder_parser.py.
  * Produces three plots, entirely OFFLINE:
      1. RSSI over time, per BSSID/SSID (line chart).
      2. Channel occupancy (bar chart).
      3. Encryption-type distribution (bar chart).
  * Default output is a SINGLE self-contained HTML dashboard (no external JS,
    no CDNs, no network calls -- the data is inlined and drawn with vanilla
    <canvas>). Optionally renders PNGs with matplotlib if you prefer.

WHAT THIS DOES *NOT* DO
  * NO external network calls of any kind. The HTML output embeds its data and
    its (tiny, hand-written) drawing code; open it offline in any browser.
  * It does not modify the input CSV.

--------------------------------------------------------------------------------
AUTHORIZED USE ONLY
  Visualize only data you collected from networks you own or are explicitly
  authorized to assess.
--------------------------------------------------------------------------------

DEPENDENCIES
  * Python 3.8+  (HTML mode uses the standard library ONLY)
  * matplotlib   (OPTIONAL)  pip install matplotlib   # only for --png mode

USAGE
  # Single self-contained HTML dashboard (default, no extra deps):
  python3 visualize.py --csv networks.csv --html dashboard.html

  # PNG charts via matplotlib instead:
  python3 visualize.py --csv networks.csv --png --outdir charts/
"""

import argparse
import csv
import json
import sys
from collections import defaultdict, OrderedDict


def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    return rows


def _label(row):
    return row.get("ssid") or row.get("bssid") or "(hidden)"


def aggregate(rows):
    """Build the structures the charts need."""
    # RSSI over time per network. CSV has first_seen/last_seen + a single rssi.
    # We plot (timestamp, rssi) points using first_seen as x; with repeated
    # captures this becomes a time series. We keep both seen timestamps.
    series = OrderedDict()
    chan_counts = defaultdict(int)
    enc_counts = defaultdict(int)

    for r in rows:
        label = _label(r)
        rssi = r.get("rssi_dbm", "")
        try:
            rssi = int(rssi)
        except (ValueError, TypeError):
            rssi = None
        pts = series.setdefault(label, [])
        for tkey in ("first_seen", "last_seen"):
            t = r.get(tkey, "")
            if t and rssi is not None:
                pts.append((t, rssi))

        ch = r.get("channel", "").strip()
        if ch:
            chan_counts[ch] += 1
        enc = (r.get("encryption") or "unknown").strip() or "unknown"
        enc_counts[enc] += 1

    # de-dup + sort each series by timestamp
    for k in series:
        series[k] = sorted(set(series[k]))
    return series, dict(chan_counts), dict(enc_counts)


# -----------------------------------------------------------------------------
# HTML dashboard -- single file, self-contained, no network.
# -----------------------------------------------------------------------------
_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Marauder Scan Dashboard (offline)</title>
<style>
  body{font-family:system-ui,Arial,sans-serif;margin:24px;background:#0f1115;color:#e6e6e6}
  h1{font-size:20px} h2{font-size:15px;margin-top:28px;color:#8fd}
  .note{color:#9aa;font-size:12px;margin-bottom:18px}
  canvas{background:#171a21;border:1px solid #2a2f3a;border-radius:8px;margin-top:8px}
  .legend{font-size:11px;color:#bcd;margin-top:6px;line-height:1.5em}
  .legend span{display:inline-block;margin-right:12px}
  .sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:middle}
</style></head><body>
<h1>ESP32 Marauder — Scan Dashboard</h1>
<div class="note">Generated offline from CSV. No network calls. Authorized testing only.</div>

<h2>1 · RSSI over time (per network)</h2>
<canvas id="rssi" width="900" height="360"></canvas>
<div class="legend" id="rssiLegend"></div>

<h2>2 · Channel occupancy</h2>
<canvas id="chan" width="900" height="280"></canvas>

<h2>3 · Encryption distribution</h2>
<canvas id="enc" width="900" height="280"></canvas>

<script>
const SERIES = __SERIES__;
const CHANS  = __CHANS__;
const ENC    = __ENC__;

const PALETTE = ["#5ad","#fa6","#6f6","#f66","#c9f","#ff6","#6ff","#f9a","#9f9","#fc6"];

function axes(ctx,w,h,pad){
  ctx.strokeStyle="#3a4150"; ctx.lineWidth=1; ctx.beginPath();
  ctx.moveTo(pad,8); ctx.lineTo(pad,h-pad); ctx.lineTo(w-8,h-pad); ctx.stroke();
}

// ---- RSSI over time ----
(function(){
  const c=document.getElementById("rssi"), ctx=c.getContext("2d");
  const w=c.width,h=c.height,pad=46;
  const names=Object.keys(SERIES);
  let times=[],rssis=[];
  names.forEach(n=>SERIES[n].forEach(p=>{times.push(Date.parse(p[0]));rssis.push(p[1]);}));
  if(times.length===0){ctx.fillStyle="#888";ctx.fillText("no data",pad,h/2);return;}
  const t0=Math.min(...times),t1=Math.max(...times)||t0+1;
  const rMin=Math.min(...rssis,-100), rMax=Math.max(...rssis,-30);
  const xx=t=>pad+(w-pad-12)*((t-t0)/((t1-t0)||1));
  const yy=r=>8+(h-pad-8)*((rMax-r)/((rMax-rMin)||1));
  axes(ctx,w,h,pad);
  ctx.fillStyle="#9aa";ctx.font="10px sans-serif";
  for(let r=rMax;r>=rMin;r-=10){ctx.fillText(r+" dBm",2,yy(r)+3);
    ctx.strokeStyle="#222833";ctx.beginPath();ctx.moveTo(pad,yy(r));ctx.lineTo(w-8,yy(r));ctx.stroke();}
  const leg=document.getElementById("rssiLegend");
  names.forEach((n,i)=>{
    const col=PALETTE[i%PALETTE.length], pts=SERIES[n];
    ctx.strokeStyle=col;ctx.fillStyle=col;ctx.lineWidth=1.5;ctx.beginPath();
    pts.forEach((p,j)=>{const x=xx(Date.parse(p[0])),y=yy(p[1]);
      if(j===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});
    ctx.stroke();
    pts.forEach(p=>{ctx.beginPath();ctx.arc(xx(Date.parse(p[0])),yy(p[1]),2.5,0,7);ctx.fill();});
    const s=document.createElement("span");
    s.innerHTML='<span class="sw" style="background:'+col+'"></span>'+n;
    leg.appendChild(s);
  });
})();

// ---- generic bar chart ----
function bar(id,obj,color,sortNum){
  const c=document.getElementById(id),ctx=c.getContext("2d");
  const w=c.width,h=c.height,pad=46;
  let keys=Object.keys(obj);
  if(keys.length===0){ctx.fillStyle="#888";ctx.fillText("no data",pad,h/2);return;}
  keys.sort(sortNum?((a,b)=>(+a)-(+b)):((a,b)=>obj[b]-obj[a]));
  const max=Math.max(...keys.map(k=>obj[k]));
  axes(ctx,w,h,pad);
  const bw=(w-pad-20)/keys.length, gap=Math.min(14,bw*0.25);
  ctx.font="11px sans-serif";
  keys.forEach((k,i)=>{
    const bh=(h-pad-16)*(obj[k]/max);
    const x=pad+10+i*bw, y=h-pad-bh;
    ctx.fillStyle=color;ctx.fillRect(x,y,bw-gap,bh);
    ctx.fillStyle="#cde";ctx.fillText(obj[k],x+(bw-gap)/2-4,y-4);
    ctx.fillStyle="#9aa";
    ctx.save();ctx.translate(x+(bw-gap)/2,h-pad+4);ctx.rotate(0.0);
    ctx.fillText(k,-(""+k).length*3,10);ctx.restore();
  });
}
bar("chan",CHANS,"#5ad",true);
bar("enc",ENC,"#fa6",false);
</script>
</body></html>
"""


def write_html(series, chans, enc, path):
    html = (_HTML_TEMPLATE
            .replace("__SERIES__", json.dumps(series))
            .replace("__CHANS__", json.dumps(chans))
            .replace("__ENC__", json.dumps(enc)))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"[+] Wrote offline dashboard -> {path}")


# -----------------------------------------------------------------------------
# matplotlib PNG mode (optional)
# -----------------------------------------------------------------------------
def write_png(series, chans, enc, outdir):
    try:
        import matplotlib
        matplotlib.use("Agg")  # no display, no network
        import matplotlib.pyplot as plt
        from datetime import datetime
    except ImportError:
        sys.stderr.write("matplotlib not installed; install with: pip install matplotlib\n")
        return 2
    import os
    os.makedirs(outdir, exist_ok=True)

    # 1) RSSI over time
    plt.figure(figsize=(10, 4))
    for name, pts in series.items():
        if not pts:
            continue
        xs = [datetime.fromisoformat(p[0]) for p in pts]
        ys = [p[1] for p in pts]
        plt.plot(xs, ys, marker="o", markersize=3, label=name)
    plt.ylabel("RSSI (dBm)"); plt.xlabel("time"); plt.title("RSSI over time per network")
    if series:
        plt.legend(fontsize=6, ncol=2)
    plt.tight_layout(); plt.savefig(os.path.join(outdir, "rssi_over_time.png"), dpi=120); plt.close()

    # 2) channel occupancy
    plt.figure(figsize=(8, 3.5))
    keys = sorted(chans, key=lambda k: int(k))
    plt.bar(keys, [chans[k] for k in keys], color="#3a7")
    plt.ylabel("# networks"); plt.xlabel("channel"); plt.title("Channel occupancy")
    plt.tight_layout(); plt.savefig(os.path.join(outdir, "channel_occupancy.png"), dpi=120); plt.close()

    # 3) encryption distribution
    plt.figure(figsize=(8, 3.5))
    ekeys = sorted(enc, key=lambda k: -enc[k])
    plt.bar(ekeys, [enc[k] for k in ekeys], color="#d83")
    plt.ylabel("# networks"); plt.xlabel("encryption"); plt.title("Encryption distribution")
    plt.tight_layout(); plt.savefig(os.path.join(outdir, "encryption_distribution.png"), dpi=120); plt.close()

    print(f"[+] Wrote PNG charts -> {outdir}/")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Offline visualization of Marauder scan CSV.")
    ap.add_argument("--csv", required=True, help="CSV from marauder_parser.py")
    ap.add_argument("--html", default="dashboard.html", help="output HTML file (default)")
    ap.add_argument("--png", action="store_true", help="render PNGs with matplotlib instead")
    ap.add_argument("--outdir", default="charts", help="PNG output dir (with --png)")
    args = ap.parse_args(argv)

    rows = load_csv(args.csv)
    series, chans, enc = aggregate(rows)

    if args.png:
        return write_png(series, chans, enc, args.outdir)
    write_html(series, chans, enc, args.html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
