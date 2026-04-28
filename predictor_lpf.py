"""
Plataforma de Scouting LPF 2026
─────────────────────────────────────────────────────────────────────────────
"""
import re, os, math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
 
# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILOS PROFESIONALES (CUSTOM UI)
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF Analytics | Scouting", layout="wide", initial_sidebar_state="expanded")
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Manrope:wght@400;600;800&display=swap');

/* Reset y tipografía base */
html, body, [class*="css"] {
    font-family: 'Manrope', sans-serif;
    background-color: #0a0a0c;
    color: #e0e0e0;
}

.stApp {
    background-color: #0a0a0c;
}

/* Ocultar elementos por defecto de Streamlit */
#MainMenu, footer, header {visibility: hidden;}

/* Banner Hero con Imagen Real */
.hero-banner {
    background: linear-gradient(to right, rgba(10, 10, 12, 1) 0%, rgba(10, 10, 12, 0.4) 50%, rgba(10, 10, 12, 1) 100%), 
                url('https://images.unsplash.com/photo-1518605368461-1eb7678b871c?q=80&w=2000&auto=format&fit=crop');
    background-size: cover;
    background-position: center 30%;
    padding: 50px 40px;
    border-radius: 12px;
    margin-bottom: 40px;
    border-bottom: 4px solid #ED1A3B; /* Acento Rojo Elite */
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.hero-subtitle {
    color: #ED1A3B;
    font-weight: 800;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 5px;
    margin-bottom: 5px;
}

.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 4rem;
    color: #ffffff;
    letter-spacing: 2px;
    line-height: 1;
    margin: 0;
}

/* Títulos de sección limpios */
.section-header {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: #ffffff;
    letter-spacing: 1.5px;
    border-left: 4px solid #ED1A3B;
    padding-left: 15px;
    margin: 40px 0 20px 0;
}

/* Marcador estilo Transmisión Deportiva (Broadcast) */
.broadcast-board {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #141417;
    border: 1px solid #2a2a30;
    border-radius: 8px;
    padding: 30px 40px;
    margin-top: 20px;
}

.team-block {
    flex: 1;
    text-align: center;
}

.team-block.home { border-right: 1px solid #2a2a30; }
.team-block.away { border-left: 1px solid #2a2a30; }

.t-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.2rem;
    color: #ffffff;
    letter-spacing: 1px;
    margin-bottom: 5px;
}

.t-prob {
    font-size: 3.5rem;
    font-weight: 800;
    color: #ED1A3B;
    line-height: 1;
}

.t-label {
    font-size: 0.8rem;
    color: #888890;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 5px;
}

.draw-block {
    flex: 0.8;
    text-align: center;
}
.draw-prob {
    font-size: 2.2rem;
    font-weight: 800;
    color: #888890;
}

/* Botones y controles */
.stButton>button {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.5rem;
    letter-spacing: 2px;
    background-color: #ED1A3B;
    color: #fff;
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    width: 100%;
    transition: background-color 0.3s;
}
.stButton>button:hover {
    background-color: #c41530;
    color: #fff;
}

.stSelectbox>div>div, .stTextInput>div>div, .stRadio>div>div { 
    background-color: #141417 !important; 
    border: 1px solid #2a2a30 !important; 
    color: #ffffff !important; 
    border-radius: 4px !important; 
}

/* Sidebar */
[data-testid="stSidebar"] { 
    background-color: #0f0f12 !important; 
    border-right: 1px solid #1f1f24 !important; 
}
.sidebar-logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.5rem;
    color: #ED1A3B;
    letter-spacing: 2px;
    text-align: center;
    margin-bottom: 30px;
    border-bottom: 1px solid #1f1f24;
    padding-bottom: 20px;
}

/* UI Elements */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 8px; }
.stTabs [data-baseweb="tab"] { font-family: 'Manrope', sans-serif !important; background: #141417 !important; border: 1px solid #2a2a30 !important; border-radius: 4px !important; color: #888890 !important; }
.stTabs [aria-selected="true"] { background: #ED1A3B !important; color: white !important; border-color: #ED1A3B !important; }
</style>
""", unsafe_allow_html=True)
 
# ── Parámetros de Motor ───────────────────────────────────────────────
W_XG = 0.75
K_SHRINK = 6.0          
K_PRIOR  = 4.0          
PRIOR_ATK_SCALE = 0.35  
PRIOR_DEF_SCALE = 0.25  
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.5, 1.0
LAM_MIN, LAM_MAX = 0.25, 4.50

# Paleta Plotly alineada al nuevo diseño
RED, BLUE, GRAY = "#ED1A3B", "#ffffff", "#4a4a52"
PLOT = dict(font=dict(family="Manrope", size=12, color="#a0a0a8"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=20, t=36, b=10))
 
# ──────────────────────────────────────────────────────────────────────
# PROCESAMIENTO (Lógica intacta)
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
            rows.append({"Equipo": eq, "PJ": 0, "V": 0, "E": 0, "D": 0,
                         "GF": 0, "GC": 0, "PTS": 0, "PPJ": 0.0, "EFEC%": 0.0})
            continue
        v = ((d["Propio"] > d["Concedido"])).sum()
        e = ((d["Propio"] == d["Concedido"])).sum()
        d_ = ((d["Propio"] < d["Concedido"])).sum()
        pts = int(v * 3 + e)
        gf = d["Propio"].sum()
        gc = d["Concedido"].sum()
        ppj = pts / pj
        efec = (pts / (pj * 3)) * 100
        
        rows.append({"Equipo": eq, "PJ": pj, "V": int(v), "E": int(e), "D": int(d_),
                     "GF": gf, "GC": gc, "PTS": pts, "PPJ": ppj, "EFEC%": efec})
 
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
    if tabla is None or eq not in tabla.index: return 1.0, 1.0
    return float(tabla.loc[eq, "prior_atk"]), float(tabla.loc[eq, "prior_def"])
 
def _adjusted_rate(d_spec, metrica, col, max_fecha_torneo, tabla, is_attack):
    df_m = d_spec[d_spec["Métrica"] == metrica]
    if df_m.empty: return np.nan
    fechas = df_m["nFecha"].values
    valores = df_m[col].values
    rivales = df_m["Rival"].values

    valores_ajustados = []
    for v, r in zip(valores, rivales):
        prior_atk_rival, prior_def_rival = _get_prior(tabla, r)
        if is_attack: adj = v / prior_def_rival if prior_def_rival > 0 else v
        else: adj = v / prior_atk_rival if prior_atk_rival > 0 else v
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
    if dx.empty: rh, rv = gh, gv
    else: rh, rv = W_XG * xh + (1-W_XG) * gh, W_XG * xv + (1-W_XG) * gv
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

    atk_val, def_val = combine(g_atk, x_atk), combine(g_def, x_def)
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
 
def fig_score_matrix(M, ea, eb, n=5):
    sub = M[:n, :n]
    z_text = [[f"{sub[i,j]*100:.1f}%" for j in range(n)] for i in range(n)]
    fig = go.Figure(go.Heatmap(
        z=sub,
        x=[str(j) for j in range(n)],
        y=[str(i) for i in range(n)],
        text=z_text, texttemplate="%{text}",
        colorscale=[[0,"#0a0a0c"],[0.5,"#590f19"],[1,"#ED1A3B"]],
        showscale=False,
    ))
    fig.update_layout(
        **PLOT, height=350,
        xaxis_title=f"GOLES {eb.upper()}",
        yaxis_title=f"GOLES {ea.upper()}",
        yaxis=dict(autorange="reversed"),
    )
    return fig

def fig_radar_pro(df, eq_a, eq_b, cond_a, cond_b):
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
    fig.add_trace(go.Scatterpolar(r=r_a, theta=theta, fill="toself", name=eq_a, line=dict(color="#ED1A3B"), hoverinfo="text+name", text=txt_a))
    fig.add_trace(go.Scatterpolar(r=r_b, theta=theta, fill="toself", name=eq_b, line=dict(color="#ffffff"), hoverinfo="text+name", text=txt_b))
    
    layout_args = PLOT.copy()
    layout_args.update(
        height=400, 
        polar=dict(
            bgcolor="rgba(0,0,0,0)", 
            radialaxis=dict(visible=True, showticklabels=False, gridcolor="#2a2a30", range=[0, 1]),
            angularaxis=dict(gridcolor="#2a2a30", linecolor="#2a2a30")
        ),
        margin=dict(l=40, r=40, t=36, b=40)
    )
    fig.update_layout(**layout_args)
    return fig
 
# ──────────────────────────────────────────────────────────────────────
# NAVEGACIÓN Y ESTRUCTURA
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">LPF SCOUTING</div>', unsafe_allow_html=True)
    ruta = st.text_input("Archivo de Datos", "Fecha_x_fecha_lpf.xlsx")
    
    st.markdown("<br>", unsafe_allow_html=True)
    nav = st.radio("MÓDULOS DE ANÁLISIS", 
                   ["Predicción de Partidos", "Métricas Globales", "Comparativa H2H", "Análisis de Rival", "Análisis de Estilos", "Posiciones"],
                   label_visibility="collapsed")
 
if not os.path.exists(ruta): st.stop()
datos  = cargar_excel(ruta)
df     = construir_df(datos)
tabla  = calcular_tabla(df, "General")

equipos, metricas = sorted(df["Equipo"].unique()), sorted(df["Métrica"].unique())

# HEADER PRINCIPAL
st.markdown("""
<div class="hero-banner">
    <div class="hero-subtitle">Base de Datos LPF 2026</div>
    <h1 class="hero-title">PLATAFORMA DE RENDIMIENTO</h1>
</div>
""", unsafe_allow_html=True)
 
# ──────────────────────────────────────────────────────────────────────
if nav == "Predicción de Partidos":
    st.markdown('<div class="section-header">Módulo Predictivo</div>', unsafe_allow_html=True)
    
    idx_river = equipos.index("River Plate") if "River Plate" in equipos else 0

    c1, c2, c3 = st.columns([4, 4, 2])
    ea  = c1.selectbox("Equipo Local", equipos, index=idx_river)
    eb  = c2.selectbox("Equipo Visitante", equipos, index=min(1, len(equipos)-1))
    loc = c3.selectbox("Ajuste Localía", ["Aplicar Ventaja", "Terreno Neutral"]) == "Aplicar Ventaja"
    
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("CALCULAR PROBABILIDADES"):
        la, lb = calcular_lambdas(df, ea, eb, loc, tabla)
        sim    = montecarlo(la, lb)
 
        # ACÁ ESTÁ LA CORRECCIÓN: Sin espacios vacíos para que Streamlit no lo rompa
        html_marcador = f"""<div class="broadcast-board">
    <div class="team-block home">
        <div class="t-name">{ea}</div>
        <div class="t-prob">{sim['victoria']*100:.1f}%</div>
        <div class="t-label">Victoria Local</div>
    </div>
    <div class="draw-block">
        <div class="t-label" style="margin-bottom:5px;">Empate</div>
        <div class="draw-prob">{sim['empate']*100:.1f}%</div>
    </div>
    <div class="team-block away">
        <div class="t-name">{eb}</div>
        <div class="t-prob" style="color:#ffffff;">{sim['derrota']*100:.1f}%</div>
        <div class="t-label">Victoria Visitante</div>
    </div>
</div>"""
        st.markdown(html_marcador, unsafe_allow_html=True)
 
        with st.expander("Parámetros del Motor (Lambdas y Priors)"):
            pa_a, pd_a = _get_prior(tabla, ea)
            pa_b, pd_b = _get_prior(tabla, eb)
            st.code(f"λ {ea}: {la:.3f} (Atk Prior: {pa_a:.2f})\nλ {eb}: {lb:.3f} (Atk Prior: {pa_b:.2f})")
 
        st.markdown('<div class="section-header">Matriz de Resultados</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_score_matrix(sim["matrix"], ea, eb), use_container_width=True)
 
# ──────────────────────────────────────────────────────────────────────
elif nav == "Métricas Globales":
    st.markdown('<div class="section-header">Rankings de Rendimiento</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    m_sel    = c1.selectbox("Métrica Analizada", metricas)
    cond_sel = c2.selectbox("Filtro Condición", ["General", "Local", "Visitante"])
    tipo_sel = c3.selectbox("Enfoque", ["Producción (A Favor)", "Concesión (En Contra)"])
    
    col_data = "Propio" if "A Favor" in tipo_sel else "Concedido"
    mask_cond = (df["Condicion"] == cond_sel) if cond_sel != "General" else df.index.notna()
    res = (df[mask_cond & (df["Métrica"] == m_sel)]
           .groupby("Equipo")[col_data].mean()
           .sort_values(ascending=False).reset_index())
           
    st.plotly_chart(
        go.Figure(go.Bar(x=res[col_data], y=res["Equipo"], orientation="h",
                         marker_color=RED if col_data == "Propio" else GRAY))
          .update_layout(**PLOT, height=700),
        use_container_width=True)
 
# ──────────────────────────────────────────────────────────────────────
elif nav == "Comparativa H2H":
    st.markdown('<div class="section-header">Head-to-Head (H2H)</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    ea = c1.selectbox("Escuadra A", equipos)
    cond_a = c1.selectbox(f"Condición de {ea}", ["General", "Local", "Visitante"])
    
    eb = c2.selectbox("Escuadra B", equipos, index=min(1, len(equipos)-1))
    cond_b = c2.selectbox(f"Condición de {eb}", ["General", "Local", "Visitante"])
    
    t1, t2 = st.tabs(["Comparativa Visual (Radar)", "Métricas Crudas"])
    
    with t1:
        st.plotly_chart(fig_radar_pro(df, ea, eb, cond_a, cond_b), use_container_width=True)
        
    with t2:
        df_a = df[df["Equipo"] == ea]
        if cond_a != "General":
            df_a = df_a[df_a["Condicion"] == cond_a]
            
        df_b = df[df["Equipo"] == eb]
        if cond_b != "General":
            df_b = df_b[df_b["Condicion"] == cond_b]

        s1 = df_a.groupby("Métrica")[["Propio","Concedido"]].mean().round(2)
        s2 = df_b.groupby("Métrica")[["Propio","Concedido"]].mean().round(2)
        
        h2h_df = pd.DataFrame({
            f"{ea} ({cond_a[:3]}) Favor": s1["Propio"], 
            f"{ea} ({cond_a[:3]}) Contra": s1["Concedido"],
            f"{eb} ({cond_b[:3]}) Favor": s2["Propio"], 
            f"{eb} ({cond_b[:3]}) Contra": s2["Concedido"]
        }).dropna()
        
        st.dataframe(h2h_df, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "Análisis de Rival":
    st.markdown('<div class="section-header">Evolución de Rendimiento</div>', unsafe_allow_html=True)
    eq_p  = st.selectbox("Seleccionar Equipo", equipos)
    met_p = st.selectbox("Métrica a Evaluar", metricas)
    d_eq  = df[(df["Equipo"] == eq_p) & (df["Métrica"] == met_p)].sort_values("nFecha")
    
    if not d_eq.empty:
        fig = go.Figure([
            go.Bar(x=d_eq["Rival"], y=d_eq["Propio"],    name="Generado", marker_color=RED),
            go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], name="Concedido", marker_color=GRAY),
        ])
        st.plotly_chart(fig.update_layout(**PLOT, barmode="group"), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "Análisis de Estilos":
    st.markdown('<div class="section-header">Matriz de Estilos de Juego</div>', unsafe_allow_html=True)
    mo = "Goles esperados (xG)" if "Goles esperados (xG)" in metricas else "Tiros totales"
    
    if "Posesión de balón" in metricas:
        df_e = pd.DataFrame({
            "P": df[df["Métrica"] == "Posesión de balón"].groupby("Equipo")["Propio"].mean(),
            "O": df[df["Métrica"] == mo].groupby("Equipo")["Propio"].mean(),
        }).dropna()
        
        mp, mo_m = df_e["P"].mean(), df_e["O"].mean()
        
        fig = go.Figure(go.Scatter(
            x=df_e["P"], y=df_e["O"], mode="markers+text",
            text=df_e.index, textposition="top center",
            marker=dict(size=14, color=RED, line=dict(width=2, color="#141417")),
            textfont=dict(family="Manrope", size=11, color="#ffffff")
        ))
        
        # Líneas promedio (Cuadrantes)
        fig.add_vline(x=mp, line=dict(color=GRAY, dash="dash", width=1))
        fig.add_hline(y=mo_m, line=dict(color=GRAY, dash="dash", width=1))
        
        # Anotaciones visuales sutiles para entender el gráfico
        fig.add_annotation(x=df_e["P"].max(), y=df_e["O"].max(), text="DOMINIO & ATAQUE", showarrow=False, font=dict(color=GRAY, size=10), xanchor="right", yanchor="bottom")
        fig.add_annotation(x=df_e["P"].min(), y=df_e["O"].min(), text="REACTIVO & DEFENSIVO", showarrow=False, font=dict(color=GRAY, size=10), xanchor="left", yanchor="top")

        st.plotly_chart(
            fig.update_layout(**PLOT, height=600,
                              xaxis_title="Posesión Promedio (%)",
                              yaxis_title=f"Volumen Ofensivo ({mo})"),
            use_container_width=True)
    else:
        st.warning("No se encontraron datos de 'Posesión de balón' para procesar la matriz de estilos.")

# ──────────────────────────────────────────────────────────────────────
elif nav == "Posiciones":
    st.markdown('<div class="section-header">Clasificación por Efectividad</div>', unsafe_allow_html=True)
    vista_tabla = st.selectbox("Escenario de Tabla", ["General", "Local", "Visitante"])
    t_dinamica = calcular_tabla(df, vista_tabla)
    
    if not t_dinamica.empty:
        t_show = t_dinamica.reset_index()[["Pos","Equipo","PJ","V","E","D","GF","GC","PTS","EFEC%"]].copy()
        t_show.columns = ["#","Equipo","PJ","V","E","D","GF","GC","PTS","Efectividad %"]
        t_show["GF"] = t_show["GF"].astype(int)
        t_show["GC"] = t_show["GC"].astype(int)
        t_show["Efectividad %"] = t_show["Efectividad %"].round(1)
        
        st.dataframe(
            t_show.style.format({"Efectividad %": "{:.1f}%"}), 
            use_container_width=True, 
            hide_index=True
        )
