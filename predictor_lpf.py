import re, os, numpy as np, pandas as pd, plotly.graph_objects as go, streamlit as st

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y MOTOR MATEMÁTICO V8.1 (CALIBRADO)
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Scouting", page_icon="⚽", layout="wide")

MONTECARLO_N, RED, BLUE, GRAY = 15000, "#e63946", "#3b82f6", "#64748b"
LIGA_MEDIA_GOLES, REGRESION_K, MAX_ROTATION_PENALTY = 1.18, 4, 0.12

st.markdown("""<style>
    .stApp { background: #080d18; color: #dde3ee; }
    h1 { font-family:'Bebas Neue'; color:#e63946; letter-spacing:3px; }
    .section-title { font-family:'Bebas Neue'; font-size:1.3rem; color:#e63946; border-bottom:1px solid #1c2a40; padding-bottom:8px; margin:28px 0 18px; }
    .kpi { background:linear-gradient(135deg,#0f1829,#162035); border:1px solid #1c2a40; border-left:4px solid #e63946; border-radius:10px; padding:16px; text-align:center; }
    .kpi.draw { border-left-color:#64748b; } .kpi.loss { border-left-color:#3b82f6; }
    .kpi .val { font-family:'Bebas Neue'; font-size:42px; color:#e63946; line-height:1; }
    .kpi.draw .val { color:#94a3b8; } .kpi.loss .val { color:#60a5fa; }
    .note { background:#0f1829; border:1px solid #1c2a40; border-radius:8px; padding:10px; font-size:12px; color:#64748b; margin-top:8px; }
</style>""", unsafe_allow_html=True)

def soft_clip_pro(x):
    if x > 1.8: return 1.8 + (x - 1.8) * 0.3
    if x < 0.5: return 0.5 - (0.5 - x) * 0.3
    return x

def calcular_lambdas(df, eq_a, eq_b, es_local, rot_a=0, rot_b=0):
    df_r = df[df["Métrica"] == "Resultado"].copy()
    if df_r.empty: return 1.2, 1.0
    m_gf_loc = df_r[df_r["Condicion"]=="Local"]["Propio"].mean()
    m_gf_vis = df_r[df_r["Condicion"]=="Visitante"]["Propio"].mean()

    def get_team_stats(eq, cond):
        d_spec = df_r[(df_r["Equipo"] == eq) & (df_r["Condicion"] == cond)]
        d_gen = df_r[df_r["Equipo"] == eq]
        n_gen = len(d_gen)
        prior = m_gf_loc if cond == "Local" else m_gf_vis
        if not d_spec.empty:
            f_ata = (d_spec["Propio"].mean()*0.7 + d_gen["Propio"].mean()*0.3)
            f_def = (d_spec["Concedido"].mean()*0.7 + d_gen["Concedido"].mean()*0.3)
        else:
            f_ata = d_gen["Propio"].mean() if n_gen > 0 else prior
            f_def = d_gen["Concedido"].mean() if n_gen > 0 else prior
        peso = n_gen / (n_gen + REGRESION_K)
        f_ata = (peso * f_ata + (1-peso)*prior)
        f_def = (peso * f_def + (1-peso)*prior)
        return f_ata / prior, f_def / prior

    ata_a, def_a = get_team_stats(eq_a, "Local" if es_local else "Visitante")
    ata_b, def_b = get_team_stats(eq_b, "Visitante" if es_local else "Local")
    lam_a = soft_clip_pro(ata_a * def_b) * (m_gf_loc if es_local else m_gf_vis)
    lam_b = soft_clip_pro(ata_b * def_a) * (m_gf_vis if es_local else m_gf_loc)

    df_xg = df[df["Métrica"] == "Goles esperados (xG)"]
    if not df_xg.empty:
        xg_a, xg_b = df_xg[df_xg["Equipo"] == eq_a]["Propio"].mean(), df_xg[df_xg["Equipo"] == eq_b]["Propio"].mean()
        m_xg = df_xg["Propio"].mean()
        if not np.isnan(xg_a): lam_a = lam_a * 0.75 + (xg_a / m_xg * (m_gf_loc if es_local else m_gf_vis)) * 0.25
        if not np.isnan(xg_b): lam_b = lam_b * 0.75 + (xg_b / m_xg * (m_gf_vis if es_local else m_gf_loc)) * 0.25

    if rot_a > 0: lam_a *= (1 - rot_a * MAX_ROTATION_PENALTY); lam_b *= (1 + rot_a * 0.05)
    if rot_b > 0: lam_b *= (1 - rot_b * MAX_ROTATION_PENALTY); lam_a *= (1 + rot_b * 0.05)
    return round(float(np.clip(lam_a, 0.4, 3.5)), 3), round(float(np.clip(lam_b, 0.4, 3.5)), 3)

@st.cache_data(ttl=120)
def preparar_datos(ruta):
    if not os.path.exists(ruta): return None
    xl, filas = pd.ExcelFile(ruta), []
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE): continue
        df = pd.read_excel(ruta, sheet_name=hoja, header=None)
        nf = int(re.search(r"\d+", hoja).group())
        for i in range(len(df)):
            c0 = str(df.iloc[i, 0])
            if " vs " in c0.lower():
                loc, vis = re.split(r" vs ", c0, flags=re.IGNORECASE)[0:2]
                j = i + 1
                while j < len(df) and str(df.iloc[j, 0]).strip() != "" and " vs " not in str(df.iloc[j, 0]).lower():
                    if pd.notna(df.iloc[j, 1]):
                        v1, v2 = str(df.iloc[j, 1]).replace('%','').replace(',','.'), str(df.iloc[j, 2]).replace('%','').replace(',','.')
                        filas.append({"nFecha": nf, "Equipo": loc.strip(), "Rival": vis.strip(), "Condicion": "Local", "Métrica": str(df.iloc[j,0]), "Propio": float(v1), "Concedido": float(v2)})
                        filas.append({"nFecha": nf, "Equipo": vis.strip(), "Rival": loc.strip(), "Condicion": "Visitante", "Métrica": str(df.iloc[j,0]), "Propio": float(v2), "Concedido": float(v1)})
                    j += 1
    return pd.DataFrame(filas)

df_full = preparar_datos("Fecha_x_fecha_lpf.xlsx")
if df_full is not None:
    equipos = sorted(df_full["Equipo"].unique())
    with st.sidebar:
        st.markdown("## ⚽ LPF 2026")
        nav = st.radio("", ["🔮 Predictor", "📊 Rankings", "🔄 Comparador H2H"])

    if nav == "🔮 Predictor":
        st.markdown("<h1>Predictor Pro v8.1</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([4, 4, 2])
        eq_a, eq_b, es_loc = c1.selectbox("Local", equipos), c2.selectbox("Visitante", equipos, index=1), c3.toggle("Localía", True)
        r1, r2 = st.columns(2)
        rot_a = r1.slider(f"Rotación {eq_a}", 0.0, 1.0, 0.4) if r1.checkbox(f"{eq_a} rota") else 0
        rot_b = r2.slider(f"Rotación {eq_b}", 0.0, 1.0, 0.4) if r2.checkbox(f"{eq_b} rota") else 0
        if st.button("🚀 SIMULAR"):
            la, lb = calcular_lambdas(df_full, eq_a, eq_b, es_loc, rot_a, rot_b)
            rng = np.random.default_rng(42)
            ga, gb = rng.poisson(la, MONTECARLO_N), rng.poisson(lb, MONTECARLO_N)
            p_v, p_e, p_d = np.mean(ga > gb), np.mean(ga == gb), np.mean(ga < gb)
            res_cols = st.columns(3)
            res_cols[0].markdown(f'<div class="kpi"><div class="val">{p_v*100:.1f}%</div><div>V. {eq_a}</div></div>', unsafe_allow_html=True)
            res_cols[1].markdown(f'<div class="kpi draw"><div class="val">{p_e*100:.1f}%</div><div>Empate</div></div>', unsafe_allow_html=True)
            res_cols[2].markdown(f'<div class="kpi loss"><div class="val">{p_d*100:.1f}%</div><div>V. {eq_b}</div></div>', unsafe_allow_html=True)
            df_m = pd.DataFrame({"A": ga, "B": gb}); top8 = df_m.value_counts().nlargest(8).reset_index()
            top8["Res"] = top8["A"].astype(str) + " - " + top8["B"].astype(str)
            fig = go.Figure(go.Bar(x=(top8["count"]/MONTECARLO_N)*100, y=top8["Res"], orientation="h", marker_color=RED))
            fig.update_layout(title="Marcadores", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    elif nav == "📊 Rankings":
        st.markdown("<h1>Rankings</h1>", unsafe_allow_html=True)
        m_sel = st.selectbox("Métrica", sorted(df_full["Métrica"].unique()))
        df_rank = df_full[df_full["Métrica"] == m_sel].groupby("Equipo")["Propio"].mean().sort_values(ascending=False).reset_index()
        fig = go.Figure(go.Bar(x=df_rank["Propio"], y=df_rank["Equipo"], orientation="h", marker_color=BLUE))
        fig.update_layout(height=600, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    elif nav == "🔄 Comparador H2H":
        st.markdown("<h1>H2H</h1>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        e1, e2 = c1.selectbox("Eq 1", equipos), c2.selectbox("Eq 2", equipos, index=1)
        s1, s2 = df_full[df_full["Equipo"]==e1].groupby("Métrica")["Propio"].mean(), df_full[df_full["Equipo"]==e2].groupby("Métrica")["Propio"].mean()
        st.dataframe(pd.DataFrame({e1: s1, e2: s2}).round(2), use_container_width=True)
else: st.error("No se encontró el Excel.")
