"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v9.3 · Fix Estructura Cache)
─────────────────────────────────────────────────────────────────────────────
Fixes v9.3:
  [F13] Corrección de TypeError en calibrar_xg_sint: Desempaquetado de tuplas 
        generadas para el sistema de cache.
  [F14] nFecha integrado en partidos_todos para habilitar la media ponderada 
        por recencia real en el motor predictivo.
  [F15] Consistencia de tipos: _league_refs ahora también maneja tuplas.
"""
import re, os, math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from numpy.linalg import lstsq

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILOS
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Analítica Pro", page_icon="⚽",
                   layout="wide", initial_sidebar_state="expanded")

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

# ── Parámetros ────────────────────────────────────────────────────────
W_SINT   = 0.65   
K_SHRINK = 5.0    
DC_RHO   = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.5, 1.0
LAM_MIN, LAM_MAX = 0.25, 4.50
RED, BLUE, GRAY = "#e63946", "#3b82f6", "#64748b"
PLOT = dict(font=dict(family="Rajdhani", size=13, color="#dde3ee"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=20, t=36, b=10))

# ──────────────────────────────────────────────────────────────────────
# CARGA Y CONSTRUCCIÓN
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
                    if r0.lower() in ("métrica","metrica") or r0==loc: j+=1; continue
                    if pd.notna(df.iloc[j,1]):
                        stats[r0] = {"local": num(df.iloc[j,1]), "visitante": num(df.iloc[j,2])}
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
                filas.append({**base, "Equipo": p["local"], "Rival": p["visitante"],
                              "Condicion": "Local", "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"],
                              "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

# ──────────────────────────────────────────────────────────────────────
# [F9] CALIBRACIÓN xG SINTÉTICO (Fix Desempaquetado Tuplas)
# ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def calibrar_xg_sint(partidos_raw: tuple):
    rows = []
    for p in partidos_raw:
        # Reconstruir dict temporal desde tupla hasheable (local, visitor, metrics_tuple)
        ms = {m[0]: {"local": m[1], "visitante": m[2]} for m in p[2]}
        
        g  = ms.get("Resultado", {})
        ta = ms.get("Tiros al arco", {})
        tt = ms.get("Tiros totales", {})
        
        for side in ("local", "visitante"):
            goles     = g.get(side)
            tiro_arco = ta.get(side)
            tiro_tot  = tt.get(side, 0) or 0
            if goles is None or tiro_arco is None: continue
            rows.append({"goles": goles, "ta": tiro_arco, "tt": tiro_tot, "cond": side})

    if len(rows) < 10:
        return 0.25, 0.0, 0.5, 1.1, 0.9 

    dfr = pd.DataFrame(rows)
    X   = np.column_stack([dfr["ta"].values, dfr["tt"].values, np.ones(len(dfr))])
    y   = dfr["goles"].values
    coef, _, _, _ = lstsq(X, y, rcond=None)
    a, b, intercept = coef

    def xg_calc(row): return max(a * row["ta"] + b * row["tt"] + intercept, 0)
    dfr["xg"] = dfr.apply(xg_calc, axis=1)
    return a, b, intercept, dfr[dfr["cond"]=="local"]["xg"].mean(), dfr[dfr["cond"]=="visitante"]["xg"].mean()

def xg_de_partido(p, side, a, b, intercept):
    # p aquí es un diccionario (partidos_todos)
    ta = p["metricas"].get("Tiros al arco", {}).get(side)
    tt = p["metricas"].get("Tiros totales", {}).get(side, 0) or 0
    if ta is None: return None
    return max(a * ta + b * tt + intercept, 0)

# ──────────────────────────────────────────────────────────────────────
# MOTOR PREDICTIVO
# ──────────────────────────────────────────────────────────────────────
def _wm(values, fechas, max_f):
    if len(values) == 0: return np.nan
    w = np.where(np.array(fechas) >= (max_f - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(values, weights=w))

@st.cache_data(ttl=120, show_spinner=False)
def _league_refs(partidos_raw: tuple):
    gl_loc, gl_vis = [], []
    for p in partidos_raw:
        ms = {m[0]: {"local": m[1], "visitante": m[2]} for m in p[2]}
        g = ms.get("Resultado", {})
        if g.get("local") is not None: gl_loc.append(g["local"])
        if g.get("visitante") is not None: gl_vis.append(g["visitante"])
    return np.mean(gl_loc) if gl_loc else 1.0, np.mean(gl_vis) if gl_vis else 1.0

def _strength_blend(partidos_todos, eq, cond, ref_home_xg, ref_away_xg,
                    ref_home_real, ref_away_real, a, b, intercept, max_f):
    side_p = "local" if cond == "Local" else "visitante"
    side_r = "visitante" if cond == "Local" else "local"

    # Filtrar partidos donde participa el equipo en esa condición
    ps_eq = [p for p in partidos_todos 
             if (cond == "Local" and p["local"] == eq) or 
                (cond == "Visitante" and p["visitante"] == eq)]

    xgs_atk, goles_atk, fechas_atk = [], [], []
    xgs_def, goles_def, fechas_def = [], [], []
    
    for p in ps_eq:
        nf = p.get("nFecha", 0)
        xg_a = xg_de_partido(p, side_p, a, b, intercept)
        xg_d = xg_de_partido(p, side_r, a, b, intercept)
        g_a  = p["metricas"].get("Resultado", {}).get(side_p)
        g_d  = p["metricas"].get("Resultado", {}).get(side_r)
        
        if xg_a is not None: 
            xgs_atk.append(xg_a); fechas_atk.append(nf)
        if xg_d is not None: 
            xgs_def.append(xg_d); fechas_def.append(nf)
        if g_a is not None: goles_atk.append(g_a)
        if g_d is not None: goles_def.append(g_d)

    n = len(goles_atk)
    ref_proc_atk = ref_home_xg if cond == "Local" else ref_away_xg
    ref_proc_def = ref_away_xg if cond == "Local" else ref_home_xg
    ref_real_atk = ref_home_real if cond == "Local" else ref_away_real
    ref_real_def = ref_away_real if cond == "Local" else ref_home_real

    def blend_rate(xgs, goles, fechas, r_proc, r_real):
        xg_m   = _wm(xgs, fechas, max_f) if xgs else np.nan
        real_m = _wm(goles, fechas[:len(goles)], max_f) if goles else np.nan
        rs = (xg_m / r_proc) if (not np.isnan(xg_m) and r_proc > 0) else 1.0
        rr = (real_m / r_real) if (not np.isnan(real_m) and r_real > 0) else rs
        return W_SINT * rs + (1 - W_SINT) * rr

    atk = (n * blend_rate(xgs_atk, goles_atk, fechas_atk, ref_proc_atk, ref_real_atk) + K_SHRINK) / (n + K_SHRINK)
    deff = (n * blend_rate(xgs_def, goles_def, fechas_def, fechas_def, ref_proc_def, ref_real_def) + K_SHRINK) / (n + K_SHRINK)
    return atk, deff, n

def calcular_lambdas(partidos_todos, eq_a, eq_b, es_loc,
                     ref_home_xg, ref_away_xg, ref_home_real, ref_away_real,
                     a, b, intercept, max_f):
    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")
    aa, da, _ = _strength_blend(partidos_todos, eq_a, ca, ref_home_xg, ref_away_xg, ref_home_real, ref_away_real, a, b, intercept, max_f)
    ab, db, _ = _strength_blend(partidos_todos, eq_b, cb, ref_home_xg, ref_away_xg, ref_home_real, ref_away_real, a, b, intercept, max_f)
    
    la = (ref_home_xg if ca=="Local" else ref_away_xg) * aa * db
    lb = (ref_home_xg if cb=="Local" else ref_away_xg) * ab * da
    return round(float(np.clip(la, LAM_MIN, LAM_MAX)), 3), round(float(np.clip(lb, LAM_MIN, LAM_MAX)), 3)

def montecarlo(la, lb):
    def _pmf(lam, kmax):
        k = np.arange(kmax + 1)
        return np.exp(k * np.log(max(lam, 1e-9)) - lam - np.array([math.log(math.factorial(x)) for x in k]))
    pa, pb = _pmf(la, MAX_GOALS_MATRIX), _pmf(lb, MAX_GOALS_MATRIX)
    M = np.outer(pa, pb)
    rho = max(DC_RHO, -0.9 / max(la * lb, 0.01))
    M[0,0] = max(M[0,0] * (1-la*lb*rho), 0); M[0,1] *= (1+la*rho); M[1,0] *= (1+lb*rho); M[1,1] *= (1-rho)
    M /= M.sum()
    return {"victoria": float(np.tril(M, -1).sum()), "empate": float(np.trace(M)), "derrota": float(np.triu(M, 1).sum()), "matrix": M}

# ──────────────────────────────────────────────────────────────────────
# TABLA Y POSICIONES
# ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def calcular_tabla(df: pd.DataFrame) -> pd.DataFrame:
    dr = df[df["Métrica"] == "Resultado"].copy()
    if dr.empty: return pd.DataFrame()
    equipos = sorted(df["Equipo"].unique())
    rows = []
    for eq in equipos:
        d = dr[dr["Equipo"] == eq]
        pj = len(d)
        if pj == 0: continue
        v = (d["Propio"] > d["Concedido"]).sum()
        e = (d["Propio"] == d["Concedido"]).sum()
        pts = int(v*3 + e)
        rows.append({"Equipo": eq, "PJ": pj, "V": int(v), "E": int(e), "D": int(pj-v-e),
                     "GF": int(d["Propio"].sum()), "GC": int(d["Concedido"].sum()),
                     "PTS": pts, "PPJ": pts/pj})
    tabla = pd.DataFrame(rows).sort_values(["PTS","GF"], ascending=False).reset_index(drop=True)
    tabla["Pos"] = tabla.index + 1
    return tabla.set_index("Equipo")

# ──────────────────────────────────────────────────────────────────────
# NAVEGACIÓN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Excel", "Fecha_x_fecha_lpf.xlsx")
    nav  = st.radio("", ["🔮 Predictor","📊 Rankings","🔄 Head-to-Head","📖 Perfil Rival","🎭 Estilos","📋 Tabla"], label_visibility="collapsed")

if not os.path.exists(ruta): st.stop()

datos = cargar_excel(ruta)
df = construir_df(datos)
tabla = calcular_tabla(df)
equipos, metricas = sorted(df["Equipo"].unique()), sorted(df["Métrica"].unique())
max_f = int(df["nFecha"].max())

# Aplanar partidos para calibración e incluir nFecha para recencia
partidos_todos = []
for fecha, ps in datos.items():
    nf = int(re.search(r"\d+", fecha).group())
    for p in ps:
        p_f = p.copy()
        p_f["nFecha"] = nf
        partidos_todos.append(p_f)

# Generar tupla hasheable para cache (Metrics sorted para consistencia)
partidos_tuple = tuple(
    (p["local"], p["visitante"], tuple(sorted((k, v["local"], v["visitante"]) for k, v in p["metricas"].items())))
    for p in partidos_todos
)

a_xg, b_xg, int_xg, ref_home_xg, ref_away_xg = calibrar_xg_sint(partidos_tuple)
ref_home_real, ref_away_real = _league_refs(partidos_tuple)

st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Predictor (v9.3)</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    ea = c1.selectbox("Local", equipos)
    eb = c2.selectbox("Visitante", equipos, index=min(1, len(equipos)-1))
    loc = c3.toggle("Bono Localía", True)

    if st.button("🚀 INICIAR ANÁLISIS"):
        la, lb = calcular_lambdas(partidos_todos, ea, eb, loc, ref_home_xg, ref_away_xg, ref_home_real, ref_away_real, a_xg, b_xg, int_xg, max_f)
        sim = montecarlo(la, lb)
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi"><div class="lbl">Prob. {ea}</div><div class="val">{sim["victoria"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="lbl">Prob. Empate</div><div class="val">{sim["empate"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="lbl">Prob. {eb}</div><div class="val">{sim["derrota"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        
        pos_a = int(tabla.loc[ea,"Pos"]) if ea in tabla.index else "?"
        pos_b = int(tabla.loc[eb,"Pos"]) if eb in tabla.index else "?"
        st.markdown(f'<div class="note">λ {ea}={la:.3f} ({pos_a}°) | λ {eb}={lb:.3f} ({pos_b}°) | Formula xG: {a_xg:.3f}·TA + {b_xg:.3f}·TT + {int_xg:.3f}</div>', unsafe_allow_html=True)

        st.plotly_chart(go.Figure(go.Heatmap(z=sim["matrix"][:5,:5], x=[str(i) for i in range(5)], y=[str(i) for i in range(5)], 
                        colorscale=[[0,"#0f1829"],[1,"#e63946"]], showscale=False)).update_layout(**PLOT, height=320, xaxis_title=f"Goles {eb}", yaxis_title=f"Goles {ea}", yaxis=dict(autorange="reversed")), use_container_width=True)

# [MANTENER RANKINGS, H2H, PERFIL Y ESTILOS DE LA V9.2]
elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    m_sel = c1.selectbox("Métrica", metricas)
    cond_sel = c2.radio("Condición", ["General","Local","Visitante"], horizontal=True)
    tipo_sel = c3.radio("Enfoque", ["A Favor","En Contra"], horizontal=True)
    col_data = "Propio" if "A Favor" in tipo_sel else "Concedido"
    mask = (df["Condicion"] == cond_sel) if cond_sel != "General" else df.index.notna()
    res = df[mask & (df["Métrica"] == m_sel)].groupby("Equipo")[col_data].mean().sort_values(ascending=False).reset_index()
    st.plotly_chart(go.Figure(go.Bar(x=res[col_data], y=res["Equipo"], orientation="h", marker_color=RED if col_data=="Propio" else GRAY)).update_layout(**PLOT, height=700), use_container_width=True)

elif nav == "📋 Tabla":
    st.markdown('<div class="section-title">📋 Tabla de Posiciones</div>', unsafe_allow_html=True)
    if not tabla.empty:
        st.dataframe(tabla.reset_index()[["Pos","Equipo","PJ","V","E","D","GF","GC","PTS","PPJ"]], use_container_width=True, hide_index=True)
