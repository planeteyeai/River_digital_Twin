# NadiTwin Demo — Mula-Mutha River (full Pune reach, real KML geometry + satellite basemap)

Same product mechanics as the earlier NadiTwin demos, rebuilt against a
new, longer KML: `data/mula_mutha_river.kml` — a ~17 km traced reach of
the Mula-Mutha River through Pune (190-point polygon).

> **SYNTHETIC DEMONSTRATION DATA.** Only the centerline / chainage /
> river width come from your real KML. Bed elevation, embankment crest,
> discharge, forecasts, thresholds, and the six demo assets are ALL
> synthetic. There is no DEM, no bathymetry survey and no real gauge
> record behind this. Do not use it for any real-world decision.

## Run it

```
python3 run.py
```
Opens `http://localhost:8080`.

## What's new vs. the previous build

- **New KML, longer reach**: 16.96 km centerline, 1,698 chainage
  stations @ 10 m, width 82–400 m (vs. the earlier 1.64 km test polygon).
- **Satellite basemap**: the reach map now defaults to Esri World
  Imagery (satellite) with a layer-switcher (top-right of the map) to
  toggle back to OpenStreetMap street view.
- Traced polygon shown in cyan, extracted centerline in yellow (more
  visible over satellite imagery), demo assets as red markers.

## How the geometry was extracted

Same method as before (`extract_centerline.py`): parse KML polygon →
project to UTM 43N → densify boundary → Voronoi skeleton → keep edges
inside the polygon → longest-path centerline → resample every 10 m →
perpendicular cross-section width at each station. See the script for
full detail. Needs `shapely`, `pyproj`, `scipy`, `networkx` to re-run;
the server itself (`run.py`, `naditwin/engine.py`) only needs the
pre-computed `naditwin/chainage_profile.json` / `reach_polygon.json`
and the Python standard library.

## Layout

```
run.py                          launcher
extract_centerline.py           KML -> chainage/width extractor (dev tool)
data/mula_mutha_river.kml       your source KML
naditwin/engine.py              twin engine (real geometry + synthetic hydraulics)
naditwin/server.py              stdlib HTTP server + JSON API
naditwin/chainage_profile.json  extracted chainage stations (pre-computed)
naditwin/reach_polygon.json     traced polygon, lon/lat (pre-computed)
naditwin/static/dashboard.html  dashboard (Chart.js + Leaflet satellite/street map)
```

## API

`/api/meta`, `/api/state`, `/api/forecast/profile?lead=`,
`/api/hydrograph?cell=`, `/api/margins`, `/api/alerts`,
`/api/scorecard`, `POST /api/advance?hours=`. `/api/meta` includes
`lon`, `lat`, `real_width_m`, `reach_polygon_lonlat` for the map.
