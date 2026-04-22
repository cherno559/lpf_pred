"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v8.2 - Calibración Fina Total)
────────────────────────────────────────────────────
Cambios realizados:
  · Se restauraron TODAS las secciones (Estilos, Perfil, H2H, Rankings, Predictor).
  · Calibración: Se ajustó REGRESION_K a 3.5 para mayor sensibilidad.
  · Calibración: Umbral de Soft-Clip a 1.40 para frenar a Lanús sin aplastar a Boca.
  · Se mantuvo el CSS pro y toda la lógica visual original.
"""

import re, os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y CONSTANTES
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Scouting", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

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
.stTabs [data-baseweb="tab-list"] { background:#0f1829; border-radius:10px; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"] { font-family:'Rajdhani'; font-weight:700; font-size:14px; color:#64748b !important; border-radius:7px; padding:6px 16px; }
.stTabs [aria-selected="true"] { background:#e63946 !important; color:#fff !important; }
.stButton>button { font-family:'Bebas Neue'; font-size:17px; letter-spacing:2px; background:linear-gradient(135deg,#e63946,#b91c2c); color:#fff; border:none; border-radius:9px; padding:13px; width:100%; transition:all .2s; }
.stButton>button:hover { transform:translateY(-1px); box-shadow:0 6px 20px rgba(230,57,70,.45); }
.stSelectbox>div>div, .stMultiSelect>div>div, .stTextInput>div>div { background:#0f1829 !important; border:1px solid #1c2a40 !important; color:#dde3ee !important; border-radius:8px !important; }
.note { background:#0f1829; border:1px solid #1c2a40; border-radius:8px; padding:10px 14px; font-size:12px; color:#64748b; margin-top:8px; }
</style>
""", unsafe_allow_html=True)

MONTECARLO_N = 15_000
RED, BLUE, GRAY, AMBER = "#e63946", "#3b82f6", "#64748b", "#f59e0b"
PLOT = dict(font=dict(family="Rajdhani", size=13, color="#dde3ee"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=20, t=36, b=10))
GRID = dict(showgrid=True, gridcolor="#1c2a40", zeroline=False)
NO_GRID = dict(showgrid=False, zeroline=False)
METRICAS_MENOS_ES_MEJOR = {"Faltas", "Tarjetas amarillas", "Tarjetas rojas", "Fueras de juego"}

N_RECENCIA = 3
PESO_RECIENTE = 2.5
PESO_NORMAL = 1.0
MAX_ROTATION_PENALTY = 0.12

# BLEND ESTADÍSTICO
PESO_ESPECIFICO_DEFAULT = 0.70
PESO_GENERAL_DEFAULT = 0.30

# ── CONSTANTES CALIBRACIÓN V8.2 ──
LIGA_MEDIA_GOLES = 1.17 
REGRESION_K = 3.5      # Bajamos a 3.5 para ser un poco más reactivos a la racha
SOFT_CLIP_UMBRAL = 1.40 # Bajamos el techo: permite ventajas pero frena la explosión del 85%
SOFT_CLIP_COMPRESION = 0.35 

# ──────────────────────────────────────────────────────────────────────
# PARSEO Y PROCESAMIENTO
# ──────────────────────────────────────────────────────────────────────
def num(v) -> float:
    if isinstance(v, str): v = v.replace('%', '').replace(',', '.').strip()
    try: return float(v)
    except Exception: return 0.0

@st.cache_data(ttl=120, show_spinner=False)
def cargar_excel(ruta: str):
    try: xl = pd.ExcelFile(ruta, engine="openpyxl")
    except Exception: return {}
    resultado = {}
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE): continue
        df = pd.read_excel(ruta, sheet_name=hoja, header=None, engine="openpyxl")
        partidos, i = [], 0
        while i < len(df):
            c0 = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""
            if re.search(r"\s+vs\s+", c0, re.IGNORECASE):
                partes = re.split(r"\s+vs\s+", c0, flags=re.IGNORECASE)
                if len(partes) == 2:
                    loc, vis, stats, j = partes[0].strip(), partes[1].strip(), {}, i + 1
                    while j < len(df):
                        r0 = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                        r1, r2 = df.iloc[j, 1] if df.shape[1] > 1 else None, df.iloc[j, 2] if df.shape[1] > 2 else None
                        if r0 == "" and (pd.isna(r1) if r1 is not None else True): break
                        if re.search(r"\s+vs\s+", r0, re.IGNORECASE): break
                        if r0.lower() in ("métrica", "metrica") or r0 == loc: j += 1; continue
                        if pd.notna(r1): stats[r0] = {"local": num(r1), "visitante": num(r2) if pd.notna(r2) else 0}
                        j += 1
                    if stats: partidos.append({"local": loc, "visitante": vis, "metricas": stats})
                    i = j
                else: i += 1
            else: i += 1
        if partidos: resultado[hoja] = partidos
    return resultado

def construir_df(datos: dict) -> pd.DataFrame:
    filas = []
    for fecha, partidos in datos.items():
        nf = int(re.search(r"\d+", fecha).group())
        for p in partidos:
            loc, vis = p["local"], p["visitante"]
            for met, vals in p["metricas"].items():
                base = {"Fecha": fecha, "nFecha": nf, "Métrica": met}
                filas.append({**base, "Equipo": loc, "Rival": vis, "Condicion": "Local", "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": vis, "Rival": loc, "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

def ranking(df: pd.DataFrame, metrica: str, columna="Propio", ascendente=False) -> pd.DataFrame:
    return (df[df["Métrica"] == metrica].groupby("Equipo")[columna]
            .agg(Promedio="mean", Total="sum", Partidos="count").reset_index()
            .round(2).sort_values("Promedio", ascending=ascendente))

# ──────────────────────────────────────────────────────────────────────
# MOTOR PREDICTOR (V8.2 - CALIBRACIÓN FINAL)
# ──────────────────────────────────────────────────────────────────────
def _weighted_mean(series: pd.Series, fecha_series: pd.Series) -> float:
    if series.empty: return float("nan")
    pesos = fecha_series.apply(lambda f: PESO_RECIENTE if f >= (fecha_series.max() - N_RECENCIA + 1) else PESO_NORMAL)
    return float(np.average(series, weights=pesos))

def soft_clip_v8(x: float) -> float:
    # Umbral asimétrico: solo frena lo que está muy por encima de la media
    if x > SOFT_CLIP_UMBRAL:
        return SOFT_CLIP_UMBRAL + (x - SOFT_CLIP_UMBRAL) * SOFT_CLIP_COMPRESION
    return x

def regresion_bayesiana(media_equipo: float, n_partidos: int, prior: float = LIGA_MEDIA_GOLES) -> float:
    peso_equipo = n_partidos / (n_partidos + REGRESION_K)
    return peso_equipo * media_equipo + (1.0 - peso_equipo) * prior

def calcular_lambdas(df: pd.DataFrame, eq_a: str, eq_b: str, a_es_local: bool, rot_a: float = 0.0, rot_b: float = 0.0):
    df_r = df[df["Métrica"] == "Resultado"].copy()
    if df_r.empty: return 1.3, 0.9

    agg = df_r.groupby(["Equipo", "Condicion"]).agg(GF=("Propio", "sum"), GC=("Concedido", "sum"), PJ=("Propio", "count")).reset_index()
    agg_gen = df_r.groupby("Equipo").agg(GF=("Propio", "sum"), GC=("Concedido", "sum"), PJ=("Propio", "count")).reset_index()

    m_gf_loc = agg[agg["Condicion"] == "Local"]["GF"].sum() / max(agg[agg["Condicion"] == "Local"]["PJ"].sum(), 1)
    m_gf_vis = agg[agg["Condicion"] == "Visitante"]["GF"].sum() / max(agg[agg["Condicion"] == "Visitante"]["PJ"].sum(), 1)
    m_gf_gen = agg_gen["GF"].sum() / max(agg_gen["PJ"].sum(), 1)

    def stats_blended(eq: str, cond: str):
        row_spec = agg[(agg["Equipo"] == eq) & (agg["Condicion"] == cond)]
        row_gen = agg_gen[agg_gen["Equipo"] == eq]
        pj_spec = int(row_spec["PJ"].sum()) if not row_spec.empty else 0
        pj_gen = int(row_gen["PJ"].sum()) if not row_gen.empty else 0
        ref_gf = m_gf_loc if cond == "Local" else m_gf_vis
        ref_gc = m_gf_vis if cond == "Local" else m_gf_loc

        gf_spec = row_spec["GF"].sum() / pj_spec if pj_spec > 0 else ref_gf
        gc_spec = row_spec["GC"].sum() / pj_spec if pj_spec > 0 else ref_gc
        
        # Blend 70/30 (Local/Visitante vs General)
        w_s = min(pj_spec / (pj_spec + 3), PESO_ESPECIFICO_DEFAULT)
        gf_blend = gf_spec * w_s + (row_gen["GF"].sum()/pj_gen if pj_gen>0 else m_gf_gen) * (1-w_s)
        gc_blend = gc_spec * w_s + (row_gen["GC"].sum()/pj_gen if pj_gen>0 else m_gf_gen) * (1-w_s)

        # Regresión a la media
        gf_final = regresion_bayesiana(gf_blend, pj_gen, ref_gf)
        gc_final = regresion_bayesiana(gc_blend, pj_gen, ref_gc)
        return gf_final, gc_final

    gfa, gca = stats_blended(eq_a, "Local" if a_es_local else "Visitante")
    gfb, gcb = stats_blended(eq_b, "Visitante" if a_es_local else "Local")
    ref_a = m_gf_loc if a_es_local else m_gf_vis
    ref_b = m_gf_vis if a_es_local else m_gf_loc

    # Cálculo Multiplicativo con Soft-Clip (Salvando a Boca, frenando a Lanús)
    lam_a = soft_clip_v8(gfa / ref_a) * soft_clip_v8(gcb / ref_b) * ref_a
    lam_b = soft_clip_v8(gfb / ref_b) * soft_clip_v8(gca / ref_a) * ref_b

    # Ajuste xG (Peso reducido para no exagerar)
    df_xg = df[df["Métrica"] == "Goles esperados (xG)"]
    if not df_xg.empty:
        xg_a = df_xg[df_xg["Equipo"] == eq_a]["Propio"].mean()
        xg_b = df_xg[df_xg["Equipo"] == eq_b]["Propio"].mean()
        m_xg = df_xg["Propio"].mean()
        w_xg = 0.22 # Reducimos influencia de xG para mayor estabilidad
        if not np.isnan(xg_a): lam_a = lam_a * (1-w_xg) + (soft_clip_v8(xg_a/m_xg) * ref_a) * w_xg
        if not np.isnan(xg_b): lam_b = lam_b * (1-w_xg) + (soft_clip_v8(xg_b/m_xg) * ref_b) * w_xg

    if rot_a > 0: lam_a *= (1 - rot_a * MAX_ROTATION_PENALTY)
    if rot_b > 0: lam_b *= (1 - rot_b * MAX_ROTATION_PENALTY)

    return round(float(np.clip(lam_a, 0.35, 4.0)), 3), round(float(np.clip(lam_b, 0.35, 4.0)), 3)

def montecarlo(lam_a: float, lam_b: float) -> dict:
    seed = int((lam_a * 1000 + lam_b * 100)) % (2**31)
    rng = np.random.default_rng(seed)
    ga, gb = rng.poisson(lam_a, MONTECARLO_N), rng.poisson(lam_b, MONTECARLO_N)
    scores = [{"A": r, "B": v, "prob": float(np.mean((ga == r) & (gb == v)))} for r in range(8) for v in range(8)]
    return {"victoria": float(np.mean(ga > gb)), "empate": float(np.mean(ga == gb)), "derrota": float(np.mean(ga < gb)), "df": pd.DataFrame(scores), "lam_a": lam_a, "lam_b": lam_b}

# ──────────────────────────────────────────────────────────────────────
# COMPONENTES VISUALES
# ──────────────────────────────────────────────────────────────────────
def fig_probs(sim, na, nb):
    fig = go.Figure(go.Bar(x=[sim["victoria"]*100, sim["empate"]*100, sim["derrota"]*100], y=[f"Victoria {na}", "Empate", f"Victoria {nb}"], orientation="h", marker_color=[RED, GRAY, BLUE], text=[f"{sim['victoria']*100:.1f}%", f"{sim['empate']*100:.1f}%", f"{sim['derrota']*100:.1f}%"], textposition="outside"))
    fig.update_layout(**PLOT, height=200, xaxis=dict(**GRID, range=[0, 105], ticksuffix="%"), showlegend=False)
    return fig

def fig_radar(df, eq_a, eq_b, cond_a="General", cond_b="General"):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco", "Pases totales", "Goles esperados (xG)", "Córners"] if m in df["Métrica"].values]
    if not mets: return go.Figure()
    def get_val(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General": d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0
    va, vb = [get_val(eq_a, cond_a, m) for m in mets], [get_val(eq_b, cond_b, m) for m in mets]
    mx = [max(abs(a), abs(b), 1e-6) for a, b in zip(va, vb)]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[a/m for a,m in zip(va,mx)]+[va[0]/mx[0]], theta=mets+[mets[0]], fill="toself", name=eq_a, line=dict(color=RED)))
    fig.add_trace(go.Scatterpolar(r=[b/m for b,m in zip(vb,mx)]+[vb[0]/mx[0]], theta=mets+[mets[0]], fill="toself", name=eq_b, line=dict(color=BLUE)))
    fig.update_layout(**PLOT, height=400, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=False)))
    return fig

# ──────────────────────────────────────────────────────────────────────
# NAVEGACIÓN Y FLUJO PRINCIPAL
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Excel", value="Fecha_x_fecha_lpf.xlsx")
    st.markdown("---")
    nav = st.radio("", ["🔮 Predictor", "📊 Rankings", "🔄 Head-to-Head", "📖 Perfil por Rival", "🎭 Estilos de Juego"], label_visibility="collapsed")

if not os.path.exists(ruta): st.warning("No se encontró el Excel."); st.stop()
datos = cargar_excel(ruta); df = construir_df(datos)
equipos, metricas = sorted(df["Equipo"].unique()), sorted(df["Métrica"].unique())
st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Predictor Pro</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    eq_a, eq_b, es_loc = c1.selectbox("Local", equipos), c2.selectbox("Visitante", equipos, index=1), c3.toggle("Ventaja local", value=True)
    r1, r2 = st.columns(2)
    rot_a = r1.slider(f"Rotación {eq_a}", 0.0, 1.0, 0.0) if r1.checkbox(f"⚠️ {eq_a} rota") else 0.0
    rot_b = r2.slider(f"Rotación {eq_b}", 0.0, 1.0, 0.0) if r2.checkbox(f"⚠️ {eq_b} rota") else 0.0
    if st.button("🚀 SIMULAR"):
        la, lb = calcular_lambdas(df, eq_a, eq_b, es_loc, rot_a, rot_b)
        sim = montecarlo(la, lb)
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi"><div class="val">{sim["victoria"]*100:.1f}%</div><div class="lbl">V. {eq_a}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="val">{sim["empate"]*100:.1f}%</div><div class="lbl">Empate</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="val">{sim["derrota"]*100:.1f}%</div><div class="lbl">V. {eq_b}</div></div>', unsafe_allow_html=True)
        st.plotly_chart(fig_probs(sim, eq_a, eq_b), use_container_width=True)
        st.plotly_chart(fig_radar(df, eq_a, eq_b, "Local" if es_loc else "General", "Visitante" if es_loc else "General"), use_container_width=True)

elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings y Matriz</div>', unsafe_allow_html=True)
    m_sel = st.selectbox("Métrica", metricas)
    df_r = ranking(df, m_sel)
    st.plotly_chart(go.Figure(go.Bar(x=df_r["Promedio"], y=df_r["Equipo"], orientation="h", marker_color=RED)).update_layout(**PLOT, height=600, yaxis=dict(autorange="reversed")), use_container_width=True)

elif nav == "🔄 Head-to-Head":
    st.markdown('<div class="section-title">🔄 Head-to-Head</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    e1, e2 = c1.selectbox("Equipo A", equipos), c2.selectbox("Equipo B", equipos, index=1)
    s1, s2 = df[df["Equipo"]==e1].groupby("Métrica")["Propio"].mean(), df[df["Equipo"]==e2].groupby("Métrica")["Propio"].mean()
    st.table(pd.DataFrame({e1: s1, e2: s2}).round(2).dropna())

elif nav == "📖 Perfil por Rival":
    st.markdown('<div class="section-title">📖 Perfil por Rival</div>', unsafe_allow_html=True)
    eq_p = st.selectbox("Equipo", equipos)
    met_p = st.selectbox("Métrica", metricas)
    d_eq = df[(df["Equipo"] == eq_p) & (df["Métrica"] == met_p)].sort_values("nFecha")
    st.plotly_chart(go.Figure([go.Bar(x=d_eq["Rival"], y=d_eq["Propio"], marker_color=RED), go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], marker_color=GRAY)]).update_layout(**PLOT, barmode="group"), use_container_width=True)

elif nav == "🎭 Estilos de Juego":
    st.markdown('<div class="section-title">🎭 Matriz de Estilos</div>', unsafe_allow_html=True)
    if "Posesión de balón" in metricas:
        df_e = pd.DataFrame({"P": df[df["Métrica"]=="Posesión de balón"].groupby("Equipo")["Propio"].mean(), "O": df[df["Métrica"]=="Tiros totales"].groupby("Equipo")["Propio"].mean()}).dropna()
        fig = go.Figure(go.Scatter(x=df_e["P"], y=df_e["O"], mode="markers+text", text=df_e.index, marker=dict(size=12, color=RED)))
        fig.add_vline(x=df_e["P"].mean(), line=dict(dash="dash")); fig.add_hline(y=df_e["O"].mean(), line=dict(dash="dash"))
        st.plotly_chart(fig.update_layout(**PLOT, height=600), use_container_width=True)
