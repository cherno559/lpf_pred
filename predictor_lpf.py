"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v11.0 · UI Pro)
─────────────────────────────────────────────────────────────────────────────
BACKEND BLOQUEADO: No se modificaron cargar_excel, construir_df,
_strength, _adjusted_rate, calcular_lambdas, montecarlo.
Solo se elevó la capa UI/UX.
"""
import re, os, math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACION
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LPF 2026 · Analitica Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ESTILOS GLOBALES
# Se inyecta via components.html para evitar que Streamlit
# interprete caracteres especiales dentro del bloque <style>.
_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@400;600;700;800&family=Barlow:wght@300;400;500&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] {
    font-family: 'Barlow', sans-serif;
    font-weight: 400;
}
.stApp {
    background: #06090f;
    color: #c8d0e0;
}
section[data-testid="stSidebar"] {
    background: #080c15 !important;
    border-right: 1px solid #111927 !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div {
    padding-top: 0 !important;
}
.sidebar-brand {
    background: linear-gradient(135deg, #e63946 0%, #9b1d28 100%);
    padding: 22px 20px 18px;
    margin: -1rem -1rem 1.5rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.sidebar-brand::before {
    content: '';
    position: absolute;
    top: -20px; right: -20px;
    width: 80px; height: 80px;
    border-radius: 50%;
    background: rgba(255,255,255,0.06);
}
.sidebar-brand::after {
    content: '';
    position: absolute;
    bottom: -30px; left: -15px;
    width: 100px; height: 100px;
    border-radius: 50%;
    background: rgba(255,255,255,0.04);
}
.sidebar-brand .league-name {
    font-family: 'Bebas Neue', cursive;
    font-size: 2rem;
    letter-spacing: 6px;
    color: #fff;
    line-height: 1;
    position: relative;
    z-index: 1;
}
.sidebar-brand .season-badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.85);
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    padding: 3px 10px;
    border-radius: 20px;
    margin-top: 6px;
    position: relative;
    z-index: 1;
}
div[data-testid="stRadio"] > label {
    display: none;
}
div[data-testid="stRadio"] > div {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
div[data-testid="stRadio"] > div > label {
    background: transparent;
    border: 1px solid #111927;
    border-radius: 8px;
    padding: 10px 14px !important;
    cursor: pointer;
    transition: all 0.18s ease;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 1px;
    color: #5a6a80 !important;
}
div[data-testid="stRadio"] > div > label:hover {
    background: #0f1825;
    color: #c8d0e0 !important;
    border-color: #1c2a3e;
}
div[data-testid="stRadio"] > div > label[data-checked="true"],
div[data-testid="stRadio"] > div > label[aria-checked="true"] {
    background: linear-gradient(135deg, #1a0a0c, #1f0d10);
    border-color: #e63946;
    color: #e63946 !important;
}
.stTextInput > div > div {
    background: #0c1220 !important;
    border: 1px solid #1c2a3e !important;
    color: #c8d0e0 !important;
    border-radius: 8px !important;
    font-family: 'Barlow', sans-serif !important;
    font-size: 13px !important;
}
.sidebar-section-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 3px;
    color: #2d3f58;
    text-transform: uppercase;
    padding: 0 2px 6px;
    border-bottom: 1px solid #111927;
    margin-bottom: 10px;
}
.main-header {
    display: flex;
    align-items: flex-end;
    gap: 18px;
    padding: 28px 0 24px;
    border-bottom: 1px solid #111927;
    margin-bottom: 28px;
}
.main-header .title-block .pre {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 4px;
    color: #e63946;
    text-transform: uppercase;
    margin-bottom: 2px;
}
.main-header .title-block h1 {
    font-family: 'Bebas Neue', cursive !important;
    font-size: 3rem !important;
    color: #ffffff !important;
    letter-spacing: 4px;
    line-height: 1 !important;
    margin: 0 !important;
    padding: 0 !important;
}
.main-header .title-block .sub {
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
    color: #3d5270;
    margin-top: 4px;
    font-weight: 300;
}
.section-title {
    font-family: 'Bebas Neue', cursive;
    font-size: 1.1rem;
    letter-spacing: 4px;
    color: #e63946;
    text-transform: uppercase;
    padding-bottom: 10px;
    border-bottom: 1px solid #111927;
    margin: 32px 0 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.section-title::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 18px;
    background: #e63946;
    border-radius: 2px;
}
.kpi-card {
    background: linear-gradient(145deg, #0b1120, #0e1628);
    border: 1px solid #141e30;
    border-radius: 12px;
    padding: 20px 18px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, border-color 0.2s;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 3px;
    background: linear-gradient(90deg, #e63946, transparent);
}
.kpi-card.blue::before { background: linear-gradient(90deg, #3b82f6, transparent); }
.kpi-card.gray::before { background: linear-gradient(90deg, #64748b, transparent); }
.kpi-card.green::before { background: linear-gradient(90deg, #22c55e, transparent); }
.kpi-card .lbl {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #3d5270;
    margin-bottom: 6px;
}
.kpi-card .val {
    font-family: 'Bebas Neue', cursive;
    font-size: 42px;
    color: #e63946;
    line-height: 1;
}
.kpi-card.blue .val { color: #3b82f6; }
.kpi-card.gray .val { color: #94a3b8; }
.kpi-card.green .val { color: #22c55e; }
.kpi-card .sub-val {
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    color: #3d5270;
    margin-top: 4px;
}
.kpi-card .icon {
    position: absolute;
    right: 16px; top: 16px;
    font-size: 26px;
    opacity: 0.12;
}
.match-card {
    background: linear-gradient(145deg, #0b1120, #0e1628);
    border: 1px solid #141e30;
    border-radius: 16px;
    padding: 32px 28px 24px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.match-card::after {
    content: '';
    position: absolute;
    top: 0; left: 50%;
    transform: translateX(-50%);
    width: 1px; height: 100%;
    background: linear-gradient(180deg, transparent, #1c2a3e 30%, #1c2a3e 70%, transparent);
}
.match-card .vs-badge {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    z-index: 10;
    background: #06090f;
    border: 1px solid #1c2a3e;
    border-radius: 50%;
    width: 44px; height: 44px;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Bebas Neue', cursive;
    font-size: 15px;
    color: #e63946;
    letter-spacing: 1px;
}
.team-block {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 0 24px;
}
.team-shield {
    width: 64px; height: 64px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Bebas Neue', cursive;
    font-size: 22px;
    color: #fff;
    position: relative;
    flex-shrink: 0;
}
.team-shield.home {
    background: linear-gradient(135deg, #e63946, #7f1d1d);
    box-shadow: 0 0 20px rgba(230, 57, 70, 0.3);
}
.team-shield.away {
    background: linear-gradient(135deg, #3b82f6, #1e3a8a);
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
}
.team-name-big {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #c8d0e0;
    text-align: center;
}
.team-condition {
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    font-weight: 500;
    color: #3d5270;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.prob-section {
    background: #0b1120;
    border: 1px solid #141e30;
    border-radius: 12px;
    padding: 22px 24px;
    margin-bottom: 16px;
}
.prob-row {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 14px;
}
.prob-row:last-child { margin-bottom: 0; }
.prob-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #3d5270;
    width: 70px;
    flex-shrink: 0;
}
.prob-bar-track {
    flex: 1;
    height: 8px;
    background: #111927;
    border-radius: 4px;
    overflow: hidden;
    position: relative;
}
.prob-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s ease;
}
.prob-bar-fill.home { background: linear-gradient(90deg, #e63946, #f87171); }
.prob-bar-fill.draw { background: linear-gradient(90deg, #64748b, #94a3b8); }
.prob-bar-fill.away { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.prob-pct {
    font-family: 'Bebas Neue', cursive;
    font-size: 22px;
    width: 58px;
    text-align: right;
    flex-shrink: 0;
}
.prob-pct.home { color: #e63946; }
.prob-pct.draw { color: #94a3b8; }
.prob-pct.away { color: #3b82f6; }

.lambda-strip {
    background: #080c15;
    border: 1px solid #111927;
    border-radius: 10px;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 16px;
}
.lambda-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.lambda-item .l-key {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #2d3f58;
}
.lambda-item .l-val {
    font-family: 'Bebas Neue', cursive;
    font-size: 18px;
    color: #c8d0e0;
}
.lambda-divider {
    width: 1px; height: 36px;
    background: #111927;
}
.stSelectbox > div > div {
    background: #0c1220 !important;
    border: 1px solid #1c2a3e !important;
    color: #c8d0e0 !important;
    border-radius: 8px !important;
    font-family: 'Barlow', sans-serif !important;
}
.stSelectbox > label {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: #3d5270 !important;
}
.stCheckbox > label, .stToggle > label {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    color: #3d5270 !important;
    text-transform: uppercase !important;
}
.stButton > button {
    font-family: 'Bebas Neue', cursive;
    font-size: 18px;
    letter-spacing: 3px;
    background: linear-gradient(135deg, #e63946, #b91c2c);
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 14px 28px;
    width: 100%;
    transition: all 0.2s ease;
    box-shadow: 0 4px 20px rgba(230,57,70,0.25);
}
.stButton > button:hover {
    background: linear-gradient(135deg, #f04855, #e63946);
    box-shadow: 0 6px 28px rgba(230,57,70,0.45);
    transform: translateY(-1px);
}
.stTabs [data-baseweb="tab-list"] {
    background: #0b1120;
    border-radius: 10px;
    padding: 5px;
    gap: 4px;
    border: 1px solid #141e30;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 1px;
    color: #3d5270 !important;
    border-radius: 7px;
    padding: 8px 18px;
    text-transform: uppercase;
}
.stTabs [aria-selected="true"] {
    background: #e63946 !important;
    color: #fff !important;
}
.stDataFrame {
    border: 1px solid #141e30 !important;
    border-radius: 10px !important;
    overflow: hidden;
}
.stDataFrame table {
    font-family: 'Barlow', sans-serif !important;
    font-size: 13px !important;
}
.mini-stat {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #0c1220;
    border: 1px solid #141e30;
    border-radius: 6px;
    padding: 4px 10px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: #5a6a80;
    letter-spacing: 1px;
}
.mini-stat span { color: #c8d0e0; }
.stat-compare-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #0f1825;
}
.stat-compare-row:last-child { border-bottom: none; }
.stat-compare-val {
    font-family: 'Bebas Neue', cursive;
    font-size: 22px;
    min-width: 50px;
    text-align: center;
}
.stat-compare-name {
    flex: 1;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #3d5270;
    text-align: center;
}
.rank-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 9px 0;
    border-bottom: 1px solid #0c1220;
}
.rank-pos {
    font-family: 'Bebas Neue', cursive;
    font-size: 18px;
    color: #2d3f58;
    width: 24px;
    text-align: right;
    flex-shrink: 0;
}
.rank-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #94a3b8;
    width: 160px;
    flex-shrink: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.rank-bar-track {
    flex: 1;
    height: 6px;
    background: #0f1825;
    border-radius: 3px;
    overflow: hidden;
}
.rank-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, #e63946, #f87171);
}
.rank-val {
    font-family: 'Bebas Neue', cursive;
    font-size: 18px;
    width: 48px;
    text-align: right;
    color: #e63946;
}
.tabla-pos {
    background: #0b1120;
    border: 1px solid #141e30;
    border-radius: 12px;
    overflow: hidden;
}
.tabla-header {
    display: grid;
    grid-template-columns: 30px 1fr 40px 30px 30px 30px 40px 40px 50px 80px;
    padding: 10px 16px;
    background: #080c15;
    border-bottom: 1px solid #141e30;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #2d3f58;
}
.tabla-row {
    display: grid;
    grid-template-columns: 30px 1fr 40px 30px 30px 30px 40px 40px 50px 80px;
    padding: 10px 16px;
    border-bottom: 1px solid #0c1220;
    align-items: center;
    transition: background 0.15s;
}
.tabla-row:last-child { border-bottom: none; }
.tabla-row:hover { background: #0d1626; }
.t-pos {
    font-family: 'Bebas Neue', cursive;
    font-size: 16px;
    color: #3d5270;
}
.t-pos.top { color: #e63946; }
.t-team {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #c8d0e0;
}
.t-num {
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
    color: #64748b;
    text-align: center;
}
.t-pts {
    font-family: 'Bebas Neue', cursive;
    font-size: 20px;
    color: #e63946;
    text-align: right;
}
.t-efec {
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    color: #94a3b8;
    text-align: right;
}
.streamlit-expanderHeader {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: #3d5270 !important;
    background: #080c15 !important;
    border: 1px solid #111927 !important;
    border-radius: 8px !important;
}
hr { border-color: #111927 !important; margin: 24px 0 !important; }
</style>
<script>
(function() {
    var style = document.querySelector('style[data-lpf]');
    if (!style) return;
    document.head.appendChild(style);
})();
</script>
"""

# Inyeccion via components.html con height=0 para no ocupar espacio visual.
# Es el metodo mas robusto: el CSS se inserta en un iframe y luego
# se eleva al documento padre via postMessage (Streamlit lo permite).
# El truco real es usar st.markdown con la hoja de estilos partida en
# bloques sin caracteres Unicode en comentarios.
components.html(_CSS, height=0, scrolling=False)

# ── Parámetros de Motor (BLOQUEADO) ──────────────────────────────────
W_XG = 0.75
K_SHRINK = 6.0
K_PRIOR  = 4.0
PRIOR_ATK_SCALE = 0.35
PRIOR_DEF_SCALE = 0.25
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.5, 1.0
LAM_MIN, LAM_MAX = 0.25, 4.50
RED, BLUE, GRAY = "#e63946", "#3b82f6", "#64748b"
PLOT = dict(
    font=dict(family="Barlow Condensed", size=13, color="#8fa3be"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=20, t=36, b=10)
)

# ──────────────────────────────────────────────────────────────────────
# PROCESAMIENTO (BLOQUEADO)
# ──────────────────────────────────────────────────────────────────────
def num(v) -> float:
    if isinstance(v, str): v = v.replace('%', '').replace(',', '.').strip()
    try: return float(v)
    except: return 0.0

@st.cache_data(ttl=120, show_spinner=False)
def cargar_excel(ruta: str):
    if not os.path.exists(ruta): return {}
    xl = pd.ExcelFile(ruta, engine="openpyxl")
    res = {}
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE): continue
        df = pd.read_excel(ruta, sheet_name=hoja, header=None)
        partidos, i = [], 0
        while i < len(df):
            c0 = str(df.iloc[i,0]).strip() if pd.notna(df.iloc[i,0]) else ""
            if re.search(r"\s+vs\s+", c0, re.IGNORECASE):
                p = re.split(r"\s+vs\s+", c0, flags=re.IGNORECASE)
                loc, vis, stats, j = p[0].strip(), p[1].strip(), {}, i+1
                while j < len(df):
                    r0 = str(df.iloc[j,0]).strip() if pd.notna(df.iloc[j,0]) else ""
                    if r0=="" or re.search(r"\s+vs\s+", r0, re.IGNORECASE): break
                    if r0.lower() in ("métrica", "metrica") or r0 == loc: j += 1; continue
                    if pd.notna(df.iloc[j,1]): stats[r0] = {"local": num(df.iloc[j,1]), "visitante": num(df.iloc[j,2])}
                    j += 1
                partidos.append({"local": loc, "visitante": vis, "metricas": stats})
                i = j
            else: i += 1
        res[hoja] = partidos
    return res

def construir_df(datos: dict) -> pd.DataFrame:
    filas = []
    for fecha, partidos in datos.items():
        nf = int(re.search(r"\d+", fecha).group())
        for p in partidos:
            tt = p["metricas"].get("Tiros totales", {"local": 0, "visitante": 0})
            oc = p["metricas"].get("Ocasiones claras", {"local": 0, "visitante": 0})
            xg_loc = (oc["local"] * 0.38) + (max(0, tt["local"] - oc["local"]) * 0.05)
            xg_vis = (oc["visitante"] * 0.38) + (max(0, tt["visitante"] - oc["visitante"]) * 0.05)
            p["metricas"]["xG_Estimado"] = {"local": xg_loc, "visitante": xg_vis}
            for met, vals in p["metricas"].items():
                base = {"nFecha": nf, "Métrica": met}
                filas.append({**base, "Equipo": p["local"],    "Rival": p["visitante"], "Condicion": "Local",     "Propio": vals["local"],     "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"],"Rival": p["local"],     "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

@st.cache_data(ttl=120, show_spinner=False)
def calcular_tabla(df: pd.DataFrame, condicion: str = "General") -> pd.DataFrame:
    dr = df[df["Métrica"] == "Resultado"].copy()
    if condicion != "General":
        dr = dr[dr["Condicion"] == condicion]
    if dr.empty:
        return pd.DataFrame()
    equipos = sorted(df["Equipo"].unique())
    rows = []
    for eq in equipos:
        d = dr[dr["Equipo"] == eq]
        pj = len(d)
        if pj == 0:
            rows.append({"Equipo": eq, "PJ": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0, "PTS": 0, "PPJ": 0.0, "EFEC%": 0.0})
            continue
        v = ((d["Propio"] > d["Concedido"])).sum()
        e = ((d["Propio"] == d["Concedido"])).sum()
        d_ = ((d["Propio"] < d["Concedido"])).sum()
        pts = int(v * 3 + e)
        gf = d["Propio"].sum()
        gc = d["Concedido"].sum()
        ppj = pts / pj
        efec = (pts / (pj * 3)) * 100
        rows.append({"Equipo": eq, "PJ": pj, "V": int(v), "E": int(e), "D": int(d_), "GF": gf, "GC": gc, "PTS": pts, "PPJ": ppj, "EFEC%": efec})
    tabla = pd.DataFrame(rows).sort_values(["EFEC%", "PTS", "GF"], ascending=[False, False, False]).reset_index(drop=True)
    tabla["Pos"] = tabla.index + 1
    ppj_mean = tabla["PPJ"].mean()
    if ppj_mean > 0:
        tabla["PPJ_norm"] = tabla["PPJ"] / ppj_mean
    else:
        tabla["PPJ_norm"] = 1.0
    tabla["prior_atk"] = 1.0 + (tabla["PPJ_norm"] - 1.0) * PRIOR_ATK_SCALE
    tabla["prior_def"] = 1.0 - (tabla["PPJ_norm"] - 1.0) * PRIOR_DEF_SCALE
    tabla["prior_atk"] = tabla["prior_atk"].clip(0.5, 2.0)
    tabla["prior_def"] = tabla["prior_def"].clip(0.5, 2.0)
    return tabla.set_index("Equipo")

def _get_prior(tabla: pd.DataFrame, eq: str):
    if tabla is None or eq not in tabla.index:
        return 1.0, 1.0
    return float(tabla.loc[eq, "prior_atk"]), float(tabla.loc[eq, "prior_def"])

# ── Motor Predictivo (BLOQUEADO) ──────────────────────────────────────
def _adjusted_rate(d_spec, metrica, col, max_fecha_torneo, tabla, is_attack):
    df_m = d_spec[d_spec["Métrica"] == metrica]
    if df_m.empty: return np.nan
    fechas = df_m["nFecha"].values
    valores = df_m[col].values
    rivales = df_m["Rival"].values
    valores_ajustados = []
    for v, r in zip(valores, rivales):
        prior_atk_rival, prior_def_rival = _get_prior(tabla, r)
        if is_attack:
            adj = v / prior_def_rival if prior_def_rival > 0 else v
        else:
            adj = v / prior_atk_rival if prior_atk_rival > 0 else v
        valores_ajustados.append(adj)
    w = np.where(fechas >= (max_fecha_torneo - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(valores_ajustados, weights=w))

@st.cache_data(ttl=120, show_spinner=False)
def _league_stats(df):
    dr = df[df["Métrica"] == "Resultado"]
    dx = df[df["Métrica"] == "xG_Estimado"]
    def get_avg(d, cond):
        v = d[d["Condicion"]==cond]["Propio"].mean() if not d.empty else np.nan
        return v if not np.isnan(v) else 1.0
    gh, gv = get_avg(dr, "Local"), get_avg(dr, "Visitante")
    xh, xv = get_avg(dx, "Local"), get_avg(dx, "Visitante")
    if dx.empty:
        rh, rv = gh, gv
    else:
        rh = W_XG * xh + (1-W_XG) * gh
        rv = W_XG * xv + (1-W_XG) * gv
    return {"ref_home": rh, "ref_away": rv, "ref_all": (rh+rv)/2}

def _strength(df, eq, cond, league, max_fecha_torneo: int, tabla: pd.DataFrame):
    d_eq   = df[df["Equipo"] == eq]
    d_spec = d_eq[d_eq["Condicion"] == cond]
    g_atk = _adjusted_rate(d_spec, "Resultado", "Propio", max_fecha_torneo, tabla, is_attack=True)
    x_atk = _adjusted_rate(d_spec, "xG_Estimado", "Propio", max_fecha_torneo, tabla, is_attack=True)
    g_def = _adjusted_rate(d_spec, "Resultado", "Concedido", max_fecha_torneo, tabla, is_attack=False)
    x_def = _adjusted_rate(d_spec, "xG_Estimado", "Concedido", max_fecha_torneo, tabla, is_attack=False)
    n_s = len(d_spec[d_spec["Métrica"] == "Resultado"])
    def combine(g, x):
        if np.isnan(g) and np.isnan(x): return np.nan
        if np.isnan(x): return g
        if np.isnan(g): return x
        return W_XG * x + (1 - W_XG) * g
    atk_val = combine(g_atk, x_atk)
    def_val = combine(g_def, x_def)
    rh, ra = league["ref_home"], league["ref_away"]
    ref_f, ref_a = (rh, ra) if cond == "Local" else (ra, rh)
    atk_obs  = (atk_val / ref_f)  if (not np.isnan(atk_val)  and ref_f  > 0) else np.nan
    def_obs  = (def_val / ref_a)  if (not np.isnan(def_val)  and ref_a  > 0) else np.nan
    prior_atk, prior_def = _get_prior(tabla, eq)
    n = n_s if n_s > 0 else 0
    atk_obs  = atk_obs  if not np.isnan(atk_obs)  else prior_atk
    def_obs  = def_obs  if not np.isnan(def_obs)  else prior_def
    atk_post = (n * atk_obs  + K_PRIOR * prior_atk) / (n + K_PRIOR)
    def_post = (n * def_obs  + K_PRIOR * prior_def)  / (n + K_PRIOR)
    return atk_post, def_post, n

def calcular_lambdas(df, eq_a, eq_b, es_loc, tabla):
    l = _league_stats(df)
    max_fecha_torneo = int(df["nFecha"].max())
    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")
    aa, da, na = _strength(df, eq_a, ca, l, max_fecha_torneo, tabla)
    ab, db, nb = _strength(df, eq_b, cb, l, max_fecha_torneo, tabla)
    la = (l["ref_home"] if ca == "Local" else l["ref_away"]) * aa * db
    lb = (l["ref_home"] if cb == "Local" else l["ref_away"]) * ab * da
    return (round(float(np.clip(la, LAM_MIN, LAM_MAX)), 3),
            round(float(np.clip(lb, LAM_MIN, LAM_MAX)), 3))

def montecarlo(la, lb):
    def _pmf(lam, kmax):
        k = np.arange(kmax + 1)
        return np.exp(k * np.log(max(lam, 1e-9)) - lam -
                      np.array([math.log(math.factorial(x)) for x in k]))
    pa, pb = _pmf(la, MAX_GOALS_MATRIX), _pmf(lb, MAX_GOALS_MATRIX)
    M = np.outer(pa, pb)
    rho = max(DC_RHO, -0.9 / max(la * lb, 0.01))
    M[0,0] = max(M[0,0] * (1 - la * lb * rho), 0.0)
    M[0,1] = max(M[0,1] * (1 + la * rho),       0.0)
    M[1,0] = max(M[1,0] * (1 + lb * rho),        0.0)
    M[1,1] = max(M[1,1] * (1 - rho),             0.0)
    M /= M.sum()
    return {
        "victoria": float(np.tril(M, -1).sum()),
        "empate":   float(np.trace(M)),
        "derrota":  float(np.triu(M, 1).sum()),
        "matrix":   M,
    }

# ── Figuras (actualizadas estéticamente) ─────────────────────────────
def fig_score_matrix(M, ea, eb, n=5):
    sub = M[:n, :n]
    z_text = [[f"{sub[i,j]*100:.1f}%" for j in range(n)] for i in range(n)]
    fig = go.Figure(go.Heatmap(
        z=sub,
        x=[str(j) for j in range(n)],
        y=[str(i) for i in range(n)],
        text=z_text, texttemplate="%{text}",
        colorscale=[[0,"#080c15"],[0.4,"#4a0a10"],[0.7,"#9b1d28"],[1,"#e63946"]],
        showscale=False,
    ))
    fig.update_layout(
        **PLOT, height=340,
        title=dict(text="DISTRIBUCIÓN DE MARCADORES", font=dict(family="Bebas Neue", size=15, color="#3d5270"), x=0.5),
        xaxis=dict(title=dict(text=f"Goles {eb}", font=dict(color="#3d5270", size=11)), gridcolor="#0f1825", linecolor="#0f1825"),
        yaxis=dict(title=dict(text=f"Goles {ea}", font=dict(color="#3d5270", size=11)), autorange="reversed", gridcolor="#0f1825", linecolor="#0f1825"),
    )
    return fig

def fig_radar(df, eq_a, eq_b, cond_a, cond_b):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco",
                         "Goles esperados (xG)", "Pases totales"]
            if m in df["Métrica"].values]
    if not mets: return go.Figure()
    def gv(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General": d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0
    def get_league_max(m):
        return df[df["Métrica"] == m].groupby("Equipo")["Propio"].mean().max()
    va = [gv(eq_a, cond_a, m) for m in mets]
    vb = [gv(eq_b, cond_b, m) for m in mets]
    mx = [max(get_league_max(m), 1e-6) for m in mets]
    text_a = [f"{m}: <b>{v:.1f}</b>" for m, v in zip(mets, va)]
    text_b = [f"{m}: <b>{v:.1f}</b>" for m, v in zip(mets, vb)]
    r_a = [a/m for a, m in zip(va, mx)] + [va[0]/mx[0]]
    r_b = [b/m for b, m in zip(vb, mx)] + [vb[0]/mx[0]]
    theta = mets + [mets[0]]
    txt_a = text_a + [text_a[0]]
    txt_b = text_b + [text_b[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r_a, theta=theta, fill="toself", name=eq_a,
        line=dict(color=RED, width=2),
        fillcolor="rgba(230,57,70,0.12)",
        hoverinfo="text+name", text=txt_a))
    fig.add_trace(go.Scatterpolar(r=r_b, theta=theta, fill="toself", name=eq_b,
        line=dict(color=BLUE, width=2),
        fillcolor="rgba(59,130,246,0.12)",
        hoverinfo="text+name", text=txt_b))
    layout_args = PLOT.copy()
    layout_args.update(
        height=420,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, showticklabels=False, gridcolor="#111927", range=[0, 1], linecolor="#111927"),
            angularaxis=dict(gridcolor="#111927", linecolor="#111927", tickfont=dict(family="Barlow Condensed", size=11, color="#3d5270"))
        ),
        legend=dict(
            font=dict(family="Barlow Condensed", size=12),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#141e30",
            borderwidth=1
        ),
        margin=dict(l=50, r=50, t=36, b=50)
    )
    fig.update_layout(**layout_args)
    return fig

# ──────────────────────────────────────────────────────────────────────
# HELPERS UI
# ──────────────────────────────────────────────────────────────────────
def initials(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2:
        return parts[0][0].upper() + parts[-1][0].upper()
    return name[:2].upper()

def kpi_card(label: str, value: str, sub: str = "", color: str = "red", icon: str = ""):
    cls = {"red": "", "blue": "blue", "gray": "gray", "green": "green"}.get(color, "")
    st.markdown(f"""
    <div class="kpi-card {cls}">
        <div class="icon">{icon}</div>
        <div class="lbl">{label}</div>
        <div class="val">{value}</div>
        <div class="sub-val">{sub}</div>
    </div>""", unsafe_allow_html=True)

def section_title(text: str):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="league-name">⚽ LPF</div>
        <div class="season-badge">TEMPORADA 2026</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-label">📂 Fuente de datos</div>', unsafe_allow_html=True)
    ruta = st.text_input("", "Fecha_x_fecha_lpf.xlsx", label_visibility="collapsed")

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-label">🗂 Módulos</div>', unsafe_allow_html=True)

    nav = st.radio(
        "",
        ["🔮 Predictor", "📊 Rankings", "🔄 Head-to-Head", "📖 Perfil Rival", "🎭 Estilos", "📋 Tabla"],
        label_visibility="collapsed"
    )

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-label">ℹ Sistema</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'Barlow',sans-serif;font-size:11px;color:#2d3f58;line-height:1.7;padding:0 2px;">
        Motor: Poisson + Dixon-Coles<br>
        xG: Sintético (tiros + OC)<br>
        Ajuste: Calidad de rival<br>
        Recencia: Últimas 3 fechas ×1.5
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# CARGA
# ──────────────────────────────────────────────────────────────────────
if not os.path.exists(ruta):
    st.markdown("""
    <div style="text-align:center;padding:80px 40px;">
        <div style="font-family:'Bebas Neue',cursive;font-size:3rem;color:#e63946;letter-spacing:4px;margin-bottom:12px;">⚠ ARCHIVO NO ENCONTRADO</div>
        <div style="font-family:'Barlow',sans-serif;font-size:14px;color:#3d5270;">Verificá la ruta del Excel en el panel lateral.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

datos  = cargar_excel(ruta)
df     = construir_df(datos)
tabla  = calcular_tabla(df, "General")
equipos, metricas = sorted(df["Equipo"].unique()), sorted(df["Métrica"].unique())

# ── Main header ──────────────────────────────────────────────────────
n_fechas = int(df["nFecha"].max()) if not df.empty else 0
n_equipos = len(equipos)

st.markdown(f"""
<div class="main-header">
    <div class="title-block">
        <div class="pre">⚽ Liga Profesional · Argentina</div>
        <h1>Scouting Dashboard</h1>
        <div class="sub">Motor v11.0 · xG Sintético · Ajuste por Rival · Poisson + Dixon-Coles</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Indicadores globales rápidos ─────────────────────────────────────
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Equipos", str(n_equipos), "en competencia", "red", "🏟")
    with c2:
        kpi_card("Fechas jugadas", str(n_fechas), "del torneo actual", "blue", "📅")
    with c3:
        l_stats = _league_stats(df)
        kpi_card("xG local promedio", f"{l_stats['ref_home']:.2f}", "goles esperados por partido", "green", "🎯")
    with c4:
        kpi_card("xG visitante promedio", f"{l_stats['ref_away']:.2f}", "goles esperados por partido", "gray", "🏃")

st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# PREDICTOR
# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor":
    section_title("Predictor de Partidos")

    with st.container():
        c1, c2, c3 = st.columns([5, 5, 3])
        ea  = c1.selectbox("🏠 Equipo Local", equipos)
        eb  = c2.selectbox("✈ Equipo Visitante", equipos, index=min(1, len(equipos)-1))
        with c3:
            st.markdown('<div style="height:26px"></div>', unsafe_allow_html=True)
            loc = st.toggle("Bono Localía", True)

    if st.button("🚀  CALCULAR PREDICCIÓN"):
        la, lb = calcular_lambdas(df, ea, eb, loc, tabla)
        sim    = montecarlo(la, lb)

        pv = sim["victoria"]  * 100
        pe = sim["empate"]    * 100
        pd_ = sim["derrota"] * 100

        # Match Card
        ini_a, ini_b = initials(ea), initials(eb)
        cond_a_txt = "Local" if loc else "Visitante"
        cond_b_txt = "Visitante" if loc else "Local"

        st.markdown(f"""
        <div class="match-card">
            <div class="vs-badge">VS</div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div class="team-block">
                    <div class="team-shield home">{ini_a}</div>
                    <div class="team-name-big">{ea}</div>
                    <div class="team-condition">🏠 {cond_a_txt}</div>
                </div>
                <div style="flex:1"></div>
                <div class="team-block">
                    <div class="team-shield away">{ini_b}</div>
                    <div class="team-name-big">{eb}</div>
                    <div class="team-condition">✈ {cond_b_txt}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Probability bars
        st.markdown(f"""
        <div class="prob-section">
            <div class="prob-row">
                <div class="prob-label">{ea.split()[0]}</div>
                <div class="prob-bar-track">
                    <div class="prob-bar-fill home" style="width:{pv:.1f}%"></div>
                </div>
                <div class="prob-pct home">{pv:.1f}%</div>
            </div>
            <div class="prob-row">
                <div class="prob-label">Empate</div>
                <div class="prob-bar-track">
                    <div class="prob-bar-fill draw" style="width:{pe:.1f}%"></div>
                </div>
                <div class="prob-pct draw">{pe:.1f}%</div>
            </div>
            <div class="prob-row">
                <div class="prob-label">{eb.split()[0]}</div>
                <div class="prob-bar-track">
                    <div class="prob-bar-fill away" style="width:{pd_:.1f}%"></div>
                </div>
                <div class="prob-pct away">{pd_:.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Lambda info strip
        pa_a, pd_a = _get_prior(tabla, ea)
        pa_b, pd_b = _get_prior(tabla, eb)
        pos_a = int(tabla.loc[ea, "Pos"]) if ea in tabla.index else "—"
        pos_b = int(tabla.loc[eb, "Pos"]) if eb in tabla.index else "—"

        st.markdown(f"""
        <div class="lambda-strip">
            <div class="lambda-item">
                <div class="l-key">λ {ea}</div>
                <div class="l-val">{la:.3f}</div>
            </div>
            <div class="lambda-divider"></div>
            <div class="lambda-item">
                <div class="l-key">Posición {ea}</div>
                <div class="l-val">{pos_a}°</div>
            </div>
            <div class="lambda-divider"></div>
            <div class="lambda-item">
                <div class="l-key">Prior ATK {ea}</div>
                <div class="l-val">{pa_a:.2f}</div>
            </div>
            <div class="lambda-divider"></div>
            <div class="lambda-item">
                <div class="l-key">λ {eb}</div>
                <div class="l-val">{lb:.3f}</div>
            </div>
            <div class="lambda-divider"></div>
            <div class="lambda-item">
                <div class="l-key">Posición {eb}</div>
                <div class="l-val">{pos_b}°</div>
            </div>
            <div class="lambda-divider"></div>
            <div class="lambda-item">
                <div class="l-key">Prior ATK {eb}</div>
                <div class="l-val">{pa_b:.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        section_title("Distribución de Marcadores")
        st.plotly_chart(fig_score_matrix(sim["matrix"], ea, eb), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# RANKINGS
# ──────────────────────────────────────────────────────────────────────
elif nav == "📊 Rankings":
    section_title("Rankings — Favor vs Concedido")

    c1, c2, c3 = st.columns(3)
    m_sel    = c1.selectbox("Métrica", metricas)
    cond_sel = c2.radio("Condición", ["General", "Local", "Visitante"], horizontal=True)
    tipo_sel = c3.radio("Enfoque", ["A Favor", "En Contra"], horizontal=True)

    col_data = "Propio" if "A Favor" in tipo_sel else "Concedido"
    mask_cond = (df["Condicion"] == cond_sel) if cond_sel != "General" else df.index.notna()
    res = (df[mask_cond & (df["Métrica"] == m_sel)]
           .groupby("Equipo")[col_data].mean()
           .sort_values(ascending=False).reset_index())

    if not res.empty:
        max_val = res[col_data].max()
        bar_color = RED if col_data == "Propio" else GRAY

        # Custom HTML ranking list
        rows_html = ""
        for i, row in res.iterrows():
            pct = (row[col_data] / max_val * 100) if max_val > 0 else 0
            rows_html += f"""
            <div class="rank-row">
                <div class="rank-pos">{i+1}</div>
                <div class="rank-name">{row['Equipo']}</div>
                <div class="rank-bar-track">
                    <div class="rank-bar-fill" style="width:{pct:.1f}%;background:{'linear-gradient(90deg,#e63946,#f87171)' if col_data=='Propio' else 'linear-gradient(90deg,#64748b,#94a3b8)'}"></div>
                </div>
                <div class="rank-val" style="color:{'#e63946' if col_data=='Propio' else '#94a3b8'}">{row[col_data]:.2f}</div>
            </div>"""

        st.markdown(f"""
        <div style="background:#0b1120;border:1px solid #141e30;border-radius:12px;padding:20px 24px;margin-top:8px;">
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;letter-spacing:3px;
                        text-transform:uppercase;color:#2d3f58;margin-bottom:14px;">
                {m_sel} · {tipo_sel} · {cond_sel}
            </div>
            {rows_html}
        </div>""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# HEAD-TO-HEAD
# ──────────────────────────────────────────────────────────────────────
elif nav == "🔄 Head-to-Head":
    section_title("Comparativo Head-to-Head")

    with st.container():
        c1, c2 = st.columns(2)
        ea = c1.selectbox("Equipo A", equipos)
        eb = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1))

    with st.container():
        c3, c4 = st.columns(2)
        cond_a = c3.radio(f"Condición {ea}", ["General", "Local", "Visitante"], horizontal=True, key="cond_a")
        cond_b = c4.radio(f"Condición {eb}", ["General", "Local", "Visitante"], horizontal=True, key="cond_b")

    t1, t2 = st.tabs(["🕸 Radar Comparativo", "📊 Datos Estadísticos"])

    with t1:
        ini_a, ini_b = initials(ea), initials(eb)
        lc1, lc2, lc3 = st.columns([2, 6, 2])
        with lc1:
            st.markdown(f"""
            <div style="display:flex;flex-direction:column;align-items:center;gap:8px;padding-top:40px;">
                <div class="team-shield home" style="width:52px;height:52px;font-size:18px;">{ini_a}</div>
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;
                            letter-spacing:1px;text-transform:uppercase;color:#e63946;text-align:center;">{ea}</div>
                <div style="font-family:'Barlow',sans-serif;font-size:10px;color:#3d5270;">{cond_a}</div>
            </div>""", unsafe_allow_html=True)
        with lc2:
            st.plotly_chart(fig_radar(df, ea, eb, cond_a, cond_b), use_container_width=True)
        with lc3:
            st.markdown(f"""
            <div style="display:flex;flex-direction:column;align-items:center;gap:8px;padding-top:40px;">
                <div class="team-shield away" style="width:52px;height:52px;font-size:18px;">{ini_b}</div>
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;
                            letter-spacing:1px;text-transform:uppercase;color:#3b82f6;text-align:center;">{eb}</div>
                <div style="font-family:'Barlow',sans-serif;font-size:10px;color:#3d5270;">{cond_b}</div>
            </div>""", unsafe_allow_html=True)

    with t2:
        df_a = df[df["Equipo"] == ea]
        if cond_a != "General": df_a = df_a[df_a["Condicion"] == cond_a]
        df_b = df[df["Equipo"] == eb]
        if cond_b != "General": df_b = df_b[df_b["Condicion"] == cond_b]

        s1 = df_a.groupby("Métrica")[["Propio","Concedido"]].mean().round(2)
        s2 = df_b.groupby("Métrica")[["Propio","Concedido"]].mean().round(2)

        h2h_df = pd.DataFrame({
            f"{ea} ({cond_a[:3]}) — Favor": s1["Propio"],
            f"{ea} ({cond_a[:3]}) — Contra": s1["Concedido"],
            f"{eb} ({cond_b[:3]}) — Favor": s2["Propio"],
            f"{eb} ({cond_b[:3]}) — Contra": s2["Concedido"]
        }).dropna()

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        st.dataframe(
            h2h_df.style
                .background_gradient(subset=[f"{ea} ({cond_a[:3]}) — Favor"], cmap="Reds")
                .background_gradient(subset=[f"{eb} ({cond_b[:3]}) — Favor"], cmap="Blues")
                .format("{:.2f}"),
            use_container_width=True,
            height=420
        )

# ──────────────────────────────────────────────────────────────────────
# PERFIL RIVAL
# ──────────────────────────────────────────────────────────────────────
elif nav == "📖 Perfil Rival":
    section_title("Perfil de Desempeño por Rival")

    c1, c2 = st.columns(2)
    eq_p  = c1.selectbox("Equipo", equipos)
    met_p = c2.selectbox("Métrica", metricas)

    d_eq = df[(df["Equipo"] == eq_p) & (df["Métrica"] == met_p)].sort_values("nFecha")

    if not d_eq.empty:
        # KPI summary bar
        avg_favor   = d_eq["Propio"].mean()
        avg_contra  = d_eq["Concedido"].mean()
        max_favor   = d_eq["Propio"].max()

        ck1, ck2, ck3 = st.columns(3)
        with ck1: kpi_card("Promedio a favor", f"{avg_favor:.2f}", f"en {len(d_eq)} partidos", "red", "📈")
        with ck2: kpi_card("Promedio en contra", f"{avg_contra:.2f}", f"en {len(d_eq)} partidos", "gray", "📉")
        with ck3: kpi_card("Mejor marca", f"{max_favor:.2f}", "máximo registrado", "green", "⭐")

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        fig = go.Figure([
            go.Bar(x=d_eq["Rival"], y=d_eq["Propio"],
                   name="A Favor", marker_color=RED, opacity=0.9,
                   marker=dict(line=dict(width=0))),
            go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"],
                   name="En Contra", marker_color="#1c2a3e", opacity=0.9,
                   marker=dict(line=dict(width=0))),
        ])
        fig.update_layout(
            **PLOT, barmode="group", height=380,
            xaxis=dict(gridcolor="#0f1825", linecolor="#0f1825", tickangle=-30),
            yaxis=dict(gridcolor="#111927", linecolor="#111927"),
            legend=dict(font=dict(family="Barlow Condensed", size=12), bgcolor="rgba(0,0,0,0)"),
            title=dict(text=f"{eq_p.upper()} · {met_p}", font=dict(family="Bebas Neue", size=15, color="#3d5270"), x=0)
        )
        st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# ESTILOS
# ──────────────────────────────────────────────────────────────────────
elif nav == "🎭 Estilos":
    section_title("Mapa de Estilos de Juego")

    mo = "Goles esperados (xG)" if "Goles esperados (xG)" in metricas else "Tiros totales"
    if "Posesión de balón" in metricas:
        df_e = pd.DataFrame({
            "P": df[df["Métrica"] == "Posesión de balón"].groupby("Equipo")["Propio"].mean(),
            "O": df[df["Métrica"] == mo].groupby("Equipo")["Propio"].mean(),
        }).dropna()
        mp, mo_m = df_e["P"].mean(), df_e["O"].mean()

        # Cuadrant labels
        fig = go.Figure()

        # Cuadrant BG zones (subtle)
        for xx, yy, lbl, col in [
            ([mp, 100, 100, mp, mp], [mo_m, mo_m, df_e["O"].max()*1.1, df_e["O"].max()*1.1, mo_m], "Dominio Efectivo", "rgba(230,57,70,0.04)"),
            ([df_e["P"].min()*0.9, mp, mp, df_e["P"].min()*0.9], [mo_m, mo_m, df_e["O"].max()*1.1, df_e["O"].max()*1.1], "Directo", "rgba(59,130,246,0.04)"),
            ([mp, 100, 100, mp], [df_e["O"].min()*0.9, df_e["O"].min()*0.9, mo_m, mo_m], "Posesión Estéril", "rgba(100,116,139,0.04)"),
            ([df_e["P"].min()*0.9, mp, mp, df_e["P"].min()*0.9], [df_e["O"].min()*0.9, df_e["O"].min()*0.9, mo_m, mo_m], "Defensivo", "rgba(100,116,139,0.04)"),
        ]:
            fig.add_trace(go.Scatter(x=xx, y=yy, fill="toself", fillcolor=col,
                                     line=dict(width=0), showlegend=False, hoverinfo="skip"))

        fig.add_trace(go.Scatter(
            x=df_e["P"], y=df_e["O"],
            mode="markers+text",
            text=df_e.index,
            textposition="top center",
            textfont=dict(family="Barlow Condensed", size=11, color="#8fa3be"),
            marker=dict(size=14, color=RED, line=dict(width=2, color="#fff"), opacity=0.9),
            hovertemplate="<b>%{text}</b><br>Posesión: %{x:.1f}%<br>Ataque: %{y:.2f}<extra></extra>",
        ))
        fig.add_vline(x=mp,   line=dict(color="#1c2a3e", dash="dot", width=1))
        fig.add_hline(y=mo_m, line=dict(color="#1c2a3e", dash="dot", width=1))
        fig.update_layout(
            **PLOT, height=580,
            xaxis=dict(title="Posesión de Balón (%)", gridcolor="#0f1825", linecolor="#0f1825", tickfont=dict(family="Barlow Condensed")),
            yaxis=dict(title=f"Índice de Ataque ({mo})", gridcolor="#111927", linecolor="#111927", tickfont=dict(family="Barlow Condensed")),
        )

        # Quadrant legend
        qc1, qc2, qc3, qc4 = st.columns(4)
        for col_obj, lbl, sub, color in [
            (qc1, "Dominio Efectivo", "Alta posesión + Ataque", "red"),
            (qc2, "Estilo Directo", "Baja posesión + Ataque", "blue"),
            (qc3, "Posesión Estéril", "Alta posesión + Defensivo", "gray"),
            (qc4, "Defensivo", "Baja posesión + Defensivo", "gray"),
        ]:
            with col_obj:
                kpi_card(lbl, "", sub, color)

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de Posesión de balón disponibles.")

# ──────────────────────────────────────────────────────────────────────
# TABLA
# ──────────────────────────────────────────────────────────────────────
elif nav == "📋 Tabla":
    section_title("Tabla de Posiciones")

    vista_tabla = st.radio("Vista:", ["General", "Local", "Visitante"], horizontal=True)
    t_dinamica = calcular_tabla(df, vista_tabla)

    if not t_dinamica.empty:
        t_show = t_dinamica.reset_index()

        # Summary KPIs
        lider = t_show.iloc[0]
        mejor_atk = t_show.loc[t_show["GF"].idxmax()]
        mejor_def = t_show.loc[t_show["GC"].idxmin()]

        ck1, ck2, ck3 = st.columns(3)
        with ck1: kpi_card("Líder", lider["Equipo"].split()[0], f"{lider['PTS']} pts · {lider['EFEC%']:.0f}% efec.", "red", "🥇")
        with ck2: kpi_card("Mejor ataque", mejor_atk["Equipo"].split()[0], f"{int(mejor_atk['GF'])} goles marcados", "green", "⚽")
        with ck3: kpi_card("Mejor defensa", mejor_def["Equipo"].split()[0], f"{int(mejor_def['GC'])} goles recibidos", "blue", "🛡")

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

        # Custom HTML table
        header_html = """
        <div class="tabla-pos">
        <div class="tabla-header">
            <div>POS</div><div>EQUIPO</div><div style="text-align:center">PJ</div>
            <div style="text-align:center">V</div><div style="text-align:center">E</div>
            <div style="text-align:center">D</div><div style="text-align:center">GF</div>
            <div style="text-align:center">GC</div><div style="text-align:right">PTS</div>
            <div style="text-align:right">EFEC%</div>
        </div>"""

        rows_html = ""
        for _, row in t_show.iterrows():
            pos_cls = "top" if row["Pos"] <= 4 else ""
            rows_html += f"""
            <div class="tabla-row">
                <div class="t-pos {pos_cls}">{int(row['Pos'])}</div>
                <div class="t-team">{row['Equipo']}</div>
                <div class="t-num">{int(row['PJ'])}</div>
                <div class="t-num" style="color:#22c55e">{int(row['V'])}</div>
                <div class="t-num">{int(row['E'])}</div>
                <div class="t-num" style="color:#3b82f6">{int(row['D'])}</div>
                <div class="t-num">{int(row['GF'])}</div>
                <div class="t-num">{int(row['GC'])}</div>
                <div class="t-pts">{int(row['PTS'])}</div>
                <div class="t-efec">{row['EFEC%']:.1f}%</div>
            </div>"""

        st.markdown(header_html + rows_html + "</div>", unsafe_allow_html=True)

        # Prior table in expander
        with st.expander("🔬 Ver coeficientes del modelo"):
            prior_df = t_show[["Pos","Equipo","PPJ","prior_atk","prior_def"]].copy()
            prior_df.columns = ["Pos","Equipo","PPJ","Prior Atk","Prior Def"]
            prior_df["PPJ"]       = prior_df["PPJ"].round(3)
            prior_df["Prior Atk"] = prior_df["Prior Atk"].round(3)
            prior_df["Prior Def"] = prior_df["Prior Def"].round(3)
            st.dataframe(prior_df.style.format({"PPJ":"{:.3f}","Prior Atk":"{:.3f}","Prior Def":"{:.3f}"}),
                         use_container_width=True, hide_index=True)
            st.markdown("""
            <div style="font-family:'Barlow',sans-serif;font-size:11px;color:#2d3f58;margin-top:8px;line-height:1.7;">
                <b style="color:#3d5270">Prior Atk</b> — Potencial ofensivo relativo a la media de la liga.<br>
                <b style="color:#3d5270">Prior Def</b> — Solidez defensiva relativa a la media de la liga.<br>
                Valores &gt;1.0 indican rendimiento sobre la media del torneo.
            </div>""", unsafe_allow_html=True)
