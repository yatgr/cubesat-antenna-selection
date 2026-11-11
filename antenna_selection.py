import argparse
import re

import numpy as np
import pandas as pd

CRITERIA_CATALOG = {
    "Max Gain (dBi)": {
        "category": "RF Performance",
        "source_column": "Max Gain (dBi)",
        "type": 1,
    },
    "Bandwidth (%)": {
        "category": "RF Performance",
        "source_column": "Bandwidth (%)",
        "type": 1,
    },
    "Radiation Efficiency (%)": {
        "category": "RF Performance",
        "source_column": "Radiation Efficiency (%)",
        "type": 1,
    },
    "ARBW (%)": {
        "category": "RF Performance",
        "source_column": "ARBW (%)",
        "type": 1,
    },
    "Height_Profile_mm": {
        "category": "Mechanical & AIT",
        "source_column": "Dimensions (mm)",
        "type": -1,
    },
    "Footprint_Area_mm2": {
        "category": "Mechanical & AIT",
        "source_column": "Dimensions (mm)",
        "type": -1,
    },
    "Estimated_Weight_g": {
        "category": "Mechanical & AIT",
        "source_column": "Weight (g)",
        "type": -1,
    },
    "Substrate_AIT_Score": {
        "category": "Mechanical & AIT",
        "source_column": "Substrate Material",
        "type": 1,
    },
    "Qualification_Score": {
        "category": "Qualification & Reliability",
        "source_column": "Environmental Qualification Tests",
        "type": 1,
    },
}

MISSION_PROFILES = {
    "balanced": {
        "description": "RF (50%), Mechanical/AIT (30%), Qualification (20%)",
        "weights": {
            "Max Gain (dBi)": 0.18,
            "Bandwidth (%)": 0.12,
            "Radiation Efficiency (%)": 0.14,
            "ARBW (%)": 0.06,
            "Height_Profile_mm": 0.10,
            "Footprint_Area_mm2": 0.07,
            "Estimated_Weight_g": 0.07,
            "Substrate_AIT_Score": 0.06,
            "Qualification_Score": 0.20,
        },
    },
    "link_budget": {
        "description": "RF (75%), Mechanical/AIT (15%), Qualification (10%)",
        "weights": {
            "Max Gain (dBi)": 0.28,
            "Bandwidth (%)": 0.15,
            "Radiation Efficiency (%)": 0.22,
            "ARBW (%)": 0.10,
            "Height_Profile_mm": 0.05,
            "Footprint_Area_mm2": 0.03,
            "Estimated_Weight_g": 0.04,
            "Substrate_AIT_Score": 0.03,
            "Qualification_Score": 0.10,
        },
    },
    "compact_1u": {
        "description": "RF (35%), Mechanical/AIT (50%), Qualification (15%)",
        "weights": {
            "Max Gain (dBi)": 0.12,
            "Bandwidth (%)": 0.10,
            "Radiation Efficiency (%)": 0.10,
            "ARBW (%)": 0.03,
            "Height_Profile_mm": 0.18,
            "Footprint_Area_mm2": 0.16,
            "Estimated_Weight_g": 0.10,
            "Substrate_AIT_Score": 0.06,
            "Qualification_Score": 0.15,
        },
    },
    "low_risk": {
        "description": "RF (35%), Mechanical/AIT (25%), Qualification (40%)",
        "weights": {
            "Max Gain (dBi)": 0.12,
            "Bandwidth (%)": 0.10,
            "Radiation Efficiency (%)": 0.10,
            "ARBW (%)": 0.03,
            "Height_Profile_mm": 0.07,
            "Footprint_Area_mm2": 0.04,
            "Estimated_Weight_g": 0.04,
            "Substrate_AIT_Score": 0.15,
            "Qualification_Score": 0.35,
        },
    },
    "classic_5": {
        "description": "5-criteria baseline (Gain, Bandwidth, Efficiency, Height, Weight)",
        "weights": {
            "Max Gain (dBi)": 0.25,
            "Bandwidth (%)": 0.20,
            "Radiation Efficiency (%)": 0.25,
            "ARBW (%)": 0.00,
            "Height_Profile_mm": 0.15,
            "Footprint_Area_mm2": 0.00,
            "Estimated_Weight_g": 0.15,
            "Substrate_AIT_Score": 0.00,
            "Qualification_Score": 0.00,
        },
    },
}

MERGE_KEYS = ["No", "Title"]

MISSING_VALUE_MARKERS = [
    "not found",
    "not enough",
    "none",
    "n/a",
    "multiple",
    "unknown",
]


def is_missing_text(value):
    if pd.isna(value):
        return True
    text = str(value).strip().lower()
    if not text:
        return True
    return any(marker in text for marker in MISSING_VALUE_MARKERS)


def resolve_band_index(band_cell, target_band):
    if not target_band or pd.isna(band_cell):
        return None
    tokens = [t.strip().upper() for t in re.split(r"[,/;]+", str(band_cell)) if t.strip()]
    target = target_band.strip().upper()
    for idx, tok in enumerate(tokens):
        if tok == target:
            return idx
    return None


def extract_number(value, band_index=None):
    if is_missing_text(value):
        return np.nan
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", str(value))
    if not numbers:
        return np.nan
    if band_index is not None and 0 <= band_index < len(numbers):
        return float(numbers[band_index])
    return float(numbers[-1])


def extract_height(value):
    if is_missing_text(value):
        return np.nan
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", str(value))
    return float(numbers[2]) if len(numbers) >= 3 else np.nan


def extract_footprint_area(value):
    if is_missing_text(value):
        return np.nan
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", str(value))
    if len(numbers) >= 2:
        return float(numbers[0]) * float(numbers[1])
    return np.nan


def parse_cubesat_u(value):
    if pd.isna(value):
        return np.nan
    match = re.search(r"(\d+(?:\.\d+)?)\s*[uU]", str(value))
    return float(match.group(1)) if match else np.nan


def score_substrate_and_ait(row):
    sub_text = str(row.get("Substrate Material", "")).lower()
    fab_text = str(row.get("Fabrication Method", "")).lower()

    if any(k in sub_text for k in ["duroid", "5880", "rogers", "4003", "4350", "taconic", "kapton", "ceramic", "alumina", "quartz"]):
        score = 4.5
    elif "fr4" in sub_text or "fr-4" in sub_text:
        score = 2.5
    else:
        score = 3.0

    if any(k in fab_text for k in ["air gap", "spacer", "multilayer", "stacked"]):
        score -= 0.5
    elif any(k in fab_text for k in ["standard pcb", "photolithography", "single"]):
        score += 0.5

    return float(np.clip(score, 1.0, 5.0))


def score_qualification_and_risk(row):
    env_text = str(row.get("Environmental Qualification Tests", "")).lower()
    heritage_text = str(row.get("Flight Heritage Mission", "")).lower()
    deploy_text = str(row.get("Deployment Mechanism", "")).lower()

    has_vibe = any(k in env_text for k in ["vib", "sine", "random", "shock", "acoustic"])
    has_thermal = any(k in env_text for k in ["tvac", "thermal", "vacuum", "cycling"])

    if has_vibe and has_thermal:
        score = 4.0
    elif has_vibe or has_thermal:
        score = 2.5
    else:
        score = 1.0

    if not is_missing_text(heritage_text):
        score += 1.0

    if not is_missing_text(deploy_text):
        score -= 1.0

    return float(np.clip(score, 1.0, 5.0))


def apply_feasibility_filters(df, args):
    kept_mask = pd.Series(True, index=df.index)
    rejection_reasons = {idx: [] for idx in df.index}

    if args.band:
        target_band = args.band.strip().upper()
        for idx, val in df.get("Frequency Band", pd.Series(index=df.index)).items():
            tokens = [t.strip().upper() for t in re.split(r"[,/;]+", str(val)) if t.strip()]
            if target_band not in tokens:
                kept_mask[idx] = False
                rejection_reasons[idx].append(f"Band '{val}' != '{target_band}'")

    if args.polarization:
        target_pol = args.polarization.strip().upper()
        for idx, val in df.get("Polarization", pd.Series(index=df.index)).items():
            pol_str = str(val).strip().upper()
            if target_pol in ("CIRCULAR", "CP"):
                match = any(p in pol_str for p in ["RHCP", "LHCP", "CP", "CIRCULAR"])
            else:
                match = target_pol in pol_str
            if not match:
                kept_mask[idx] = False
                rejection_reasons[idx].append(f"Polarization '{val}' != '{args.polarization}'")

    if args.max_cubesat_size:
        max_u = parse_cubesat_u(args.max_cubesat_size)
        if not np.isnan(max_u):
            for idx, val in df.get("Target CubeSat Size", pd.Series(index=df.index)).items():
                ant_u = parse_cubesat_u(val)
                if not np.isnan(ant_u) and ant_u > max_u:
                    kept_mask[idx] = False
                    rejection_reasons[idx].append(f"Target size '{val}' exceeds '{args.max_cubesat_size}'")

    if args.max_height is not None:
        for idx, val in df.get("Dimensions (mm)", pd.Series(index=df.index)).items():
            h = extract_height(val)
            if not np.isnan(h) and h > args.max_height:
                kept_mask[idx] = False
                rejection_reasons[idx].append(f"Height {h} mm > {args.max_height} mm")

    if args.max_weight is not None:
        for idx, val in df.get("Weight (g)", pd.Series(index=df.index)).items():
            w = extract_number(val)
            if not np.isnan(w) and w > args.max_weight:
                kept_mask[idx] = False
                rejection_reasons[idx].append(f"Weight {w} g > {args.max_weight} g")

    if args.no_deployable:
        for idx, val in df.get("Deployment Mechanism", pd.Series(index=df.index)).items():
            if not is_missing_text(val):
                kept_mask[idx] = False
                rejection_reasons[idx].append(f"Requires deployment ('{val}')")

    rejected = []
    for idx in df.index[~kept_mask]:
        rejected.append({
            "No": df.loc[idx, "No"],
            "Title": df.loc[idx, "Title"],
            "Reasons": "; ".join(rejection_reasons[idx]),
        })

    return df[kept_mask].copy(), rejected


def run_topsis(decision_matrix, weights, criteria_types):
    if len(decision_matrix) == 1:
        return np.array([1.0])

    norm = np.sqrt(np.sum(decision_matrix ** 2, axis=0))
    norm[norm == 0] = 1e-10
    r = decision_matrix / norm

    v = r * weights

    ideal_best = np.where(criteria_types == 1, v.max(axis=0), v.min(axis=0))
    ideal_worst = np.where(criteria_types == 1, v.min(axis=0), v.max(axis=0))

    dist_best = np.sqrt(np.sum((v - ideal_best) ** 2, axis=1))
    dist_worst = np.sqrt(np.sum((v - ideal_worst) ** 2, axis=1))

    denom = dist_best + dist_worst
    denom[denom == 0] = 1e-10
    return dist_worst / denom


def run_wsm(decision_matrix, weights, criteria_types):
    if len(decision_matrix) == 1:
        return np.array([1.0])

    col_min = decision_matrix.min(axis=0)
    col_max = decision_matrix.max(axis=0)
    span = col_max - col_min

    u = np.zeros_like(decision_matrix, dtype=float)
    for j in range(decision_matrix.shape[1]):
        if span[j] == 0:
            u[:, j] = 1.0
        elif criteria_types[j] == 1:
            u[:, j] = (decision_matrix[:, j] - col_min[j]) / span[j]
        else:
            u[:, j] = (col_max[j] - decision_matrix[:, j]) / span[j]

    return u @ weights


def load_and_merge(rf_path, ait_path):
    df_rf = pd.read_csv(rf_path, sep=None, engine="python")
    df_ait = pd.read_csv(ait_path, sep=None, engine="python")

    missing_rf = [k for k in MERGE_KEYS if k not in df_rf.columns]
    missing_ait = [k for k in MERGE_KEYS if k not in df_ait.columns]
    if missing_rf or missing_ait:
        raise ValueError(
            f"Merge key(s) not found -- RF missing {missing_rf}, AIT missing {missing_ait}."
        )

    merged = pd.merge(df_rf, df_ait, on=MERGE_KEYS, how="inner")
    if len(merged) < max(len(df_rf), len(df_ait)):
        print(
            f"Warning: merge kept {len(merged)} rows out of {len(df_rf)} "
            f"(RF) / {len(df_ait)} (AIT)."
        )
    return merged


def build_decision_table(merged_df, active_criteria, target_band=None):
    decision = pd.DataFrame(index=merged_df.index)
    for key in MERGE_KEYS:
        decision[key] = merged_df[key]

    for meta_col in ["Antenna Info", "Frequency Band", "Polarization", "Target CubeSat Size", "Substrate Material"]:
        if meta_col in merged_df.columns:
            decision[meta_col] = merged_df[meta_col]

    n_missing = pd.Series(0, index=decision.index)
    print("Criterion extraction & missing-data summary:")

    for name in active_criteria:
        spec = CRITERIA_CATALOG[name]
        if name == "Height_Profile_mm":
            raw_values = merged_df[spec["source_column"]].apply(extract_height)
        elif name == "Footprint_Area_mm2":
            raw_values = merged_df[spec["source_column"]].apply(extract_footprint_area)
        elif name == "Substrate_AIT_Score":
            raw_values = merged_df.apply(score_substrate_and_ait, axis=1)
        elif name == "Qualification_Score":
            raw_values = merged_df.apply(score_qualification_and_risk, axis=1)
        elif name == "ARBW (%)":
            def extract_arbw(row):
                val = extract_number(
                    row.get("ARBW (%)"),
                    resolve_band_index(row.get("Frequency Band"), target_band),
                )
                if not np.isnan(val):
                    return val
                pol = str(row.get("Polarization", "")).upper()
                if "LINEAR" in pol:
                    return 0.0
                return np.nan

            raw_values = merged_df.apply(extract_arbw, axis=1)
        elif name in ("Max Gain (dBi)", "Bandwidth (%)"):
            raw_values = merged_df.apply(
                lambda r: extract_number(
                    r.get(spec["source_column"]),
                    resolve_band_index(r.get("Frequency Band"), target_band),
                ),
                axis=1,
            )
        else:
            raw_values = merged_df[spec["source_column"]].apply(extract_number)

        decision[f"{name} (raw)"] = raw_values

        is_missing = raw_values.isna()
        n_missing += is_missing.astype(int)

        median = raw_values.median()
        if np.isnan(median):
            median = 0.0
        decision[name] = raw_values.fillna(median)

        if is_missing.sum() > 0:
            print(
                f"  - {name:26s}: {is_missing.sum():2d}/{len(decision)} missing "
                f"({is_missing.mean():.0%}) -> median = {median:.3g}"
            )
        else:
            print(f"  - {name:26s}: complete")

    decision["N_Criteria_Imputed"] = n_missing
    return decision


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate and select CubeSat antennas using feasibility filters and mission trade-off profiles."
    )
    parser.add_argument("--rf", default="data/example_rf_data.csv", help="Path to RF CSV/TSV file.")
    parser.add_argument("--ait", default="data/example_ait_data.csv", help="Path to AIT CSV/TSV file.")
    parser.add_argument("--output", default="ranking_results.csv", help="Output CSV path.")
    parser.add_argument(
        "--profile",
        choices=list(MISSION_PROFILES.keys()),
        default="balanced",
        help="Mission priority profile.",
    )
    parser.add_argument(
        "--method",
        choices=["topsis", "wsm"],
        default="topsis",
        help="Scoring method ('topsis' or 'wsm').",
    )

    filter_group = parser.add_argument_group("Feasibility Filters")
    filter_group.add_argument("--band", default=None, help="Required frequency band (e.g., 'S', 'X').")
    filter_group.add_argument("--polarization", default=None, help="Required polarization (e.g., 'RHCP', 'Circular').")
    filter_group.add_argument("--max-cubesat-size", default=None, help="Max CubeSat form factor (e.g., '1U', '3U').")
    filter_group.add_argument("--max-height", type=float, default=None, help="Max profile height in mm.")
    filter_group.add_argument("--max-weight", type=float, default=None, help="Max mass in grams.")
    filter_group.add_argument("--no-deployable", action="store_true", help="Exclude deployable antennas.")

    args, _unknown_args = parser.parse_known_args()

    profile = MISSION_PROFILES[args.profile]
    weights_dict = profile["weights"]
    active_criteria = [k for k, w in weights_dict.items() if w > 0]

    weight_sum = sum(weights_dict[k] for k in active_criteria)
    assert abs(weight_sum - 1.0) < 1e-9, f"Active weights must sum to 1.0 (got {weight_sum})"

    merged = load_and_merge(args.rf, args.ait)
    print(f"Loaded {len(merged)} candidates from '{args.rf}' and '{args.ait}'.")

    feasible_df, rejected = apply_feasibility_filters(merged, args)
    if rejected:
        print(f"\n=== Stage 1: Feasibility Screening ({len(rejected)} excluded, {len(feasible_df)} passed) ===")
        for item in rejected:
            print(f"  [EXCLUDED] #{item['No']} {item['Title']} -> {item['Reasons']}")
    else:
        print(f"\n=== Stage 1: Feasibility Screening (All {len(feasible_df)} passed) ===")

    if feasible_df.empty:
        print("\nNo candidates satisfied all feasibility constraints.")
        return

    print(f"\n=== Stage 2: Trade-Off Evaluation (Profile: '{args.profile}' | Method: {args.method.upper()}) ===")
    decision = build_decision_table(feasible_df, active_criteria, target_band=args.band)

    matrix = decision[active_criteria].to_numpy(dtype=float)
    weights = np.array([weights_dict[k] for k in active_criteria])
    types = np.array([CRITERIA_CATALOG[k]["type"] for k in active_criteria])

    decision["TOPSIS_Score"] = run_topsis(matrix, weights, types)
    decision["WSM_Score"] = run_wsm(matrix, weights, types)

    primary_score_col = "TOPSIS_Score" if args.method == "topsis" else "WSM_Score"
    decision["Score"] = decision[primary_score_col]
    decision["Rank"] = decision["Score"].rank(ascending=False, method="min").astype(int)

    ranking = decision.sort_values(["Rank", "No"])
    display_cols = [
        "Rank",
        "Title",
        "Frequency Band",
        "Polarization",
        "Target CubeSat Size",
        "Score",
        "N_Criteria_Imputed",
    ]
    display_cols = [c for c in display_cols if c in ranking.columns]

    print("\n=== Final Candidate Ranking ===")
    print(ranking[display_cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    ranking.to_csv(args.output, index=False)
    print(f"\nResults written to '{args.output}'")


if __name__ == "__main__":
    main()
