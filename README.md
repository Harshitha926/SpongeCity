# Sponge City Risk Detector

A decision-support tool that identifies which neighborhoods need rain gardens,
permeable pavement, or groundwater recharge wells based on urban flood/runoff
risk — built for HSR Layout / Bellandur, Bengaluru, using free satellite data.

Built for Smart India Hackathon 2026. Aligned with SDG 11 (Sustainable Cities),
SDG 13 (Climate Action), and SDG 6 (Clean Water).

## The problem

Bengaluru floods every monsoon because concrete has replaced natural
water-absorbing surfaces. Cities like Chennai, Mumbai, and Kochi are already
planning "sponge city" strategies (rain gardens, permeable pavement,
groundwater recharge) — Bengaluru hasn't yet. This project identifies exactly
*where* those interventions are needed, at a per-neighborhood-cell level,
using only free satellite data (no hardware, no sensors required).

## How it works

1. **Grid the area** into ~100m x 100m cells (Google Earth Engine)
2. **Pull features** per cell: elevation (SRTM), imperviousness (ESA
   WorldCover), distance to permanent water (JRC Global Surface Water)
3. **Detect flooding** using Sentinel-1 **radar** (not optical satellite) —
   because Bengaluru's monsoon cloud cover makes optical imagery unusable
   during actual flood events (confirmed: 99.999% cloud cover on the day of
   the May 22, 2026 flood)
4. **Filter false positives** using a dry-season (January) radar control —
   permanent lakes look "wet" year-round and must be excluded from flood-risk
   labels
5. **Train a Random Forest classifier** on the resulting labels to predict
   flood risk for every cell
6. **Generate recommendations** (rain garden / permeable pavement / recharge
   well / none) based on risk category and cell characteristics
7. **Visualize** as an interactive color-coded map

## Project structure

```
sponge-city-risk-detector/
├── earth_engine/
│   └── data_pull.js          # Run in code.earthengine.google.com
├── src/
│   ├── merge_data.py         # Combine wet + dry season data, filter false positives
│   ├── train_model.py        # Train Random Forest, score all cells
│   └── generate_map.py       # Build the interactive Folium map
├── data/                     # Raw CSVs exported from Earth Engine (not committed)
├── outputs/                  # Generated model, scored dataset, map (not committed)
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the pipeline

1. **Pull satellite data** — open `earth_engine/data_pull.js` in the
   [Earth Engine Code Editor](https://code.earthengine.google.com/), run it,
   and download both exported CSVs from Google Drive into `data/`:
   - `sponge_city_grid_dataset.csv`
   - `sponge_city_dry_season_control.csv`

2. **Merge and clean the data**
   ```bash
   python src/merge_data.py
   ```

3. **Train the model and score all cells**
   ```bash
   python src/train_model.py
   ```

4. **Generate the interactive map**
   ```bash
   python src/generate_map.py
   ```
   Open `outputs/sponge_city_risk_map.html` in a browser.

## Model performance

Trained on 1,288 grid cells (98 confirmed flood-risk, satellite-derived and
false-positive filtered), using elevation, imperviousness, and distance to
water as features:

- ROC-AUC: 0.76
- Feature importance: elevation (40%) > imperviousness (31%) > distance to
  water (30%)

This is a proof-of-concept trained on two confirmed 2026 flood events. Model
performance is expected to improve with more flood events and additional
features (rainfall intensity, slope, drain proximity).

## Known limitations

- Single ~12.5 sq km zone (HSR Layout / Bellandur), not city-wide
- Only 2 confirmed flood events used as ground truth (no official BBMP
  incident dataset was available/accessible)
- Radar revisit gaps mean flood detection may be several hours to a few days
  offset from the actual event
- Citizen-reporting feedback loop is designed but not yet implemented as a
  live app

## License

MIT
