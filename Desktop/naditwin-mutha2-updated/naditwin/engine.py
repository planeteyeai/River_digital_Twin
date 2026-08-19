"""
NadiTwin demo engine — Mula-Mutha reach — SYNTHETIC DEMONSTRATION DATA ONLY.

Same product mechanics as the generic NadiTwin demo, but the reach
geometry (chainage, lon/lat, river width) is derived from a real,
user-supplied KML polygon (a hand-traced outline of a Mula-Mutha reach,
Pune) instead of a straight synthetic line:

  - chainage_profile.json  : centerline stations (10 m spacing) extracted
                              from the KML polygon via a Voronoi-skeleton
                              centerline algorithm, each with real lon/lat
                              and the polygon cross-section width at that
                              station.
  - reach_polygon.json     : the original KML polygon (lon/lat) for the
                              dashboard basemap overlay.

Bed elevation, embankment crest, per-cell sigma, discharge "truth",
ensemble forecasts, margins, alerts and scorecard are ALL still
synthetic/toy — exactly as in the generic demo. Only the plan-view
geometry (where the reach runs, how wide it is at each chainage) comes
from the real KML. There is no DEM, no bathymetry survey, and no real
discharge record behind this; nothing here should be used for any real
decision.

Pure Python standard library at runtime (chainage_profile.json /
reach_polygon.json are pre-computed once from the KML using
extract_centerline.py, which needs shapely/pyproj/scipy/networkx —
those are NOT required to run the server itself).
"""

import json
import math
import random
import csv
import os
import time as _time

# ----------------------------- configuration -----------------------------

HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "chainage_profile.json")) as f:
    _STATIONS = json.load(f)
with open(os.path.join(HERE, "reach_polygon.json")) as f:
    REACH_POLYGON_LONLAT = json.load(f)
_LANDMARKS_PATH = os.path.join(HERE, "landmarks.json")
if os.path.exists(_LANDMARKS_PATH):
    with open(_LANDMARKS_PATH) as f:
        LANDMARKS = json.load(f)
else:
    LANDMARKS = []

N_CELLS = len(_STATIONS)                      # stations along the real centerline
CHAINAGE_M = [s["chainage_m"] for s in _STATIONS]
LON = [s["lon"] for s in _STATIONS]
LAT = [s["lat"] for s in _STATIONS]
REAL_WIDTH_M = [s["width_m"] for s in _STATIONS]
REACH_LEN_M = CHAINAGE_M[-1]

PAST_HOURS = 72
FORECAST_HOURS = 72
N_MEMBERS = 50
TRUTH_HOURS = PAST_HOURS + 480   # long truth so the sim can be advanced

BED_US_ELEV = 100.0     # upstream bed elevation (m, arbitrary datum) — SYNTHETIC
SLOPE = 0.0009           # m per m — steeper toy slope for a short urban reach
DEPTH_COEF = 0.10        # hydraulic-geometry style depth = c * Q^0.6 * width_factor
DEPTH_EXP = 0.6

_MEAN_WIDTH = sum(REAL_WIDTH_M) / len(REAL_WIDTH_M)


class TwinEngine:
    def __init__(self, seed=42, gauge_csv=None):
        self.seed = seed
        self.rng = random.Random(seed)
        self.t0 = _time.time()
        self.now_idx = PAST_HOURS + 24
        self._build_geometry()
        self._build_truth_discharge(gauge_csv)
        self._build_assets()
        self.refresh_forecast()

    # ------------------------- geometry / bathymetry -------------------------

    def _build_geometry(self):
        """Bed/crest/sigma are still SYNTHETIC (toy formulas, no DEM). The
        width_factor layer, however, is derived from the real KML polygon
        cross-section width at each chainage — this is the one genuinely
        measured layer in the demo."""
        rng = random.Random(self.seed + 1)
        self.bed = []
        self.crest = []
        self.width_factor = []
        self.sigma_bed = []
        for i in range(N_CELLS):
            x = CHAINAGE_M[i]
            base = BED_US_ELEV - SLOPE * x
            pools = 0.6 * math.sin(2 * math.pi * x / 500.0) \
                  + 0.3 * math.sin(2 * math.pi * x / 140.0 + 1.3)
            noise = rng.gauss(0, 0.12)
            bed = base + pools + noise
            self.bed.append(bed)
            crest = base + 6.0 + 0.5 * math.sin(2 * math.pi * x / 700.0 + 0.7)
            # deliberately weak demo segments, picked near the narrowest
            # real cross-sections (narrow => higher toy depth => more exposed)
            if REAL_WIDTH_M[i] < _MEAN_WIDTH * 0.55:
                crest -= 1.4
            self.crest.append(crest)
            # real-geometry-derived width factor, normalised around 1.0
            wf = REAL_WIDTH_M[i] / _MEAN_WIDTH
            self.width_factor.append(max(0.15, min(2.2, wf)))
            # sigma: ends of the traced polygon are least reliable (hand
            # digitised near the boundary), middle stations more confident
            edge_frac = min(x, REACH_LEN_M - x) / (REACH_LEN_M / 2.0)
            s = 0.6 - 0.4 * edge_frac
            self.sigma_bed.append(round(max(0.12, s), 3))

    # ------------------------- discharge truth series -------------------------

    def _build_truth_discharge(self, gauge_csv):
        self.q_truth = None
        if gauge_csv and os.path.exists(gauge_csv):
            try:
                vals = []
                with open(gauge_csv, newline="") as f:
                    for row in csv.reader(f):
                        if not row:
                            continue
                        try:
                            vals.append(float(row[-1]))
                        except ValueError:
                            continue
                if len(vals) >= PAST_HOURS + FORECAST_HOURS:
                    self.q_truth = vals[:TRUTH_HOURS]
                    while len(self.q_truth) < TRUTH_HOURS:
                        self.q_truth.append(vals[-1])
                    self.q_source = "user_csv:" + os.path.basename(gauge_csv)
            except Exception:
                self.q_truth = None
        if self.q_truth is None:
            rng = random.Random(self.seed + 2)
            base = 180.0
            pulses = []
            t = 20
            while t < TRUTH_HOURS:
                amp = rng.uniform(200, 1400)
                width = rng.uniform(6, 20)
                pulses.append((t, amp, width))
                t += int(rng.uniform(40, 110))
            q = []
            for h in range(TRUTH_HOURS):
                v = base + 30 * math.sin(2 * math.pi * h / 240.0)
                for (pt, amp, w) in pulses:
                    v += amp * math.exp(-0.5 * ((h - pt) / w) ** 2)
                v *= (1 + rng.gauss(0, 0.015))
                q.append(max(40.0, v))
            self.q_truth = q
            self.q_source = "synthetic_demo"

    # ------------------------------- assets -------------------------------

    def _build_assets(self):
        def crest_at(x_m):
            return self.crest[self._cell_for_chainage(x_m)]

        # placed at chainages tagged to real Pune localities along the
        # reach (Sangam -> Bund Garden -> Dhanori -> Wadgaon Sheri ->
        # Kharadi -> Mundhwa -> Hadapsar -> Manjari, see landmarks.json /
        # reverse_and_tag_landmarks.py). Asset TYPE/threshold/exposure are
        # still illustrative DEMO placeholders, not verified real
        # infrastructure -- only the chainage + locality tag is grounded
        # in the reversed, KML-derived centerline.
        type_cycle = ["embankment", "habitation", "habitation", "embankment",
                      "bridge", "embankment", "infrastructure", "habitation"]
        self.assets = []
        if LANDMARKS:
            ordered = sorted(LANDMARKS, key=lambda lm: lm["chainage_m"])
            for i, lm in enumerate(ordered):
                x = lm["chainage_m"]
                typ = type_cycle[i % len(type_cycle)]
                cell = self._cell_for_chainage(x)
                aid = f"{typ[:3].upper()}-{i+1}"
                self.assets.append({
                    "id": aid,
                    "name": f"{lm['name']} — {typ} (illustrative)",
                    "type": typ,
                    "locality": lm["name"],
                    "chainage_m": round(x, 1),
                    "lon": LON[cell], "lat": LAT[cell],
                    "threshold": round(crest_at(x) - 0.8, 2),
                })
        else:
            # fallback if landmarks.json hasn't been generated
            picks = [
                ("EMB-A", "Left-bank embankment (narrow section)", "embankment", REACH_LEN_M * 0.10),
                ("EMB-B", "Right-bank embankment (narrow section)", "embankment", REACH_LEN_M * 0.55),
                ("VIL-1", "River-front habitation, u/s bend", "habitation", REACH_LEN_M * 0.28),
                ("VIL-2", "River-front habitation, d/s bend", "habitation", REACH_LEN_M * 0.78),
                ("BRG-1", "Road/rail crossing (illustrative)", "bridge", REACH_LEN_M * 0.45),
                ("PMP-1", "Riverside utility structure", "infrastructure", REACH_LEN_M * 0.92),
            ]
            for aid, name, typ, x in picks:
                cell = self._cell_for_chainage(x)
                self.assets.append({
                    "id": aid, "name": name, "type": typ,
                    "chainage_m": round(x, 1),
                    "lon": LON[cell], "lat": LAT[cell],
                    "threshold": round(crest_at(x) - 0.8, 2),
                })

    def _cell_for_chainage(self, x_m):
        # CHAINAGE_M is monotonic increasing; nearest-station lookup
        best = 0
        best_d = abs(CHAINAGE_M[0] - x_m)
        for i, c in enumerate(CHAINAGE_M):
            d = abs(c - x_m)
            if d < best_d:
                best, best_d = i, d
        return best

    # --------------------------- hydraulic mapping ---------------------------

    def _depth_from_q(self, q, cell):
        return DEPTH_COEF * (q ** DEPTH_EXP) / max(0.4, self.width_factor[cell])

    def wse_profile(self, q):
        prof = []
        for i in range(N_CELLS):
            att = 1.0 - 0.08 * (i / N_CELLS)
            d = self._depth_from_q(q * att, i)
            prof.append(self.bed[i] + d)
        return prof

    def wse_at(self, q, cell):
        att = 1.0 - 0.08 * (cell / N_CELLS)
        return self.bed[cell] + self._depth_from_q(q * att, cell)

    # ------------------------------ forecasting ------------------------------

    def refresh_forecast(self):
        self.members = []
        for m in range(N_MEMBERS):
            rng = random.Random(self.seed * 1000 + self.now_idx * 7 + m)
            phase = rng.gauss(0, 2.5)
            bias = rng.gauss(0, 0.04)
            series = []
            noise = 0.0
            for k in range(1, FORECAST_HOURS + 1):
                noise += rng.gauss(0, 0.012)
                idx = self.now_idx + k + phase
                i0 = max(0, min(TRUTH_HOURS - 2, int(idx)))
                frac = min(1.0, max(0.0, idx - i0))
                q = self.q_truth[i0] * (1 - frac) + self.q_truth[i0 + 1] * frac
                series.append(max(30.0, q * (1 + bias + noise)))
            self.members.append(series)

    def q_quantiles(self, k, qs=(0.1, 0.5, 0.9)):
        vals = sorted(m[k] for m in self.members)
        out = []
        for q in qs:
            pos = q * (len(vals) - 1)
            lo = int(pos)
            hi = min(lo + 1, len(vals) - 1)
            out.append(vals[lo] + (vals[hi] - vals[lo]) * (pos - lo))
        return out

    # ------------------------------- analytics -------------------------------

    def state_now(self):
        q = self.q_truth[self.now_idx]
        return {"q_now": round(q, 1), "wse": [round(v, 3) for v in self.wse_profile(q)]}

    def observed_hydrograph(self, cell):
        out = []
        for h in range(self.now_idx - PAST_HOURS, self.now_idx + 1):
            out.append(round(self.wse_at(self.q_truth[h], cell), 3))
        return out

    def forecast_hydrograph(self, cell):
        med, p10, p90 = [], [], []
        for k in range(FORECAST_HOURS):
            q10, q50, q90 = self.q_quantiles(k)
            p10.append(round(self.wse_at(q10, cell), 3))
            med.append(round(self.wse_at(q50, cell), 3))
            p90.append(round(self.wse_at(q90, cell), 3))
        return {"median": med, "p10": p10, "p90": p90}

    def forecast_profile(self, lead_h):
        k = max(0, min(FORECAST_HOURS - 1, lead_h - 1))
        q10, q50, q90 = self.q_quantiles(k)
        return {
            "lead_h": lead_h,
            "median": [round(v, 3) for v in self.wse_profile(q50)],
            "p10": [round(v, 3) for v in self.wse_profile(q10)],
            "p90": [round(v, 3) for v in self.wse_profile(q90)],
        }

    def margins(self):
        out = []
        q_now = self.q_truth[self.now_idx]
        for a in self.assets:
            cell = self._cell_for_chainage(a["chainage_m"])
            wse_now = self.wse_at(q_now, cell)
            margin_now = a["threshold"] - wse_now
            exceed_members = 0
            tth = None
            min_margin_med = margin_now
            for k in range(FORECAST_HOURS):
                q10, q50, q90 = self.q_quantiles(k)
                m_med = a["threshold"] - self.wse_at(q50, cell)
                min_margin_med = min(min_margin_med, m_med)
                if tth is None and m_med <= 0:
                    tth = k + 1
            for m in self.members:
                if any(self.wse_at(m[k], cell) >= a["threshold"]
                       for k in range(FORECAST_HOURS)):
                    exceed_members += 1
            p = exceed_members / N_MEMBERS
            if p >= 0.6 or margin_now <= 0:
                status = "DANGER"
            elif p >= 0.3:
                status = "WARNING"
            elif p >= 0.1:
                status = "WATCH"
            else:
                status = "SAFE"
            out.append({
                "id": a["id"], "name": a["name"], "type": a["type"],
                "chainage_m": a["chainage_m"], "lon": a["lon"], "lat": a["lat"],
                "threshold": a["threshold"],
                "wse_now": round(wse_now, 2),
                "margin_now_m": round(margin_now, 2),
                "min_margin_median_m": round(min_margin_med, 2),
                "p_exceed_72h": round(p, 2),
                "time_to_threshold_h": tth,
                "status": status,
            })
        return out

    def alerts(self):
        out = []
        for m in self.margins():
            if m["status"] in ("WATCH", "WARNING", "DANGER"):
                msg = (f"{m['name']}: probability of threshold exceedance in next "
                       f"72 h is {int(m['p_exceed_72h']*100)}%.")
                if m["time_to_threshold_h"]:
                    msg += (f" Median forecast crosses threshold in "
                            f"~{m['time_to_threshold_h']} h.")
                msg += f" Current margin {m['margin_now_m']} m."
                out.append({"severity": m["status"], "asset": m["id"],
                            "message": msg,
                            "confidence_note":
                                "Ensemble-based estimate on SYNTHETIC demo data."})
        return out

    def scorecard(self):
        if self.now_idx - 24 < 0:
            return {"note": "insufficient history yet", "rows": []}
        saved_idx = self.now_idx
        self.now_idx = saved_idx - 24
        self.refresh_forecast()
        cell = self._cell_for_chainage(self.assets[0]["chainage_m"])
        errs = []
        hits = misses = false_alarms = 0
        thr = self.assets[0]["threshold"]
        for k in range(24):
            q10, q50, q90 = self.q_quantiles(k)
            pred = self.wse_at(q50, cell)
            truth = self.wse_at(self.q_truth[self.now_idx + 1 + k], cell)
            errs.append((pred - truth) ** 2)
            pe = pred >= thr
            te = truth >= thr
            if pe and te:
                hits += 1
            elif te and not pe:
                misses += 1
            elif pe and not te:
                false_alarms += 1
        rmse = math.sqrt(sum(errs) / len(errs))
        self.now_idx = saved_idx
        self.refresh_forecast()
        return {
            "note": "",
            "rows": [
                {"metric": f"WSE 24 h forecast RMSE at {self.assets[0]['id']} ({self.assets[0].get('locality','')})",
                 "value": f"{rmse:.2f} m"},
                {"metric": "Threshold-exceedance hits (24 h)", "value": str(hits)},
                {"metric": "Misses", "value": str(misses)},
                {"metric": "False alarms", "value": str(false_alarms)},
                {"metric": "Ensemble size", "value": str(N_MEMBERS)},
                {"metric": "Data source", "value": self.q_source},
            ],
        }

    def meta(self):
        return {
            "product": "NadiTwin demo twin — Mula-Mutha reach (real KML geometry)",
            "disclaimer": ("SYNTHETIC DEMONSTRATION DATA. Reach plan-view geometry "
                            "(centerline + width) is extracted from a user-supplied "
                            "KML polygon of a real Mula-Mutha reach, Pune. Bed "
                            "elevation, discharge, forecasts, thresholds and assets "
                            "are ALL synthetic/toy. Contains no real river "
                            "measurements, no DEM/bathymetry, and no real gauge "
                            "record. Must not be used for any real decision."),
            "reach_km": round(REACH_LEN_M / 1000.0, 3),
            "n_cells": N_CELLS,
            "past_hours": PAST_HOURS,
            "forecast_hours": FORECAST_HOURS,
            "members": N_MEMBERS,
            "sim_hour": self.now_idx - PAST_HOURS,
            "q_source": self.q_source,
            "assets": self.assets,
            "chainage_km": [round(v / 1000.0, 4) for v in CHAINAGE_M],
            "lon": LON,
            "lat": LAT,
            "real_width_m": REAL_WIDTH_M,
            "reach_polygon_lonlat": REACH_POLYGON_LONLAT,
            "landmarks": LANDMARKS,
            "bed": [round(v, 3) for v in self.bed],
            "crest": [round(v, 3) for v in self.crest],
            "sigma_bed": self.sigma_bed,
        }

    def advance(self, hours=6):
        hours = int(hours)
        # Allow -24 to +24; reject zero
        hours = max(-24, min(24, hours))
        if hours == 0:
            hours = 1
        # Clamp so sim_hour never goes below 0 or past available truth data
        self.now_idx = max(
            PAST_HOURS,
            min(TRUTH_HOURS - FORECAST_HOURS - 2, self.now_idx + hours)
        )
        self.refresh_forecast()
        return {"sim_hour": self.now_idx - PAST_HOURS}
