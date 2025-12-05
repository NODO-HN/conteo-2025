"""
Análisis Electoral Honduras 2025 - Visualizaciones de Alto Impacto
Genera visualizaciones de alta calidad y legibilidad.
"""

import json
import re
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Polygon
import matplotlib.patheffects as path_effects
from matplotlib.patches import Patch
import sys

# --- CONFIGURACIÓN ---
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Segoe UI", "Arial", "Helvetica", "DejaVu Sans"]
plt.rcParams["text.color"] = "#333333"
plt.rcParams["axes.labelcolor"] = "#333333"
plt.rcParams["xtick.color"] = "#333333"
plt.rcParams["ytick.color"] = "#333333"

# Rutas actualizadas
DATA_DIR = Path("data/dec_5")
VIZ_DIR = DATA_DIR / "visualizaciones"
GEOJSON_PATH = Path("assets") / "geoBoundaries-HND-ADM1.geojson"
ROOT_DIR = Path(".")

# --- COLORES ---
COLOR_REPORTED = "#2C3E50"    # Azul oscuro (Sólido, confiable)
COLOR_ESTIMATED_FILL = "#ffffff" # Relleno blanco para rayado
COLOR_ESTIMATED_EDGE = "#F39C12" # Borde naranja para rayado
COLOR_ASFURA = "#1F618D"      # Azul profesional
COLOR_NASRALLA = "#C0392B"    # Rojo profundo
COLOR_MONCADA = "#922B21"     # Rojo más oscuro

# --- TEXTO GLOBAL ---
TIMESTAMP = "2025-12-05 6:00 pm"
ASSUMPTION_TEXT = "Supuesto: Votos estimados siguen patrones departamentales observados."

def load_logo():
    logo_path = Path("assets") / "logo_nodo.png"
    if logo_path.exists():
        return mpimg.imread(logo_path)
    return None

def add_branding(fig, logo=None, source_text=""):
    """Añade pie de página y logo de alta calidad."""
    # Barra de pie de página
    footer_ax = fig.add_axes([0, 0, 1, 0.05])
    footer_ax.set_facecolor("#F4F6F7")
    footer_ax.set_xticks([])
    footer_ax.set_yticks([])
    footer_ax.spines['top'].set_visible(True)
    footer_ax.spines['top'].set_color('#D5D8DC')
    for s in ['bottom', 'left', 'right']:
        footer_ax.spines[s].set_visible(False)

    # Texto de fuente
    fig.text(
        0.02, 0.025,
        source_text,
        ha="left", va="center",
        fontsize=12, color="#555555", fontfamily="Segoe UI"
    )

    # Logo
    if logo is not None:
        logo_ax = fig.add_axes([0.82, 0.005, 0.15, 0.04])
        logo_ax.imshow(logo)
        logo_ax.axis("off")
    else:
        # Texto alternativo
        fig.text(
            0.98, 0.025,
            "NODO | HONDURAS 2025",
            ha="right", va="center",
            fontsize=16, fontweight="bold", color="#2C3E50"
        )

def format_number(x):
    if x >= 1_000_000:
        return f"{x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{x/1_000:.0f}K"
    return f"{x:.0f}"

# --- CARGAR DATOS ---
# Añadir el directorio scripts al path para importar el módulo
sys.path.insert(0, str(Path(__file__).parent))
from analisis_y_procesamiento import load_dec5_results, summarize_departments, load_geojson, add_remaining_votes_to_geojson

def create_dazzle_map(dept_stats_df):
    print("Creando mapa de alto impacto (Español)...")
    geojson = load_geojson()
    add_remaining_votes_to_geojson(geojson, dept_stats_df)
    logo = load_logo()

    cmap = LinearSegmentedColormap.from_list(
        "professional_blue",
        ["#e8f1f8", "#b3d9f2", "#5fa8d3", "#2874a6", "#1a5276"],
    )

    fig = plt.figure(figsize=(24, 16))
    ax = plt.subplot(111)

    patches = []
    values = []

    for feature in geojson["features"]:
        coords = feature["geometry"]["coordinates"]
        val = feature["properties"].get("estimated_remaining_votes", 0)
        if feature["geometry"]["type"] == "MultiPolygon":
            for poly in coords:
                for ring in poly:
                    patches.append(Polygon(ring))
                    values.append(val)
        else:
            for ring in coords:
                patches.append(Polygon(ring))
                values.append(val)

    values = np.array(values)
    vmax = np.percentile(values, 95) if len(values) > 0 else 1

    p = PatchCollection(patches, cmap=cmap, alpha=1.0, edgecolors="white", linewidths=1.5)
    p.set_array(values)
    p.set_clim([0, vmax])
    ax.add_collection(p)

    ax.set_aspect('equal')
    ax.set_xlim(-89.5, -83)
    ax.set_ylim(12.8, 16.6)
    ax.axis("off")

    # Etiquetas
    for feature in geojson["features"]:
        remaining = feature["properties"].get("estimated_remaining_votes", 0)
        if remaining < 2000: continue

        coords = feature["geometry"]["coordinates"]
        all_points = []
        if feature["geometry"]["type"] == "MultiPolygon":
            for poly in coords:
                for ring in poly: all_points.extend(ring)
        else:
            for ring in coords: all_points.extend(ring)

        cx = np.mean([pt[0] for pt in all_points])
        cy = np.mean([pt[1] for pt in all_points])

        label = f"{remaining/1000:.0f}K"

        ax.text(cx, cy, label,
                ha="center", va="center",
                fontsize=14, fontweight="bold", color="#1a5276",
                bbox=dict(boxstyle="round,pad=0.3", fc="#e8f1f8", ec="#2874a6", lw=1.5, alpha=0.9))

    # Título (Centrado)
    fig.text(0.5, 0.90, "¿Dónde están los Votos Faltantes?",
             ha="center", fontsize=48, fontweight="bold", color="#1a5276")
    fig.text(0.5, 0.86, "Volumen estimado de actas no reportadas + inconsistentes por departamento",
             ha="center", fontsize=24, color="#5fa8d3")

    # Leyenda (Horizontal, abajo a la derecha en espacio blanco)
    cbar_ax = fig.add_axes([0.55, 0.12, 0.35, 0.02])  # [izq, abajo, ancho, alto]
    cbar = fig.colorbar(p, cax=cbar_ax, orientation="horizontal")
    cbar.ax.tick_params(labelsize=14)
    cbar.set_label("Votos No Contados Estimados", fontsize=16, fontweight="bold", labelpad=12)

    add_branding(fig, logo, f"Fuente: Datos TREP {TIMESTAMP} | {ASSUMPTION_TEXT}")

    out_path = VIZ_DIR / "mapa_votos_faltantes.png"
    plt.tight_layout(rect=[0, 0.06, 1, 0.85])
    plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Guardado: {out_path}")

def create_dazzle_dept_bars(dept_stats_df):
    print("Creando barras por departamento (Español)...")
    logo = load_logo()

    df = dept_stats_df.sort_values("estimated_remaining_votes", ascending=True)

    names = df["dept_name"].tolist()
    reported = df["reported_valid_votes"].values
    remaining = df["estimated_remaining_votes"].values

    fig, ax = plt.subplots(figsize=(24, 26))

    y = np.arange(len(names))
    bar_height = 0.75

    # 1. Reportado
    p1 = ax.barh(y, reported, height=bar_height, color=COLOR_REPORTED, label="Reportado")

    # 2. Estimado
    p2 = ax.barh(y, remaining, left=reported, height=bar_height,
                 color="white", edgecolor=COLOR_ESTIMATED_EDGE, hatch="///", linewidth=0)
    ax.barh(y, remaining, left=reported, height=bar_height,
            color="none", edgecolor=COLOR_ESTIMATED_EDGE, linewidth=2)

    # Formato de Ejes
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=24, fontweight="700", color="#2C3E50")

    ax.tick_params(axis='x', labelsize=20)
    ax.set_xlabel("Votos Totales", fontsize=24, fontweight="bold", labelpad=15)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0)
    ax.grid(axis='x', alpha=0.2, linestyle='--')

    # --- ETIQUETAS DE VALOR ---
    for i, (rep, rem) in enumerate(zip(reported, remaining)):
        total = rep + rem

        # Etiqueta Reportado (con contorno para visibilidad)
        rep_text = f"{rep/1000:.0f}K"
        if rep > (total * 0.15):
            text = ax.text(rep/2, i, rep_text, ha="center", va="center",
                    color="white", fontsize=22, fontweight="bold")
            text.set_path_effects([path_effects.withStroke(linewidth=3, foreground='#1a5276')])

        # Etiqueta Restante (con mejor contraste)
        rem_text = f"Est.\n{rem/1000:.0f}K"
        label_color = COLOR_REPORTED

        if rem > (total * 0.15):
            ax.text(rep + rem/2, i, rem_text, ha="center", va="center",
                    color=label_color, fontsize=22, fontweight="bold",
                    bbox=dict(facecolor="white", alpha=0.95, edgecolor="none", pad=4))
        else:
            ax.text(rep + rem + (total*0.01), i, rem_text.replace("\n", " "), ha="left", va="center",
                    color=label_color, fontsize=24, fontweight="bold")

    # Título (Centrado)
    fig.text(0.5, 0.94, "Estado del Voto Departamental: Reportado vs. Estimado",
             ha="center", fontsize=42, fontweight="bold", color="#2C3E50")
    fig.text(0.5, 0.91, "Azul Sólido: Reportado | Naranja Rayado: Estimado (No reportado + Inconsistente)",
             ha="center", fontsize=24, color="#7F8C8D")

    add_branding(fig, logo, f"Fuente: Datos TREP {TIMESTAMP} | {ASSUMPTION_TEXT}")

    out_path = VIZ_DIR / "barras_departamentales.png"
    plt.tight_layout(rect=[0, 0.05, 1, 0.90])
    plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Guardado: {out_path}")

def create_dazzle_projection(results_df, dept_stats_df):
    print("Creando proyección nacional (Español)...")
    logo = load_logo()

    # Preparación de Datos
    nat_reported = results_df.groupby("candidate")["votes"].sum()
    proj_rows = []
    for candidate, group in results_df.groupby("candidate"):
        proj_total = 0.0
        for dept, sub in group.groupby("department"):
            dept_row = dept_stats_df[dept_stats_df["dept_name"] == dept]
            if dept_row.empty: continue
            remaining_vol = dept_row.iloc[0]["estimated_remaining_votes"]
            dept_total_reported = results_df[results_df["department"]==dept]["votes"].sum()
            share = sub["votes"].sum() / dept_total_reported if dept_total_reported > 0 else 0
            proj_total += sub["votes"].sum() + (share * remaining_vol)
        proj_rows.append({"candidate": candidate, "projected": proj_total, "reported": nat_reported.get(candidate, 0)})

    # ORDENAR DESCENDENTE (Ganador Primero) - MATEMÁTICO
    df = pd.DataFrame(proj_rows).sort_values("projected", ascending=False).head(3)

    # INVERTIR para Graficado Barh (para que el índice 0/Ganador esté ARRIBA)
    df = df.iloc[::-1]

    def get_color(cand):
        if "ASFURA" in cand.upper(): return COLOR_ASFURA
        if "NASRALLA" in cand.upper(): return COLOR_NASRALLA
        if "MONCADA" in cand.upper(): return COLOR_MONCADA
        return "#7F8C8D"

    def get_name(cand):
        if "ASFURA" in cand.upper(): return "Nasry Asfura"
        if "NASRALLA" in cand.upper(): return "Salvador Nasralla"
        if "MONCADA" in cand.upper(): return "Rixi Moncada"
        return cand.title()

    df["color"] = df["candidate"].apply(get_color)
    df["short_name"] = df["candidate"].apply(get_name)

    # GRÁFICO
    fig, ax = plt.subplots(figsize=(22, 14))
    y = np.arange(len(df))
    height = 0.6

    for i, row in df.iterrows():
        # 1. Reportado
        p_rep = ax.barh(i, row["reported"], height=height, color=row["color"], alpha=1.0)

        # 2. Estimado
        est_val = row["projected"] - row["reported"]
        p_est = ax.barh(i, est_val, left=row["reported"], height=height,
                        color="white", hatch="///", edgecolor=row["color"])

        # --- ETIQUETAS ---
        ax.text(0, i + (height/2) + 0.05, row["short_name"].upper(),
                fontsize=26, fontweight="bold", color=row["color"], va="bottom")

        # Etiqueta de reportado con contorno para mejor visibilidad
        text_rep = ax.text(row["reported"] / 2, i, format_number(row["reported"]),
                ha="center", va="center", color="white", fontsize=26, fontweight="bold")
        text_rep.set_path_effects([path_effects.withStroke(linewidth=4, foreground='black', alpha=0.5)])

        center_est = row["reported"] + (est_val / 2)
        est_label = f"Est. {est_val/1000:.0f}K\n(±0.4%)"

        if est_val < 100000:
            ax.text(row["projected"] + 10000, i, est_label.replace("\n", " "),
                    ha="left", va="center", color=row["color"], fontsize=20, fontweight="bold")
        else:
            ax.text(center_est, i, est_label,
                    ha="center", va="center", color=row["color"], fontsize=18, fontweight="bold",
                    bbox=dict(facecolor="white", alpha=0.95, edgecolor="none", pad=5))

        total_share = (row["projected"] / df["projected"].sum()) * 100
        if est_val >= 100000:
            ax.text(row["projected"] + 25000, i, f"{total_share:.1f}%",
                    ha="left", va="center", color=row["color"], fontsize=26, fontweight="bold")

    ax.set_yticks([])
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.1)
    ax.tick_params(axis='x', labelsize=16)

    moe_pct = 0.40

    # Título (Centrado)
    fig.text(0.5, 0.94, "Proyección Nacional",
             ha="center", fontsize=48, fontweight="bold", color="#2C3E50")
    fig.text(0.5, 0.89, "Sólido: Votos Reportados | Rayado: Estimado Restante",
             ha="center", fontsize=22, color="#7F8C8D")

    add_branding(fig, logo, f"Fuente: Datos TREP {TIMESTAMP} | {ASSUMPTION_TEXT}")

    out_path = VIZ_DIR / "proyeccion_nacional.png"
    plt.tight_layout(rect=[0, 0.08, 1, 0.88])
    plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Guardado: {out_path}")

def main():
    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    print("Cargando datos...")
    results_df, dept_stats_df = load_dec5_results()
    dept_stats_df = summarize_departments(results_df, dept_stats_df)

    create_dazzle_map(dept_stats_df)
    create_dazzle_dept_bars(dept_stats_df)
    create_dazzle_projection(results_df, dept_stats_df)
    print("Hecho.")

if __name__ == "__main__":
    main()
