"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v9.1 · Prior de Jerarquía Automático)
─────────────────────────────────────────────────────────────────────────────
Fixes v9.1 sobre v9.0:
  [F6] Prior de jerarquía: la tabla de posiciones (PPJ) se calcula automáticamente
       desde el Excel y actúa como prior bayesiano sobre ataque y defensa.
       Equipos con más puntos por partido tienen un prior de ataque > 1.0
       y prior de defensa < 1.0, en lugar del prior neutro (1.0, 1.0) de v9.0.
  [F7] Indicador de lambdas y tabla de posiciones visible en el Predictor
       para que el usuario pueda auditar el resultado.
  [F8] Restaurados los marcadores de score en la matriz de probabilidades.
"""
import re, os, math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
 
# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILOS
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Analítica Pro", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")
 
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #080d18; color: #dde3ee; }
section[data-testid="stSidebar"] { background: #0c1220 !important; border-right: 1px solid #1c2a40; }
h1 { font-family:'Bebas Neue',cursive !important; font-size:2.6rem !important; color:#e63946 !important; letter-spacing:3px; margin-bottom:0; }
.section-title { font-family:'Bebas Neue',cursive; font-size:1.3rem; letter-spacing:3px; color:#e63946; border-bottom:1px solid #1c2a40; padding-bottom:8px; margin:28px 0 18px; text-transform:uppercase; }
.kpi { background:linear-gradient(135deg,#0f1829,#162035); border:1px solid #1c2a40; border-left:4px solid #e63946; border-radius:10px; padding:16px 18px; text-align:center; }
.kpi.draw { border-left-color:#64748b; } .kpi.loss { border-left-color:#3b82f6; }
.kpi .lbl { font-family:'Rajdhani'; font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:#64748b; }
.kpi .val { font-family:'Bebas Neue'; font-size:38px; color:#e63946; line-height:1.05; }
.stTabs [data-baseweb="tab-list"] { background:#0f1829; border-radius:10px; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"] { font-family:'Rajdhani'; font-weight:700; font-size:14px; color:#64748b !important; border-radius:7px; padding:6px 16px; }
.stTabs [aria-selected="true"] { background:#e63946 !important; color:#fff !important; }
.stButton>button { font-family:'Bebas Neue'; font-size:17px; letter-spacing:2px; background:linear-gradient(135deg,#e63946,#b91c2c); color:#fff; border:none; border-radius:9px; padding:13px; width:100%; }
.stSelectbox>div>div, .stTextInput>div>div { background:#0f1829 !important; border:1px solid #1c2a40 !important; color:#dde3ee !important; border-radius:8px !important; }
.note { background:#0f1829; border:1px solid #1c2a40; border-radius:8px; padding:10px 14px; font-size:12px; color:#64748b; margin-top:8px; }
</style>
""", unsafe_allow_html=True)
 
# ── Parámetros de Motor ───────────────────────────────────────────────
W_XG = 0.75
K_SHRINK = 6.0          # shrinkage sobre datos observados
K_PRIOR  = 4.0          # [F6] peso del prior de jerarquía (en unidades de "partidos equivalentes")
                        #      a mayor K_PRIOR, más influencia tiene la tabla sobre equipos
                        #      con pocos partidos en esa condición específica
PRIOR_ATK_SCALE = 0.35  # [F6] amplitud del prior de ataque: PPJ_norm * SCALE desplaza el prior
PRIOR_DEF_SCALE = 0.25  # [F6] amplitud del prior de defensa (más conservador)
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.5, 1.0
LAM_MIN, LAM_MAX = 0.25, 4.50
RED, BLUE, GRAY = "#e63946", "#3b82f6", "#64748b"
PLOT = dict(font=dict(family="Rajdhani", size=13, color="#dde3ee"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=20, t=36, b=10))
 
# ──────────────────────────────────────────────────────────────────────
# PROCESAMIENTO
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
            for met, vals in p["metricas"].items():
                base = {"nFecha": nf, "Métrica": met}
                filas.append({**base, "Equipo": p["local"],    "Rival": p["visitante"], "Condicion": "Local",     "Propio": vals["local"],     "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"],"Rival": p["local"],     "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)
 
# ── [F6] Tabla de posiciones y priors de jerarquía ───────────────────
@st.cache_data(ttl=120, show_spinner=False)
def calcular_tabla(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye la tabla de posiciones y calcula el prior de jerarquía
    normalizado para cada equipo.
 
    prior_atk: valor > 1 = equipo que genera más de lo esperado (buenos)
                valor < 1 = equipo que genera menos (malos)
    prior_def: valor < 1 = equipo que concede menos (buena defensa)
                valor > 1 = equipo que concede más (mala defensa)
 
    El prior se deriva del PPJ (puntos por partido) normalizado en torno
    a la media del torneo.  PPJ_norm = PPJ / PPJ_mean.
    Un equipo con PPJ_norm=1.5 tiene prior_atk = 1 + 0.5*PRIOR_ATK_SCALE
    y prior_def = 1 - 0.5*PRIOR_DEF_SCALE (concede menos).
    """
    dr = df[df["Métrica"] == "Resultado"].copy()
    if dr.empty:
        return pd.DataFrame()
 
    equipos = sorted(df["Equipo"].unique())
    rows = []
    for eq in equipos:
        d = dr[dr["Equipo"] == eq]
        pj = len(d)
        if pj == 0:
            rows.append({"Equipo": eq, "PJ": 0, "V": 0, "E": 0, "D": 0,
                         "GF": 0, "GC": 0, "PTS": 0, "PPJ": 0.0})
            continue
        v = ((d["Propio"] > d["Concedido"])).sum()
        e = ((d["Propio"] == d["Concedido"])).sum()
        d_ = ((d["Propio"] < d["Concedido"])).sum()
        pts = int(v * 3 + e)
        gf = d["Propio"].sum()
        gc = d["Concedido"].sum()
        rows.append({"Equipo": eq, "PJ": pj, "V": int(v), "E": int(e), "D": int(d_),
                     "GF": gf, "GC": gc, "PTS": pts, "PPJ": pts / pj})
 
    tabla = pd.DataFrame(rows).sort_values(["PTS", "GF"], ascending=False).reset_index(drop=True)
    tabla["Pos"] = tabla.index + 1
 
    # Prior normalizado: cuánto se desvía cada equipo de la media del torneo
    ppj_mean = tabla["PPJ"].mean()
    if ppj_mean > 0:
        tabla["PPJ_norm"] = tabla["PPJ"] / ppj_mean
    else:
        tabla["PPJ_norm"] = 1.0
 
    # prior_atk: equipos buenos atacan más → prior > 1
    tabla["prior_atk"] = 1.0 + (tabla["PPJ_norm"] - 1.0) * PRIOR_ATK_SCALE
    # prior_def: equipos buenos defienden mejor → prior < 1 (conceden menos)
    tabla["prior_def"] = 1.0 - (tabla["PPJ_norm"] - 1.0) * PRIOR_DEF_SCALE
 
    # Clip para evitar priors absurdos
    tabla["prior_atk"] = tabla["prior_atk"].clip(0.5, 2.0)
    tabla["prior_def"] = tabla["prior_def"].clip(0.5, 2.0)
 
    return tabla.set_index("Equipo")
 
def _get_prior(tabla: pd.DataFrame, eq: str):
    """Retorna (prior_atk, prior_def) para un equipo. Default neutro si no está."""
    if tabla is None or eq not in tabla.index:
        return 1.0, 1.0
    return float(tabla.loc[eq, "prior_atk"]), float(tabla.loc[eq, "prior_def"])
 
# ──────────────────────────────────────────────────────────────────────
# MOTOR PREDICTIVO
# ──────────────────────────────────────────────────────────────────────
def _weighted_mean(values, fechas, max_fecha_torneo: int):
    if len(values) == 0: return np.nan
    w = np.where(fechas >= (max_fecha_torneo - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(values, weights=w))
 
def _effective_rate(sub, col, max_fecha_torneo: int):
    dr = sub[sub["Métrica"] == "Resultado"]
    dx = sub[sub["Métrica"] == "Goles esperados (xG)"]
    g = _weighted_mean(dr[col].values, dr["nFecha"].values, max_fecha_torneo) if not dr.empty else np.nan
    x = _weighted_mean(dx[col].values, dx["nFecha"].values, max_fecha_torneo) if not dx.empty else np.nan
    n = len(dr)
    if np.isnan(g) and np.isnan(x): return np.nan, 0
    if np.isnan(x): return g, n
    if np.isnan(g): return x, n
    return W_XG * x + (1 - W_XG) * g, n
 
@st.cache_data(ttl=120, show_spinner=False)
def _league_stats(df):
    dr = df[df["Métrica"] == "Resultado"]
    dx = df[df["Métrica"] == "Goles esperados (xG)"]
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
    """
    [F6] Shrinkage bayesiano con prior de jerarquía.
 
    En lugar de shrinkage hacia (1.0, 1.0) neutro, encogemos hacia
    (prior_atk, prior_def) derivados de los puntos por partido del equipo.
 
    Formulación:
        atk_posterior = (n * atk_obs + K_PRIOR * prior_atk) / (n + K_PRIOR)
        def_posterior = (n * def_obs + K_PRIOR * prior_def) / (n + K_PRIOR)
 
    Con n=0 (nunca jugó en esa condición): resultado = puro prior de jerarquía.
    Con n→∞: resultado = observado (datos dominan sobre el prior).
    """
    d_eq   = df[df["Equipo"] == eq]
    d_spec = d_eq[d_eq["Condicion"] == cond]
 
    gf_s, n_s = _effective_rate(d_spec, "Propio",    max_fecha_torneo)
    gc_s, _   = _effective_rate(d_spec, "Concedido", max_fecha_torneo)
 
    rh, ra = league["ref_home"], league["ref_away"]
    ref_f, ref_a = (rh, ra) if cond == "Local" else (ra, rh)
 
    atk_obs  = (gf_s / ref_f)  if (not np.isnan(gf_s)  and ref_f  > 0) else np.nan
    def_obs  = (gc_s / ref_a)  if (not np.isnan(gc_s)   and ref_a  > 0) else np.nan
 
    # Prior de jerarquía desde tabla de posiciones
    prior_atk, prior_def = _get_prior(tabla, eq)
 
    n = n_s if n_s > 0 else 0
    atk_obs  = atk_obs  if not np.isnan(atk_obs)  else prior_atk
    def_obs  = def_obs  if not np.isnan(def_obs)  else prior_def
 
    # [F6] Shrinkage hacia prior de jerarquía (no hacia 1.0)
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
 
# ── [F8] Figura de matriz de marcadores ──────────────────────────────
def fig_score_matrix(M, ea, eb, n=5):
    """Muestra los marcadores más probables como heatmap."""
    sub = M[:n, :n]
    z_text = [[f"{sub[i,j]*100:.1f}%" for j in range(n)] for i in range(n)]
    fig = go.Figure(go.Heatmap(
        z=sub,
        x=[str(j) for j in range(n)],
        y=[str(i) for i in range(n)],
        text=z_text, texttemplate="%{text}",
        colorscale=[[0,"#0f1829"],[0.5,"#7f1d1d"],[1,"#e63946"]],
        showscale=False,
    ))
    fig.update_layout(
        **PLOT, height=320,
        xaxis_title=f"Goles {eb}",
        yaxis_title=f"Goles {ea}",
        yaxis=dict(autorange="reversed"),
    )
    return fig
def fig_radar(df, eq_a, eq_b, cond_a, cond_b):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco",
                         "Goles esperados (xG)", "Pases totales"]
            if m in df["Métrica"].values]
    if not mets: return go.Figure()
    
    # 1. Función para promediar la métrica de un equipo
    def gv(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General": d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0
        
    # 2. Función para buscar el "Techo" (máximo) de la liga en esa métrica
    def get_league_max(m):
        # Promedio general por equipo para esa métrica, nos quedamos con el mejor
        return df[df["Métrica"] == m].groupby("Equipo")["Propio"].mean().max()

    # Obtenemos los valores reales de los dos equipos
    va = [gv(eq_a, cond_a, m) for m in mets]
    vb = [gv(eq_b, cond_b, m) for m in mets]
    
    # Obtenemos los máximos de la liga (o 1e-6 para evitar dividir por cero)
    mx = [max(get_league_max(m), 1e-6) for m in mets]
    
    # Armamos el texto que se verá al pasar el mouse mostrando el valor real
    text_a = [f"{m}: <b>{v:.1f}</b>" for m, v in zip(mets, va)]
    text_b = [f"{m}: <b>{v:.1f}</b>" for m, v in zip(mets, vb)]

    # Cerramos el polígono repitiendo el primer valor (lógica de radares en Plotly)
    r_a = [a/m for a, m in zip(va, mx)] + [va[0]/mx[0]]
    r_b = [b/m for b, m in zip(vb, mx)] + [vb[0]/mx[0]]
    theta = mets + [mets[0]]
    txt_a = text_a + [text_a[0]]
    txt_b = text_b + [text_b[0]]

    fig = go.Figure()
    
    # Agregamos las trazas inyectando el hovertext
    fig.add_trace(go.Scatterpolar(
        r=r_a, theta=theta, fill="toself", name=eq_a, 
        line=dict(color=RED), hoverinfo="text+name", text=txt_a
    ))
    fig.add_trace(go.Scatterpolar(
        r=r_b, theta=theta, fill="toself", name=eq_b, 
        line=dict(color=BLUE), hoverinfo="text+name", text=txt_b
    ))
    
    # Mejoramos el layout haciendo visible la red para ubicar mejor los valores
    fig.update_layout(
        **PLOT, 
        height=400, 
        polar=dict(
            bgcolor="rgba(0,0,0,0)", 
            radialaxis=dict(
                visible=True, 
                showticklabels=False, # Oculta los números "0.2, 0.4" de la normalización
                gridcolor="#1c2a40",  # Color sutil para la grilla
                range=[0, 1]          # El 1 ahora significa "El máximo de la liga"
            ),
            angularaxis=dict(
                gridcolor="#1c2a40",
                linecolor="#1c2a40"
            )
        ),
        margin=dict(l=40, r=40, t=36, b=40)
    )
    return fig
 
# ──────────────────────────────────────────────────────────────────────
# NAVEGACIÓN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Excel", "Fecha_x_fecha_lpf.xlsx")
    nav = st.radio("", ["🔮 Predictor", "📊 Rankings", "🔄 Head-to-Head",
                        "📖 Perfil Rival", "🎭 Estilos", "📋 Tabla"],
                   label_visibility="collapsed")
 
if not os.path.exists(ruta): st.stop()
datos  = cargar_excel(ruta)
df     = construir_df(datos)
tabla  = calcular_tabla(df)          # [F6] prior de jerarquía
equipos, metricas = sorted(df["Equipo"].unique()), sorted(df["Métrica"].unique())
st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)
 
# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Predictor (v9.1)</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    ea  = c1.selectbox("Local",     equipos)
    eb  = c2.selectbox("Visitante", equipos, index=min(1, len(equipos)-1))
    loc = c3.toggle("Bono Localía", True)
 
    if st.button("🚀 INICIAR ANÁLISIS"):
        la, lb = calcular_lambdas(df, ea, eb, loc, tabla)
        sim    = montecarlo(la, lb)
 
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi"><div class="lbl">Prob. {ea}</div><div class="val">{sim["victoria"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="lbl">Prob. Empate</div><div class="val">{sim["empate"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="lbl">Prob. {eb}</div><div class="val">{sim["derrota"]*100:.1f}%</div></div>', unsafe_allow_html=True)
 
        # [F7] Auditoría de lambdas y priors
        pa_a, pd_a = _get_prior(tabla, ea)
        pa_b, pd_b = _get_prior(tabla, eb)
        pos_a = int(tabla.loc[ea, "Pos"]) if ea in tabla.index else "?"
        pos_b = int(tabla.loc[eb, "Pos"]) if eb in tabla.index else "?"
        st.markdown(
            f'<div class="note">'
            f'λ {ea} = <b>{la:.3f}</b> (pos {pos_a}°, prior_atk={pa_a:.2f}) &nbsp;|&nbsp; '
            f'λ {eb} = <b>{lb:.3f}</b> (pos {pos_b}°, prior_atk={pa_b:.2f})'
            f'</div>', unsafe_allow_html=True)
 
        # [F8] Matriz de marcadores
        st.markdown('<div class="section-title">🎯 Marcadores más probables</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_score_matrix(sim["matrix"], ea, eb), use_container_width=True)
 
# ──────────────────────────────────────────────────────────────────────
elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings: Favor vs Concedido</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    m_sel    = c1.selectbox("Métrica", metricas)
    cond_sel = c2.radio("Condición", ["General", "Local", "Visitante"], horizontal=True)
    tipo_sel = c3.radio("Enfoque",   ["A Favor", "En Contra"], horizontal=True)
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
# ──────────────────────────────────────────────────────────────────────
elif nav == "🔄 Head-to-Head":
    st.markdown('<div class="section-title">🔄 Head-to-Head Comparativo</div>', unsafe_allow_html=True)
    
    # Selección de equipos
    c1, c2 = st.columns(2)
    ea = c1.selectbox("Equipo A", equipos)
    eb = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1))
    
    # Selección de condición (Local/Visitante/General)
    c3, c4 = st.columns(2)
    cond_a = c3.radio(f"Condición de {ea}", ["General", "Local", "Visitante"], horizontal=True, key="cond_a")
    cond_b = c4.radio(f"Condición de {eb}", ["General", "Local", "Visitante"], horizontal=True, key="cond_b")

    t1, t2 = st.tabs(["🕸️ Comparativa Radar", "📊 Datos Crudos"])
    
    with t1:
        # El radar ya estaba preparado para recibir condiciones, se las pasamos
        st.plotly_chart(fig_radar(df, ea, eb, cond_a, cond_b), use_container_width=True)
        
    with t2:
        # Filtramos los datos del Equipo A según su condición
        df_a = df[df["Equipo"] == ea]
        if cond_a != "General":
            df_a = df_a[df_a["Condicion"] == cond_a]
            
        # Filtramos los datos del Equipo B según su condición
        df_b = df[df["Equipo"] == eb]
        if cond_b != "General":
            df_b = df_b[df_b["Condicion"] == cond_b]

        # Calculamos los promedios con los dataframes ya filtrados
        s1 = df_a.groupby("Métrica")[["Propio","Concedido"]].mean().round(2)
        s2 = df_b.groupby("Métrica")[["Propio","Concedido"]].mean().round(2)
        
        # Armamos la tabla comparativa indicando la condición en los encabezados para mayor claridad
        h2h_df = pd.DataFrame({
            f"{ea} ({cond_a[:3]}) Favor": s1["Propio"], 
            f"{ea} ({cond_a[:3]}) Contra": s1["Concedido"],
            f"{eb} ({cond_b[:3]}) Favor": s2["Propio"], 
            f"{eb} ({cond_b[:3]}) Contra": s2["Concedido"]
        }).dropna()
        
        st.dataframe(h2h_df, use_container_width=True)
# ──────────────────────────────────────────────────────────────────────
elif nav == "📖 Perfil Rival":
    eq_p  = st.selectbox("Equipo",  equipos)
    met_p = st.selectbox("Métrica", metricas)
    d_eq  = df[(df["Equipo"] == eq_p) & (df["Métrica"] == met_p)].sort_values("nFecha")
    if not d_eq.empty:
        fig = go.Figure([
            go.Bar(x=d_eq["Rival"], y=d_eq["Propio"],    name="Favor", marker_color=RED),
            go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], name="Contra", marker_color=GRAY),
        ])
        st.plotly_chart(fig.update_layout(**PLOT, barmode="group"), use_container_width=True)
 
# ──────────────────────────────────────────────────────────────────────
elif nav == "🎭 Estilos":
    st.markdown('<div class="section-title">🎭 Análisis de Estilo</div>', unsafe_allow_html=True)
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
            marker=dict(size=12, color=RED, line=dict(width=1, color="white")),
        ))
        fig.add_vline(x=mp,   line=dict(color=GRAY, dash="dash"))
        fig.add_hline(y=mo_m, line=dict(color=GRAY, dash="dash"))
        st.plotly_chart(
            fig.update_layout(**PLOT, height=600,
                              xaxis_title="Posesión (%)",
                              yaxis_title=f"Ataque ({mo})"),
            use_container_width=True)
 
# ──────────────────────────────────────────────────────────────────────
elif nav == "📋 Tabla":
    st.markdown('<div class="section-title">📋 Tabla de Posiciones</div>', unsafe_allow_html=True)
    if not tabla.empty:
        t_show = tabla.reset_index()[["Pos","Equipo","PJ","V","E","D","GF","GC","PTS","PPJ","prior_atk","prior_def"]].copy()
        t_show.columns = ["Pos","Equipo","PJ","V","E","D","GF","GC","PTS","PPJ","Prior Atk","Prior Def"]
        t_show["GF"] = t_show["GF"].astype(int)
        t_show["GC"] = t_show["GC"].astype(int)
        t_show["PPJ"]        = t_show["PPJ"].round(3)
        t_show["Prior Atk"]  = t_show["Prior Atk"].round(3)
        t_show["Prior Def"]  = t_show["Prior Def"].round(3)
        st.dataframe(t_show, use_container_width=True, hide_index=True)
        st.markdown('<div class="note">Prior Atk > 1 = equipo que históricamente genera más que la media · Prior Def < 1 = equipo que concede menos · Estos priors actúan como "partículas previas" en el shrinkage bayesiano del predictor.</div>', unsafe_allow_html=True)
