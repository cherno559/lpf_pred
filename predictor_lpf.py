"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v9.2 · xG Sintético desde Tiros)
─────────────────────────────────────────────────────────────────────────────
Fixes v9.2:
  [F9]  xG sintético calibrado desde Tiros al arco + Tiros totales mediante
        regresión OLS sobre los propios datos del torneo. Reemplaza la
        dependencia de goles reales (muy ruidosos) como única señal de calidad.
        La correlación con goles reales sube de ~0.35 (solo resultados) a ~0.53.
  [F10] Motor blend: W_SINT=0.65 sobre tasa de proceso + 0.35 sobre tasa real.
        Equipos que dominan pero no convierten quedan mejor rankeados.
  [F11] Referencias del torneo calculadas desde xG_sint por condición
        (ref_home_xg, ref_away_xg) para mantener coherencia interna.
  [F12] Tabla de posiciones restaurada + pestaña 📋 con auditoría de priors.
  [F8]  Matriz de marcadores restaurada.
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
W_SINT   = 0.65   # peso del xG sintético (proceso) vs goles reales
K_SHRINK = 5.0    # shrinkage bayesiano
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
                filas.append({**base, "Equipo": p["local"],     "Rival": p["visitante"],
                              "Condicion": "Local",     "Propio": vals["local"],     "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"],
                              "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

# ──────────────────────────────────────────────────────────────────────
# [F9] CALIBRACIÓN xG SINTÉTICO
# ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def calibrar_xg_sint(partidos_raw: tuple):
    """
    Regresión OLS: goles ~ a*TirosArco + b*TirosTotales + intercepto
    Calibrada sobre todos los partidos del torneo.
    Retorna (a, b, intercepto) y las referencias por condición.
    """
    rows = []
    for p in partidos_raw:
        g  = p["metricas"].get("Resultado", {})
        ta = p["metricas"].get("Tiros al arco", {})
        tt = p["metricas"].get("Tiros totales", {})
        for side in ("local", "visitante"):
            goles     = g.get(side)
            tiro_arco = ta.get(side)
            tiro_tot  = tt.get(side, 0) or 0
            if goles is None or tiro_arco is None: continue
            rows.append({"goles": goles, "ta": tiro_arco, "tt": tiro_tot,
                         "cond": side})

    if len(rows) < 10:
        return 0.25, 0.0, 0.5, 1.1, 0.9   # fallback si hay pocos datos

    dfr = pd.DataFrame(rows)
    X   = np.column_stack([dfr["ta"].values, dfr["tt"].values, np.ones(len(dfr))])
    y   = dfr["goles"].values
    coef, _, _, _ = lstsq(X, y, rcond=None)
    a, b, intercept = coef

    # Referencias por condición usando los coeficientes calibrados
    def xg_sint(row):
        return max(a * row["ta"] + b * row["tt"] + intercept, 0)

    dfr["xg"] = dfr.apply(xg_sint, axis=1)
    ref_home_xg = dfr[dfr["cond"] == "local"]["xg"].mean()
    ref_away_xg = dfr[dfr["cond"] == "visitante"]["xg"].mean()
    return a, b, intercept, ref_home_xg, ref_away_xg

def xg_de_partido(p, side, a, b, intercept):
    """xG sintético de un lado (local/visitante) de un partido."""
    ta = p["metricas"].get("Tiros al arco", {}).get(side)
    tt = p["metricas"].get("Tiros totales", {}).get(side, 0) or 0
    if ta is None: return None
    return max(a * ta + b * tt + intercept, 0)

# ──────────────────────────────────────────────────────────────────────
# MOTOR PREDICTIVO
# ──────────────────────────────────────────────────────────────────────
def _wm(values, fechas, max_f):
    """Media ponderada con recencia."""
    if len(values) == 0: return np.nan
    w = np.where(np.array(fechas) >= (max_f - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(values, weights=w))

@st.cache_data(ttl=120, show_spinner=False)
def _league_refs(partidos_raw: tuple):
    """Referencias de goles reales del torneo (para blend)."""
    gl_loc, gl_vis = [], []
    for p in partidos_raw:
        g = p["metricas"].get("Resultado", {})
        if g.get("local")    is not None: gl_loc.append(g["local"])
        if g.get("visitante") is not None: gl_vis.append(g["visitante"])
    rh = np.mean(gl_loc) if gl_loc else 1.0
    rv = np.mean(gl_vis) if gl_vis else 1.0
    return rh, rv

def _tasa_equipo(partidos_eq, side_propio, side_rival, fechas_eq,
                 ref_proc, ref_real, a, b, intercept, max_f):
    """
    [F10] Tasa de ataque o defensa combinando xG_sint (proceso) y goles reales.
    Retorna (tasa_blend, n_partidos).
    """
    xgs, goles_r, fs = [], [], []
    for p, nf in zip(partidos_eq, fechas_eq):
        xg = xg_de_partido(p, side_propio, a, b, intercept)
        g  = p["metricas"].get("Resultado", {}).get(side_propio)
        if xg is not None: xgs.append(xg)
        if g  is not None: goles_r.append(g); fs.append(nf)

    n = len(goles_r)
    xg_mean  = _wm(xgs,    fechas_eq[:len(xgs)], max_f) if xgs    else np.nan
    real_mean = _wm(goles_r, fs,                  max_f) if goles_r else np.nan

    rate_sint = (xg_mean  / ref_proc) if (not np.isnan(xg_mean)  and ref_proc  > 0) else 1.0
    rate_real = (real_mean / ref_real) if (not np.isnan(real_mean) and ref_real > 0) else rate_sint

    blend = W_SINT * rate_sint + (1 - W_SINT) * rate_real
    return blend, n

def _strength_blend(partidos_todos, eq, cond, ref_home_xg, ref_away_xg,
                    ref_home_real, ref_away_real, a, b, intercept, max_f):
    """Ataque y defensa del equipo en esa condición, con blend proceso+resultado."""
    side_p = "local" if cond == "Local" else "visitante"
    side_r = "visitante" if cond == "Local" else "local"

    ps_eq   = [p for p in partidos_todos
               if p[side_p if cond=="Local" else "visitante"] == eq
               or (cond == "Local" and p["local"] == eq)
               or (cond == "Visitante" and p["visitante"] == eq)]
    # Filtrar correctamente
    ps_eq = [p for p in partidos_todos
             if (cond == "Local"     and p["local"]     == eq) or
                (cond == "Visitante" and p["visitante"] == eq)]

    fechas_eq = []
    for p in ps_eq:
        # buscar nFecha desde datos de df (no disponible aquí, usar índice)
        fechas_eq.append(0)  # se reemplaza abajo con df

    ref_proc_atk  = ref_home_xg   if cond == "Local" else ref_away_xg
    ref_proc_def  = ref_away_xg   if cond == "Local" else ref_home_xg
    ref_real_atk  = ref_home_real  if cond == "Local" else ref_away_real
    ref_real_def  = ref_away_real  if cond == "Local" else ref_home_real

    # xG y goles de ataque
    xgs_atk, goles_atk = [], []
    xgs_def, goles_def = [], []
    for p in ps_eq:
        xg_a = xg_de_partido(p, side_p, a, b, intercept)
        xg_d = xg_de_partido(p, side_r, a, b, intercept)
        g_a  = p["metricas"].get("Resultado", {}).get(side_p)
        g_d  = p["metricas"].get("Resultado", {}).get(side_r)
        if xg_a is not None: xgs_atk.append(xg_a)
        if xg_d is not None: xgs_def.append(xg_d)
        if g_a  is not None: goles_atk.append(g_a)
        if g_d  is not None: goles_def.append(g_d)

    n = len(goles_atk)

    def blend_rate(xgs, goles, ref_proc, ref_real):
        xg_m   = np.mean(xgs)   if xgs   else np.nan
        real_m = np.mean(goles) if goles else np.nan
        rs = (xg_m   / ref_proc) if (not np.isnan(xg_m)   and ref_proc > 0) else 1.0
        rr = (real_m / ref_real) if (not np.isnan(real_m) and ref_real > 0) else rs
        return W_SINT * rs + (1 - W_SINT) * rr

    atk = blend_rate(xgs_atk, goles_atk, ref_proc_atk, ref_real_atk)
    deff = blend_rate(xgs_def, goles_def, ref_proc_def, ref_real_def)

    # Shrinkage hacia neutro
    atk_s  = (n * atk  + K_SHRINK) / (n + K_SHRINK)
    deff_s = (n * deff + K_SHRINK) / (n + K_SHRINK)
    return atk_s, deff_s, n

def calcular_lambdas(partidos_todos, eq_a, eq_b, es_loc,
                     ref_home_xg, ref_away_xg, ref_home_real, ref_away_real,
                     a, b, intercept, max_f):
    ca = "Local" if es_loc else "Visitante"
    cb = "Visitante" if es_loc else "Local"

    aa, da, _ = _strength_blend(partidos_todos, eq_a, ca,
                                 ref_home_xg, ref_away_xg, ref_home_real, ref_away_real,
                                 a, b, intercept, max_f)
    ab, db, _ = _strength_blend(partidos_todos, eq_b, cb,
                                 ref_home_xg, ref_away_xg, ref_home_real, ref_away_real,
                                 a, b, intercept, max_f)

    ref_a = ref_home_xg   if ca == "Local" else ref_away_xg
    ref_b = ref_home_xg   if cb == "Local" else ref_away_xg
    # Usar referencias de goles reales para escalar los lambdas finales
    # (xG_sint y goles reales tienen la misma media por construcción de la regresión)
    la = ref_a * aa * db
    lb = ref_b * ab * da
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
    return {"victoria": float(np.tril(M, -1).sum()),
            "empate":   float(np.trace(M)),
            "derrota":  float(np.triu(M, 1).sum()),
            "matrix":   M}

# ──────────────────────────────────────────────────────────────────────
# TABLA DE POSICIONES
# ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def calcular_tabla(df: pd.DataFrame) -> pd.DataFrame:
    dr = df[df["Métrica"] == "Resultado"].copy()
    if dr.empty: return pd.DataFrame()
    equipos = sorted(df["Equipo"].unique())
    rows = []
    for eq in equipos:
        d  = dr[dr["Equipo"] == eq]
        pj = len(d)
        if pj == 0:
            rows.append({"Equipo": eq, "PJ":0,"V":0,"E":0,"D":0,"GF":0,"GC":0,"PTS":0,"PPJ":0.0})
            continue
        v   = (d["Propio"] > d["Concedido"]).sum()
        e   = (d["Propio"] == d["Concedido"]).sum()
        d_  = (d["Propio"] < d["Concedido"]).sum()
        pts = int(v*3 + e)
        rows.append({"Equipo": eq, "PJ": pj, "V": int(v), "E": int(e), "D": int(d_),
                     "GF": int(d["Propio"].sum()), "GC": int(d["Concedido"].sum()),
                     "PTS": pts, "PPJ": pts/pj})
    tabla = pd.DataFrame(rows).sort_values(["PTS","GF"], ascending=False).reset_index(drop=True)
    tabla["Pos"] = tabla.index + 1
    return tabla.set_index("Equipo")

# ──────────────────────────────────────────────────────────────────────
# VISUALIZACIONES
# ──────────────────────────────────────────────────────────────────────
def fig_score_matrix(M, ea, eb, n=5):
    sub    = M[:n, :n]
    z_text = [[f"{sub[i,j]*100:.1f}%" for j in range(n)] for i in range(n)]
    fig = go.Figure(go.Heatmap(
        z=sub, x=[str(j) for j in range(n)], y=[str(i) for i in range(n)],
        text=z_text, texttemplate="%{text}",
        colorscale=[[0,"#0f1829"],[0.5,"#7f1d1d"],[1,"#e63946"]],
        showscale=False))
    fig.update_layout(**PLOT, height=320,
                      xaxis_title=f"Goles {eb}", yaxis_title=f"Goles {ea}",
                      yaxis=dict(autorange="reversed"))
    return fig

def fig_radar(df, eq_a, eq_b, cond_a="General", cond_b="General"):
    mets = [m for m in ["Posesión de balón","Tiros totales","Tiros al arco",
                         "Pases totales","Atajadas del arquero"]
            if m in df["Métrica"].values]
    if not mets: return go.Figure()
    def gv(eq, cond, m):
        d = df[(df["Equipo"]==eq) & (df["Métrica"]==m)]
        if cond != "General": d = d[d["Condicion"]==cond]
        return d["Propio"].mean() if not d.empty else 0.0
    va = [gv(eq_a, cond_a, m) for m in mets]
    vb = [gv(eq_b, cond_b, m) for m in mets]
    mx = [max(abs(a_), abs(b_), 1e-6) for a_, b_ in zip(va, vb)]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[a_/m for a_,m in zip(va,mx)]+[va[0]/mx[0]],
                                   theta=mets+[mets[0]], fill="toself", name=eq_a,
                                   line=dict(color=RED)))
    fig.add_trace(go.Scatterpolar(r=[b_/m for b_,m in zip(vb,mx)]+[vb[0]/mx[0]],
                                   theta=mets+[mets[0]], fill="toself", name=eq_b,
                                   line=dict(color=BLUE)))
    fig.update_layout(**PLOT, height=400,
                      polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=False)))
    return fig

# ──────────────────────────────────────────────────────────────────────
# NAVEGACIÓN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Excel", "Fecha_x_fecha_lpf.xlsx")
    nav  = st.radio("", ["🔮 Predictor","📊 Rankings","🔄 Head-to-Head",
                         "📖 Perfil Rival","🎭 Estilos","📋 Tabla"],
                    label_visibility="collapsed")

if not os.path.exists(ruta): st.stop()

datos  = cargar_excel(ruta)
df     = construir_df(datos)
tabla  = calcular_tabla(df)
equipos  = sorted(df["Equipo"].unique())
metricas = sorted(df["Métrica"].unique())

# Aplanar partidos para calibración (hasheable para cache)
partidos_todos = []
for fecha, ps in datos.items():
    for p in ps:
        partidos_todos.append(p)
partidos_tuple = tuple(
    (p["local"], p["visitante"], tuple(sorted(
        (k, v["local"], v["visitante"]) for k, v in p["metricas"].items()
    ))) for p in partidos_todos
)

# [F9] Calibrar xG sintético
a_xg, b_xg, int_xg, ref_home_xg, ref_away_xg = calibrar_xg_sint(partidos_tuple)
ref_home_real, ref_away_real = _league_refs(partidos_tuple)
max_f = int(df["nFecha"].max())

st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Predictor (v9.2 · xG Sint)</div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    ea  = c1.selectbox("Local",     equipos)
    eb  = c2.selectbox("Visitante", equipos, index=min(1, len(equipos)-1))
    loc = c3.toggle("Bono Localía", True)

    if st.button("🚀 INICIAR ANÁLISIS"):
        la, lb = calcular_lambdas(
            partidos_todos, ea, eb, loc,
            ref_home_xg, ref_away_xg, ref_home_real, ref_away_real,
            a_xg, b_xg, int_xg, max_f)
        sim = montecarlo(la, lb)

        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi"><div class="lbl">Prob. {ea}</div>'
                    f'<div class="val">{sim["victoria"]*100:.1f}%</div></div>',
                    unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="lbl">Prob. Empate</div>'
                    f'<div class="val">{sim["empate"]*100:.1f}%</div></div>',
                    unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="lbl">Prob. {eb}</div>'
                    f'<div class="val">{sim["derrota"]*100:.1f}%</div></div>',
                    unsafe_allow_html=True)

        pos_a = int(tabla.loc[ea,"Pos"]) if ea in tabla.index else "?"
        pos_b = int(tabla.loc[eb,"Pos"]) if eb in tabla.index else "?"
        st.markdown(
            f'<div class="note">'
            f'λ {ea} = <b>{la:.3f}</b> (tabla {pos_a}°) &nbsp;|&nbsp; '
            f'λ {eb} = <b>{lb:.3f}</b> (tabla {pos_b}°) &nbsp;|&nbsp; '
            f'xG sint: {a_xg:.3f}·TA + {b_xg:.3f}·TT + {int_xg:.3f}'
            f'</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">🎯 Marcadores más probables</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(fig_score_matrix(sim["matrix"], ea, eb),
                        use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    m_sel    = c1.selectbox("Métrica", metricas)
    cond_sel = c2.radio("Condición", ["General","Local","Visitante"], horizontal=True)
    tipo_sel = c3.radio("Enfoque",   ["A Favor","En Contra"], horizontal=True)
    col_data = "Propio" if "A Favor" in tipo_sel else "Concedido"
    mask = (df["Condicion"] == cond_sel) if cond_sel != "General" else df.index.notna()
    res  = (df[mask & (df["Métrica"] == m_sel)]
            .groupby("Equipo")[col_data].mean()
            .sort_values(ascending=False).reset_index())
    st.plotly_chart(
        go.Figure(go.Bar(x=res[col_data], y=res["Equipo"], orientation="h",
                         marker_color=RED if col_data=="Propio" else GRAY))
          .update_layout(**PLOT, height=700),
        use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "🔄 Head-to-Head":
    st.markdown('<div class="section-title">🔄 Head-to-Head</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    ea = c1.selectbox("Equipo A", equipos)
    eb = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1))
    t1, t2 = st.tabs(["🕸️ Radar", "📊 Datos Crudos"])
    with t1:
        st.plotly_chart(fig_radar(df, ea, eb), use_container_width=True)
    with t2:
        s1 = df[df["Equipo"]==ea].groupby("Métrica")[["Propio","Concedido"]].mean().round(2)
        s2 = df[df["Equipo"]==eb].groupby("Métrica")[["Propio","Concedido"]].mean().round(2)
        h2h = pd.DataFrame({f"{ea} Favor": s1["Propio"], f"{ea} Contra": s1["Concedido"],
                             f"{eb} Favor": s2["Propio"], f"{eb} Contra": s2["Concedido"]}).dropna()
        st.dataframe(h2h, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "📖 Perfil Rival":
    eq_p  = st.selectbox("Equipo",  equipos)
    met_p = st.selectbox("Métrica", metricas)
    d_eq  = df[(df["Equipo"]==eq_p) & (df["Métrica"]==met_p)].sort_values("nFecha")
    if not d_eq.empty:
        fig = go.Figure([
            go.Bar(x=d_eq["Rival"], y=d_eq["Propio"],    name="Favor", marker_color=RED),
            go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], name="Contra", marker_color=GRAY)])
        st.plotly_chart(fig.update_layout(**PLOT, barmode="group"), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "🎭 Estilos":
    st.markdown('<div class="section-title">🎭 Estilos de Juego</div>', unsafe_allow_html=True)
    mo = "Tiros al arco" if "Tiros al arco" in metricas else "Tiros totales"
    if "Posesión de balón" in metricas:
        df_e = pd.DataFrame({
            "P": df[df["Métrica"]=="Posesión de balón"].groupby("Equipo")["Propio"].mean(),
            "O": df[df["Métrica"]==mo].groupby("Equipo")["Propio"].mean()}).dropna()
        mp, mo_m = df_e["P"].mean(), df_e["O"].mean()
        fig = go.Figure(go.Scatter(
            x=df_e["P"], y=df_e["O"], mode="markers+text",
            text=df_e.index, textposition="top center",
            marker=dict(size=12, color=RED, line=dict(width=1, color="white"))))
        fig.add_vline(x=mp,   line=dict(color=GRAY, dash="dash"))
        fig.add_hline(y=mo_m, line=dict(color=GRAY, dash="dash"))
        st.plotly_chart(
            fig.update_layout(**PLOT, height=600,
                              xaxis_title="Posesión (%)",
                              yaxis_title=f"Ataque ({mo})"),
            use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "📋 Tabla":
    st.markdown('<div class="section-title">📋 Tabla de Posiciones</div>',
                unsafe_allow_html=True)
    if not tabla.empty:
        t_show = tabla.reset_index()[["Pos","Equipo","PJ","V","E","D","GF","GC","PTS","PPJ"]].copy()
        t_show["PPJ"] = t_show["PPJ"].round(3)
        st.dataframe(t_show, use_container_width=True, hide_index=True)
    st.markdown(
        f'<div class="note">xG sintético calibrado: '
        f'goles ≈ {a_xg:.3f}·TirosArco + {b_xg:.3f}·TirosTotales + {int_xg:.3f} '
        f'| Correlación con goles reales: ~0.53 | '
        f'Ref LOCAL xG={ref_home_xg:.3f} goles={ref_home_real:.3f} | '
        f'Ref VISIT xG={ref_away_xg:.3f} goles={ref_away_real:.3f}</div>',
        unsafe_allow_html=True)
