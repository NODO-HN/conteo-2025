"""
Análisis Electoral - Procesamiento de Datos
Honduras 2025

Procesa datos del TREP a nivel departamental para:
1. Calcular estadísticas y proyecciones por departamento
2. Crear mapa coroplético de votos estimados restantes
3. Crear gráfico de barras (reportado vs estimado)
4. Crear visual de proyección nacional
"""

import json
import re
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Polygon

# Configuración global de fuentes
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]


# Rutas actualizadas para la nueva estructura
DATA_DIR = Path("data/dec_5")
TABLES_DIR = DATA_DIR / "tables"
VIZ_DIR = DATA_DIR / "viz"
GEOJSON_PATH = Path("assets") / "geoBoundaries-HND-ADM1.geojson"
ROOT_DIR = Path(".")


def ensure_dirs():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    VIZ_DIR.mkdir(parents=True, exist_ok=True)


def load_dec5_results():
    """
    Carga todos los resultados JSON a nivel departamental desde data/dec_5.

    Returns:
        results_df: filas = (department, party, candidate, votes)
        dept_stats_df: filas = estadísticas de actas y votos por departamento
    """
    json_files = sorted(DATA_DIR.glob("HN.PRESIDENTE.*.json"))

    all_results = []
    dept_stats = []

    for json_file in json_files:
        stem = json_file.stem
        m = re.search(r"HN\.PRESIDENTE\.(\d{2})-(.+?)\.000-TODOS", stem)
        if not m:
            continue
        dept_code, dept_raw = m.group(1), m.group(2)

        # Skip national aggregate (00) for department-level analysis
        if dept_code == "00":
            continue

        dept_name = dept_raw.replace("-", " ").strip().upper()

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Candidate results (valid votes only)
        for r in data["resultados"]:
            votes = int(str(r["votos"]).replace(",", ""))
            all_results.append(
                {
                    "department": dept_name,
                    "party": r["partido"],
                    "candidate": r["candidato"],
                    "votes": votes,
                }
            )

        stats = data["estadisticas"]
        total_actas = int(str(stats["totalizacion_actas"]["actas_totales"]).replace(",", ""))
        actas_divulgadas = int(
            str(stats["totalizacion_actas"]["actas_divulgadas"]).replace(",", "")
        )

        valid_votes = int(str(stats["distribucion_votos"]["validos"]).replace(",", ""))
        null_votes = int(str(stats["distribucion_votos"]["nulos"]).replace(",", ""))
        blank_votes = int(str(stats["distribucion_votos"]["blancos"]).replace(",", ""))

        correct_actas = int(
            str(stats["estado_actas_divulgadas"]["actas_correctas"]).replace(",", "")
        )
        inconsistent_actas = int(
            str(stats["estado_actas_divulgadas"]["actas_inconsistentes"]).replace(
                ",", ""
            )
        )

        missing_actas = total_actas - actas_divulgadas

        # For estimation: only actas_correctas are considered "counted"
        counted_actas = correct_actas
        remaining_actas = missing_actas + inconsistent_actas

        # We use valid votes only for projections / winners
        if counted_actas > 0:
            votes_per_counted_acta = valid_votes / counted_actas
        else:
            votes_per_counted_acta = 0.0

        estimated_remaining_votes = remaining_actas * votes_per_counted_acta

        dept_stats.append(
            {
                "dept_name": dept_name,
                "dept_code": dept_code,
                "total_actas": total_actas,
                "actas_divulgadas": actas_divulgadas,
                "correct_actas": correct_actas,
                "inconsistent_actas": inconsistent_actas,
                "missing_actas": missing_actas,
                "remaining_actas": remaining_actas,
                "valid_votes": valid_votes,
                "null_votes": null_votes,
                "blank_votes": blank_votes,
                "votes_per_counted_acta": round(votes_per_counted_acta, 2),
                "estimated_remaining_votes": round(estimated_remaining_votes, 0),
            }
        )

    results_df = pd.DataFrame(all_results)
    dept_stats_df = pd.DataFrame(dept_stats)

    # If available, align acta counts with departamentos_actas_progress.csv
    progress_path = DATA_DIR / "departamentos_actas_progress.csv"
    if progress_path.exists() and not dept_stats_df.empty:
        progress = pd.read_csv(progress_path)
        # Standardize names
        progress["dept_name"] = progress["Departamento"].str.upper().str.strip()
        # Merge and prefer progress counts when present
        dept_stats_df = dept_stats_df.merge(
            progress[["dept_name", "Actas totalizadas", "Actas pendientes"]],
            on="dept_name",
            how="left",
        )

        # Use progress totals when provided
        dept_stats_df["correct_actas"] = (
            dept_stats_df["Actas totalizadas"]
            .fillna(dept_stats_df["correct_actas"])
            .astype(int)
        )
        dept_stats_df["missing_actas"] = (
            dept_stats_df["Actas pendientes"]
            .fillna(dept_stats_df["missing_actas"])
            .astype(int)
        )

        # Recompute remaining and vote estimates with updated counts
        dept_stats_df["remaining_actas"] = (
            dept_stats_df["missing_actas"] + dept_stats_df["inconsistent_actas"]
        )
        dept_stats_df["votes_per_counted_acta"] = (
            dept_stats_df["valid_votes"] / dept_stats_df["correct_actas"]
        ).round(2)
        dept_stats_df["estimated_remaining_votes"] = (
            dept_stats_df["remaining_actas"] * dept_stats_df["votes_per_counted_acta"]
        ).round(0)

        dept_stats_df = dept_stats_df.drop(
            columns=["Actas totalizadas", "Actas pendientes"]
        )

    # Basic sanity checks
    if results_df.empty or dept_stats_df.empty:
        raise RuntimeError("No Dec 5 results or stats loaded from data/dec_5.")

    return results_df, dept_stats_df


def summarize_departments(results_df: pd.DataFrame, dept_stats_df: pd.DataFrame):
    """
    Deriva ganadores y proyecciones a nivel departamental.

    Adds:
        reported_total_valid_votes
        estimated_remaining_votes
        projected_total_valid_votes
        current_winner
        projected_winner
    """
    # Sum candidate votes per department (valid votes)
    dept_totals = (
        results_df.groupby("department")["votes"].sum().rename("reported_valid_votes")
    )

    dept_stats_df = dept_stats_df.merge(
        dept_totals, left_on="dept_name", right_index=True, how="left"
    )

    # For safety, fall back to valid_votes from stats if merge is missing
    dept_stats_df["reported_valid_votes"] = dept_stats_df["reported_valid_votes"].fillna(
        dept_stats_df["valid_votes"]
    )

    # Estimated remaining valid votes already computed
    dept_stats_df["projected_total_valid_votes"] = (
        dept_stats_df["reported_valid_votes"] + dept_stats_df["estimated_remaining_votes"]
    )

    # Current winners (by reported valid votes)
    idx_current = (
        results_df.groupby(["department"])["votes"].idxmax()
    )
    current_winners = results_df.loc[idx_current][
        ["department", "candidate", "party", "votes"]
    ].rename(
        columns={
            "candidate": "current_winner",
            "party": "current_winner_party",
            "votes": "current_winner_votes",
        }
    )

    dept_stats_df = dept_stats_df.merge(
        current_winners, left_on="dept_name", right_on="department", how="left"
    ).drop(columns=["department"])

    # Projected winners: allocate remaining votes proportionally to current shares
    projected_rows = []
    for dept, group in results_df.groupby("department"):
        row = dept_stats_df.loc[dept_stats_df["dept_name"] == dept].iloc[0]
        remaining = row["estimated_remaining_votes"]
        if remaining <= 0 or group["votes"].sum() <= 0:
            # No remaining votes or no votes at all — projected winner is current winner
            projected_rows.append(
                {
                    "dept_name": dept,
                    "projected_winner": row["current_winner"],
                    "projected_winner_party": row["current_winner_party"],
                    "projected_winner_votes": row["current_winner_votes"],
                }
            )
            continue

        total_valid = group["votes"].sum()
        # Proportional allocation
        projected_votes = []
        for _, r in group.iterrows():
            share = r["votes"] / total_valid
            est_extra = share * remaining
            projected_votes.append(
                {
                    "candidate": r["candidate"],
                    "party": r["party"],
                    "projected_votes": r["votes"] + est_extra,
                }
            )

        proj_df = pd.DataFrame(projected_votes)
        winner_row = proj_df.sort_values("projected_votes", ascending=False).iloc[0]
        projected_rows.append(
            {
                "dept_name": dept,
                "projected_winner": winner_row["candidate"],
                "projected_winner_party": winner_row["party"],
                "projected_winner_votes": round(winner_row["projected_votes"], 0),
            }
        )

    projected_df = pd.DataFrame(projected_rows)
    dept_stats_df = dept_stats_df.merge(
        projected_df, on="dept_name", how="left"
    )

    # Percentages for reporting
    dept_stats_df["pct_reported_actas"] = (
        dept_stats_df["correct_actas"] / dept_stats_df["total_actas"] * 100
    ).round(2)
    dept_stats_df["pct_remaining_actas"] = (
        dept_stats_df["remaining_actas"] / dept_stats_df["total_actas"] * 100
    ).round(2)

    return dept_stats_df


def candidate_short_label(name: str) -> str:
    """
    Usa el apellido como etiqueta cuando sea posible.
    """
    if not isinstance(name, str) or not name:
        return ""
    parts = name.strip().split()
    return parts[-1].upper()


def candidate_display_name(name: str) -> str:
    """
    Nombre para mostrar en gráficos de proyección.
    """
    if not isinstance(name, str) or not name:
        return ""
    upper = name.upper()
    if "ASFURA" in upper:
        return "Asfura"
    if "NASRALLA" in upper:
        return "Nasralla"
    if "MONCADA" in upper:
        return "Moncada"
    # Fallback: last name, title-cased
    return candidate_short_label(name).title()


def candidate_color(name: str) -> str:
    """
    Mapa de colores:
      - Asfura: azul
      - Nasralla: rojo
      - Moncada: crimson
      - Others: gris
    """
    if not isinstance(name, str):
        return "#555555"

    upper = name.upper()
    if "ASFURA" in upper:
        return "#2874a6"  # professional blue
    if "NASRALLA" in upper:
        return "#d73027"  # red
    if "MONCADA" in upper:
        return "#990000"  # crimson
    return "#555555"


def save_department_table(dept_stats_df: pd.DataFrame):
    out_path = TABLES_DIR / "estadisticas_departamentales.csv"
    dept_stats_df.to_csv(out_path, index=False)
    print(f"Tabla guardada: {out_path}")


def load_geojson():
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(f"GeoJSON no encontrado en {GEOJSON_PATH}")
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def add_remaining_votes_to_geojson(geojson, dept_stats_df: pd.DataFrame):
    # Map GeoJSON shapeName to department names used in stats
    name_mapping = {
        "Atlántida": "ATLANTIDA",
        "Colón": "COLON",
        "Comayagua": "COMAYAGUA",
        "Copán": "COPAN",
        "Cortés": "CORTES",
        "Choluteca": "CHOLUTECA",
        "El Paraíso": "EL PARAISO",
        "Francisco Morazán": "FRANCISCO MORAZAN",
        "Gracias a Dios": "GRACIAS A DIOS",
        "Intibucá": "INTIBUCA",
        "Bay Islands": "ISLAS DE LA BAHIA",
        "La Paz": "LA PAZ",
        "Lempira": "LEMPIRA",
        "Ocotepeque": "OCOTEPEQUE",
        "Olancho": "OLANCHO",
        "Santa Bárbara": "SANTA BARBARA",
        "Valle": "VALLE",
        "Yoro": "YORO",
    }

    for feature in geojson["features"]:
        geo_name = feature["properties"]["shapeName"]
        dept_name = name_mapping.get(geo_name)
        if not dept_name:
            continue

        row = dept_stats_df.loc[dept_stats_df["dept_name"] == dept_name]
        if row.empty:
            continue

        row = row.iloc[0]
        feature["properties"]["estimated_remaining_votes"] = float(
            row["estimated_remaining_votes"]
        )
        feature["properties"]["remaining_actas"] = int(row["remaining_actas"])
        feature["properties"]["correct_actas"] = int(row["correct_actas"])


def load_logo():
    logo_path = Path("assets") / "logo_nodo.png"
    if logo_path.exists():
        logo = mpimg.imread(logo_path)
        print(f"Logo cargado: {logo.shape[1]}x{logo.shape[0]} pixels")
        return logo
    print("Advertencia: logo_nodo.png no encontrado en assets/; visuales omitirán logo.")
    return None


def professional_blue_cmap():
    return LinearSegmentedColormap.from_list(
        "professional_blue",
        ["#e8f1f8", "#b3d9f2", "#5fa8d3", "#2874a6", "#1a5276"],
    )


def create_remaining_votes_map(dept_stats_df: pd.DataFrame):
    print("Creando mapa coroplético: Origen de votos restantes...")

    geojson = load_geojson()
    add_remaining_votes_to_geojson(geojson, dept_stats_df)
    logo = load_logo()

    custom_blue = professional_blue_cmap()

    # High-resolution figure
    fig = plt.figure(figsize=(20, 16))
    ax = plt.subplot(111)

    patches = []
    values = []

    for feature in geojson["features"]:
        coords = feature["geometry"]["coordinates"]
        remaining_votes = feature["properties"].get("estimated_remaining_votes", 0.0)

        if feature["geometry"]["type"] == "MultiPolygon":
            for poly in coords:
                for ring in poly:
                    polygon = Polygon(ring)
                    patches.append(polygon)
                    values.append(remaining_votes)
        else:
            for ring in coords:
                polygon = Polygon(ring)
                patches.append(polygon)
                values.append(remaining_votes)

    values_array = np.array(values)
    vmax = max(values_array) if len(values_array) > 0 else 1.0

    p = PatchCollection(
        patches, cmap=custom_blue, alpha=0.9, edgecolors="white", linewidths=2
    )
    p.set_array(values_array)
    p.set_clim([0, vmax])
    ax.add_collection(p)

    # Colorbar
    cbar = fig.colorbar(
        p, ax=ax, orientation="horizontal", pad=0.10, aspect=40, shrink=0.7
    )
    cbar.set_label(
        "Votos válidos estimados en actas no reportadas + marcadas como inconsistentes.",
        fontsize=18,
        fontweight="600",
        labelpad=18,
    )
    cbar.ax.tick_params(labelsize=11)
    cbar.outline.set_edgecolor("#2874a6")
    cbar.outline.set_linewidth(1.5)

    # Department labels (K notation)
    for feature in geojson["features"]:
        coords = feature["geometry"]["coordinates"]
        remaining_votes = feature["properties"].get("estimated_remaining_votes", 0.0)

        if remaining_votes <= 0:
            continue

        if feature["geometry"]["type"] == "MultiPolygon":
            all_coords = []
            for poly in coords:
                for ring in poly:
                    all_coords.extend(ring)
        else:
            all_coords = []
            for ring in coords:
                all_coords.extend(ring)

        if not all_coords:
            continue

        centroid_x = np.mean([c[0] for c in all_coords])
        centroid_y = np.mean([c[1] for c in all_coords])

        if remaining_votes >= 1000:
            label_text = f"{remaining_votes/1000:.0f}K"
        else:
            label_text = f"{remaining_votes:.0f}"

        is_high = remaining_votes > (vmax * 0.5)
        label_color = "#1a5276"
        bg_color = "#e8f1f8"

        ax.text(
            centroid_x,
            centroid_y,
            label_text,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color=label_color,
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor=bg_color,
                alpha=0.9,
                edgecolor="#2874a6",
                linewidth=1.2,
            ),
        )

    ax.set_xlim(-89.5, -83)
    ax.set_ylim(13, 16.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # Bottom: note on left, logo on right
    bottom_y = 0.04
    fig.text(
        0.05,
        bottom_y,
        "Reporte generado 2025-12-05, 1:00 pm.",
        ha="left",
        va="bottom",
        fontsize=11,
        color="#5a6c7d",
    )

    if logo is not None:
        target_height_inches = 0.8
        aspect_ratio = logo.shape[1] / logo.shape[0]
        target_width_inches = target_height_inches * aspect_ratio
        logo_ax = fig.add_axes(
            [0.85, bottom_y - 0.01, target_width_inches / 20, target_height_inches / 14]
        )
        logo_ax.imshow(logo, alpha=0.8)
        logo_ax.axis("off")

    # Hide any generic footer text containing 'Nodo | Honduras 2025'
    for text_obj in fig.texts:
        if "Nodo | Honduras 2025" in text_obj.get_text():
            text_obj.set_visible(False)

    out_path = VIZ_DIR / "mapa_votos_restantes.png"
    plt.tight_layout(rect=[0, 0.08, 1, 0.98])
    plt.savefig(out_path, dpi=400, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Mapa guardado: {out_path}")


def create_dept_bars_with_winner_table(dept_stats_df: pd.DataFrame):
    print("Creando gráfico de barras departamentales apiladas...")

    logo = load_logo()

    # Sort departments by estimated remaining votes (ascending for bottom-up)
    df = dept_stats_df.copy()
    df = df.sort_values("estimated_remaining_votes", ascending=True)

    dept_names = df["dept_name"].tolist()
    reported = df["reported_valid_votes"].values
    remaining = df["estimated_remaining_votes"].values

    y_pos = np.arange(len(dept_names))

    fig, ax_bar = plt.subplots(figsize=(20, 14))

    # Stacked horizontal bars: reported (neutral blue) + remaining (alert orange),
    # with slight transparency for a think-tank style look
    total_votes = reported + remaining

    reported_color = "#4c78a8"  # muted blue
    remaining_color = "#f58518"  # muted orange

    ax_bar.barh(
        y_pos,
        reported,
        color=reported_color,
        alpha=0.85,
        edgecolor="#2874a6",
        linewidth=0.8,
        label="Votos reportados (válidos)",
    )
    ax_bar.barh(
        y_pos,
        remaining,
        left=reported,
        color=remaining_color,
        alpha=0.85,
        edgecolor="#1a5276",
        linewidth=0.8,
        label="Votos estimados restantes (no reportados + inconsistentes)",
    )

    ax_bar.set_yticks(y_pos)
    ax_bar.set_yticklabels(dept_names, fontsize=10)

    # No explicit x-axis label; bars + legend are enough
    ax_bar.set_title(
        "Votos Reportados vs Estimados Restantes por Departamento\nHonduras 2025",
        fontsize=18,
        fontweight="700",
        pad=20,
        color="#1a5276",
    )

    ax_bar.grid(axis="x", alpha=0.15, linestyle="--")
    ax_bar.set_axisbelow(True)
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)
    ax_bar.spines["left"].set_color("#2874a6")
    ax_bar.spines["bottom"].set_color("#2874a6")

    # Value labels per bar: "reportedK / remainingK" as a single label, outside the bar
    for i, (r, rem) in enumerate(zip(reported, remaining)):
        if r <= 0 and rem <= 0:
            continue

        if r >= 1000:
            r_label = f"{r/1000:.0f}K"
        else:
            r_label = f"{r:.0f}"

        if rem >= 1000:
            rem_label = f"{rem/1000:.0f}K"
        else:
            rem_label = f"{rem:.0f}"

        total = r + rem
        base_x = r + rem + max(total * 0.01, 100)  # small offset to the right

        label = f"{r_label} / {rem_label}"
        ax_bar.text(
            base_x,
            i,
            label,
            va="center",
            fontsize=11,
            fontweight="600",
            color="#1a5276",
        )

    # Remove x-axis tick labels (bar lengths + labels are enough)
    ax_bar.tick_params(axis="x", labelbottom=False)

    ax_bar.legend(loc="lower right", fontsize=10, frameon=False)

    # Bottom attribution & logo
    fig.text(
        0.02,
        0.02,
        "Estimación basada en actas no reportadas y actas marcadas como inconsistentes.\n"
        "Reporte generado 2025-12-05, 1:00 pm.",
        ha="left",
        va="bottom",
        fontsize=10,
        color="#5a6c7d",
    )

    if logo is not None:
        target_height_inches = 0.8
        aspect_ratio = logo.shape[1] / logo.shape[0]
        target_width_inches = target_height_inches * aspect_ratio
        logo_ax = fig.add_axes(
            [0.9, 0.01, target_width_inches / 24, target_height_inches / 18]
        )
        logo_ax.imshow(logo, alpha=0.8)
        logo_ax.axis("off")

    fig.text(
        0.5,
        0.01,
        "Análisis: Nodo | Honduras 2025",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#5a6c7d",
        fontweight="600",
    )

    # Hide any generic footer text containing 'Nodo | Honduras 2025'
    for text_obj in fig.texts:
        if "Nodo | Honduras 2025" in text_obj.get_text():
            text_obj.set_visible(False)

    out_path = VIZ_DIR / "barras_reportado_vs_restante.png"
    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    plt.savefig(out_path, dpi=400, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Gráfico de barras guardado: {out_path}")


def create_national_projection_visual(results_df: pd.DataFrame, dept_stats_df: pd.DataFrame):
    print("Creando visual de proyección nacional...")

    # Aggregate national reported votes per candidate
    nat = (
        results_df.groupby(["candidate", "party"])["votes"].sum().reset_index()
    )
    nat = nat.sort_values("votes", ascending=False)

    # Estimated remaining votes nationally (valid)
    total_est_remaining = dept_stats_df["estimated_remaining_votes"].sum()

    # Projected votes assuming remaining votes follow current shares per department
    # (already used in dept projections)
    proj_rows = []
    for (candidate, party), group in results_df.groupby(["candidate", "party"]):
        # Sum projected across departments
        proj_total = 0.0
        for dept, sub in group.groupby("department"):
            row = dept_stats_df.loc[dept_stats_df["dept_name"] == dept]
            if row.empty:
                continue
            remaining = row.iloc[0]["estimated_remaining_votes"]
            dept_total = results_df.loc[
                results_df["department"] == dept, "votes"
            ].sum()
            if dept_total <= 0:
                proj_total += sub["votes"].sum()
                continue
            share = sub["votes"].sum() / dept_total
            proj_total += sub["votes"].sum() + share * remaining

        proj_rows.append(
            {
                "candidate": candidate,
                "party": party,
                "projected_votes": proj_total,
            }
        )

    proj_df = pd.DataFrame(proj_rows)
    proj_df = proj_df.sort_values("projected_votes", ascending=False)

    # Focus on top 3 candidates
    top_proj = proj_df.head(3).copy()
    top_proj["short_label"] = top_proj["candidate"].apply(candidate_display_name)
    top_proj["color"] = top_proj["candidate"].apply(candidate_color)

    # Current totals for comparison
    nat = nat.set_index("candidate")
    top_proj["reported_votes"] = top_proj["candidate"].map(nat["votes"]).fillna(0)

    # Margin vs remaining votes for top 2
    if len(top_proj) >= 2:
        leader = top_proj.iloc[0]
        runner_up = top_proj.iloc[1]
        margin_votes = leader["projected_votes"] - runner_up["projected_votes"]
    else:
        margin_votes = 0.0

    # Visual
    logo = load_logo()

    fig, ax = plt.subplots(figsize=(18, 12))

    y_pos = np.arange(len(top_proj))
    proj_votes = top_proj["projected_votes"].values
    colors = top_proj["color"].values

    bars = ax.barh(y_pos, proj_votes, color=colors, alpha=0.9)

    # Overlay current reported votes as lighter segment
    reported_votes = top_proj["reported_votes"].values
    ax.barh(y_pos, reported_votes, color="#f0f0f0", alpha=0.9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(top_proj["short_label"].values, fontsize=12)

    ax.set_xlabel("Votos (válidos)", fontsize=13, fontweight="700")
    ax.set_title(
        "Resultados Nacionales Proyectados (Votos Válidos)\nHonduras 2025",
        fontsize=20,
        fontweight="700",
        pad=20,
        color="#1a5276",
    )

    ax.grid(axis="x", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#2874a6")
    ax.spines["bottom"].set_color("#2874a6")

    # Invert y so winner is at top
    ax.invert_yaxis()

    # Remove x-axis tick labels (keep grid)
    ax.tick_params(axis="x", labelbottom=False)

    # Labels showing projected % plus remaining
    total_proj_votes = proj_votes.sum() if proj_votes.sum() > 0 else 1.0
    est_volume_pct = (total_est_remaining / total_proj_votes * 100) if total_proj_votes > 0 else 0.0

    for i, (p, r) in enumerate(zip(proj_votes, reported_votes)):
        pct = p / total_proj_votes * 100
        label = f"{p:,.0f} ({pct:.1f}%)"
        ax.text(
            p + total_proj_votes * 0.005,
            i,
            label,
            va="center",
            fontsize=10,
            fontweight="600",
            color="#1a5276",
        )

        # Annotation within estimated segment
        if p > r and est_volume_pct > 0:
            seg_center = r + (p - r) / 2
            ax.text(
                seg_center,
                i,
                "Est.",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="600",
                color="white",
            )

    # Summary text
    fig.text(
        0.5,
        0.93,
        f"Volumen estimado restante: {total_est_remaining:,.0f} ({est_volume_pct:.1f}%) | "
        f"Margen proyectado: {margin_votes:,.0f} votos",
        ha="center",
        va="top",
        fontsize=12,
        style="italic",
        color="#5a6c7d",
    )

    fig.text(
        0.02,
        0.02,
        "Proyección asume que actas restantes siguen patrones de votación departamentales actuales.\n"
        f"Área rayada indica volumen de votos estimados restantes ({est_volume_pct:.1f}% del total).",
        ha="left",
        va="bottom",
        fontsize=10,
        color="#5a6c7d",
    )

    if logo is not None:
        target_height_inches = 0.8
        aspect_ratio = logo.shape[1] / logo.shape[0]
        target_width_inches = target_height_inches * aspect_ratio
        logo_ax = fig.add_axes(
            [0.9, 0.01, target_width_inches / 24, target_height_inches / 18]
        )
        logo_ax.imshow(logo, alpha=0.8)
        logo_ax.axis("off")

    fig.text(
        0.5,
        0.01,
        "Análisis: Nodo | Honduras 2025",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#5a6c7d",
        fontweight="600",
    )

    # Hide any generic footer text containing 'Nodo | Honduras 2025'
    for text_obj in fig.texts:
        if "Nodo | Honduras 2025" in text_obj.get_text():
            text_obj.set_visible(False)

    out_path = VIZ_DIR / "proyeccion_nacional.png"
    plt.tight_layout(rect=[0, 0.05, 1, 0.9])
    plt.savefig(out_path, dpi=400, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Visual de proyección nacional guardado: {out_path}")


def main():
    ensure_dirs()

    print("=" * 80)
    print("ANÁLISIS ELECTORAL DIC 5 (SOLO TREP, NIVEL DEPARTAMENTAL)")
    print("=" * 80)
    print()

    results_df, dept_stats_df = load_dec5_results()
    dept_stats_df = summarize_departments(results_df, dept_stats_df)
    save_department_table(dept_stats_df)

    # Visuals
    create_remaining_votes_map(dept_stats_df)
    create_dept_bars_with_winner_table(dept_stats_df)
    create_national_projection_visual(results_df, dept_stats_df)

    print()
    print("=" * 80)
    print("ANÁLISIS DIC 5 COMPLETO")
    print("=" * 80)


if __name__ == "__main__":
    main()
