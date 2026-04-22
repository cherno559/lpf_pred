"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v8.1 TOTAL)
────────────────────────────────────────────────────
Motor: Calibración Pro (Soft-Clip + Regresión Bayesiana)
UI: Full Dashboard (Predictor, Rankings, Radar, Matriz, Estilos)
"""

import re, os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# 1. CONFIGURACIÓN Y ESTILOS CSS
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Scouting Pro", page_icon="⚽", layout="wide")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #080d18; color: #dde3ee; }
    section[data-testid="stSidebar"] { background: #0c1220 !important; border-right: 1px solid #1c2a40; }
    h1 { font-family:'Bebas Neue',cursive !important; font-size:2.6rem !important; color:#e63946 !important; letter-spacing:3px; margin-bottom:0; }
    .section-title { font-family:'Bebas Neue',cursive; font-size:1.3rem; letter-spacing:3px; color:#e63946; border-bottom:1px solid #1c2a40; padding-bottom:8px; margin:28px 0 18px; text-transform:uppercase; }
    .kpi { background:linear-gradient(135deg,#0f1829,#162035); border:1px solid #1c2a40; border-left:4px solid #e63946; border-radius:10px; padding:16px; text-align:center; }
    .kpi.draw { border-left-color:#64748b; } .kpi.loss { border-left-color:#3b82f6; }
    .kpi .val { font-family:'Bebas Neue'; font-size:42px; color:#e63946; line-height:1; }
    .kpi.draw .val { color:#94a3b8; } .kpi.loss .val { color:#60a5fa; }
    .kpi .lbl { font-family:'Rajdhani'; font-size:12px; font-weight:700; color:#8899aa; text-transform:uppercase; margin-top:5px; }
    .note { background:#0f1829; border:1px solid #1c2a40; border-radius:8px; padding:10px; font-size:12px; color:#64748b; margin-top:8px; }
    .stTabs [data-baseweb="tab-list"] { background:#0f1829; padding:4px; border-radius:10px; }
    .stTabs [data-baseweb="tab"] { font-family:'Rajdhani'; font-weight:700; color:#64748b !important; }
    .stTabs [aria-selected="true"] { background:#e63946 !important; color:#fff !important; border-radius:7px; }
</style>
""", unsafe_allow_html=True)

# CONSTANTES
MONTECARLO_N, RED, BLUE, GRAY = 15000, "#e63946", "#3b82f6", "#64748b"
LIGA_MEDIA_GOLES, REGRESION_K, MAX_ROTATION_PENALTY = 1.18, 4, 0.12
PLOT_LAYOUT = dict(font=dict(family="Rajdhani", color="#dde3ee"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=40, b=10))

# ──────────────────────────────────────────────────────────────────────
# 2. MOTOR MATEMÁTICO (CALIBRADO V8.1)
# ──────────────────────────────────────────────────────────────────────

def soft_clip_pro(x):
    if x > 1.8: return 1.8 + (x - 1.8) * 0.3
    if x < 0.5: return 0.5 - (0.5 - x) * 0.3
    return x

def calcular_lambdas(df, eq_a, eq_b, es_local, rot_a=0, rot_b=0):
    df_r = df[df["Métrica"] == "Resultado"].copy()
    if df_r.empty: return 1.2, 1.0
    m_gf_loc, m_gf_vis = df_r[df_r["Condicion"]=="Local"]["Propio"].mean(), df_r[df_r["Condicion"]=="Visitante"]["Propio"].mean()

    def get_team_stats(eq, cond):
        d_spec, d_gen = df_r[(df_r["Equipo"] == eq) & (df_r["Condicion"] == cond)], df_r[df_r["Equipo"] == eq]
        n_gen, prior = len(d_gen), (m_gf_loc if cond == "Local" else m_gf_vis)
        if not d_spec.empty:
            f_ata, f_def = (d_spec["Propio"].mean()*0.7 + d_gen["Propio"].mean()*0.3), (d_spec["Concedido"].mean()*0.7 + d_gen["Concedido"].mean()*0.3)
        else: f_ata, f_def = (d_gen["Propio"].mean() if n_gen > 0 else prior), (d_gen["Concedido"].mean() if n_gen > 0 else prior)
        peso = n_gen / (n_gen + REGRESION_K)
        f_ata, f_def = (peso * f_ata + (1-peso)*prior), (peso * f_def + (1-peso)*prior)
        return f_ata / prior, f_def / prior

    ata_a, def_a = get_team_stats(eq_a, "Local" if es_local else "Visitante")
    ata_b, def_b = get_team_stats(eq_b, "Visitante" if es_local else "Local")
    lam_a = soft_clip_pro(ata_a * def_b) * (m_gf_loc if es_local else m_gf_vis)
    lam_b = soft_clip_pro(ata_b * def_a) * (m_gf_vis if es_local else m_gf_loc)

    df_xg = df[df["Métrica"] == "Goles esperados (xG)"]
    if not df_xg.empty:
        xg_a, xg_b, m_xg = df_xg[df_xg["Equipo"] == eq_a]["Propio"].mean(), df_xg[df_xg["Equipo"] == eq_b]["Propio"].mean(), df_xg["Propio"].mean()
        if not np.isnan(xg_a): lam_a = lam_a * 0.75 + (xg_a / m_xg * (m_gf_loc if es_local else m_gf_vis)) * 0.25
        if not np.isnan(xg_b): lam_b = lam_b * 0.75 + (xg_b / m_xg * (m_gf_vis if es_local else m_gf_loc)) * 0.25

    if rot_a > 0: lam_a *= (1 - rot_a * MAX_ROTATION_PENALTY)
    if rot_b > 0: lam_b *= (1 - rot_b * MAX_ROTATION_PENALTY)
    return round(float(np.clip(lam_a, 0.4, 3.5)), 3), round(float(np.clip(lam_b, 0.4, 3.5)), 3)

# ──────────────────────────────────────────────────────────────────────
# 3. FUNCIONES VISUALES
# ──────────────────────────────────────────────────────────────────────

def fig_radar(df, eq_a, eq_b, cond_a, cond_b):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco", "Pases totales", "Goles esperados (xG)", "Córners"] if m in df["Métrica"].values]
    if not mets: return go.Figure()
    def get_v(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General": d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0
    va, vb = [get_v(eq_a, cond_a, m) for m in mets], [get_v(eq_b, cond_b, m) for m in mets]
    mx = [max(a, b, 0.1) for a, b in zip(va, vb)]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[a/m for a,m in zip(va,mx)]+[va[0]/mx[0]], theta=mets+[mets[0]], fill='toself', name=eq_a, line=dict(color=RED)))
    fig.add_trace(go.Scatterpolar(r=[b/m for b,m in zip(vb,mx)]+[vb[0]/mx[0]], theta=mets+[mets[0]], fill='toself', name=eq_b, line=dict(color=BLUE)))
    fig.update_layout(**PLOT_LAYOUT, polar=dict(radialaxis=dict(visible=False), bgcolor="rgba(0,0,0,0)"))
    return fig

# ──────────────────────────────────────────────────────────────────────
# 4. CARGA DE DATOS Y FLUJO PRINCIPAL
# ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def cargar_datos(ruta):
    if not os.path.exists(ruta): return None
    xl, filas = pd.ExcelFile(ruta), []
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE): continue
        df = pd.read_excel(ruta, sheet_name=hoja, header=None)
        nf = int(re.search(r"\d+", hoja).group())
        for i in range(len(df)):
            c0 = str(df.iloc[i, 0])
            if " vs " in c0.lower():
                loc, vis = re.split(r" vs ", c0, flags=re.IGNORECASE)[:2]
                j = i + 1
                while j < len(df) and str(df.iloc[j, 0]).strip() != "" and " vs " not in str(df.iloc[j, 0]).lower():
                    if pd.notna(df.iloc[j, 1]):
                        v1 = float(str(df.iloc[j, 1]).replace('%','').replace(',','.'))
                        v2 = float(str(df.iloc[j, 2]).replace('%','').replace(',','.'))
                        filas.append({"nFecha": nf, "Equipo": loc.strip(), "Rival": vis.strip(), "Condicion": "Local", "Métrica": str(df.iloc[j,0]), "Propio": v1, "Concedido": v2})
                        filas.append({"nFecha": nf, "Equipo": vis.strip(), "Rival": loc.strip(), "Condicion": "Visitante", "Métrica": str(df.iloc[j,0]), "Propio": v2, "Concedido": v1})
                    j += 1
    return pd.DataFrame(filas)

df_full = cargar_datos("Fecha_x_fecha_lpf.xlsx")
if df_full is not None:
    equipos, metricas = sorted(df_full["Equipo"].unique()), sorted(df_full["Métrica"].unique())
    with st.sidebar:
        st.markdown("## ⚽ LPF 2026")
        nav = st.radio("", ["🔮 Predictor", "📊 Rankings", "🔄 Head-to-Head", "🎭 Estilos de Juego"], label_visibility="collapsed")

    st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

    if nav == "🔮 Predictor":
        c1, c2, c3 = st.columns([4, 4, 2])
        e_loc, e_vis, v_loc = c1.selectbox("Local", equipos), c2.selectbox("Visitante", equipos, index=1), c3.toggle("Localía", True)
        r1, r2 = st.columns(2); rot_a = r1.slider(f"Rotar {e_loc}", 0.0, 1.0, 0.0) if r1.checkbox(f"Rotar {e_loc}") else 0
        rot_b = r2.slider(f"Rotar {e_vis}", 0.0, 1.0, 0.0) if r2.checkbox(f"Rotar {e_vis}") else 0
        if st.button("🚀 SIMULAR"):
            la, lb = calcular_lambdas(df_full, e_loc, e_vis, v_loc, rot_a, rot_b)
            rng = np.random.default_rng(42); ga, gb = rng.poisson(la, MONTECARLO_N), rng.poisson(lb, MONTECARLO_N)
            pv, pe, pd = np.mean(ga > gb), np.mean(ga == gb), np.mean(ga < gb)
            res = st.columns(3)
            res[0].markdown(f'<div class="kpi"><div class="val">{pv*100:.1f}%</div><div class="lbl">V. {e_loc}</div></div>', unsafe_allow_html=True)
            res[1].markdown(f'<div class="kpi draw"><div class="val">{pe*100:.1f}%</div><div class="lbl">Empate</div></div>', unsafe_allow_html=True)
            res[2].markdown(f'<div class="kpi loss"><div class="val">{pd*100:.1f}%</div><div class="lbl">V. {e_vis}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="note">⚙️ V8.1 Calibrado | λ {e_loc}: {la} - λ {e_vis}: {lb}</div>', unsafe_allow_html=True)
            t1, t2 = st.tabs(["🎯 Marcadores", "🕸️ Radar"])
            with t1:
                df_m = pd.DataFrame({"A": ga, "B": gb}); top = df_m.value_counts().nlargest(8).reset_index()
                top["Score"] = top["A"].astype(str) + " - " + top["B"].astype(str)
                st.plotly_chart(go.Figure(go.Bar(x=top["Score"], y=(top["count"]/MONTECARLO_N)*100, marker_color=RED)).update_layout(**PLOT_LAYOUT))
            with t2: st.plotly_chart(fig_radar(df_full, e_loc, e_vis, "Local" if v_loc else "General", "Visitante" if v_loc else "General"), use_container_width=True)

    elif nav == "📊 Rankings":
        st.markdown('<div class="section-title">📊 Rankings y Matriz de Eficiencia</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([4, 3, 3])
        m_sel, cond_sel, vista = c1.selectbox("Métrica", metricas), c2.radio("Condición", ["General", "Local", "Visitante"], horizontal=True), c3.radio("Vista", ["Barras", "Matriz"], horizontal=True)
        if vista == "Barras":
            d_r = df_full[(df_full["Métrica"]==m_sel) & (df_full["Condicion"]==cond_sel if cond_sel!="General" else True)].groupby("Equipo")["Propio"].mean().sort_values(ascending=False).reset_index()
            st.plotly_chart(go.Figure(go.Bar(x=d_r["Propio"], y=d_r["Equipo"], orientation="h", marker_color=RED)).update_layout(**PLOT_LAYOUT, height=600, yaxis=dict(autorange="reversed")))
        else:
            d_mat = df_full[(df_full["Métrica"]==m_sel) & (df_full["Condicion"]==cond_sel if cond_sel!="General" else True)].groupby("Equipo").agg(P=("Propio","mean"), C=("Concedido","mean")).reset_index()
            fig = go.Figure(go.Scatter(x=d_mat["C"], y=d_mat["P"], mode="markers+text", text=d_mat["Equipo"], textposition="top center", marker=dict(size=12, color=RED)))
            fig.add_vline(x=d_mat["C"].mean(), line=dict(dash="dot")); fig.add_hline(y=d_mat["P"].mean(), line=dict(dash="dot"))
            st.plotly_chart(fig.update_layout(**PLOT_LAYOUT, xaxis_title="Concedido", yaxis_title="Propio"))

    elif nav == "🔄 Head-to-Head":
        c1, c2 = st.columns(2); eq1, eq2 = c1.selectbox("Equipo 1", equipos), c2.selectbox("Equipo 2", equipos, index=1)
        s1, s2 = df_full[df_full["Equipo"]==eq1].groupby("Métrica")["Propio"].mean(), df_full[df_full["Equipo"]==eq2].groupby("Métrica")["Propio"].mean()
        st.table(pd.DataFrame({eq1: s1, eq2: s2}).round(2).dropna())
        st.plotly_chart(fig_radar(df_full, eq1, eq2, "General", "General"), use_container_width=True)

    elif nav == "🎭 Estilos de Juego":
        st.markdown('<div class="section-title">🎭 Matriz de Estilos de Juego</div>', unsafe_allow_html=True)
        mo = "Goles esperados (xG)" if "Goles esperados (xG)" in metricas else "Tiros totales"
        if "Posesión de balón" in metricas:
            df_e = pd.DataFrame({"P": df_full[df_full["Métrica"]=="Posesión de balón"].groupby("Equipo")["Propio"].mean(), "O": df_full[df_full["Métrica"]==mo].groupby("Equipo")["Propio"].mean()}).dropna()
            mp, mo_m = df_e["P"].mean(), df_e["O"].mean()
            fig = go.Figure(go.Scatter(x=df_e["P"], y=df_e["O"], mode="markers+text", text=df_e.index, marker=dict(size=12, color=RED)))
            fig.add_vline(x=mp, line=dict(dash="dash", color=GRAY)); fig.add_hline(y=mo_m, line=dict(dash="dash", color=GRAY))
            st.plotly_chart(fig.update_layout(**PLOT_LAYOUT, height=600, xaxis_title="Posesión (%)", yaxis_title=mo))
            def cat(r):
                if r["P"]>mp and r["O"]>mo_m: return "🟢 Ofensivo Posesión"
                elif r["P"]<=mp and r["O"]>mo_m: return "🟠 Ofensivo Directo"
                return "🔴 Defensivo Reactivo" if r["P"]<=mp else "🔵 Defensivo Posesión"
            df_e["Estilo"] = df_e.apply(cat, axis=1)
            st.dataframe(df_e.sort_values("Estilo"), use_container_width=True)

else: st.error("No se encontró el archivo Excel.")
