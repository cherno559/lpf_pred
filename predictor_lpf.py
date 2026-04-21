"""
dashboard_lpf.py
────────────────
App Streamlit: Predictor de partidos + tablas comparativas de la Liga Profesional Argentina.
Lee directamente del Excel generado por sofascore_lpf_generales.py

Instalación:
    pip install streamlit plotly pandas openpyxl numpy tls-client

Correr:
    streamlit run dashboard_lpf.py
"""

import re
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ─────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LPF 2026 · Scouting Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@400;600;700&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
/* Base */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0a0e1a; color: #e2e8f0; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f1629 !important;
    border-right: 1px solid #1e2d4a;
}
section[data-testid="stSidebar"] * { color: #cbd5e0 !important; }

/* Títulos */
h1, h2, h3 { font-family: 'Bebas Neue', cursive !important; letter-spacing: 2px; }
h1 { font-size: 2.8rem !important; color: #e53e3e !important; }
h2 { font-size: 1.8rem !important; color: #f0f4f8 !important; }
h3 { font-size: 1.3rem !important; color: #a0aec0 !important; }

/* KPI Card */
.kpi-card {
    background: linear-gradient(135deg, #111827 0%, #1a2035 100%);
    border: 1px solid #1e2d4a;
    border-left: 4px solid #e53e3e;
    border-radius: 12px;
    padding: 18px 22px;
    text-align: center;
    margin-bottom: 8px;
    transition: transform .2s;
}
.kpi-card:hover { transform: translateY(-2px); }
.kpi-card.empate  { border-left-color: #718096; }
.kpi-card.derrota { border-left-color: #3182ce; }
.kpi-card.neutral { border-left-color: #38a169; }
.kpi-card .kpi-label {
    font-family: 'Rajdhani', sans-serif;
    font-size: 10px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #718096; margin-bottom: 4px;
}
.kpi-card .kpi-val {
    font-family: 'Bebas Neue', cursive;
    font-size: 40px; color: #e53e3e; line-height: 1;
}
.kpi-card.empate .kpi-val  { color: #a0aec0; }
.kpi-card.derrota .kpi-val { color: #63b3ed; }
.kpi-card.neutral .kpi-val { color: #68d391; }

/* Section header */
.section-head {
    font-family: 'Bebas Neue', cursive;
    font-size: 1.4rem; letter-spacing: 3px;
    color: #e53e3e; border-bottom: 2px solid #1e2d4a;
    padding-bottom: 6px; margin: 24px 0 16px;
    text-transform: uppercase;
}

/* Badge */
.badge {
    display: inline-block; padding: 3px 14px;
    border-radius: 20px; font-family: 'Rajdhani'; font-size: 12px; font-weight: 700;
    background: #1a3a1a; color: #68d391; margin-bottom: 12px;
}

/* Tablas Streamlit */
.stDataFrame { border-radius: 10px !important; }
div[data-testid="stDataFrame"] > div { border-radius: 10px !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #111827; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Rajdhani'; font-weight: 700; font-size: 14px;
    color: #718096 !important; border-radius: 8px;
}
.stTabs [aria-selected="true"] { background: #e53e3e !important; color: white !important; }

/* Buttons */
.stButton > button {
    font-family: 'Bebas Neue'; font-size: 18px; letter-spacing: 2px;
    background: linear-gradient(135deg, #e53e3e, #c53030);
    color: white; border: none; border-radius: 10px;
    padding: 12px 0; width: 100%;
    transition: all .2s;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(229,62,62,.4); }

/* Selectbox, multiselect */
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: #111827 !important; border: 1px solid #2d3748 !important;
    color: #e2e8f0 !important; border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────
MONTECARLO_N = 15_000
RED, BLUE, GRAY = "#e53e3e", "#3182ce", "#718096"

PLOT_BASE = dict(
    font=dict(family="Rajdhani", size=13, color="#e2e8f0"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=30, b=10),
)

# Métricas numéricas que se pueden comparar directamente
METRICAS_NUMERICAS = [
    "Posesión de balón", "Goles esperados (xG)", "Tiros totales", "Tiros al arco",
    "Tiros afuera", "Tiros bloqueados", "Córners", "Fueras de juego", "Faltas",
    "Tarjetas amarillas", "Tarjetas rojas", "Pases totales", "Pases precisos",
    "Balones largos precisos", "Centros precisos", "Atajadas del arquero",
    "Quites", "Intercepciones", "Despejes", "Resultado",
]

EQUIPOS_LPF = [
    "Ind. Rivadavia", "River Plate", "Vélez", "Estudiantes", "Argentinos Jrs.",
    "Lanús", "Belgrano", "Boca Juniors", "Rosario Central", "Talleres",
    "Huracán", "Unión", "Defensa y Justicia", "Barracas Central", "Tigre",
    "Independiente", "Racing Club", "San Lorenzo", "Instituto", "Gimnasia LP",
    "Platense", "Sarmiento", "Banfield", "Gimnasia (M)", "Central Córdoba",
    "Atl. Tucumán", "Newell's", "Riestra", "Aldosivi", "Estudiantes RC",
]

# ─────────────────────────────────────────────────────────────────
# CARGA Y PARSEO DEL EXCEL
# ─────────────────────────────────────────────────────────────────

def extraer_numero(valor) -> float:
    if isinstance(valor, str):
        valor = valor.replace('%', '').replace(',', '.').strip()
    try:
        return float(valor)
    except (ValueError, TypeError):
        return 0.0


@st.cache_data(ttl=300, show_spinner=False)
def cargar_excel(ruta: str) -> dict[str, list[dict]]:
    """
    Lee el Excel hoja por hoja.
    Cada hoja = una fecha. Cada tabla de partido tiene estructura:
        Fila título  → "Equipo A  vs  Equipo B"
        Fila cabecera → ["Métrica", local, visitante]
        Fila resultado → ["Resultado", gl, gv]
        Filas métricas → [métrica, val_local, val_visitante]
    Retorna dict { "Fecha 5": [partido_dict, ...], ... }
    """
    try:
        xl = pd.ExcelFile(ruta, engine="openpyxl")
    except Exception as e:
        st.error(f"No se pudo abrir el Excel: {e}")
        return {}

    datos = {}
    for hoja in xl.sheet_names:
        if not hoja.strip().lower().startswith("fecha"):
            continue
        df = pd.read_excel(ruta, sheet_name=hoja, header=None, engine="openpyxl")
        partidos = _parsear_hoja(df, hoja)
        if partidos:
            datos[hoja] = partidos
    return datos


def _parsear_hoja(df: pd.DataFrame, nombre_hoja: str) -> list[dict]:
    """Parsea una hoja y devuelve lista de dicts con stats de cada partido."""
    partidos = []
    i = 0
    max_row = len(df)

    while i < max_row:
        cell_val = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""

        # Detectar fila de título: "Equipo A  vs  Equipo B"
        if " vs " in cell_val.lower() and i + 2 < max_row:
            # Extraer nombres
            partes = re.split(r"\s+vs\s+", cell_val, flags=re.IGNORECASE)
            if len(partes) == 2:
                local   = partes[0].strip().lstrip()
                visitante = partes[1].strip()

                # Cabecera en i+1, datos desde i+2
                stats = {"local": local, "visitante": visitante, "metricas": {}}
                j = i + 2  # saltamos el título y la cabecera
                while j < max_row:
                    r0 = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                    r1 = df.iloc[j, 1] if df.shape[1] > 1 else None
                    r2 = df.iloc[j, 2] if df.shape[1] > 2 else None

                    # Fin de tabla: celda vacía o nueva tabla
                    if r0 == "" and (pd.isna(r1) or str(r1).strip() == ""):
                        break
                    if " vs " in r0.lower():
                        break

                    # Saltar fila de cabecera (Métrica / local / visitante)
                    if r0.lower() in ("métrica", "metrica"):
                        j += 1
                        continue

                    stats["metricas"][r0] = {
                        "local":     extraer_numero(r1) if pd.notna(r1) else 0,
                        "visitante": extraer_numero(r2) if pd.notna(r2) else 0,
                    }
                    j += 1

                if stats["metricas"]:
                    partidos.append(stats)
                i = j
            else:
                i += 1
        else:
            i += 1

    return partidos


def construir_df_equipos(datos: dict) -> pd.DataFrame:
    """
    Construye un DataFrame largo:
    [Fecha, Partido, Equipo, Condicion, Métrica, Valor]
    """
    filas = []
    for fecha, partidos in datos.items():
        for p in partidos:
            for metrica, vals in p["metricas"].items():
                filas.append({
                    "Fecha":     fecha,
                    "Partido":   f"{p['local']} vs {p['visitante']}",
                    "Equipo":    p["local"],
                    "Condicion": "Local",
                    "Métrica":   metrica,
                    "Valor":     vals["local"],
                })
                filas.append({
                    "Fecha":     fecha,
                    "Partido":   f"{p['local']} vs {p['visitante']}",
                    "Equipo":    p["visitante"],
                    "Condicion": "Visitante",
                    "Métrica":   metrica,
                    "Valor":     vals["visitante"],
                })
    return pd.DataFrame(filas)


def df_promedios_por_equipo(df_largo: pd.DataFrame) -> pd.DataFrame:
    """Promedio de cada métrica por equipo en todo el torneo."""
    return (
        df_largo.groupby(["Equipo", "Métrica"])["Valor"]
        .mean()
        .reset_index()
        .rename(columns={"Valor": "Promedio"})
    )


def df_tabla_ranking(df_largo: pd.DataFrame, metrica: str, orden_asc=False) -> pd.DataFrame:
    df_m = df_largo[df_largo["Métrica"] == metrica].copy()
    return (
        df_m.groupby("Equipo")["Valor"]
        .agg(["mean", "sum", "count"])
        .reset_index()
        .rename(columns={"mean": "Promedio", "sum": "Total", "count": "Partidos"})
        .sort_values("Promedio", ascending=orden_asc)
        .round(2)
    )


# ─────────────────────────────────────────────────────────────────
# PREDICTOR (Modelo Dixon-Coles simplificado con datos reales)
# ─────────────────────────────────────────────────────────────────

def calcular_lambdas_reales(df_largo: pd.DataFrame, equipo_a: str, equipo_b: str, es_local: bool):
    """
    Calcula λ de goles esperados para cada equipo usando datos reales del torneo.
    Usa ataque (GF/PJ) y defensa (GC/PJ) de cada equipo relativo a la media.
    """
    df_res = df_largo[df_largo["Métrica"] == "Resultado"].copy()
    if df_res.empty:
        return 1.3, 0.9

    equipos_stats = {}
    for _, row in df_res.iterrows():
        eq = row["Equipo"]
        if eq not in equipos_stats:
            equipos_stats[eq] = {"GF": 0, "GC": 0, "PJ": 0}
        # GF del equipo = Valor de "Resultado" en su condición
        equipos_stats[eq]["GF"] += row["Valor"]
        equipos_stats[eq]["PJ"] += 1

    # GC = GF del oponente en cada partido
    df_partidos = df_largo[df_largo["Métrica"] == "Resultado"].copy()
    for fecha, grupo in df_partidos.groupby(["Fecha", "Partido"]):
        if len(grupo) == 2:
            r = grupo.to_dict("records")
            local_eq = r[0]["Equipo"] if r[0]["Condicion"] == "Local" else r[1]["Equipo"]
            visit_eq = r[1]["Equipo"] if r[1]["Condicion"] == "Visitante" else r[0]["Equipo"]
            gl = r[0]["Valor"] if r[0]["Condicion"] == "Local" else r[1]["Valor"]
            gv = r[1]["Valor"] if r[1]["Condicion"] == "Visitante" else r[0]["Valor"]
            if local_eq in equipos_stats:
                equipos_stats[local_eq]["GC"] += gv
            if visit_eq in equipos_stats:
                equipos_stats[visit_eq]["GC"] += gl

    def safe_pj(eq): return max(equipos_stats.get(eq, {}).get("PJ", 1), 1)
    def gf_p90(eq):  return equipos_stats.get(eq, {}).get("GF", 1.2) / safe_pj(eq)
    def gc_p90(eq):  return equipos_stats.get(eq, {}).get("GC", 1.2) / safe_pj(eq)

    todos_gf = [gf_p90(e) for e in equipos_stats]
    media_gf = np.mean(todos_gf) if todos_gf else 1.2

    fa_a = gf_p90(equipo_a) / media_gf
    fd_a = gc_p90(equipo_a) / media_gf
    fa_b = gf_p90(equipo_b) / media_gf
    fd_b = gc_p90(equipo_b) / media_gf

    ventaja_local = 1.18

    # λ = ataque_local × defensa_rival × media × ventaja_local
    lam_a = fa_a * fd_b * media_gf * (ventaja_local if es_local else 1.0)
    lam_b = fa_b * fd_a * media_gf * (1.0 if es_local else ventaja_local)

    # Ajuste por xG si está disponible
    df_xg = df_largo[df_largo["Métrica"] == "Goles esperados (xG)"]
    if not df_xg.empty:
        xg_a = df_xg[df_xg["Equipo"] == equipo_a]["Valor"].mean()
        xg_b = df_xg[df_xg["Equipo"] == equipo_b]["Valor"].mean()
        xg_media = df_xg["Valor"].mean()
        if not np.isnan(xg_a) and xg_media > 0:
            lam_a = lam_a * 0.6 + (xg_a / xg_media * media_gf) * 0.4
        if not np.isnan(xg_b) and xg_media > 0:
            lam_b = lam_b * 0.6 + (xg_b / xg_media * media_gf) * 0.4

    return round(float(np.clip(lam_a, 0.2, 4.5)), 3), round(float(np.clip(lam_b, 0.2, 4.5)), 3)


def simular_montecarlo(lam_a, lam_b) -> dict:
    rng = np.random.default_rng(99)
    ga  = rng.poisson(lam_a, MONTECARLO_N)
    gb  = rng.poisson(lam_b, MONTECARLO_N)

    resultados = []
    for r in range(7):
        for v in range(7):
            resultados.append({
                "EquipoA": r, "EquipoB": v,
                "prob": float(np.mean((ga == r) & (gb == v)))
            })

    return {
        "prob_victoria": float(np.mean(ga > gb)),
        "prob_empate":   float(np.mean(ga == gb)),
        "prob_derrota":  float(np.mean(ga < gb)),
        "df_resultados": pd.DataFrame(resultados),
        "lam_a": lam_a, "lam_b": lam_b,
    }


# ─────────────────────────────────────────────────────────────────
# FIGURAS PLOTLY
# ─────────────────────────────────────────────────────────────────

def fig_probabilidades(sim, nombre_a, nombre_b):
    vals  = [sim["prob_victoria"], sim["prob_empate"], sim["prob_derrota"]]
    etiq  = [f"Victoria {nombre_a}", "Empate", f"Victoria {nombre_b}"]
    colrs = [RED, GRAY, BLUE]
    fig = go.Figure(go.Bar(
        x=[v * 100 for v in vals], y=etiq, orientation="h",
        marker_color=colrs,
        text=[f"{v*100:.1f}%" for v in vals],
        textposition="outside",
        textfont=dict(size=15, family="Rajdhani", color="#e2e8f0"),
    ))
    fig.update_layout(**PLOT_BASE, height=220,
        xaxis=dict(range=[0, 100], showgrid=True, gridcolor="#1e2d4a", ticksuffix="%"),
        yaxis=dict(showgrid=False, tickfont=dict(size=14, family="Rajdhani")),
    )
    return fig


def fig_marcadores_top(sim, nombre_a, nombre_b):
    df = sim["df_resultados"].copy()
    df["Marcador"] = nombre_a + " " + df["EquipoA"].astype(str) + " – " + df["EquipoB"].astype(str) + " " + nombre_b
    df_top = df.sort_values("prob", ascending=False).head(8).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=df_top["prob"] * 100,
        y=df_top["Marcador"],
        orientation="h",
        marker=dict(color=RED, opacity=0.85),
        text=(df_top["prob"] * 100).apply(lambda x: f"{x:.1f}%"),
        textposition="auto",
        textfont=dict(color="white", size=14, family="Rajdhani"),
    ))
    fig.update_layout(**PLOT_BASE, height=360,
        xaxis=dict(showgrid=True, gridcolor="#1e2d4a", ticksuffix="%"),
        yaxis=dict(showgrid=False, tickfont=dict(size=13, family="Rajdhani")),
    )
    return fig


def fig_radar_comparativo(df_largo, equipo_a, equipo_b):
    metricas_radar = [
        "Posesión de balón", "Tiros totales", "Tiros al arco",
        "Pases totales", "Goles esperados (xG)", "Córners",
        "Quites", "Intercepciones",
    ]
    df_prom = df_promedios_por_equipo(df_largo)

    def get_prom(eq, met):
        v = df_prom[(df_prom["Equipo"] == eq) & (df_prom["Métrica"] == met)]["Promedio"]
        return float(v.iloc[0]) if not v.empty else 0

    vals_a = [get_prom(equipo_a, m) for m in metricas_radar]
    vals_b = [get_prom(equipo_b, m) for m in metricas_radar]

    # Normalizar 0-1
    maximos = [max(a, b, 0.001) for a, b in zip(vals_a, vals_b)]
    vals_a_n = [a / mx for a, mx in zip(vals_a, maximos)]
    vals_b_n = [b / mx for b, mx in zip(vals_b, maximos)]

    fig = go.Figure()
    for vals, nombre, color in [(vals_a_n, equipo_a, RED), (vals_b_n, equipo_b, BLUE)]:
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=metricas_radar + [metricas_radar[0]],
            fill="toself", name=nombre,
            line=dict(color=color, width=2),
            fillcolor=color.replace("e5", "3d").replace("31", "0d") + "33",
        ))
    fig.update_layout(
        **PLOT_BASE, height=420,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 1], gridcolor="#1e2d4a", tickfont=dict(size=9)),
            angularaxis=dict(gridcolor="#1e2d4a", tickfont=dict(size=12, family="Rajdhani")),
        ),
        legend=dict(font=dict(family="Rajdhani", size=13)),
    )
    return fig


def fig_ranking_metrica(df_largo, metrica, top_n=15, ascendente=False):
    df_r = df_tabla_ranking(df_largo, metrica, ascendente).head(top_n).iloc[::-1]
    if df_r.empty:
        return go.Figure()
    colores = [RED if i == len(df_r) - 1 else "#2d3a56" for i in range(len(df_r))]
    fig = go.Figure(go.Bar(
        x=df_r["Promedio"], y=df_r["Equipo"],
        orientation="h",
        marker_color=colores,
        text=df_r["Promedio"].apply(lambda x: f"{x:.2f}"),
        textposition="outside",
        textfont=dict(size=12, family="Rajdhani", color="#e2e8f0"),
    ))
    titulo_ord = "↑ Mayor a menor" if not ascendente else "↓ Menor a mayor"
    fig.update_layout(
        **PLOT_BASE, height=max(350, top_n * 28),
        title=dict(text=f"{metrica} por equipo  ({titulo_ord})", font=dict(family="Bebas Neue", size=18), x=0),
        xaxis=dict(showgrid=True, gridcolor="#1e2d4a"),
        yaxis=dict(showgrid=False, tickfont=dict(size=12, family="Rajdhani")),
    )
    return fig


def fig_evolucion_equipo(df_largo, equipo, metricas_sel):
    df_eq = df_largo[(df_largo["Equipo"] == equipo) & (df_largo["Métrica"].isin(metricas_sel))].copy()
    if df_eq.empty:
        return go.Figure()
    # Extraer número de fecha para ordenar
    df_eq["nFecha"] = df_eq["Fecha"].str.extract(r"(\d+)").astype(float)
    df_eq = df_eq.sort_values("nFecha")

    COLORES_LINEAS = [RED, BLUE, "#68d391", "#f6e05e", "#b794f4", "#fc8181"]
    fig = go.Figure()
    for idx, met in enumerate(metricas_sel):
        df_m = df_eq[df_eq["Métrica"] == met]
        fig.add_trace(go.Scatter(
            x=df_m["Fecha"], y=df_m["Valor"],
            mode="lines+markers", name=met,
            line=dict(color=COLORES_LINEAS[idx % len(COLORES_LINEAS)], width=2),
            marker=dict(size=8),
        ))
    fig.update_layout(
        **PLOT_BASE, height=360,
        title=dict(text=f"Evolución de {equipo}", font=dict(family="Bebas Neue", size=18), x=0),
        xaxis=dict(showgrid=True, gridcolor="#1e2d4a", tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#1e2d4a"),
        legend=dict(font=dict(family="Rajdhani", size=12)),
    )
    return fig


def fig_dispersion(df_largo, metrica_x, metrica_y):
    df_prom = df_promedios_por_equipo(df_largo)
    df_x = df_prom[df_prom["Métrica"] == metrica_x].rename(columns={"Promedio": "X"})
    df_y = df_prom[df_prom["Métrica"] == metrica_y].rename(columns={"Promedio": "Y"})
    df_m = df_x.merge(df_y, on="Equipo")
    if df_m.empty:
        return go.Figure()
    fig = go.Figure(go.Scatter(
        x=df_m["X"], y=df_m["Y"],
        mode="markers+text",
        text=df_m["Equipo"],
        textposition="top center",
        textfont=dict(size=10, family="Rajdhani", color="#a0aec0"),
        marker=dict(size=12, color=RED, opacity=0.8, line=dict(color="white", width=1)),
    ))
    fig.update_layout(
        **PLOT_BASE, height=420,
        xaxis=dict(title=metrica_x, showgrid=True, gridcolor="#1e2d4a"),
        yaxis=dict(title=metrica_y, showgrid=True, gridcolor="#1e2d4a"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    st.markdown("---")
    ruta_excel = st.text_input(
        "📂 Ruta del Excel",
        value="Fecha_x_fecha_lpf.xlsx",
        help="Ruta al archivo generado por sofascore_lpf_generales.py",
    )
    st.markdown("---")
    nav = st.radio(
        "Navegación",
        ["🔮 Predictor", "📊 Tablas Comparativas", "📈 Evolución por Equipo", "🔍 Dispersión"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown(
        '<div style="font-family:Rajdhani;font-size:11px;color:#4a5568;text-align:center;">'
        'Datos: SofaScore API<br>Liga Profesional 2026</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────────────────────────

archivo_existe = os.path.exists(ruta_excel)
if not archivo_existe:
    st.markdown('<h1>LPF 2026 · Dashboard</h1>', unsafe_allow_html=True)
    st.warning(
        f"No se encontró el archivo **{ruta_excel}**.\n\n"
        "Corré primero `sofascore_lpf_generales.py` para generar el Excel con los datos."
    )
    st.stop()

with st.spinner("Cargando datos del Excel…"):
    datos_excel = cargar_excel(ruta_excel)

if not datos_excel:
    st.error("El Excel no contiene hojas con el formato esperado (Fecha X).")
    st.stop()

df_largo = construir_df_equipos(datos_excel)
equipos_disponibles = sorted(df_largo["Equipo"].unique().tolist())
metricas_disponibles = sorted(df_largo["Métrica"].unique().tolist())
fechas_disponibles   = sorted(datos_excel.keys(), key=lambda x: int(re.search(r"\d+", x).group()))

# ─────────────────────────────────────────────────────────────────
# HEADER GLOBAL
# ─────────────────────────────────────────────────────────────────
st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)
st.markdown(
    f'<div class="badge">✅ {len(fechas_disponibles)} fecha(s) cargada(s) · '
    f'{len(equipos_disponibles)} equipos · '
    f'{len(df_largo[df_largo["Métrica"]=="Resultado"])} partidos</div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────
# SECCIÓN: PREDICTOR
# ─────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor":
    st.markdown('<div class="section-head">🔮 Predictor de Partidos</div>', unsafe_allow_html=True)
    st.caption("Modelo Dixon-Coles simplificado calibrado con datos reales del torneo + ajuste xG.")

    c1, c2, c3 = st.columns([2, 2, 1])
    equipo_a = c1.selectbox("Equipo A (Local)", equipos_disponibles,
                             index=equipos_disponibles.index("River Plate") if "River Plate" in equipos_disponibles else 0)
    equipo_b = c2.selectbox("Equipo B (Visitante)", equipos_disponibles,
                             index=min(1, len(equipos_disponibles) - 1))
    es_local = c3.radio("Condición A", ["Local 🏠", "Visitante ✈️"]) == "Local 🏠"

    if equipo_a == equipo_b:
        st.warning("Seleccioná dos equipos diferentes.")
    else:
        if st.button("🚀 SIMULAR", use_container_width=True, type="primary"):
            with st.spinner("Simulando 15,000 partidos…"):
                lam_a, lam_b = calcular_lambdas_reales(df_largo, equipo_a, equipo_b, es_local)
                sim = simular_montecarlo(lam_a, lam_b)

            st.markdown(f"### {equipo_a} {'🏠' if es_local else '✈️'} vs {equipo_b}")

            k1, k2, k3, k4, k5 = st.columns(5)
            for col, label, val, clase in [
                (k1, "Victoria " + equipo_a[:8],  f"{sim['prob_victoria']*100:.1f}%", ""),
                (k2, "Empate",                     f"{sim['prob_empate']*100:.1f}%",   "empate"),
                (k3, "Victoria " + equipo_b[:8],  f"{sim['prob_derrota']*100:.1f}%",  "derrota"),
                (k4, f"λ {equipo_a[:8]}",          f"{lam_a:.2f}",                    "neutral"),
                (k5, f"λ {equipo_b[:8]}",          f"{lam_b:.2f}",                    "neutral"),
            ]:
                col.markdown(
                    f'<div class="kpi-card {clase}"><div class="kpi-label">{label}</div>'
                    f'<div class="kpi-val">{val}</div></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            t1, t2, t3 = st.tabs(["📊 Probabilidades", "🎯 Marcadores Exactos", "🕸️ Radar Comparativo"])

            with t1:
                st.plotly_chart(fig_probabilidades(sim, equipo_a, equipo_b), use_container_width=True)

            with t2:
                st.plotly_chart(fig_marcadores_top(sim, equipo_a, equipo_b), use_container_width=True)

                df_top8 = (
                    sim["df_resultados"]
                    .sort_values("prob", ascending=False)
                    .head(8)
                    .copy()
                )
                df_top8["Marcador"] = equipo_a + " " + df_top8["EquipoA"].astype(str) + " – " + df_top8["EquipoB"].astype(str) + " " + equipo_b
                df_top8["Probabilidad"] = (df_top8["prob"] * 100).round(1).astype(str) + "%"
                st.dataframe(
                    df_top8[["Marcador", "Probabilidad"]].reset_index(drop=True),
                    use_container_width=True, hide_index=True,
                )

            with t3:
                st.plotly_chart(fig_radar_comparativo(df_largo, equipo_a, equipo_b), use_container_width=True)
                st.caption("Valores normalizados al máximo entre ambos equipos para facilitar comparación.")

# ─────────────────────────────────────────────────────────────────
# SECCIÓN: TABLAS COMPARATIVAS
# ─────────────────────────────────────────────────────────────────
elif nav == "📊 Tablas Comparativas":
    st.markdown('<div class="section-head">📊 Tablas Comparativas</div>', unsafe_allow_html=True)

    tabs = st.tabs([
        "⚡ Rankings", "🔄 Head-to-Head", "📋 Resumen Completo"
    ])

    # ── TAB 1: Rankings por métrica ─────────────────────────────
    with tabs[0]:
        c1, c2, c3 = st.columns([3, 1, 1])
        met_sel = c1.selectbox("Métrica a rankear", metricas_disponibles,
                                index=metricas_disponibles.index("Tiros totales") if "Tiros totales" in metricas_disponibles else 0)
        top_n    = c2.slider("Top N equipos", 5, len(equipos_disponibles), 15)
        asc      = c3.radio("Orden", ["Mayor = Mejor ↓", "Menor = Mejor ↑"]) == "Menor = Mejor ↑"

        st.plotly_chart(fig_ranking_metrica(df_largo, met_sel, top_n, asc), use_container_width=True)

        df_rank = df_tabla_ranking(df_largo, met_sel, asc).head(top_n)
        st.dataframe(
            df_rank.style.background_gradient(subset=["Promedio"], cmap="RdYlGn" if not asc else "RdYlGn_r"),
            use_container_width=True, hide_index=True,
        )

        st.markdown("---")
        st.markdown("#### 📌 Top 5 rápidos")

        # Muestro 4 rankings rápidos en columnas
        metricas_rapidas = {
            "⚽ Más tiros totales":     ("Tiros totales",     False),
            "🥅 Más tiros recibidos":   ("Tiros al arco",     False),
            "🎯 Mejor xG":              ("Goles esperados (xG)", False),
            "🏃 Más faltas cometidas":  ("Faltas",            False),
        }
        # Solo mostrar si las métricas existen
        metricas_rapidas = {k: v for k, v in metricas_rapidas.items() if v[0] in metricas_disponibles}
        cols = st.columns(len(metricas_rapidas))
        for col, (titulo, (met, asc_r)) in zip(cols, metricas_rapidas.items()):
            df_r = df_tabla_ranking(df_largo, met, asc_r).head(5)
            col.markdown(f"**{titulo}**")
            col.dataframe(
                df_r[["Equipo", "Promedio"]].rename(columns={"Promedio": "Prom."}),
                use_container_width=True, hide_index=True,
            )

    # ── TAB 2: Head-to-Head ─────────────────────────────────────
    with tabs[1]:
        c1, c2 = st.columns(2)
        eq_h2h_a = c1.selectbox("Equipo A", equipos_disponibles, key="h2h_a")
        eq_h2h_b = c2.selectbox("Equipo B", equipos_disponibles,
                                  index=min(1, len(equipos_disponibles) - 1), key="h2h_b")

        if eq_h2h_a != eq_h2h_b:
            df_prom = df_promedios_por_equipo(df_largo)
            df_a = df_prom[df_prom["Equipo"] == eq_h2h_a].set_index("Métrica")["Promedio"]
            df_b = df_prom[df_prom["Equipo"] == eq_h2h_b].set_index("Métrica")["Promedio"]
            idx_comun = df_a.index.intersection(df_b.index)

            if idx_comun.empty:
                st.info("No hay métricas comunes para comparar.")
            else:
                df_h2h = pd.DataFrame({
                    "Métrica": idx_comun,
                    eq_h2h_a: df_a[idx_comun].values.round(2),
                    eq_h2h_b: df_b[idx_comun].values.round(2),
                })
                df_h2h["Ventaja"] = df_h2h.apply(
                    lambda r: f"▲ {eq_h2h_a}" if r[eq_h2h_a] > r[eq_h2h_b] else (
                        f"▲ {eq_h2h_b}" if r[eq_h2h_b] > r[eq_h2h_a] else "— Empate"),
                    axis=1,
                )
                st.dataframe(df_h2h, use_container_width=True, hide_index=True)

                # Resumen de ventajas
                vc_a = (df_h2h["Ventaja"].str.startswith(f"▲ {eq_h2h_a}")).sum()
                vc_b = (df_h2h["Ventaja"].str.startswith(f"▲ {eq_h2h_b}")).sum()
                ca, cb, cc = st.columns(3)
                ca.metric(f"Métricas mejor: {eq_h2h_a}", vc_a)
                cb.metric(f"Métricas mejor: {eq_h2h_b}", vc_b)
                cc.metric("Empates", len(df_h2h) - vc_a - vc_b)

                st.plotly_chart(fig_radar_comparativo(df_largo, eq_h2h_a, eq_h2h_b), use_container_width=True)

    # ── TAB 3: Resumen completo ──────────────────────────────────
    with tabs[2]:
        met_resumen = st.multiselect(
            "Métricas a incluir",
            metricas_disponibles,
            default=metricas_disponibles[:8],
        )
        if met_resumen:
            df_prom = df_promedios_por_equipo(df_largo)
            df_pivot = (
                df_prom[df_prom["Métrica"].isin(met_resumen)]
                .pivot(index="Equipo", columns="Métrica", values="Promedio")
                .round(2)
                .reset_index()
            )
            st.dataframe(
                df_pivot.style.background_gradient(
                    subset=[c for c in df_pivot.columns if c != "Equipo"],
                    cmap="RdYlGn",
                ),
                use_container_width=True, hide_index=True,
                height=600,
            )

# ─────────────────────────────────────────────────────────────────
# SECCIÓN: EVOLUCIÓN POR EQUIPO
# ─────────────────────────────────────────────────────────────────
elif nav == "📈 Evolución por Equipo":
    st.markdown('<div class="section-head">📈 Evolución Fecha a Fecha</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([2, 3])
    eq_ev = c1.selectbox("Equipo", equipos_disponibles)
    mets_ev = c2.multiselect(
        "Métricas",
        metricas_disponibles,
        default=["Tiros totales", "Goles esperados (xG)", "Posesión de balón"][:len(metricas_disponibles)],
        max_selections=6,
    )

    if mets_ev:
        st.plotly_chart(fig_evolucion_equipo(df_largo, eq_ev, mets_ev), use_container_width=True)

        # Tabla con los valores por fecha
        df_ev_tbl = (
            df_largo[(df_largo["Equipo"] == eq_ev) & (df_largo["Métrica"].isin(mets_ev))]
            .pivot_table(index="Fecha", columns="Métrica", values="Valor", aggfunc="mean")
            .round(2)
            .reset_index()
        )
        st.dataframe(df_ev_tbl, use_container_width=True, hide_index=True)

        # KPIs de tendencia
        st.markdown("#### Tendencia (última vs primera fecha disponible)")
        cols_kpi = st.columns(len(mets_ev))
        for col, met in zip(cols_kpi, mets_ev):
            df_m = df_largo[(df_largo["Equipo"] == eq_ev) & (df_largo["Métrica"] == met)].copy()
            df_m["nFecha"] = df_m["Fecha"].str.extract(r"(\d+)").astype(float)
            df_m = df_m.sort_values("nFecha")
            if len(df_m) >= 2:
                delta = round(df_m["Valor"].iloc[-1] - df_m["Valor"].iloc[0], 2)
                col.metric(met[:20], round(df_m["Valor"].iloc[-1], 2), delta=delta)
            elif len(df_m) == 1:
                col.metric(met[:20], round(df_m["Valor"].iloc[0], 2))

# ─────────────────────────────────────────────────────────────────
# SECCIÓN: DISPERSIÓN
# ─────────────────────────────────────────────────────────────────
elif nav == "🔍 Dispersión":
    st.markdown('<div class="section-head">🔍 Análisis de Dispersión</div>', unsafe_allow_html=True)
    st.caption("Correlación entre dos métricas. Cada punto = un equipo (promedio del torneo).")

    c1, c2 = st.columns(2)
    met_x = c1.selectbox("Eje X", metricas_disponibles,
                          index=metricas_disponibles.index("Posesión de balón") if "Posesión de balón" in metricas_disponibles else 0)
    met_y = c2.selectbox("Eje Y", metricas_disponibles,
                          index=metricas_disponibles.index("Goles esperados (xG)") if "Goles esperados (xG)" in metricas_disponibles else 1)

    if met_x != met_y:
        st.plotly_chart(fig_dispersion(df_largo, met_x, met_y), use_container_width=True)

        df_prom = df_promedios_por_equipo(df_largo)
        df_x = df_prom[df_prom["Métrica"] == met_x].rename(columns={"Promedio": met_x})
        df_y = df_prom[df_prom["Métrica"] == met_y].rename(columns={"Promedio": met_y})
        df_scatter_tbl = df_x.merge(df_y, on="Equipo")[[" Equipo", met_x, met_y]].rename(columns={" Equipo": "Equipo"})
        corr = df_scatter_tbl[met_x].corr(df_scatter_tbl[met_y])
        st.metric("Correlación de Pearson", f"{corr:.3f}")
        st.dataframe(
            df_scatter_tbl.sort_values(met_x, ascending=False).round(2),
            use_container_width=True, hide_index=True,
        )