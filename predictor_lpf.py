"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v8.2 · Full Credibilidad)
─────────────────────────────────────────────────────────────────────────────
"""
import re, os, math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILOS CSS
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Analítica Pro", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #080d18; color: #dde3ee; }
section[data-testid="stSidebar"] { background: #0c1220 !important; border-right: 1px solid #1c2a40; }
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: #8899aa !important; font-size:13px !important; }
h1 { font-family:'Bebas Neue',cursive !important; font-size:2.6rem !important; color:#e63946 !important; letter-spacing:3px; margin-bottom:0; }
.section-title { font-family:'Bebas Neue',cursive; font-size:1.3rem; letter-spacing:3px; color:#e63946; border-bottom:1px solid #1c2a40; padding-bottom:8px; margin:28px 0 18px; text-transform:uppercase; }
.kpi { background:linear-gradient(135deg,#0f1829,#162035); border:1px solid #1c2a40; border-left:4px solid #e63946; border-radius:10px; padding:16px 18px; text-align:center; }
.kpi.draw { border-left-color:#64748b; } .kpi.loss { border-left-color:#3b82f6; }
.kpi .lbl { font-family:'Rajdhani'; font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:#64748b; }
.kpi .val { font-family:'Bebas Neue'; font-size:38px; color:#e63946; line-height:1.05; }
.kpi.draw .val { color:#94a3b8; } .kpi.loss .val { color:#60a5fa; }
.stTabs [data-baseweb="tab-list"] { background:#0f1829; border-radius:10px; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"] { font-family:'Rajdhani'; font-weight:700; font-size:14px; color:#64748b !important; border-radius:7px; padding:6px 16px; }
.stTabs [aria-selected="true"] { background:#e63946 !important; color:#fff !important; }
.stButton>button { font-family:'Bebas Neue'; font-size:17px; letter-spacing:2px; background:linear-gradient(135deg,#e63946,#b91c2c); color:#fff; border:none; border-radius:9px; padding:13px; width:100%; }
.stSelectbox>div>div, .stMultiSelect>div>div, .stTextInput>div>div { background:#0f1829 !important; border:1px solid #1c2a40 !important; color:#dde3ee !important; border-radius:8px !important; }
.note { background:#0f1829; border:1px solid #1c2a40; border-radius:8px; padding:10px 14px; font-size:12px; color:#64748b; margin-top:8px; }
</style>
""", unsafe_allow_html=True)

# ── Parámetros del Motor (Credibilidad Ajustada) ──────────────────────
W_XG = 0.85            # Prioridad máxima al xG sobre el resultado
K_SHRINK = 5.0         # Mayor escepticismo con equipos atípicos
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
PESO_ESP_ALTO, PESO_ESP_BAJO, PESO_ESPECIFICO_MIN_N = 0.70, 0.40, 3
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 2.5, 1.0
MAX_ROTATION_PENALTY, LAM_MIN, LAM_MAX = 0.12, 0.25, 4.50

RED, BLUE, GRAY = "#e63946", "#3b82f6", "#64748b"
PLOT = dict(font=dict(family="Rajdhani", size=13, color="#dde3ee"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=20, t=36, b=10))
GRID = dict(showgrid=True, gridcolor="#1c2a40", zeroline=False)

# ──────────────────────────────────────────────────────────────────────
# PROCESAMIENTO DE DATOS
# ──────────────────────────────────────────────────────────────────────
def num(v) -> float:
    if isinstance(v, str): v = v.replace('%', '').replace(',', '.').strip()
    try: return float(v)
    except: return 0.0

@st.cache_data(ttl=120, show_spinner=False)
def cargar_excel(ruta: str):
    if not os.path.exists(ruta): return {}
    xl = pd.ExcelFile(ruta, engine="openpyxl")
    resultado = {}
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE): continue
        df = pd.read_excel(ruta, sheet_name=hoja, header=None)
        partidos, i = [], 0
        while i < len(df):
            c0 = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""
            if re.search(r"\s+vs\s+", c0, re.IGNORECASE):
                p = re.split(r"\s+vs\s+", c0, flags=re.IGNORECASE)
                loc, vis, stats, j = p[0].strip(), p[1].strip(), {}, i + 1
                while j < len(df):
                    r0 = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                    if r0 == "" or re.search(r"\s+vs\s+", r0, re.IGNORECASE): break
                    if r0.lower() in ("métrica", "metrica") or r0 == loc: j += 1; continue
                    if pd.notna(df.iloc[j, 1]): stats[r0] = {"local": num(df.iloc[j, 1]), "visitante": num(df.iloc[j, 2])}
                    j += 1
                if stats: partidos.append({"local": loc, "visitante": vis, "metricas": stats})
                i = j
            else: i += 1
        resultado[hoja] = partidos
    return resultado

def construir_df(datos: dict) -> pd.DataFrame:
    filas = []
    for fecha, partidos in datos.items():
        nf = int(re.search(r"\d+", fecha).group())
        for p in partidos:
            for met, vals in p["metricas"].items():
                base = {"Fecha": fecha, "nFecha": nf, "Métrica": met}
                filas.append({**base, "Equipo": p["local"], "Rival": p["visitante"], "Condicion": "Local", "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"], "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

# ──────────────────────────────────────────────────────────────────────
# MOTOR MATEMÁTICO V8.2
# ──────────────────────────────────────────────────────────────────────
def _weighted_mean(values: np.ndarray, fechas: np.ndarray) -> float:
    if len(values) == 0: return float("nan")
    max_f = fechas.max()
    w = np.where(fechas >= (max_f - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(values, weights=w))

def _effective_rate(sub: pd.DataFrame, col: str) -> tuple[float, int]:
    dr, dx = sub[sub["Métrica"] == "Resultado"], sub[sub["Métrica"] == "Goles esperados (xG)"]
    g = _weighted_mean(dr[col].values, dr["nFecha"].values) if not dr.empty else float("nan")
    x = _weighted_mean(dx[col].values, dx["nFecha"].values) if not dx.empty else float("nan")
    if np.isnan(g) and np.isnan(x): return 1.0, 0
    if np.isnan(x): return g, len(dr)
    return W_XG * x + (1 - W_XG) * g, len(dr)

def _strength(df: pd.DataFrame, eq: str, cond: str, league: dict) -> tuple[float, float, int]:
    d_eq = df[df["Equipo"] == eq]
    d_spec = d_eq[d_eq["Condicion"] == cond]
    gf_s, n_s = _effective_rate(d_spec, "Propio"); gc_s, _ = _effective_rate(d_spec, "Concedido")
    gf_g, _ = _effective_rate(d_eq, "Propio"); gc_g, _ = _effective_rate(d_eq, "Concedido")
    rh, ra, rall = league["ref_home"], league["ref_away"], league["ref_all"]
    ref_f, ref_a = (rh, ra) if cond == "Local" else (ra, rh)
    
    aspec, gspec = gf_s / ref_f if ref_f > 0 else 1.0, gc_s / ref_a if ref_a > 0 else 1.0
    agen, ggen = gf_g / rall if rall > 0 else 1.0, gc_g / rall if rall > 0 else 1.0
    w_s = PESO_ESP_ALTO if n_s >= PESO_ESPECIFICO_MIN_N else PESO_ESP_BAJO
    
    atk = np.nan_to_num(w_s * aspec + (1-w_s) * agen, nan=1.0)
    deff = np.nan_to_num(w_s * gspec + (1-w_s) * ggen, nan=1.0)
    
    # Shrinkage K=5.0
    atk = (n_s * atk + K_SHRINK * 1.0) / (n_s + K_SHRINK)
    deff = (n_s * deff + K_SHRINK * 1.0) / (n_s + K_SHRINK)
    return atk, deff, n_s

def calcular_lambdas(df, eq_a, eq_b, es_loc, rot_a=0, rot_b=0):
    dr = df[df["Métrica"] == "Resultado"]
    lh, lv = dr[dr["Condicion"] == "Local"]["Propio"].mean() or 1.3, dr[dr["Condicion"] == "Visitante"]["Propio"].mean() or 1.0
    l_stats = {"ref_home": lh, "ref_away": lv, "ref_all": (lh+lv)/2}
    
    aa, da, na = _strength(df, eq_a, "Local" if es_loc else "Visitante", l_stats)
    ab, db, nb = _strength(df, eq_b, "Visitante" if es_loc else "Local", l_stats)
    
    la = (lh if es_loc else lv) * aa * db
    lb = (lv if es_loc else lh) * ab * da
    if rot_a > 0: la *= (1 - rot_a * MAX_ROTATION_PENALTY)
    if rot_b > 0: lb *= (1 - rot_b * MAX_ROTATION_PENALTY)
    return round(float(np.clip(la, LAM_MIN, LAM_MAX)), 3), round(float(np.clip(lb, LAM_MIN, LAM_MAX)), 3)

def montecarlo(lam_a, lam_b):
    def _pmf(lam, kmax):
        k = np.arange(kmax + 1)
        return np.exp(k * np.log(max(lam, 1e-9)) - lam - np.array([math.log(math.factorial(x)) for x in k]))
    pa, pb = _pmf(lam_a, MAX_GOALS_MATRIX), _pmf(lam_b, MAX_GOALS_MATRIX)
    M = np.outer(pa, pb)
    rho = max(DC_RHO, -0.9 / max(lam_a * lam_b, 0.01))
    M[0,0]*=(1-lam_a*lam_b*rho); M[0,1]*=(1+lam_a*rho); M[1,0]*=(1+lam_b*rho); M[1,1]*=(1-rho)
    M /= M.sum()
    return {"victoria": float(np.tril(M, -1).sum()), "empate": float(np.trace(M)), "derrota": float(np.triu(M, 1).sum())}

# ──────────────────────────────────────────────────────────────────────
# FUNCIONES VISUALES
# ──────────────────────────────────────────────────────────────────────
def fig_radar(df, eq_a, eq_b, cond_a, cond_b):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco", "Goles esperados (xG)", "Pases totales"] if m in df["Métrica"].values]
    if not mets: return go.Figure()
    def gv(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General": d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0
    va, vb = [gv(eq_a, cond_a, m) for m in mets], [gv(eq_b, cond_b, m) for m in mets]
    mx = [max(abs(a), abs(b), 1e-6) for a, b in zip(va, vb)]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[a/m for a,m in zip(va,mx)]+[va[0]/mx[0]], theta=mets+[mets[0]], fill="toself", name=eq_a, line=dict(color=RED)))
    fig.add_trace(go.Scatterpolar(r=[b/m for b,m in zip(vb,mx)]+[vb[0]/mx[0]], theta=mets+[mets[0]], fill="toself", name=eq_b, line=dict(color=BLUE)))
    fig.update_layout(**PLOT, height=400, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=False)))
    return fig

# ──────────────────────────────────────────────────────────────────────
# NAVEGACIÓN Y RENDER
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Archivo Excel", "Fecha_x_fecha_lpf.xlsx")
    st.markdown("---")
    nav = st.radio("", ["🔮 Predictor", "📊 Rankings", "🔄 Head-to-Head", "📖 Perfil Rival", "🎭 Estilos"], label_visibility="collapsed")

if not os.path.exists(ruta): st.warning("Cargar Excel."); st.stop()
datos = cargar_excel(ruta); df = construir_df(datos)
equipos, metricas = sorted(df["Equipo"].unique()), sorted(df["Métrica"].unique())
st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Simulación Analítica (W_xG=0.85)</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    ea, eb, loc = c1.selectbox("Local", equipos), c2.selectbox("Visitante", equipos, index=1), c3.toggle("Bono Localía", True)
    rc1, rc2 = st.columns(2)
    rota = rc1.slider(f"Rotación {ea}", 0.0, 1.0, 0.0) if rc1.checkbox(f"Rotar {ea}") else 0.0
    rotb = rc2.slider(f"Rotación {eb}", 0.0, 1.0, 0.0) if rc2.checkbox(f"Rotar {eb}") else 0.0
    if st.button("🚀 INICIAR ANÁLISIS"):
        la, lb = calcular_lambdas(df, ea, eb, loc, rota, rotb)
        sim = montecarlo(la, lb)
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi"><div class="lbl">Prob. {ea}</div><div class="val">{sim["victoria"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="lbl">Prob. Empate</div><div class="val">{sim["empate"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="lbl">Prob. {eb}</div><div class="val">{sim["derrota"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="note">⚙️ Ajuste de Credibilidad: λ {ea}={la} · λ {eb}={lb}</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_radar(df, ea, eb, "Local" if loc else "General", "Visitante" if loc else "General"), use_container_width=True)

elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings</div>', unsafe_allow_html=True)
    m_sel = st.selectbox("Métrica", metricas)
    df_r = df[df["Métrica"] == m_sel].groupby("Equipo")["Propio"].mean().sort_values(ascending=False).reset_index()
    st.plotly_chart(go.Figure(go.Bar(x=df_r["Propio"], y=df_r["Equipo"], orientation="h", marker_color=RED)).update_layout(**PLOT, height=600), use_container_width=True)

elif nav == "🔄 Head-to-Head":
    st.markdown('<div class="section-title">🔄 H2H</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2); ea, eb = c1.selectbox("Equipo A", equipos), c2.selectbox("Equipo B", equipos, index=1)
    s1, s2 = df[df["Equipo"]==ea].groupby("Métrica")["Propio"].mean(), df[df["Equipo"]==eb].groupby("Métrica")["Propio"].mean()
    st.dataframe(pd.DataFrame({ea: s1, eb: s2}).round(2).dropna(), use_container_width=True)

elif nav == "📖 Perfil Rival":
    st.markdown('<div class="section-title">📖 Perfil</div>', unsafe_allow_html=True)
    eq_p, met_p = st.selectbox("Equipo", equipos), st.selectbox("Métrica", metricas)
    d_eq = df[(df["Equipo"] == eq_p) & (df["Métrica"] == met_p)].sort_values("nFecha")
    if not d_eq.empty: st.plotly_chart(go.Figure([go.Bar(x=d_eq["Rival"], y=d_eq["Propio"], name="Favor", marker_color=RED), go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], name="Contra", marker_color=GRAY)]).update_layout(**PLOT, barmode="group"), use_container_width=True)

elif nav == "🎭 Estilos":
    st.markdown('<div class="section-title">🎭 Estilos</div>', unsafe_allow_html=True)
    if "Posesión de balón" in metricas:
        mo = "Goles esperados (xG)" if "Goles esperados (xG)" in metricas else "Tiros totales"
        df_e = pd.DataFrame({"P": df[df["Métrica"]=="Posesión de balón"].groupby("Equipo")["Propio"].mean(), "O": df[df["Métrica"]==mo].groupby("Equipo")["Propio"].mean()}).dropna()
        fig = go.Figure(go.Scatter(x=df_e["P"], y=df_e["O"], mode="markers+text", text=df_e.index, marker=dict(size=12, color=RED)))
        st.plotly_chart(fig.update_layout(**PLOT, height=600, xaxis_title="Posesión", yaxis_title=mo), use_container_width=True)
