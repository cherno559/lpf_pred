"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v8 - Calibrado para Casas de Apuestas)
────────────────────────────────────────────────────
Cambios V8 vs V7:
  · Eliminado el calibrador anti-empate (principal causa de sesgo).
  · Regresión bayesiana al prior de la liga para muestras pequeñas.
  · Peso xG reducido de 60% → máximo 30%, crece gradualmente con la muestra.
  · Soft-clip con umbral más ancho (0.625–1.60 vs 0.75–1.25).
  · Clip de lambdas acotado a rango más realista (0.40–4.0).
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

# ── CONSTANTES V8 ──
# Ajustá LIGA_MEDIA_GOLES con el promedio real de goles por partido de tu Excel
LIGA_MEDIA_GOLES  = 1.15   # Prior de Poisson: media histórica de la LPF
REGRESION_K       = 5      # Partidos para darle peso pleno al equipo (↓ = más regresión a la media)
SOFT_CLIP_UMBRAL  = 1.60   # Rango "normal": 0.625–1.60 (más ancho que V7's 0.75–1.25)
SOFT_CLIP_COMPRESION = 0.45  # Factor de compresión fuera del umbral

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
                filas.append({**base, "Equipo": loc, "Rival": vis, "Condicion": "Local",     "Propio": vals["local"],     "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": vis, "Rival": loc, "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

def ranking(df: pd.DataFrame, metrica: str, columna="Propio", ascendente=False) -> pd.DataFrame:
    return (df[df["Métrica"] == metrica]
            .groupby("Equipo")[columna]
            .agg(Promedio="mean", Total="sum", Partidos="count")
            .reset_index()
            .round(2)
            .sort_values("Promedio", ascending=ascendente))

# ──────────────────────────────────────────────────────────────────────
# MOTOR PREDICTOR (V8 - Calibrado para casas de apuestas)
# ──────────────────────────────────────────────────────────────────────
def _weighted_mean(series: pd.Series, fecha_series: pd.Series) -> float:
    if series.empty: return float("nan")
    pesos = fecha_series.apply(lambda f: PESO_RECIENTE if f >= (fecha_series.max() - N_RECENCIA + 1) else PESO_NORMAL)
    return float(np.average(series, weights=pesos))

def soft_clip_v8(x: float) -> float:
    """
    Compresión dinámica con umbral más ancho que V7.
    Rango sin comprimir: [1/UMBRAL, UMBRAL] = [0.625, 1.60].
    Fuera de ese rango se aplasta con factor COMPRESION.
    """
    low = 1.0 / SOFT_CLIP_UMBRAL          # ≈ 0.625
    if x > SOFT_CLIP_UMBRAL:
        return SOFT_CLIP_UMBRAL + (x - SOFT_CLIP_UMBRAL) * SOFT_CLIP_COMPRESION
    if x < low:
        return low - (low - x) * SOFT_CLIP_COMPRESION
    return x

def regresion_bayesiana(media_equipo: float, n_partidos: int, prior: float = LIGA_MEDIA_GOLES) -> float:
    """
    Regresión a la media bayesiana (prior de Poisson).
    Con n_partidos=0  → 100% prior de la liga.
    Con n_partidos=K  → 50% equipo / 50% liga.
    Con n_partidos→∞  → 100% observado del equipo.
    """
    peso_equipo = n_partidos / (n_partidos + REGRESION_K)
    return peso_equipo * media_equipo + (1.0 - peso_equipo) * prior

def calcular_lambdas(df: pd.DataFrame, eq_a: str, eq_b: str, a_es_local: bool,
                     rot_a: float = 0.0, rot_b: float = 0.0):
    df_r = df[df["Métrica"] == "Resultado"].copy()
    if df_r.empty:
        return 1.3, 0.9

    # ── Agregados por equipo y condición ──
    agg = df_r.groupby(["Equipo", "Condicion"]).agg(
        GF=("Propio", "sum"), GC=("Concedido", "sum"), PJ=("Propio", "count")
    ).reset_index()
    agg_gen = df_r.groupby("Equipo").agg(
        GF=("Propio", "sum"), GC=("Concedido", "sum"), PJ=("Propio", "count")
    ).reset_index()

    # ── Medias de referencia de la liga ──
    m_gf_loc = agg[agg["Condicion"] == "Local"]["GF"].sum()      / max(agg[agg["Condicion"] == "Local"]["PJ"].sum(), 1)
    m_gf_vis = agg[agg["Condicion"] == "Visitante"]["GF"].sum()  / max(agg[agg["Condicion"] == "Visitante"]["PJ"].sum(), 1)
    m_gf_gen = agg_gen["GF"].sum() / max(agg_gen["PJ"].sum(), 1)

    # Anclar medias de la liga al prior si hay pocos datos totales
    n_total  = int(agg_gen["PJ"].sum())
    m_gf_loc = regresion_bayesiana(m_gf_loc, n_total, LIGA_MEDIA_GOLES * 1.10)
    m_gf_vis = regresion_bayesiana(m_gf_vis, n_total, LIGA_MEDIA_GOLES * 0.90)
    m_gf_gen = regresion_bayesiana(m_gf_gen, n_total, LIGA_MEDIA_GOLES)

    def stats_blended(eq: str, cond: str):
        row_spec = agg[(agg["Equipo"] == eq) & (agg["Condicion"] == cond)]
        row_gen  = agg_gen[agg_gen["Equipo"] == eq]

        pj_spec = int(row_spec["PJ"].sum()) if not row_spec.empty else 0
        pj_gen  = int(row_gen["PJ"].sum())  if not row_gen.empty  else 0

        ref_gf = m_gf_loc if cond == "Local" else m_gf_vis
        ref_gc = m_gf_vis if cond == "Local" else m_gf_loc

        gf_spec    = row_spec["GF"].sum() / pj_spec if pj_spec > 0 else ref_gf
        gc_spec    = row_spec["GC"].sum() / pj_spec if pj_spec > 0 else ref_gc
        gf_gen_val = row_gen["GF"].sum()  / pj_gen  if pj_gen  > 0 else m_gf_gen
        gc_gen_val = row_gen["GC"].sum()  / pj_gen  if pj_gen  > 0 else m_gf_gen

        # Blend dinámico: más peso al general cuando hay pocos datos específicos
        w_s = min(pj_spec / (pj_spec + 4), PESO_ESPECIFICO_DEFAULT)
        w_g = 1.0 - w_s

        gf_blend = gf_spec * w_s + gf_gen_val * w_g
        gc_blend = gc_spec * w_s + gc_gen_val * w_g

        # Regresión bayesiana al prior de la liga
        gf_blend = regresion_bayesiana(gf_blend, pj_gen, ref_gf)
        gc_blend = regresion_bayesiana(gc_blend, pj_gen, ref_gc)

        return gf_blend, gc_blend, pj_spec, pj_gen, w_s, w_g

    cond_a = "Local"     if a_es_local else "Visitante"
    cond_b = "Visitante" if a_es_local else "Local"

    gfa, gca, pja_spec, pja_gen, wsa, wga = stats_blended(eq_a, cond_a)
    gfb, gcb, pjb_spec, pjb_gen, wsb, wgb = stats_blended(eq_b, cond_b)

    ref_a = m_gf_loc if a_es_local else m_gf_vis
    ref_b = m_gf_vis if a_es_local else m_gf_loc

    # ── Fuerza de ataque × Debilidad defensiva rival (con soft-clip V8) ──
    fza_ataque_a  = soft_clip_v8(gfa / max(ref_a, 0.01))
    deb_defensa_b = soft_clip_v8(gcb / max(ref_b, 0.01))
    lam_a = fza_ataque_a * deb_defensa_b * ref_a

    fza_ataque_b  = soft_clip_v8(gfb / max(ref_b, 0.01))
    deb_defensa_a = soft_clip_v8(gca / max(ref_a, 0.01))
    lam_b = fza_ataque_b * deb_defensa_a * ref_b

    # ── Ajuste con xG (peso conservador, crece gradualmente con la muestra) ──
    df_xg = df[df["Métrica"] == "Goles esperados (xG)"]
    if not df_xg.empty:
        m_xg_loc = df_xg[df_xg["Condicion"] == "Local"]["Propio"].mean()
        m_xg_vis = df_xg[df_xg["Condicion"] == "Visitante"]["Propio"].mean()
        m_xg_gen = df_xg["Propio"].mean()

        def xg_blended(eq: str, cond: str):
            d_spec = df_xg[(df_xg["Equipo"] == eq) & (df_xg["Condicion"] == cond)]
            d_gen  = df_xg[df_xg["Equipo"] == eq]
            n_spec = len(d_spec)
            n_gen  = len(d_gen)
            x_spec = _weighted_mean(d_spec["Propio"], d_spec["nFecha"]) if not d_spec.empty else float("nan")
            x_gen  = _weighted_mean(d_gen["Propio"],  d_gen["nFecha"])  if not d_gen.empty  else float("nan")

            if np.isnan(x_spec) and np.isnan(x_gen): return float("nan"), 0
            if np.isnan(x_spec): return x_gen, n_gen

            w_s_xg = min(n_spec / (n_spec + 4), 0.65)
            return x_spec * w_s_xg + x_gen * (1.0 - w_s_xg), n_gen

        xa, n_xa = xg_blended(eq_a, cond_a)
        xb, n_xb = xg_blended(eq_b, cond_b)

        m_ref_xg_a = m_xg_loc if a_es_local else m_xg_vis
        m_ref_xg_b = m_xg_vis if a_es_local else m_xg_loc

        # Peso xG máximo 30%, crece con n:
        #   2 partidos ≈ 15% | 10 partidos ≈ 25% | 20+ partidos ≈ 29%
        w_xg_a = min(n_xa / (n_xa + 10), 0.30) if n_xa > 0 else 0.0
        w_xg_b = min(n_xb / (n_xb + 10), 0.30) if n_xb > 0 else 0.0

        if not np.isnan(xa) and m_ref_xg_a > 0:
            ajuste_xa = soft_clip_v8(xa / m_ref_xg_a)
            lam_a = lam_a * (1 - w_xg_a) + (ajuste_xa * ref_a) * w_xg_a
        if not np.isnan(xb) and m_ref_xg_b > 0:
            ajuste_xb = soft_clip_v8(xb / m_ref_xg_b)
            lam_b = lam_b * (1 - w_xg_b) + (ajuste_xb * ref_b) * w_xg_b

    # ── Penalización por rotación / Copa ──
    if rot_a > 0:
        lam_a *= (1 - rot_a * MAX_ROTATION_PENALTY)
        lam_b *= (1 + rot_a * MAX_ROTATION_PENALTY * 0.3)
    if rot_b > 0:
        lam_b *= (1 - rot_b * MAX_ROTATION_PENALTY)
        lam_a *= (1 + rot_b * MAX_ROTATION_PENALTY * 0.3)

    # ── SIN calibrador anti-empate ──
    # Eliminado en V8 porque el bloque ×1.10/×0.90 inflaba artificialmente
    # al favorito y destruía la estimación de empate frente a casas de apuestas.

    lam_a = float(np.clip(lam_a, 0.40, 4.0))
    lam_b = float(np.clip(lam_b, 0.40, 4.0))

    return round(lam_a, 3), round(lam_b, 3)

def montecarlo(lam_a: float, lam_b: float) -> dict:
    seed = int((lam_a * 1000 + lam_b * 100)) % (2**31)
    rng  = np.random.default_rng(seed)
    ga, gb = rng.poisson(lam_a, MONTECARLO_N), rng.poisson(lam_b, MONTECARLO_N)
    scores = [{"A": r, "B": v, "prob": float(np.mean((ga == r) & (gb == v)))} for r in range(8) for v in range(8)]
    return {
        "victoria": float(np.mean(ga > gb)),
        "empate":   float(np.mean(ga == gb)),
        "derrota":  float(np.mean(ga < gb)),
        "df":       pd.DataFrame(scores),
        "lam_a":    lam_a,
        "lam_b":    lam_b,
    }

# ──────────────────────────────────────────────────────────────────────
# COMPONENTES VISUALES
# ──────────────────────────────────────────────────────────────────────
def fig_probs(sim, na, nb):
    fig = go.Figure(go.Bar(
        x=[sim["victoria"]*100, sim["empate"]*100, sim["derrota"]*100],
        y=[f"Victoria {na}", "Empate", f"Victoria {nb}"],
        orientation="h", marker_color=[RED, GRAY, BLUE],
        text=[f"{sim['victoria']*100:.1f}%", f"{sim['empate']*100:.1f}%", f"{sim['derrota']*100:.1f}%"],
        textposition="outside"
    ))
    fig.update_layout(**PLOT, height=200,
                      xaxis=dict(**GRID, range=[0, 105], ticksuffix="%"),
                      showlegend=False)
    return fig

def fig_marcadores(sim, na, nb):
    df = sim["df"].copy()
    df["label"] = na + " " + df["A"].astype(str) + "–" + df["B"].astype(str) + " " + nb
    top = df.nlargest(8, "prob").iloc[::-1]
    fig = go.Figure(go.Bar(
        x=top["prob"]*100, y=top["label"],
        orientation="h", marker_color=RED,
        text=(top["prob"]*100).map(lambda x: f"{x:.1f}%"),
        textposition="auto",
        textfont=dict(color="white", size=14, family="Rajdhani")
    ))
    fig.update_layout(**PLOT, height=340,
                      xaxis=dict(**GRID, ticksuffix="%"),
                      yaxis=dict(**NO_GRID, tickfont=dict(size=13, family="Rajdhani")))
    return fig

def fig_radar(df, eq_a, eq_b, cond_a="General", cond_b="General"):
    mets = [m for m in [
        "Posesión de balón", "Tiros totales", "Tiros al arco",
        "Pases totales", "Goles esperados (xG)", "Córners",
        "Quites", "Intercepciones"
    ] if m in df["Métrica"].values]
    if not mets: return go.Figure()

    def get_val(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General": d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0

    va  = [get_val(eq_a, cond_a, m) for m in mets]
    vb  = [get_val(eq_b, cond_b, m) for m in mets]
    mx  = [max(abs(a), abs(b), 1e-6) for a, b in zip(va, vb)]
    van = [a / m for a, m in zip(va, mx)]
    vbn = [b / m for b, m in zip(vb, mx)]

    fig = go.Figure()
    for v, n, c in [(van, f"{eq_a} ({cond_a})", RED), (vbn, f"{eq_b} ({cond_b})", BLUE)]:
        r, g, b_ = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
        fig.add_trace(go.Scatterpolar(
            r=v+[v[0]], theta=mets+[mets[0]], fill="toself", name=n,
            line=dict(color=c, width=2),
            fillcolor=f"rgba({r},{g},{b_},0.2)"
        ))
    fig.update_layout(**PLOT, height=400,
                      polar=dict(bgcolor="rgba(0,0,0,0)",
                                 radialaxis=dict(visible=True, range=[0, 1], gridcolor="#1c2a40")))
    return fig

def fig_matriz_ranking(df, metrica, condicion):
    d = df[df["Métrica"] == metrica].copy()
    if condicion != "General": d = d[d["Condicion"] == condicion]
    res = d.groupby("Equipo").agg(
        Propio=("Propio", "mean"), Concedido=("Concedido", "mean")
    ).reset_index()
    if res.empty: return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=res["Concedido"], y=res["Propio"], mode="markers+text",
        text=res["Equipo"], textposition="top center",
        marker=dict(size=12, color=RED, opacity=0.8, line=dict(width=1, color="white"))
    ))
    fig.add_vline(x=res["Concedido"].mean(), line=dict(color=GRAY, dash="dot"))
    fig.add_hline(y=res["Propio"].mean(),    line=dict(color=GRAY, dash="dot"))
    fig.update_layout(**PLOT, height=500,
                      xaxis_title=f"{metrica} Concedido",
                      yaxis_title=f"{metrica} Propio",
                      xaxis=dict(**GRID), yaxis=dict(**GRID))
    return fig

# ──────────────────────────────────────────────────────────────────────
# SIDEBAR Y NAVEGACIÓN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Excel", value="Fecha_x_fecha_lpf.xlsx")
    st.markdown("---")
    nav = st.radio("", [
        "🔮 Predictor", "📊 Rankings",
        "🔄 Head-to-Head", "📖 Perfil por Rival",
        "🎭 Estilos de Juego"
    ], label_visibility="collapsed")

if not os.path.exists(ruta):
    st.warning("No se encontró el Excel.")
    st.stop()

datos = cargar_excel(ruta)
if not datos:
    st.error("Sin datos.")
    st.stop()

df       = construir_df(datos)
equipos  = sorted(df["Equipo"].unique())
metricas = sorted(df["Métrica"].unique())
st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# SECCIONES
# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Predictor de Partidos</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    eq_a  = c1.selectbox("Local",     equipos)
    eq_b  = c2.selectbox("Visitante", equipos, index=min(1, len(equipos) - 1))
    es_loc = c3.toggle("Ventaja local", value=True)

    st.markdown('<div class="section-title">🔄 Penalización por Rotación / Copa</div>', unsafe_allow_html=True)
    rc1, rc2 = st.columns(2)
    with rc1:
        rot_a_int = st.slider("Rotación Local",  1, 5, 2, key="rot_a") / 5.0 if st.checkbox(f"⚠️ {eq_a} rota") else 0.0
    with rc2:
        rot_b_int = st.slider("Rotación Visit.", 1, 5, 2, key="rot_b") / 5.0 if st.checkbox(f"⚠️ {eq_b} rota") else 0.0

    if st.button("🚀 SIMULAR"):
        lam_a, lam_b = calcular_lambdas(df, eq_a, eq_b, es_loc, rot_a_int, rot_b_int)
        sim = montecarlo(lam_a, lam_b)

        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi"><div class="lbl">V. {eq_a}</div><div class="val">{sim["victoria"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="lbl">Empate</div><div class="val">{sim["empate"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="lbl">V. {eq_b}</div><div class="val">{sim["derrota"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="note">⚙️ Modelo V8 (Calibrado) | '
            f'λ {eq_a} = {lam_a} · λ {eq_b} = {lam_b} | '
            f'Prior liga: {LIGA_MEDIA_GOLES} goles/partido</div>',
            unsafe_allow_html=True
        )

        t1, t2, t3 = st.tabs(["📊 Probabilidades", "🎯 Marcadores exactos", "🕸️ Radar"])
        with t1: st.plotly_chart(fig_probs(sim, eq_a, eq_b), use_container_width=True)
        with t2: st.plotly_chart(fig_marcadores(sim, eq_a, eq_b), use_container_width=True)
        with t3: st.plotly_chart(fig_radar(df, eq_a, eq_b, "Local" if es_loc else "Visitante", "Visitante" if es_loc else "Local"), use_container_width=True)

elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings y Matriz de Eficiencia</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([4, 3, 3])
    met_sel  = c1.selectbox("Métrica",   metricas)
    cond_sel = c2.radio("Condición", ["General", "Local", "Visitante"], horizontal=True)
    vista_sel = c3.radio("Vista",    ["Barras", "Matriz"], horizontal=True)

    if vista_sel == "Barras":
        p_sel = st.radio("Enfoque", ["Propio 🟢", "Concedido 🔴"], horizontal=True)
        df_r  = ranking(
            df[df["Condicion"] == cond_sel] if cond_sel != "General" else df,
            met_sel,
            "Propio" if "Propio" in p_sel else "Concedido",
            met_sel in METRICAS_MENOS_ES_MEJOR
        )
        st.plotly_chart(
            go.Figure(go.Bar(
                x=df_r["Promedio"], y=df_r["Equipo"],
                orientation="h", marker_color=RED,
                text=df_r["Promedio"], textposition="outside"
            )).update_layout(**PLOT, height=500),
            use_container_width=True
        )
    else:
        st.plotly_chart(fig_matriz_ranking(df, met_sel, cond_sel), use_container_width=True)

elif nav == "🔄 Head-to-Head":
    st.markdown('<div class="section-title">🔄 Head-to-Head Comparativo</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    ea = c1.selectbox("Equipo A",    equipos, key="ea")
    ca = c1.selectbox("Condición A", ["General", "Local", "Visitante"], key="ca")
    eb = c2.selectbox("Equipo B",    equipos, index=min(1, len(equipos)-1), key="eb")
    cb = c2.selectbox("Condición B", ["General", "Local", "Visitante"], key="cb")

    if ea == eb and ca == cb:
        st.info("⚠️ Seleccioná equipos o condiciones diferentes.")
    else:
        def get_fs(eq, cond):
            d = df[df["Equipo"] == eq]
            if cond != "General": d = d[d["Condicion"] == cond]
            return d.groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)

        sa, sb = get_fs(ea, ca), get_fs(eb, cb)
        idx = sa.index.intersection(sb.index)
        if not idx.empty:
            df_h2h = pd.DataFrame({
                f"{ea} (A Favor)":   sa.loc[idx, "Propio"].values,
                f"{eb} (A Favor)":   sb.loc[idx, "Propio"].values,
                f"{ea} (En Contra)": sa.loc[idx, "Concedido"].values,
                f"{eb} (En Contra)": sb.loc[idx, "Concedido"].values,
            }, index=idx)

            def hw(r):
                m    = r.name
                stl  = ["", "", "", ""]
                v1, v2 = r.iloc[0], r.iloc[1]
                if v1 != v2:
                    win = (v1 > v2) if m not in METRICAS_MENOS_ES_MEJOR else (v1 < v2)
                    stl[0 if win else 1] = "background-color: rgba(34, 197, 94, 0.2)"
                return stl

            st.dataframe(df_h2h.style.apply(hw, axis=1), use_container_width=True)
            st.plotly_chart(fig_radar(df, ea, eb, ca, cb), use_container_width=True)

elif nav == "📖 Perfil por Rival":
    st.markdown('<div class="section-title">📖 Perfil por Rival</div>', unsafe_allow_html=True)
    eq_sel  = st.selectbox("Equipo",  equipos)
    met_sel = st.selectbox("Métrica", metricas)
    d_eq = df[(df["Equipo"] == eq_sel) & (df["Métrica"] == met_sel)].sort_values("nFecha")
    if not d_eq.empty:
        fig = go.Figure([
            go.Bar(x=d_eq["Rival"], y=d_eq["Propio"],    name="A favor",  marker_color=RED),
            go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], name="En contra", marker_color=GRAY)
        ])
        fig.update_layout(**PLOT, barmode="group")
        st.plotly_chart(fig, use_container_width=True)

elif nav == "🎭 Estilos de Juego":
    st.markdown('<div class="section-title">🎭 Matriz de Estilos de Juego</div>', unsafe_allow_html=True)
    mo = "Goles esperados (xG)" if "Goles esperados (xG)" in metricas else "Tiros totales"

    if "Posesión de balón" in metricas and mo in metricas:
        df_e = pd.DataFrame({
            "P": df[df["Métrica"] == "Posesión de balón"].groupby("Equipo")["Propio"].mean(),
            "O": df[df["Métrica"] == mo].groupby("Equipo")["Propio"].mean()
        }).dropna()

        mp, mo_m = df_e["P"].mean(), df_e["O"].mean()

        fig = go.Figure(go.Scatter(
            x=df_e["P"], y=df_e["O"], mode="markers+text",
            text=df_e.index, textposition="top center",
            marker=dict(size=12, color=RED, line=dict(width=1, color="white"))
        ))
        fig.add_vline(x=mp,   line=dict(color=GRAY, dash="dash"))
        fig.add_hline(y=mo_m, line=dict(color=GRAY, dash="dash"))
        fig.update_layout(
            **PLOT, height=600,
            xaxis_title="Posesión (%)", yaxis_title=f"Ataque ({mo})",
            xaxis=dict(**GRID), yaxis=dict(**GRID)
        )
        st.plotly_chart(fig, use_container_width=True)

        def categorizar(row):
            if   row["P"] >  mp and row["O"] >  mo_m: return "🟢 Ofensivo de Posesión"
            elif row["P"] <= mp and row["O"] >  mo_m: return "🟠 Ofensivo Directo"
            elif row["P"] >  mp and row["O"] <= mo_m: return "🔵 Defensivo de Posesión"
            else:                                      return "🔴 Defensivo Reactivo"

        df_e["Categoría Asignada"] = df_e.apply(categorizar, axis=1)
        st.dataframe(
            df_e.sort_values(["Categoría Asignada", "O"], ascending=[True, False]),
            use_container_width=True
        )
    else:
        st.warning("Faltan métricas de Posesión o Tiros/xG en el Excel para armar la matriz.")
