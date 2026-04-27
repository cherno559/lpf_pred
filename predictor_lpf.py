"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v10.1 · Professional UI Edition)
─────────────────────────────────────────────────────────────────────────────
Cambios en v10.1:
  - Rediseño de UI con CSS personalizado (Estética Dark/Elite).
  - Match Cards dinámicas para el Predictor con barras de probabilidad.
  - Organización por contenedores para evitar el desorden visual.
  - Bloque lógico (xG Sintético y Motor Poisson) preservado al 100%.
"""
import re, os, math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
 
# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILOS DE ÉLITE
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Analítica Pro", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")
 
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
    /* Estética General */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #0b0f19; color: #e2e8f0; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background: #111827 !important; border-right: 1px solid #1f2937; }
    
    /* Títulos y Secciones */
    h1 { font-family:'Bebas Neue', cursive !important; font-size:3.5rem !important; color:#ffffff !important; letter-spacing:2px; margin-bottom:1rem; }
    .section-title { font-family:'Bebas Neue', cursive; font-size:1.8rem; letter-spacing:2px; color:#ef4444; border-bottom:2px solid #1f2937; padding-bottom:10px; margin-bottom:25px; text-transform:uppercase; }
    
    /* Match Card Predictor */
    .match-card { background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 24px; margin-bottom: 20px; }
    .team-name { font-family: 'Rajdhani', sans-serif; font-weight: 700; font-size: 1.5rem; color: #ffffff; text-align: center; }
    .prob-bar-container { background: #21262d; border-radius: 8px; height: 12px; width: 100%; margin: 10px 0; overflow: hidden; display: flex; }
    .prob-win { background: #ef4444; height: 100%; }
    .prob-draw { background: #6b7280; height: 100%; }
    .prob-loss { background: #3b82f6; height: 100%; }
    
    /* KPIs */
    .kpi-box { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; text-align: center; }
    .kpi-label { font-family: 'Rajdhani'; font-size: 12px; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: 1.5px; }
    .kpi-value { font-family: 'Bebas Neue'; font-size: 2.5rem; color: #ffffff; margin-top: 5px; }
    
    /* Tablas y Estilo */
    .stDataFrame { border: 1px solid #30363d !important; border-radius: 8px !important; }
    .note { background: #0d1117; border-left: 4px solid #ef4444; padding: 15px; font-size: 13px; color: #8b949e; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)
 
# ── Parámetros de Motor (Bloque Puro) ───────────────────────────────────────────────
W_XG = 0.75
K_SHRINK = 6.0          
K_PRIOR  = 4.0          
PRIOR_ATK_SCALE = 0.35  
PRIOR_DEF_SCALE = 0.25  
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.5, 1.0
LAM_MIN, LAM_MAX = 0.25, 4.50
RED, BLUE, GRAY = "#ef4444", "#3b82f6", "#6b7280"
PLOT = dict(font=dict(family="Rajdhani", size=13, color="#e2e8f0"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=20, t=36, b=10))
 
# ──────────────────────────────────────────────────────────────────────
# PROCESAMIENTO LÓGICO (Bloque Puro - No Tocar)
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
                filas.append({**base, "Equipo": p["local"], "Rival": p["visitante"], "Condicion": "Local", "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"],"Rival": p["local"], "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)
 
@st.cache_data(ttl=120, show_spinner=False)
def calcular_tabla(df: pd.DataFrame, condicion: str = "General") -> pd.DataFrame:
    dr = df[df["Métrica"] == "Resultado"].copy()
    if condicion != "General": dr = dr[dr["Condicion"] == condicion]
    if dr.empty: return pd.DataFrame()
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
        gf, gc = d["Propio"].sum(), d["Concedido"].sum()
        rows.append({"Equipo": eq, "PJ": pj, "V": int(v), "E": int(e), "D": int(d_), "GF": gf, "GC": gc, "PTS": pts, "PPJ": pts / pj, "EFEC%": (pts / (pj * 3)) * 100})
    tabla = pd.DataFrame(rows).sort_values(["EFEC%", "PTS", "GF"], ascending=[False, False, False]).reset_index(drop=True)
    tabla["Pos"] = tabla.index + 1
    ppj_mean = tabla["PPJ"].mean()
    tabla["PPJ_norm"] = tabla["PPJ"] / ppj_mean if ppj_mean > 0 else 1.0
    tabla["prior_atk"] = (1.0 + (tabla["PPJ_norm"] - 1.0) * PRIOR_ATK_SCALE).clip(0.5, 2.0)
    tabla["prior_def"] = (1.0 - (tabla["PPJ_norm"] - 1.0) * PRIOR_DEF_SCALE).clip(0.5, 2.0)
    return tabla.set_index("Equipo")
 
def _get_prior(tabla, eq):
    return (float(tabla.loc[eq, "prior_atk"]), float(tabla.loc[eq, "prior_def"])) if tabla is not None and eq in tabla.index else (1.0, 1.0)

# ──────────────────────────────────────────────────────────────────────
# MOTOR PREDICTIVO (Bloque Puro)
# ──────────────────────────────────────────────────────────────────────
def _adjusted_rate(d_spec, metrica, col, max_fecha_torneo, tabla, is_attack):
    df_m = d_spec[d_spec["Métrica"] == metrica]
    if df_m.empty: return np.nan
    fechas, valores, rivales = df_m["nFecha"].values, df_m[col].values, df_m["Rival"].values
    adj_vals = []
    for v, r in zip(valores, rivales):
        pa_r, pd_r = _get_prior(tabla, r)
        adj_vals.append(v / pd_r if is_attack and pd_r > 0 else v / pa_r if not is_attack and pa_r > 0 else v)
    w = np.where(fechas >= (max_fecha_torneo - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(adj_vals, weights=w))

@st.cache_data(ttl=120, show_spinner=False)
def _league_stats(df):
    dr, dx = df[df["Métrica"] == "Resultado"], df[df["Métrica"] == "xG_Estimado"]
    def ga(d, c): return d[d["Condicion"]==c]["Propio"].mean() if not d.empty else 1.0
    gh, gv, xh, xv = ga(dr, "Local"), ga(dr, "Visitante"), ga(dx, "Local"), ga(dx, "Visitante")
    return {"ref_home": W_XG*xh + (1-W_XG)*gh, "ref_away": W_XG*xv + (1-W_XG)*gv}

def _strength(df, eq, cond, league, max_fecha_torneo, tabla):
    d_spec = df[(df["Equipo"] == eq) & (df["Condicion"] == cond)]
    ga, xa = _adjusted_rate(d_spec, "Resultado", "Propio", max_fecha_torneo, tabla, True), _adjusted_rate(d_spec, "xG_Estimado", "Propio", max_fecha_torneo, tabla, True)
    gd, xd = _adjusted_rate(d_spec, "Resultado", "Concedido", max_fecha_torneo, tabla, False), _adjusted_rate(d_spec, "xG_Estimado", "Concedido", max_fecha_torneo, tabla, False)
    n = len(d_spec[d_spec["Métrica"] == "Resultado"])
    atk_v, def_v = W_XG*(xa if not np.isnan(xa) else ga) + (1-W_XG)*ga, W_XG*(xd if not np.isnan(xd) else gd) + (1-W_XG)*gd
    ref_f, ref_a = (league["ref_home"], league["ref_away"]) if cond == "Local" else (league["ref_away"], league["ref_home"])
    pa, pd_ = _get_prior(tabla, eq)
    atk_o, def_o = (atk_v/ref_f) if ref_f>0 else pa, (def_v/ref_a) if ref_a>0 else pd_
    return (n*atk_o + K_PRIOR*pa)/(n + K_PRIOR), (n*def_o + K_PRIOR*pd_)/(n + K_PRIOR), n

def calcular_lambdas(df, ea, eb, es_loc, tabla):
    l, max_f = _league_stats(df), int(df["nFecha"].max())
    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")
    aa, da, _ = _strength(df, ea, ca, l, max_f, tabla)
    ab, db, _ = _strength(df, eb, cb, l, max_f, tabla)
    la, lb = (l["ref_home"] if ca=="Local" else l["ref_away"])*aa*db, (l["ref_home"] if cb=="Local" else l["ref_away"])*ab*da
    return round(float(np.clip(la, LAM_MIN, LAM_MAX)), 3), round(float(np.clip(lb, LAM_MIN, LAM_MAX)), 3)

def montecarlo(la, lb):
    def pmf(lam, k): return np.exp(k * np.log(max(lam, 1e-9)) - lam - np.array([math.log(math.factorial(x)) for x in np.arange(k+1)]))
    pa, pb = pmf(la, MAX_GOALS_MATRIX), pmf(lb, MAX_GOALS_MATRIX)
    M = np.outer(pa, pb)
    rho = max(DC_RHO, -0.9 / max(la * lb, 0.01))
    M[0,0], M[0,1], M[1,0], M[1,1] = M[0,0]*(1-la*lb*rho), M[0,1]*(1+la*rho), M[1,0]*(1+lb*rho), M[1,1]*(1-rho)
    M /= M.sum()
    return {"vic": float(np.tril(M, -1).sum()), "emp": float(np.trace(M)), "der": float(np.triu(M, 1).sum()), "matrix": M}

# ──────────────────────────────────────────────────────────────────────
# UI COMPONENTS (Radares y Visuales)
# ──────────────────────────────────────────────────────────────────────
def fig_radar(df, ea, eb, ca, cb):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco", "xG_Estimado", "Pases totales"] if m in df["Métrica"].values]
    if not mets: return go.Figure()
    def gv(eq, c, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if c != "General": d = d[d["Condicion"] == c]
        return d["Propio"].mean() if not d.empty else 0.0
    va, vb = [gv(ea, ca, m) for m in mets], [gv(eb, cb, m) for m in mets]
    mx = [max(df[df["Métrica"] == m].groupby("Equipo")["Propio"].mean().max(), 1e-6) for m in mets]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[v/m for v,m in zip(va,mx)]+[va[0]/mx[0]], theta=mets+[mets[0]], fill="toself", name=ea, line=dict(color=RED), text=[f"{m}: {v:.1f}" for m,v in zip(mets,va)]+[f"{mets[0]}: {va[0]:.1f}"], hoverinfo="name+text"))
    fig.add_trace(go.Scatterpolar(r=[v/m for v,m in zip(vb,mx)]+[vb[0]/mx[0]], theta=mets+[mets[0]], fill="toself", name=eb, line=dict(color=BLUE), text=[f"{m}: {v:.1f}" for m,v in zip(mets,vb)]+[f"{mets[0]}: {vb[0]:.1f}"], hoverinfo="name+text"))
    layout = PLOT.copy()
    layout.update(height=450, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, showticklabels=False, gridcolor="#1f2937", range=[0,1])), margin=dict(l=60, r=60, t=40, b=40))
    fig.update_layout(**layout)
    return fig

# ──────────────────────────────────────────────────────────────────────
# APP MAIN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='font-family:Bebas Neue; color:white; letter-spacing:2px;'>⚽ LPF SCOUTING</h2>", unsafe_allow_html=True)
    ruta = st.text_input("📂 Base de Datos (Excel)", "Fecha_x_fecha_lpf.xlsx")
    nav = st.radio("", ["🔮 Predictor Pro", "📊 Rankings", "🔄 Head-to-Head", "📋 Tabla de Posiciones"], label_visibility="collapsed")

if not os.path.exists(ruta):
    st.error(f"Archivo '{ruta}' no encontrado. Por favor, verifica la ruta en el sidebar.")
    st.stop()

datos, df = cargar_excel(ruta), construir_df(cargar_excel(ruta))
tabla_gen = calcular_tabla(df, "General")
equipos = sorted(df["Equipo"].unique())

# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor Pro":
    st.markdown('<div class="section-title">🔮 Predictor de Probabilidades Poisson</div>', unsafe_allow_html=True)
    
    col_sel1, col_sel2, col_sel3 = st.columns([4, 4, 2])
    ea = col_sel1.selectbox("Equipo Local", equipos)
    eb = col_sel2.selectbox("Equipo Visitante", equipos, index=min(1, len(equipos)-1))
    loc_on = col_sel3.toggle("Bono Localía", True)
    
    if st.button("🚀 GENERAR PREDICCIÓN"):
        la, lb = calcular_lambdas(df, ea, eb, loc_on, tabla_gen)
        sim = montecarlo(la, lb)
        
        # Match Card Visual
        st.markdown(f"""
        <div class="match-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="width: 40%;" class="team-name">{ea}</div>
                <div style="width: 20%; text-align: center; font-family: 'Bebas Neue'; font-size: 2rem;">VS</div>
                <div style="width: 40%;" class="team-name">{eb}</div>
            </div>
            <div class="prob-bar-container">
                <div class="prob-win" style="width: {sim['vic']*100}%"></div>
                <div class="prob-draw" style="width: {sim['emp']*100}%"></div>
                <div class="prob-loss" style="width: {sim['der']*100}%"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-family: 'Rajdhani'; font-weight: 700; font-size: 0.9rem;">
                <span style="color: #ef4444;">LOCAL: {sim['vic']*100:.1f}%</span>
                <span style="color: #9ca3af;">EMPATE: {sim['emp']*100:.1f}%</span>
                <span style="color: #3b82f6;">VISITANTE: {sim['der']*100:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="kpi-box"><div class="kpi-label">λ Esperado {ea}</div><div class="kpi-value">{la:.2f}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="kpi-box"><div class="kpi-label">Prob. Marcador 0-0</div><div class="kpi-value">{sim["matrix"][0,0]*100:.1f}%</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="kpi-box"><div class="kpi-label">λ Esperado {eb}</div><div class="kpi-value">{lb:.2f}</div></div>', unsafe_allow_html=True)
        
        # Heatmap de Marcadores
        st.markdown('<div class="section-title" style="font-size: 1.2rem; margin-top:30px;">🎯 Probabilidades de Marcadores Exactos</div>', unsafe_allow_html=True)
        m = sim["matrix"][:5, :5]
        fig_m = go.Figure(data=go.Heatmap(z=m, x=[str(i) for i in range(5)], y=[str(i) for i in range(5)], text=[[f"{v*100:.1f}%" for v in row] for row in m], texttemplate="%{text}", colorscale='Reds', showscale=False))
        fig_m.update_layout(**PLOT, height=350, xaxis_title=f"Goles {eb}", yaxis_title=f"Goles {ea}", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_m, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings de Rendimiento</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    m_sel = c1.selectbox("Métrica", sorted(df["Métrica"].unique()))
    cond_sel = c2.radio("Filtro Condición", ["General", "Local", "Visitante"], horizontal=True)
    tipo_sel = c3.radio("Enfoque", ["A Favor", "En Contra"], horizontal=True)
    
    col_d = "Propio" if tipo_sel == "A Favor" else "Concedido"
    mask = (df["Condicion"] == cond_sel) if cond_sel != "General" else df.index.notna()
    res = df[mask & (df["Métrica"] == m_sel)].groupby("Equipo")[col_d].mean().sort_values(ascending=False).reset_index()
    
    fig = go.Figure(go.Bar(x=res[col_d], y=res["Equipo"], orientation='h', marker_color=RED if tipo_sel == "A Favor" else GRAY))
    fig.update_layout(**PLOT, height=700, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "🔄 Head-to-Head":
    st.markdown('<div class="section-title">🔄 Head-to-Head Comparativo</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    ea, eb = c1.selectbox("Equipo A", equipos), c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1))
    c3, c4 = st.columns(2)
    ca, cb = c3.radio(f"Contexto {ea}", ["General", "Local", "Visitante"], horizontal=True, key="ca"), c4.radio(f"Contexto {eb}", ["General", "Local", "Visitante"], horizontal=True, key="cb")
    
    st.plotly_chart(fig_radar(df, ea, eb, ca, cb), use_container_width=True)
    
    # Tabla Comparativa
    s1 = df[(df["Equipo"]==ea) & ((df["Condicion"]==ca) if ca!="General" else True)].groupby("Métrica")[["Propio","Concedido"]].mean().round(2)
    s2 = df[(df["Equipo"]==eb) & ((df["Condicion"]==cb) if cb!="General" else True)].groupby("Métrica")[["Propio","Concedido"]].mean().round(2)
    h2h = pd.DataFrame({f"{ea} ({ca[:3]}) Fav": s1["Propio"], f"{ea} ({ca[:3]}) Con": s1["Concedido"], f"{eb} ({cb[:3]}) Fav": s2["Propio"], f"{eb} ({cb[:3]}) Con": s2["Concedido"]}).dropna()
    st.dataframe(h2h, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "📋 Tabla de Posiciones":
    st.markdown('<div class="section-title">📋 Clasificación LPF por Efectividad</div>', unsafe_allow_html=True)
    v_tab = st.radio("Ver Tabla:", ["General", "Local", "Visitante"], horizontal=True)
    t_dyn = calcular_tabla(df, v_tab)
    if not t_dyn.empty:
        t_show = t_dyn.reset_index()[["Pos","Equipo","PJ","PTS","EFEC%","GF","GC","PPJ","prior_atk","prior_def"]].copy()
        t_show.columns = ["#","Equipo","PJ","PTS","Efectividad %","GF","GC","PPJ","Atk Prior","Def Prior"]
        st.dataframe(t_show.style.format({"Efectividad %": "{:.1f}%", "PPJ": "{:.2f}", "Atk Prior": "{:.2f}", "Def Prior": "{:.2f}"}), use_container_width=True, hide_index=True)
        st.markdown('<div class="note">La tabla se ordena automáticamente por <b>Efectividad %</b> para normalizar el rendimiento en calendarios asimétricos.</div>', unsafe_allow_html=True)
