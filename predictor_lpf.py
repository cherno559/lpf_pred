"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard
────────────────────────────────────────────────
Lee el Excel generado por sofascore_lpf_generales.py y construye:
  · Predictor de partidos (modelo Dixon-Coles + xG con split Local/Visitante)
  · Tablas comparativas por métrica (propias y concedidas)
  · Perfil por Rival

Instalación:
    pip install streamlit plotly pandas openpyxl numpy

Uso:
    streamlit run predictor_lpf.py
"""

import re, os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LPF 2026 · Scouting",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #080d18; color: #dde3ee; }
section[data-testid="stSidebar"] { background: #0c1220 !important; border-right: 1px solid #1c2a40; }
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: #8899aa !important; font-size:13px !important; }
h1 { font-family:'Bebas Neue',cursive !important; font-size:2.6rem !important; color:#e63946 !important; letter-spacing:3px; margin-bottom:0; }
h2 { font-family:'Bebas Neue',cursive !important; font-size:1.6rem !important; color:#dde3ee !important; letter-spacing:2px; }
h3 { font-family:'Rajdhani',sans-serif !important; font-size:1.1rem !important; color:#8899aa !important; font-weight:700; }
.section-title { font-family:'Bebas Neue',cursive; font-size:1.3rem; letter-spacing:3px; color:#e63946; border-bottom:1px solid #1c2a40; padding-bottom:8px; margin:28px 0 18px; text-transform:uppercase; }
.kpi { background:linear-gradient(135deg,#0f1829,#162035); border:1px solid #1c2a40; border-left:4px solid #e63946; border-radius:10px; padding:16px 18px; text-align:center; }
.kpi.draw { border-left-color:#64748b; }
.kpi.loss { border-left-color:#3b82f6; }
.kpi.info { border-left-color:#22c55e; }
.kpi .lbl { font-family:'Rajdhani'; font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:#64748b; }
.kpi .val { font-family:'Bebas Neue'; font-size:38px; color:#e63946; line-height:1.05; }
.kpi.draw .val { color:#94a3b8; }
.kpi.loss .val { color:#60a5fa; }
.kpi.info .val { color:#4ade80; }
.badge { display:inline-block; padding:3px 14px; border-radius:20px; font-family:'Rajdhani'; font-size:12px; font-weight:700; background:#0d2b1a; color:#4ade80; margin-bottom:14px; }
.stTabs [data-baseweb="tab-list"] { background:#0f1829; border-radius:10px; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"] { font-family:'Rajdhani'; font-weight:700; font-size:14px; color:#64748b !important; border-radius:7px; padding:6px 16px; }
.stTabs [aria-selected="true"] { background:#e63946 !important; color:#fff !important; }
.stButton>button { font-family:'Bebas Neue'; font-size:17px; letter-spacing:2px; background:linear-gradient(135deg,#e63946,#b91c2c); color:#fff; border:none; border-radius:9px; padding:13px; width:100%; transition:all .2s; }
.stButton>button:hover { transform:translateY(-1px); box-shadow:0 6px 20px rgba(230,57,70,.45); }
.stSelectbox>div>div, .stMultiSelect>div>div, .stTextInput>div>div { background:#0f1829 !important; border:1px solid #1c2a40 !important; color:#dde3ee !important; border-radius:8px !important; }
.stDataFrame { border-radius:10px !important; }
.note { background:#0f1829; border:1px solid #1c2a40; border-radius:8px; padding:10px 14px; font-size:12px; color:#64748b; margin-top:8px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# CONSTANTES
# ──────────────────────────────────────────────────────────────────────
MONTECARLO_N = 15_000
RED, BLUE, GRAY = "#e63946", "#3b82f6", "#64748b"

PLOT = dict(
    font=dict(family="Rajdhani", size=13, color="#dde3ee"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=20, t=36, b=10),
)
GRID = dict(showgrid=True, gridcolor="#1c2a40", zeroline=False)
NO_GRID = dict(showgrid=False, zeroline=False)

METRICAS_MENOS_ES_MEJOR = {"Faltas", "Tarjetas amarillas", "Tarjetas rojas", "Fueras de juego"}

# ──────────────────────────────────────────────────────────────────────
# PARSEO DEL EXCEL
# ──────────────────────────────────────────────────────────────────────
def num(v) -> float:
    if isinstance(v, str):
        v = v.replace('%', '').replace(',', '.').strip()
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0

@st.cache_data(ttl=120, show_spinner=False)
def cargar_excel(ruta: str) -> dict[str, list[dict]]:
    try:
        xl = pd.ExcelFile(ruta, engine="openpyxl")
    except Exception as e:
        st.error(f"No se pudo abrir el Excel: {e}")
        return {}

    resultado = {}
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE):
            continue
        df = pd.read_excel(ruta, sheet_name=hoja, header=None, engine="openpyxl")
        partidos = _parsear_hoja(df)
        if partidos:
            resultado[hoja] = partidos
    return resultado

def _parsear_hoja(df: pd.DataFrame) -> list[dict]:
    partidos, i = [], 0
    while i < len(df):
        c0 = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""
        if re.search(r"\s+vs\s+", c0, re.IGNORECASE):
            partes = re.split(r"\s+vs\s+", c0, flags=re.IGNORECASE)
            if len(partes) == 2:
                local, visitante = partes[0].strip().lstrip(), partes[1].strip()
                stats: dict[str, dict] = {}
                j = i + 1
                while j < len(df):
                    r0 = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                    r1 = df.iloc[j, 1] if df.shape[1] > 1 else None
                    r2 = df.iloc[j, 2] if df.shape[1] > 2 else None
                    if r0 == "" and (pd.isna(r1) if r1 is not None else True): break
                    if re.search(r"\s+vs\s+", r0, re.IGNORECASE): break
                    if r0.lower() in ("métrica", "metrica") or r0 == local:
                        j += 1
                        continue
                    if pd.notna(r1):
                        stats[r0] = {"local": num(r1), "visitante": num(r2) if pd.notna(r2) else 0}
                    j += 1
                if stats:
                    partidos.append({"local": local, "visitante": visitante, "metricas": stats})
                i = j
            else: i += 1
        else: i += 1
    return partidos

def construir_df(datos: dict) -> pd.DataFrame:
    filas = []
    for fecha, partidos in datos.items():
        nf = int(re.search(r"\d+", fecha).group())
        for p in partidos:
            loc, vis = p["local"], p["visitante"]
            for met, vals in p["metricas"].items():
                filas.append({
                    "Fecha": fecha, "nFecha": nf, "Partido": f"{loc} vs {vis}",
                    "Equipo": loc, "Rival": vis, "Condicion": "Local",
                    "Métrica": met, "Propio": vals["local"], "Concedido": vals["visitante"],
                })
                filas.append({
                    "Fecha": fecha, "nFecha": nf, "Partido": f"{loc} vs {vis}",
                    "Equipo": vis, "Rival": loc, "Condicion": "Visitante",
                    "Métrica": met, "Propio": vals["visitante"], "Concedido": vals["local"],
                })
    return pd.DataFrame(filas)

def prom_equipo(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["Equipo", "Métrica"])[["Propio", "Concedido"]].mean().round(2).reset_index()

def prom_equipo_cond(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["Equipo", "Métrica", "Condicion"])[["Propio", "Concedido"]].mean().round(2).reset_index()

def ranking(df: pd.DataFrame, metrica: str, columna="Propio", ascendente=False) -> pd.DataFrame:
    df_m = df[df["Métrica"] == metrica].copy()
    return df_m.groupby("Equipo")[columna].agg(Promedio="mean", Total="sum", Partidos="count").reset_index().round(2).sort_values("Promedio", ascending=ascendente)

# ──────────────────────────────────────────────────────────────────────
# PREDICTOR ESTRATIFICADO (LOCAL/VISITANTE)
# ──────────────────────────────────────────────────────────────────────
def calcular_lambdas(df: pd.DataFrame, eq_a: str, eq_b: str, a_es_local: bool):
    df_r = df[df["Métrica"] == "Resultado"].copy()
    if df_r.empty: return 1.3, 0.9

    agg = df_r.groupby(["Equipo", "Condicion"]).agg(
        GF=("Propio", "sum"), GC=("Concedido", "sum"), PJ=("Propio", "count")
    ).reset_index()

    media_gf_local = agg[agg["Condicion"] == "Local"]["GF"].sum() / max(agg[agg["Condicion"] == "Local"]["PJ"].sum(), 1)
    media_gf_vis = agg[agg["Condicion"] == "Visitante"]["GF"].sum() / max(agg[agg["Condicion"] == "Visitante"]["PJ"].sum(), 1)

    def stats(eq, condicion):
        row = agg[(agg["Equipo"] == eq) & (agg["Condicion"] == condicion)]
        if row.empty:
            return (media_gf_local if condicion == "Local" else media_gf_vis), (media_gf_vis if condicion == "Local" else media_gf_local), 1
        r = row.iloc[0]
        return r["GF"] / max(r["PJ"], 1), r["GC"] / max(r["PJ"], 1), r["PJ"]

    if a_es_local:
        gf_a_loc, gc_a_loc, _ = stats(eq_a, "Local")
        gf_b_vis, gc_b_vis, _ = stats(eq_b, "Visitante")
        fa_a = gf_a_loc / media_gf_local
        fd_b = gc_b_vis / media_gf_local
        fa_b = gf_b_vis / media_gf_vis
        fd_a = gc_a_loc / media_gf_vis
        lam_a = fa_a * fd_b * media_gf_local
        lam_b = fa_b * fd_a * media_gf_vis
    else:
        gf_a_vis, gc_a_vis, _ = stats(eq_a, "Visitante")
        gf_b_loc, gc_b_loc, _ = stats(eq_b, "Local")
        fa_a = gf_a_vis / media_gf_vis
        fd_b = gc_b_loc / media_gf_vis
        fa_b = gf_b_loc / media_gf_local
        fd_a = gc_a_vis / media_gf_local
        lam_a = fa_a * fd_b * media_gf_vis
        lam_b = fa_b * fd_a * media_gf_local

    df_xg = df[df["Métrica"] == "Goles esperados (xG)"]
    if not df_xg.empty:
        cond_a = "Local" if a_es_local else "Visitante"
        cond_b = "Visitante" if a_es_local else "Local"
        xg_media_a = df_xg[df_xg["Condicion"] == cond_a]["Propio"].mean()
        xg_media_b = df_xg[df_xg["Condicion"] == cond_b]["Propio"].mean()
        xg_a = df_xg[(df_xg["Equipo"] == eq_a) & (df_xg["Condicion"] == cond_a)]["Propio"].mean()
        xg_b = df_xg[(df_xg["Equipo"] == eq_b) & (df_xg["Condicion"] == cond_b)]["Propio"].mean()
        if not np.isnan(xg_a) and xg_media_a > 0:
            esperado_a = (xg_a / xg_media_a) * (media_gf_local if a_es_local else media_gf_vis)
            lam_a = (lam_a * 0.55) + (esperado_a * 0.45)
        if not np.isnan(xg_b) and xg_media_b > 0:
            esperado_b = (xg_b / xg_media_b) * (media_gf_vis if a_es_local else media_gf_local)
            lam_b = (lam_b * 0.55) + (esperado_b * 0.45)

    return round(float(np.clip(lam_a, 0.15, 5.0)), 3), round(float(np.clip(lam_b, 0.15, 5.0)), 3)

def montecarlo(lam_a, lam_b) -> dict:
    rng = np.random.default_rng(42)
    ga = rng.poisson(lam_a, MONTECARLO_N)
    gb = rng.poisson(lam_b, MONTECARLO_N)
    res = [{"A": r, "B": v, "prob": float(np.mean((ga == r) & (gb == v)))} for r in range(8) for v in range(8)]
    return {
        "victoria": float(np.mean(ga > gb)),
        "empate": float(np.mean(ga == gb)),
        "derrota": float(np.mean(ga < gb)),
        "df": pd.DataFrame(res),
        "lam_a": lam_a, "lam_b": lam_b,
    }

# ──────────────────────────────────────────────────────────────────────
# GRÁFICOS
# ──────────────────────────────────────────────────────────────────────
def fig_probs(sim, na, nb):
    vals = [sim["victoria"], sim["empate"], sim["derrota"]]
    etiq = [f"Victoria {na}", "Empate", f"Victoria {nb}"]
    fig = go.Figure(go.Bar(
        x=[v*100 for v in vals], y=etiq, orientation="h",
        marker_color=[RED, GRAY, BLUE], text=[f"{v*100:.1f}%" for v in vals],
        textposition="outside", textfont=dict(size=15, family="Rajdhani")
    ))
    fig.update_layout(**PLOT, height=200, xaxis=dict(**GRID, range=[0, 105], ticksuffix="%"), yaxis=dict(**NO_GRID, tickfont=dict(size=14, family="Rajdhani")), showlegend=False)
    return fig

def fig_marcadores(sim, na, nb):
    df = sim["df"].copy()
    df["label"] = na + " " + df["A"].astype(str) + "–" + df["B"].astype(str) + " " + nb
    top = df.nlargest(8, "prob").iloc[::-1]
    fig = go.Figure(go.Bar(
        x=top["prob"]*100, y=top["label"], orientation="h", marker_color=RED,
        text=(top["prob"]*100).map(lambda x: f"{x:.1f}%"), textposition="auto",
        textfont=dict(color="white", size=14, family="Rajdhani")
    ))
    fig.update_layout(**PLOT, height=340, xaxis=dict(**GRID, ticksuffix="%"), yaxis=dict(**NO_GRID, tickfont=dict(size=13, family="Rajdhani")))
    return fig

def fig_radar(df: pd.DataFrame, eq_a: str, eq_b: str, cond_a: str = "General", cond_b: str = "General"):
    mets = ["Posesión de balón", "Tiros totales", "Tiros al arco", "Pases totales", "Goles esperados (xG)", "Córners", "Quites", "Intercepciones"]
    mets = [m for m in mets if m in df["Métrica"].values]
    prom_gen = prom_equipo(df)
    prom_cnd = prom_equipo_cond(df)

    def get(eq, cond, m):
        if cond == "General":
            v = prom_gen[(prom_gen["Equipo"] == eq) & (prom_gen["Métrica"] == m)]["Propio"]
        else:
            v = prom_cnd[(prom_cnd["Equipo"] == eq) & (prom_cnd["Condicion"] == cond) & (prom_cnd["Métrica"] == m)]["Propio"]
        return float(v.iloc[0]) if not v.empty else 0

    va = [get(eq_a, cond_a, m) for m in mets]
    vb = [get(eq_b, cond_b, m) for m in mets]
    mx = [max(a, b, 0.001) for a, b in zip(va, vb)]
    van = [a/m for a, m in zip(va, mx)]
    vbn = [b/m for b, m in zip(vb, mx)]

    def hex_to_rgba(hex_code, alpha):
        hex_code = hex_code.lstrip('#')
        r, g, b = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"

    fig = go.Figure()
    name_a = f"{eq_a} ({cond_a})" if cond_a != "General" else eq_a
    name_b = f"{eq_b} ({cond_b})" if cond_b != "General" else eq_b
    for vals, name, col in [(van, name_a, RED), (vbn, name_b, BLUE)]:
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=mets + [mets[0]],
            fill="toself", name=name, line=dict(color=col, width=2), fillcolor=hex_to_rgba(col, 0.2)
        ))
    fig.update_layout(**PLOT, height=400, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, range=[0, 1], gridcolor="#1c2a40", tickfont=dict(size=9)), angularaxis=dict(gridcolor="#1c2a40", tickfont=dict(size=11, family="Rajdhani"))), legend=dict(font=dict(family="Rajdhani", size=13)))
    return fig

def fig_bar_ranking(df_r: pd.DataFrame, titulo: str, top_n=16, asc=False):
    df = df_r.head(top_n).iloc[::-1]
    if df.empty: return go.Figure()
    colores = [RED if i == len(df)-1 else "#1c2a40" for i in range(len(df))]
    fig = go.Figure(go.Bar(
        x=df["Promedio"], y=df["Equipo"], orientation="h", marker_color=colores,
        text=df["Promedio"].map(lambda x: f"{x:.2f}"), textposition="outside",
        textfont=dict(size=12, family="Rajdhani")
    ))
    fig.update_layout(**PLOT, height=max(320, top_n * 26), title=dict(text=titulo, font=dict(family="Bebas Neue", size=20), x=0), xaxis=dict(**GRID), yaxis=dict(**NO_GRID, tickfont=dict(size=12, family="Rajdhani")))
    return fig

# ──────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽  LPF 2026")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    ruta = st.text_input("📂 Ruta del Excel", value="Fecha_x_fecha_lpf.xlsx")
    st.markdown("---")
    nav = st.radio("", ["🔮  Predictor", "📊  Rankings", "🔄  Head-to-Head", "📖  Perfil por Rival"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown('<p style="font-size:11px;color:#334155;text-align:center;">Fuente: SofaScore API<br>Liga Profesional 2026</p>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# CARGA Y HEADER
# ──────────────────────────────────────────────────────────────────────
if not os.path.exists(ruta):
    st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)
    st.warning(f"**Archivo no encontrado:** `{ruta}`\n\nCorré primero el scraper para generar el Excel.")
    st.stop()

with st.spinner("Cargando datos…"):
    datos = cargar_excel(ruta)

if not datos:
    st.error("El Excel no tiene hojas con el formato esperado (`Fecha X`).")
    st.stop()

df = construir_df(datos)
equipos   = sorted(df["Equipo"].unique())
metricas  = sorted(df["Métrica"].unique())
fechas    = sorted(datos.keys(), key=lambda x: int(re.search(r"\d+", x).group()))
n_partidos = df[df["Métrica"] == "Resultado"]["Partido"].nunique()

st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)
st.markdown(f'<div class="badge">✅ {len(fechas)} fecha(s) · {len(equipos)} equipos · {n_partidos} partidos</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# VISTAS
# ──────────────────────────────────────────────────────────────────────
if nav == "🔮  Predictor":
    st.markdown('<div class="section-title">🔮 Predictor de Partidos</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    eq_a = c1.selectbox("Equipo A", equipos)
    eq_b = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1))
    cond = c3.radio("Condición A", ["Local 🏠", "Visitante ✈️"])
    es_local = cond == "Local 🏠"

    if eq_a == eq_b:
        st.info("Seleccioná dos equipos diferentes.")
    else:
        if st.button("🚀  SIMULAR PARTIDO", use_container_width=True):
            with st.spinner("Calculando modelo estratificado Local/Visitante…"):
                lam_a, lam_b = calcular_lambdas(df, eq_a, eq_b, es_local)
                sim = montecarlo(lam_a, lam_b)
            nombre_a = eq_a + (" 🏠" if es_local else " ✈️")
            nombre_b = eq_b + (" ✈️" if es_local else " 🏠")
            st.markdown(f"### {nombre_a}  vs  {nombre_b}")
            k1, k2, k3, k4, k5 = st.columns(5)
            for col, lbl, val, cls in [(k1, f"Victoria {eq_a[:10]}", f"{sim['victoria']*100:.1f}%", ""), (k2, "Empate", f"{sim['empate']*100:.1f}%", "draw"), (k3, f"Victoria {eq_b[:10]}", f"{sim['derrota']*100:.1f}%", "loss"), (k4, f"λ {eq_a[:10]}", f"{lam_a:.2f}", "info"), (k5, f"λ {eq_b[:10]}", f"{lam_b:.2f}", "info")]:
                col.markdown(f'<div class="kpi {cls}"><div class="lbl">{lbl}</div><div class="val">{val}</div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            t1, t2, t3 = st.tabs(["📊 Probabilidades", "🎯 Marcadores exactos", "🕸️ Radar H2H"])
            with t1:
                st.plotly_chart(fig_probs(sim, eq_a, eq_b), use_container_width=True)
                st.markdown('<div class="note">λ = goles esperados. El modelo cruza el desempeño específico de A en su condición vs el desempeño específico de B en su condición.</div>', unsafe_allow_html=True)
            with t2: st.plotly_chart(fig_marcadores(sim, eq_a, eq_b), use_container_width=True)
            with t3:
                cond_str_a = "Local" if es_local else "Visitante"
                cond_str_b = "Visitante" if es_local else "Local"
                st.plotly_chart(fig_radar(df, eq_a, eq_b, cond_str_a, cond_str_b), use_container_width=True)
                st.caption(f"Radar cruzando {eq_a} como {cond_str_a} vs {eq_b} como {cond_str_b}.")

elif nav == "📊  Rankings":
    st.markdown('<div class="section-title">📊 Rankings por Métrica</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
    met_sel = c1.selectbox("Métrica", metricas)
    perspectiva = c2.radio("Perspectiva", ["Propio 🟢", "Concedido 🔴"], help="**Propio**: lo que el equipo genera (ej. sus tiros).\n**Concedido**: lo que le genera el rival (ej. tiros que recibe).")
    col_datos = "Propio" if perspectiva == "Propio 🟢" else "Concedido"
    top_n = c3.slider("Top N", 5, len(equipos), min(16, len(equipos)))
    asc = c4.radio("Orden", ["Mayor primero ↓", "Menor primero ↑"]) == "Menor primero ↑"
    df_r = ranking(df, met_sel, col_datos, asc)
    sufijo = "recibido" if col_datos == "Concedido" else ""
    titulo_fig = f"{met_sel} {sufijo} — {'Menor a mayor' if asc else 'Mayor a menor'}"
    st.plotly_chart(fig_bar_ranking(df_r, titulo_fig, top_n, asc), use_container_width=True)
    st.dataframe(df_r.head(top_n).rename(columns={"Promedio": "Prom/partido", "Total": "Total acum.", "Partidos": "PJ"}).style.background_gradient(subset=["Prom/partido"], cmap="RdYlGn" if not asc else "RdYlGn_r"), use_container_width=True, hide_index=True)

elif nav == "🔄  Head-to-Head":
    st.markdown('<div class="section-title">🔄 Head-to-Head Comparativo</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    eq_a = c1.selectbox("Equipo A", equipos, key="h2h_a")
    cond_a = c1.selectbox("Condición A", ["General", "Local", "Visitante"], key="c_a")
    eq_b = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1), key="h2h_b")
    cond_b = c2.selectbox("Condición B", ["General", "Local", "Visitante"], key="c_b")
    if eq_a == eq_b and cond_a == cond_b:
        st.info("Seleccioná equipos o condiciones diferentes.")
    else:
        prom_gen, prom_cnd = prom_equipo(df), prom_equipo_cond(df)
        def get_df(eq, cond):
            if cond == "General": return prom_gen[prom_gen["Equipo"] == eq].set_index("Métrica")
            else: return prom_cnd[(prom_cnd["Equipo"] == eq) & (prom_cnd["Condicion"] == cond)].set_index("Métrica")
        pa, pb = get_df(eq_a, cond_a), get_df(eq_b, cond_b)
        idx = pa.index.intersection(pb.index)
        if idx.empty: st.warning("No hay métricas comunes en estas condiciones.")
        else:
            col_a, col_b = f"{eq_a} ({cond_a})", f"{eq_b} ({cond_b})"
            df_h2h = pd.DataFrame({"Métrica": idx, f"{col_a} (Propio)": pa.loc[idx, "Propio"].values.round(2), f"{col_b} (Propio)": pb.loc[idx, "Propio"].values.round(2), f"{col_a} (Concedido)": pa.loc[idx, "Concedido"].values.round(2), f"{col_b} (Concedido)": pb.loc[idx, "Concedido"].values.round(2)})
            def ventaja(row):
                a, b = row[f"{col_a} (Propio)"], row[f"{col_b} (Propio)"]
                if a > b: return f"▲ {eq_a}"
                if b > a: return f"▲ {eq_b}"
                return "— Igual"
            df_h2h["Ventaja (Propio)"] = df_h2h.apply(ventaja, axis=1)
            st.dataframe(df_h2h, use_container_width=True, hide_index=True)
            va, vb = (df_h2h["Ventaja (Propio)"].str.startswith(f"▲ {eq_a}")).sum(), (df_h2h["Ventaja (Propio)"].str.startswith(f"▲ {eq_b}")).sum()
            ca, cb, cc = st.columns(3)
            ca.metric(f"Gana {eq_a}", va); cb.metric(f"Gana {eq_b}", vb); cc.metric("Empates", len(df_h2h) - va - vb)
            st.plotly_chart(fig_radar(df, eq_a, eq_b, cond_a, cond_b), use_container_width=True)

elif nav == "📖  Perfil por Rival":
    st.markdown('<div class="section-title">📖 Perfil por Rival (Contextual)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    eq_sel = c1.selectbox("Seleccionar Equipo", equipos)
    met_sel = c2.selectbox("Métrica a analizar", metricas, index=metricas.index("Goles esperados (xG)") if "Goles esperados (xG)" in metricas else 0)
    df_eq = df[(df["Equipo"] == eq_sel) & (df["Métrica"] == met_sel)].sort_values("nFecha")
    if not df_eq.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_eq["Rival"], y=df_eq["Propio"], name="Generado (A Favor)", marker_color=RED))
        fig.add_trace(go.Bar(x=df_eq["Rival"], y=df_eq["Concedido"], name="Concedido (En Contra)", marker_color=GRAY))
        fig.update_layout(**PLOT, barmode='group', xaxis_title="Rival Enfrentado", yaxis_title=met_sel, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("### Historial de Partidos")
        df_res = df[(df["Equipo"] == eq_sel) & (df["Métrica"] == "Resultado")].sort_values("nFecha")
        df_display = pd.merge(df_res[["Fecha", "Condicion", "Rival", "Propio", "Concedido"]], df_eq[["Fecha", "Propio", "Concedido"]], on="Fecha", suffixes=("_goles", "_metrica"))
        df_display["Resultado"] = df_display["Propio_goles"].astype(int).astype(str) + " - " + df_display["Concedido_goles"].astype(int).astype(str)
        df_display = df_display[["Fecha", "Condicion", "Rival", "Resultado", "Propio_metrica", "Concedido_metrica"]]
        df_display.columns = ["Jornada", "Condición", "Rival", "Resultado Final", f"{met_sel} (A Favor)", f"{met_sel} (En Contra)"]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
