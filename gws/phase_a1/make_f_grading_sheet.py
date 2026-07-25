"""Human-validation exhibit: 20 random strict-PIT Family-F events rendered as candlestick
charts with the detected trendline, touch markers, and entry bar — for Scott to grade
'real trendline break: y/n'. Seeded, era-stratified. Output: single self-contained HTML.

    python -m gws.phase_a1.make_f_grading_sheet
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")

from gws.phase_a1.detect_anchor_events import P, load_series          # noqa: E402

SEED = 20260719
RUN = "banchor3_pilot:f_confirm=10"
OUT = pathlib.Path(r"C:\Users\scott\Desktop\Kaizen-Alpha Reports\studies") / \
    "gws_f_grading_sheet_2026-07-25.html"


def f_geometry(d, h, lo, c, B_target, p):
    """Re-derive the (a0, a1, touches, line) that produced the event at bar B_target."""
    n = len(c)
    FW, FT = p["f_win"], p["f_tol"]
    swings = [i for i in range(10, n - 5) if h[i] == h[max(0, i - 10):i + 11].max()]
    for si, a0 in enumerate(swings):
        for a1 in swings[si + 1:]:
            if a1 - a0 < 5 or a1 - a0 > FW or h[a1] >= h[a0]:
                continue
            slope = (h[a1] - h[a0]) / (a1 - a0)
            end = min(a0 + FW + 1, n)
            line = h[a0] + slope * (np.arange(a0, end) - a0)
            seg_h, seg_c = h[a0:end], c[a0:end]
            near = (seg_h >= line * (1 - FT)) & (seg_c <= line)
            tidx = np.where(near)[0]
            picked, last = [], -9
            for tt in tidx:
                if tt - last >= 3:
                    picked.append(tt)
                    last = tt
            if len(picked) < p["f_touch"]:
                continue
            after = picked[-1] + 1
            brk = np.where(seg_c[after:] > line[after:] * 1.01)[0]
            for bb in brk:
                B = a0 + after + bb
                if B < a1 + p.get("f_confirm", 0):
                    continue
                if c[B] > c[B - 1]:
                    if B == B_target:
                        return a0, a1, [a0 + t for t in picked], slope
                    break
            break
    return None


def main() -> int:
    import plotly.graph_objects as go
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    ev = pd.DataFrame(conn.execute(
        "SELECT e.ticker_id, e.event_date, e.outcome, ent.norgate_symbol "
        "FROM gws.anchor_events e JOIN ka_history.entities ent "
        "ON ent.entity_id = e.ticker_id WHERE e.run_id=%s", (RUN,)).fetchall())
    ev["era"] = ev["event_date"].map(
        lambda d: "pre1990" if str(d) < "1990-01-01" else "1990s" if str(d) < "2000-01-01"
        else "2000s" if str(d) < "2010-01-01" else "2010s")
    rng = np.random.default_rng(SEED)
    sample = (ev.groupby("era", group_keys=False)
                .apply(lambda g: g.sample(min(5, len(g)), random_state=SEED))
                .reset_index(drop=True))

    p = {**P, "f_confirm": 10}
    figs = []
    for k, r in enumerate(sample.itertuples(), 1):
        s = load_series(conn, int(r.ticker_id))
        if s is None:
            continue
        d, o, h, lo, c, v = s
        didx = {dd: i for i, dd in enumerate(d)}
        B = didx.get(r.event_date)
        if B is None:
            continue
        geo = f_geometry(d, h, lo, c, B, p)
        w0, w1 = max(0, (geo[0] if geo else B - 90) - 10), min(len(c), B + 40)
        x = [str(dd) for dd in d[w0:w1]]
        fig = go.Figure(go.Candlestick(x=x, open=o[w0:w1], high=h[w0:w1],
                                       low=lo[w0:w1], close=c[w0:w1],
                                       showlegend=False))
        if geo:
            a0, a1, touches, slope = geo
            xs = [str(d[a0]), str(d[B])]
            ys = [h[a0], h[a0] + slope * (B - a0)]
            fig.add_scatter(x=xs, y=ys, mode="lines",
                            line=dict(color="orange", width=2), showlegend=False)
            fig.add_scatter(x=[str(d[t]) for t in touches],
                            y=[h[t] for t in touches], mode="markers",
                            marker=dict(color="orange", size=9, symbol="circle-open"),
                            showlegend=False)
        fig.add_scatter(x=[str(d[B])], y=[c[B]], mode="markers",
                        marker=dict(color="lime", size=12, symbol="triangle-up"),
                        showlegend=False)
        fig.update_layout(
            title=f"#{k}  {r.norgate_symbol}  {r.event_date}  (grade the SETUP, "
                  f"not the outcome)", height=420, template="plotly_dark",
            xaxis_rangeslider_visible=False, xaxis=dict(type="category", nticks=12),
            margin=dict(l=40, r=20, t=50, b=30))
        figs.append(fig)

    parts = [f.to_html(full_html=False,
                       include_plotlyjs=("cdn-off" and (i == 0)))
             for i, f in enumerate(figs)]
    html = ("<html><head><title>GWS F-Family Grading Sheet</title></head>"
            "<body style='background:#111;color:#ddd;font-family:sans-serif'>"
            "<h2>Family F (trendline break) — human validation sheet</h2>"
            "<p>20 strict-PIT detected events, era-stratified, seed 20260719. For each: "
            "is this a REAL declining-trendline breakout entry you would recognize? "
            "Reply in chat like: '1 y, 2 n, 3 y, ...'. Orange = detected line + touches; "
            "green triangle = entry bar. Post-entry bars shown only for context — grade "
            "the setup.</p>" + "".join(parts) + "</body></html>")
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({len(figs)} charts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
