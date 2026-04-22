"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard
────────────────────────────────────────────────
Lee el Excel generado por sofascore_lpf_generales.py y construye:
  · Predictor de partidos (con Marcadores Exactos devueltos)
  · Matriz de Eficiencia (Propio vs Concedido)
  · Head-to-Head con Tabla (A favor / En contra) y Radar
  · Perfil por Rival
  · Matriz de Estilos de Juego (Modelo Heurístico)
"""

import re, os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
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
# PARSEO Y PROCESAMIENTO
# ──────────────────────────────────────────────────────────────────────
def num(v) -> float:
    if isinstance(v, str): v = v.replace('%', '').replace(',', '.').strip()
    try: return float(v)
    except: return 0.0

@st.cache_data(ttl=120, show_spinner=False)
def cargar_excel(ruta: str):
    try: xl = pd.ExcelFile(ruta, engine="openpyxl")
    except: return {}
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
                        r1, r2 = df.iloc[j, 1] if df.shape[1]>1 else None, df.iloc[j, 2] if df.shape[1]>2 else None
                        if r0 == "" and (pd.isna(r1) if r1 is not None else True): break
                        if re.search(r"\s+vs\s+", r0, re.IGNORECASE): break
                        if r0.lower() in ("métrica", "metrica") or r0 == loc: 
                            j += 1
                            continue
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
                filas.append({"Fecha": fecha, "nFecha": nf, "Equipo": loc, "Rival": vis, "Condicion": "Local", "Métrica": met, "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({"Fecha": fecha, "nFecha": nf, "Equipo": vis, "Rival": loc, "Condicion": "Visitante", "Métrica": met, "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

def ranking(df: pd.DataFrame, metrica: str, columna="Propio", ascendente=False) -> pd.DataFrame:
    df_m = df[df["Métrica"] == metrica].copy()
    return df_m.groupby("Equipo")[columna].agg(Promedio="mean", Total="sum", Partidos="count").reset_index().round(2).sort_values("Promedio", ascending=ascendente)

# ──────────────────────────────────────────────────────────────────────
# MOTOR PREDICTOR
# ──────────────────────────────────────────────────────────────────────
def calcular_lambdas(df: pd.DataFrame, eq_a: str, eq_b: str, a_es_local: bool):
    df_r = df[df["Métrica"] == "Resultado"].copy()
    if df_r.empty: return 1.3, 0.9
    agg = df_r.groupby(["Equipo", "Condicion"]).agg(GF=("Propio", "sum"), GC=("Concedido", "sum"), PJ=("Propio", "count")).reset_index()
    m_gf_loc = agg[agg["Condicion"] == "Local"]["GF"].sum() / max(agg[agg["Condicion"] == "Local"]["PJ"].sum(), 1)
    m_gf_vis = agg[agg["Condicion"] == "Visitante"]["GF"].sum() / max(agg[agg["Condicion"] == "Visitante"]["PJ"].sum(), 1)

    def stats(eq, cond):
        row = agg[(agg["Equipo"] == eq) & (agg["Condicion"] == cond)]
        if row.empty: return (m_gf_loc if cond == "Local" else m_gf_vis), (m_gf_vis if cond == "Local" else m_gf_loc), 1
        return row.iloc[0]["GF"]/row.iloc[0]["PJ"], row.iloc[0]["GC"]/row.iloc[0]["PJ"], row.iloc[0]["PJ"]

    if a_es_local:
        gfa, gca, _ = stats(eq_a, "Local"); gfb, gcb, _ = stats(eq_b, "Visitante")
        lam_a = (gfa/m_gf_loc) * (gcb/m_gf_loc) * m_gf_loc
        lam_b = (gfb/m_gf_vis) * (gca/m_gf_vis) * m_gf_vis
    else:
        gfa, gca, _ = stats(eq_a, "Visitante"); gfb, gcb, _ = stats(eq_b, "Local")
        lam_a = (gfa/m_gf_vis) * (gcb/m_gf_vis) * m_gf_vis
        lam_b = (gfb/m_gf_loc) * (gca/m_gf_loc) * m_gf_loc

    df_xg = df[df["Métrica"] == "Goles esperados (xG)"]
    if not df_xg.empty:
        ca, cb = ("Local" if a_es_local else "Visitante"), ("Visitante" if a_es_local else "Local")
        m_xg_a, m_xg_b = df_xg[df_xg["Condicion"] == ca]["Propio"].mean(), df_xg[df_xg["Condicion"] == cb]["Propio"].mean()
        xa, xb = df_xg[(df_xg["Equipo"] == eq_a) & (df_xg["Condicion"] == ca)]["Propio"].mean(), df_xg[(df_xg["Equipo"] == eq_b) & (df_xg["Condicion"] == cb)]["Propio"].mean()
        if not np.isnan(xa) and m_xg_a > 0: lam_a = lam_a*0.55 + (xa/m_xg_a * (m_gf_loc if a_es_local else m_gf_vis))*0.45
        if not np.isnan(xb) and m_xg_b > 0: lam_b = lam_b*0.55 + (xb/m_xg_b * (m_gf_vis if a_es_local else m_gf_loc))*0.45
    return round(float(np.clip(lam_a, 0.15, 5.0)), 3), round(float(np.clip(lam_b, 0.15, 5.0)), 3)

def montecarlo(lam_a, lam_b):
    rng = np.random.default_rng(42)
    ga, gb = rng.poisson(lam_a, MONTECARLO_N), rng.poisson(lam_b, MONTECARLO_N)
    df_m = pd.DataFrame([{"A": r, "B": v, "prob": float(np.mean((ga == r) & (gb == v)))} for r in range(8) for v in range(8)])
    return {"victoria": float(np.mean(ga > gb)), "empate": float(np.mean(ga == gb)), "derrota": float(np.mean(ga < gb)), "df": df_m}

# ──────────────────────────────────────────────────────────────────────
# COMPONENTES VISUALES
# ──────────────────────────────────────────────────────────────────────
def fig_probs(sim, na, nb):
    fig = go.Figure(go.Bar(x=[sim["victoria"]*100, sim["empate"]*100, sim["derrota"]*100], y=[f"Victoria {na}", "Empate", f"Victoria {nb}"], orientation="h", marker_color=[RED, GRAY, BLUE], text=[f"{sim['victoria']*100:.1f}%", f"{sim['empate']*100:.1f}%", f"{sim['derrota']*100:.1f}%"], textposition="outside"))
    fig.update_layout(**PLOT, height=200, xaxis=dict(**GRID, range=[0, 105], ticksuffix="%"), showlegend=False)
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

def fig_radar(df, eq_a, eq_b, cond_a="General", cond_b="General"):
    mets = ["Posesión de balón", "Tiros totales", "Tiros al arco", "Pases totales", "Goles esperados (xG)", "Córners", "Quites", "Intercepciones"]
    mets = [m for m in mets if m in df["Métrica"].values]
    
    def get_val(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General": d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0

    va, vb = [get_val(eq_a, cond_a, m) for m in mets], [get_val(eq_b, cond_b, m) for m in mets]
    mx = [max(a, b, 0.001) for a, b in zip(va, vb)]
    van, vbn = [a/m for a, m in zip(va, mx)], [b/m for b, m in zip(vb, mx)]
    
    fig = go.Figure()
    for v, n, c in [(van, f"{eq_a} ({cond_a})", RED), (vbn, f"{eq_b} ({cond_b})", BLUE)]:
        fig.add_trace(go.Scatterpolar(r=v + [v[0]], theta=mets + [mets[0]], fill="toself", name=n, line=dict(color=c, width=2), fillcolor=f"rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},0.2)"))
    fig.update_layout(**PLOT, height=400, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, range=[0, 1], gridcolor="#1c2a40")))
    return fig

def fig_matriz_ranking(df, metrica, condicion):
    d = df[df["Métrica"] == metrica].copy()
    if condicion != "General": d = d[d["Condicion"] == condicion]
    res = d.groupby("Equipo").agg(Propio=("Propio", "mean"), Concedido=("Concedido", "mean")).reset_index()
    if res.empty: return go.Figure()
    m_p, m_c = res["Propio"].mean(), res["Concedido"].mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=res["Concedido"], y=res["Propio"], mode="markers+text", text=res["Equipo"], textposition="top center", marker=dict(size=12, color=RED, opacity=0.8, line=dict(width=1, color="white"))))
    fig.add_vline(x=m_c, line=dict(color=GRAY, dash="dot"))
    fig.add_hline(y=m_p, line=dict(color=GRAY, dash="dot"))
    fig.update_layout(**PLOT, height=500, xaxis_title=f"{metrica} Concedido", yaxis_title=f"{metrica} Propio", xaxis=dict(**GRID), yaxis=dict(**GRID))
    return fig

# ──────────────────────────────────────────────────────────────────────
# NAVEGACIÓN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Excel", value="Fecha_x_fecha_lpf.xlsx")
    st.markdown("---")
    # Agregado de vuelta: 🎭 Estilos de Juego
    nav = st.radio("", ["🔮 Predictor", "📊 Rankings", "🔄 Head-to-Head", "📖 Perfil por Rival", "🎭 Estilos de Juego"], label_visibility="collapsed")

if not os.path.exists(ruta):
    st.warning("No se encontró el Excel."); st.stop()

datos = cargar_excel(ruta)
if not datos: st.error("Sin datos."); st.stop()

df = construir_df(datos)
equipos, metricas = sorted(df["Equipo"].unique()), sorted(df["Métrica"].unique())
st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# VISTAS
# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Predictor de Partidos</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    eq_a = c1.selectbox("Local", equipos)
    eq_b = c2.selectbox("Visitante", equipos, index=1)
    es_loc = c3.toggle("Ventaja local", value=True)
    
    if st.button("🚀 SIMULAR"):
        lam_a, lam_b = calcular_lambdas(df, eq_a, eq_b, es_loc)
        sim = montecarlo(lam_a, lam_b)
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi"><div class="lbl">V. {eq_a}</div><div class="val">{sim["victoria"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="lbl">Empate</div><div class="val">{sim["empate"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="lbl">V. {eq_b}</div><div class="val">{sim["derrota"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        
        t1, t2, t3 = st.tabs(["📊 Probabilidades", "🎯 Marcadores exactos", "🕸️ Radar"])
        with t1: 
            st.plotly_chart(fig_probs(sim, eq_a, eq_b), use_container_width=True)
        with t2:
            st.plotly_chart(fig_marcadores(sim, eq_a, eq_b), use_container_width=True)
        with t3: 
            st.plotly_chart(fig_radar(df, eq_a, eq_b, "Local" if es_loc else "Visitante", "Visitante" if es_loc else "Local"), use_container_width=True)

elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings y Matriz de Eficiencia</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([4, 3, 3])
    met_sel = c1.selectbox("Métrica", metricas)
    cond_sel = c2.radio("Condición", ["General", "Local", "Visitante"], horizontal=True)
    vista_sel = c3.radio("Vista", ["Barras (Ranking)", "Matriz (Propio vs Concedido)"], horizontal=True)
    
    if vista_sel == "Barras (Ranking)":
        p_sel = st.radio("Enfoque", ["Propio 🟢", "Concedido 🔴"], horizontal=True)
        col = "Propio" if "Propio" in p_sel else "Concedido"
        df_r = ranking(df[df["Condicion"]==cond_sel] if cond_sel!="General" else df, met_sel, col, met_sel in METRICAS_MENOS_ES_MEJOR)
        st.plotly_chart(go.Figure(go.Bar(x=df_r["Promedio"], y=df_r["Equipo"], orientation="h", marker_color=RED, text=df_r["Promedio"], textposition="outside")).update_layout(**PLOT, height=500), use_container_width=True)
    else:
        st.plotly_chart(fig_matriz_ranking(df, met_sel, cond_sel), use_container_width=True)

elif nav == "🔄 Head-to-Head":
    st.markdown('<div class="section-title">🔄 Head-to-Head Comparativo</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    ea = c1.selectbox("Equipo A", equipos, key="ea")
    ca = c1.selectbox("Condición A", ["General", "Local", "Visitante"], key="ca")
    
    eb = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1), key="eb")
    cb = c2.selectbox("Condición B", ["General", "Local", "Visitante"], key="cb")

    if ea == eb and ca == cb:
        st.info("⚠️ Seleccioná equipos o condiciones diferentes para comparar.")
    else:
        st.markdown("### Tabla Comparativa de Datos Exactos")
        
        def get_full_stats(eq, cond):
            d = df[df["Equipo"] == eq]
            if cond != "General": 
                d = d[d["Condicion"] == cond]
            return d.groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)

        stats_a = get_full_stats(ea, ca)
        stats_b = get_full_stats(eb, cb)
        
        idx = stats_a.index.intersection(stats_b.index)

        if idx.empty:
            st.warning("No hay suficientes datos para comparar a estos equipos en estas condiciones.")
        else:
            col_a = f"{ea} ({ca})"
            col_b = f"{eb} ({cb})"
            
            c_a_fav = f"{col_a} (A Favor)"
            c_b_fav = f"{col_b} (A Favor)"
            c_a_con = f"{col_a} (En Contra)"
            c_b_con = f"{col_b} (En Contra)"

            df_h2h = pd.DataFrame({
                c_a_fav: stats_a.loc[idx, "Propio"].values,
                c_b_fav: stats_b.loc[idx, "Propio"].values,
                c_a_con: stats_a.loc[idx, "Concedido"].values,
                c_b_con: stats_b.loc[idx, "Concedido"].values
            }, index=idx)

            def highlight_winner(row):
                m = row.name
                styles = [""] * 4 
                val_a = row[c_a_fav] 
                val_b = row[c_b_fav]
                
                if val_a != val_b:
                    is_less_better = m in METRICAS_MENOS_ES_MEJOR
                    a_wins = (val_a > val_b) if not is_less_better else (val_a < val_b)
                    if a_wins:
                        styles[0] = "background-color: rgba(34, 197, 94, 0.2)"
                    else:
                        styles[1] = "background-color: rgba(34, 197, 94, 0.2)"
                return styles

            st.dataframe(df_h2h.style.apply(highlight_winner, axis=1), use_container_width=True)
            
            st.markdown("---")
            st.plotly_chart(fig_radar(df, ea, eb, ca, cb), use_container_width=True)

elif nav == "📖 Perfil por Rival":
    st.markdown('<div class="section-title">📖 Perfil por Rival</div>', unsafe_allow_html=True)
    e_sel = st.selectbox("Equipo", equipos)
    m_sel = st.selectbox("Métrica", metricas)
    d_eq = df[(df["Equipo"] == e_sel) & (df["Métrica"] == m_sel)].sort_values("nFecha" if "nFecha" in df.columns else "n_Fecha")
    
    if not d_eq.empty:
        fig = go.Figure([
            go.Bar(x=d_eq["Rival"], y=d_eq["Propio"], name="Favor", marker_color=RED), 
            go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], name="Contra", marker_color=GRAY)
        ])
        fig.update_layout(**PLOT, barmode="group")
        st.plotly_chart(fig, use_container_width=True)

elif nav == "🎭 Estilos de Juego":
    st.markdown('<div class="section-title">🎭 Matriz de Estilos de Juego</div>', unsafe_allow_html=True)
    st.markdown("Esta matriz clasifica a los equipos basándose en su posesión (Eje X) y su volumen ofensivo (Eje Y).")

    # Definimos las dos métricas clave (buscamos xG, si no hay, usamos Tiros totales)
    metrica_ofensiva = "Goles esperados (xG)" if "Goles esperados (xG)" in metricas else "Tiros totales"
    metrica_posesion = "Posesión de balón"
    
    if metrica_posesion not in metricas or metrica_ofensiva not in metricas:
        st.warning("Faltan métricas de Posesión o Tiros/xG en el Excel para armar la matriz.")
    else:
        # Extraemos los promedios
        df_pos = df[df["Métrica"] == metrica_posesion].groupby("Equipo")["Propio"].mean()
        df_ata = df[df["Métrica"] == metrica_ofensiva].groupby("Equipo")["Propio"].mean()
        
        df_estilos = pd.DataFrame({"Posesion": df_pos, "Ofensiva": df_ata}).dropna()
        
        # Calculamos la media de la liga para trazar los cuadrantes
        media_pos = df_estilos["Posesion"].mean()
        media_ata = df_estilos["Ofensiva"].mean()

        fig = go.Figure()
        
        # Trazamos los equipos
        fig.add_trace(go.Scatter(
            x=df_estilos["Posesion"], 
            y=df_estilos["Ofensiva"], 
            mode="markers+text", 
            text=df_estilos.index, 
            textposition="top center",
            marker=dict(size=12, color=RED, opacity=0.8, line=dict(width=1, color="white"))
        ))
        
        # Trazamos los ejes cruzados (Promedios)
        fig.add_vline(x=media_pos, line=dict(color=GRAY, dash="dash"))
        fig.add_hline(y=media_ata, line=dict(color=GRAY, dash="dash"))
        
        # Anotaciones de los Cuadrantes
        fig.add_annotation(x=df_estilos["Posesion"].max(), y=df_estilos["Ofensiva"].max(), text="OFENSIVO DE POSESIÓN", showarrow=False, font=dict(color="#22c55e", size=11), xanchor="right")
        fig.add_annotation(x=df_estilos["Posesion"].min(), y=df_estilos["Ofensiva"].max(), text="OFENSIVO DIRECTO", showarrow=False, font=dict(color="#f59e0b", size=11), xanchor="left")
        fig.add_annotation(x=df_estilos["Posesion"].max(), y=df_estilos["Ofensiva"].min(), text="DEFENSIVO DE POSESIÓN", showarrow=False, font=dict(color="#3b82f6", size=11), xanchor="right")
        fig.add_annotation(x=df_estilos["Posesion"].min(), y=df_estilos["Ofensiva"].min(), text="DEFENSIVO REACTIVO", showarrow=False, font=dict(color="#ef4444", size=11), xanchor="left")

        fig.update_layout(
            **PLOT, 
            height=600, 
            xaxis_title="Promedio de Posesión de Balón (%)", 
            yaxis_title=f"Volumen de Ataque ({metrica_ofensiva})", 
            xaxis=dict(**GRID), yaxis=dict(**GRID)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla resumen debajo
        def categorizar(row):
            if row["Posesion"] > media_pos and row["Ofensiva"] > media_ata: return "🟢 Ofensivo de Posesión (Elaboran y Atacan)"
            elif row["Posesion"] <= media_pos and row["Ofensiva"] > media_ata: return "🟠 Ofensivo Directo (Contragolpe / Verticales)"
            elif row["Posesion"] > media_pos and row["Ofensiva"] <= media_ata: return "🔵 Defensivo de Posesión (Tenencia pasiva)"
            else: return "🔴 Defensivo Reactivo (Bloque bajo)"
            
        df_estilos["Categoría Asignada"] = df_estilos.apply(categorizar, axis=1)
        st.dataframe(df_estilos.sort_values(["Categoría Asignada", "Ofensiva"], ascending=[True, False]), use_container_width=True)
