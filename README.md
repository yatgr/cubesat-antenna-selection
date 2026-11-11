# CubeSat Antenna Selection

A framework and Python tool ([`antenna_selection.py`](antenna_selection.py)) for evaluating CubeSat antennas across **RF Performance**, **Mechanical & AIT (Assembly, Integration & Test)**, and **Space Qualification** criteria.

The selection process is divided into two stages:
1. **Stage 1 — Feasibility Screening:** Eliminates candidates that violate hard mission constraints (frequency band, polarization, CubeSat U-size, height profile, mass, or deployment mechanism).
2. **Stage 2 — Trade-Off Scoring:** Ranks surviving candidates using mission-specific weight profiles (`balanced`, `link_budget`, `compact_1u`, `low_risk`, `classic_5`).

---

## 1. Selection Criteria

### 1.1 RF & Link Budget (`data/example_rf_data.csv`)

| Criterion | Column | Type | Rationale |
|---|---|---|---|
| **Frequency Band** | `Frequency Band`, `Central Frequency (GHz)` | Filter | Must match the mission frequency allocation (UHF/VHF, S, X, Ka). |
| **Max Gain** | `Max Gain (dBi)` | Maximize | Drives link margin ($\text{EIRP}$ and $G/T$). |
| **Radiation Efficiency** | `Radiation Efficiency (%)` | Maximize | Minimizes DC power consumption and thermal dissipation. |
| **Impedance Bandwidth** | `Bandwidth (%)` | Maximize | $\lvert S_{11}\rvert \le -10\text{ dB}$ margin against fabrication tolerances and thermal drift. |
| **Polarization** | `Polarization` | Filter | `RHCP`/`LHCP` preferred in LEO to mitigate Faraday rotation and attitude mismatch. |
| **Axial Ratio Bandwidth** | `ARBW (%)` | Maximize | $\le 3\text{ dB}$ circular polarization purity bandwidth ($0\%$ for linear antennas). |

### 1.2 Mechanical & AIT (`data/example_ait_data.csv`)

| Criterion | Column / Derived | Type | Rationale |
|---|---|---|---|
| **CubeSat Size** | `Target CubeSat Size` | Filter | Bus form factor compatibility (`1U`, `3U`, `6U`, ...). |
| **Height Profile** | `Height_Profile_mm` *(3rd value of `Dimensions (mm)`)* | Minimize / Filter | Protrusion above panel (standard CDS deployer rail limit is $\le 6.5\text{ mm}$). |
| **Footprint Area** | `Footprint_Area_mm2` *(derived $L \times W$)* | Minimize | Panel surface area competing with body-mounted solar cells. |
| **Mass** | `Weight (g)` | Minimize / Filter | Impact on total spacecraft mass budget. |
| **Substrate & AIT** | `Substrate Material`, `Fabrication Method` | Maximize ($1\text{–}5$) | Space-grade low-loss/low-outgassing laminates (e.g., Rogers RT/duroid, RO4003C) score higher than commercial FR4; single-layer PCB scores higher than complex multilayer/air-gap assemblies. |
| **Deployment** | `Deployment Mechanism` | Filter / Risk | Conformal body-mounted designs avoid single-point mechanical deployment failures. |

### 1.3 Qualification & Heritage (`data/example_ait_data.csv`)

| Criterion | Column | Type | Rationale |
|---|---|---|---|
| **Qualification & TRL** | `Environmental Qualification Tests`, `Flight Heritage Mission` | Maximize ($1\text{–}5$) | Vibration + TVAC testing ($4.0$), partial testing ($2.5$), untested ($1.0$); $+1.0$ for orbital flight heritage; $-1.0$ if a deployment mechanism is required. |

---

## 2. Mission Weight Profiles

Weights sum to $1.00$ per profile (`--profile`):

| Criterion | Direction | `balanced` | `link_budget` | `compact_1u` | `low_risk` | `classic_5` |
|---|---|---|---|---|---|---|
| `Max Gain (dBi)` | Maximize | 0.18 | 0.28 | 0.12 | 0.12 | 0.25 |
| `Bandwidth (%)` | Maximize | 0.12 | 0.15 | 0.10 | 0.10 | 0.20 |
| `Radiation Efficiency (%)` | Maximize | 0.14 | 0.22 | 0.10 | 0.10 | 0.25 |
| `ARBW (%)` | Maximize | 0.06 | 0.10 | 0.03 | 0.03 | 0.00 |
| `Height_Profile_mm` | Minimize | 0.10 | 0.05 | 0.18 | 0.07 | 0.15 |
| `Footprint_Area_mm2` | Minimize | 0.07 | 0.03 | 0.16 | 0.04 | 0.00 |
| `Estimated_Weight_g` | Minimize | 0.07 | 0.04 | 0.10 | 0.04 | 0.15 |
| `Substrate_AIT_Score` | Maximize | 0.06 | 0.03 | 0.06 | 0.15 | 0.00 |
| `Qualification_Score` | Maximize | 0.20 | 0.10 | 0.15 | 0.35 | 0.00 |

- **Missing Data:** Unreported numeric values are imputed with the candidate-set median and tracked via `N_Criteria_Imputed`.
- **Multi-Band Extraction:** When `--band` is specified (e.g., `--band S`), slash-separated values (e.g., `6.10/11.30`) are extracted at the matching band index.
- **Scoring (`--method`):** Supports `topsis` (default closeness coefficient $C^* \in [0, 1]$) and `wsm` (normalized Weighted Sum Model).

---

## 3. Usage

```bash
pip install -r requirements.txt

# Run with default dataset and balanced profile
python antenna_selection.py

# Run with Stage 1 constraints and compact_1u profile
python antenna_selection.py \
    --rf data/example_rf_data.csv \
    --ait data/example_ait_data.csv \
    --band S \
    --polarization Circular \
    --max-cubesat-size 1U \
    --max-height 6.5 \
    --no-deployable \
    --profile compact_1u \
    --output ranking_results.csv
```

### CLI Options

| Argument | Default | Description |
|---|---|---|
| `--rf` | `data/example_rf_data.csv` | RF performance CSV/TSV path |
| `--ait` | `data/example_ait_data.csv` | Mechanical/AIT CSV/TSV path |
| `--output` | `ranking_results.csv` | Output CSV path |
| `--profile` | `balanced` | `balanced`, `link_budget`, `compact_1u`, `low_risk`, `classic_5` |
| `--method` | `topsis` | `topsis` or `wsm` |
| `--band` | `None` | Filter by frequency band (`S`, `X`, `UHF`, ...) |
| `--polarization` | `None` | Filter by polarization (`RHCP`, `LHCP`, `Circular`, `Linear`) |
| `--max-cubesat-size` | `None` | Max CubeSat size (`1U`, `2U`, `3U`, `6U`) |
| `--max-height` | `None` | Max Z-height thickness in mm |
| `--max-weight` | `None` | Max mass in grams |
| `--no-deployable` | `False` | Exclude mechanically deployable antennas |

---

## 4. References

1. **CubeSat Design Specification (CDS):** Cal Poly CubeSat Program, *CubeSat Design Specification Rev. 14.1*, California Polytechnic State University, 2022.
2. **NASA Small Spacecraft SOA:** NASA Ames Research Center, *State-of-the-Art of Small Spacecraft Technology* (Communications / Antennas), NASA, 2024.
3. **Outgassing Standard:** ASTM E595 / NASA SP-R-0022A, *Standard Test Method for Total Mass Loss and Collected Volatile Condensable Materials from Outgassing in a Vacuum Environment*.
4. Y. Rahmat-Samii, V. Manohar, and J. M. Kovitz, "For Satellites, Think Small, Think CubeSats: A review of current status and emerging antenna technologies for CubeSats," *IEEE Antennas and Propagation Magazine*, vol. 59, no. 2, pp. 22–30, 2017 (`doi: 10.1109/MAP.2017.2655582`).
5. S. Abulgasem et al., "Antenna Designs for CubeSats: A Review," *IEEE Access*, vol. 9, pp. 45289–45324, 2021 (`doi: 10.1109/ACCESS.2021.3066632`).
6. **MCDM / TOPSIS:** C.-L. Hwang and K. Yoon, *Multiple Attribute Decision Making: Methods and Applications*, Springer-Verlag, 1981. Initial script structure inspired by [Pegah-Ardehkhani/Multi-Criteria-Decision-Making](https://github.com/Pegah-Ardehkhani/Multi-Criteria-Decision-Making).
