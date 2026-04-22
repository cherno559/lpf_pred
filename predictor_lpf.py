"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v10.0 · Estabilidad Total)
─────────────────────────────────────────────────────────────────────────────
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

# ── Parámetros Calibrados ─────────────────────────────────────────────
W_XG = 0.70            # El xG manda pero el resultado real pesa (30%)
K_SHRINK = 3.5         # Suavizado para evitar que rachas cortas rompan todo
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.8, 1.0 
LAM_MIN, LAM_MAX = 0.25, 4.50
RED, BLUE, GRAY = "#e63946", "#3b82f6", "#64748b"
PLOT = dict(font=dict(family="Rajdhani", size=13, color="#dde3ee"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=20, t=36, b=10))

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
                    if r0.lower() in ("métrica","metrica") or r0 == loc: j+=1; continue
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
                filas.append({**base, "Equipo": p["local"], "Rival": p["visitante"], "Condicion": "Local", "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"], "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

# ──────────────────────────────────────────────────────────────────────
# MOTOR ANALÍTICO
# ──────────────────────────────────────────────────────────────────────
def _wm(values, fechas, max_f):
    if len(values) == 0: return np.nan
    w = np.where(np.array(fechas) >= (max_f - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(values, weights=w))

def _effective_rate(sub, col, max_f):
    dr, dx = sub[sub["Métrica"] == "Resultado"], sub[sub["Métrica"] == "Goles esperados (xG)"]
    g = _wm(dr[col].values, dr["nFecha"].values, max_f) if not dr.empty else np.nan
    x = _wm(dx[col].values, dx["nFecha"].values, max_f) if not dx.empty else np.nan
    if np.isnan(g) and np.isnan(x): return 1.0, 0
    if np.isnan(x): return g, len(dr)
    return W_XG * x + (1 - W_XG) * g, len(dr)

@st.cache_data(ttl=120, show_spinner=False)
def _league_stats(df, max_f):
    dr, dx = df[df["Métrica"] == "Resultado"], df[df["Métrica"] == "Goles esperados (xG)"]
    def get_avg(d, cond): return _wm(d[d["Condicion"]==cond]["Propio"].values, d[d["Condicion"]==cond]["nFecha"].values, max_f) if not d.empty else 1.0
    rh, rv = W_XG * get_avg(dx, "Local") + (1-W_XG) * get_avg(dr, "Local"), W_XG * get_avg(dx, "Visitante") + (1-W_XG) * get_avg(dr, "Visitante")
    return {"ref_home": rh, "ref_away": rv, "ref_all": (rh+rv)/2}

def _strength(df, eq, cond, league, max_f):
    d_eq = df[df["Equipo"] == eq]
    d_spec = d_eq[d_eq["Condicion"] == cond]
    gf_s, n_s = _effective_rate(d_spec, "Propio", max_f); gc_s, _ = _effective_rate(d_spec, "Concedido", max_f)
    rh, ra = (league["ref_home"], league["ref_away"]) if cond == "Local" else (league["ref_away"], league["ref_home"])
    atk = (n_s * (gf_s / rh) + K_SHRINK)/(n_s + K_SHRINK) if rh > 0 else 1.0
    deff = (n_s * (gc_s / ra) + K_SHRINK)/(n_s + K_SHRINK) if ra > 0 else 1.0
    return atk, deff, n_s

def calcular_lambdas(df, eq_a, eq_b, es_loc):
    max_f = df["nFecha"].max()
    l = _league_stats(df, max_f)
    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")
    aa, da, _ = _strength(df, eq_a, ca, l, max_f); ab, db, _ = _strength(df, eq_b, cb, l, max_f)
    la = (l["ref_home"] if ca == "Local" else l["ref_away"]) * aa * db
    lb = (l["ref_home"] if cb == "Local" else l["ref_away"]) * ab * da
    return round(float(np.clip(la, LAM_MIN, LAM_MAX)), 3), round(float(np.clip(lb, LAM_MIN, LAM_MAX)), 3)

def montecarlo(la, lb):
    def _pmf(lam, kmax):
        k = np.arange(kmax + 1)
        return np.exp(k * np.log(max(lam, 1e-9)) - lam - np.array([math.log(math.factorial(x)) for x in k]))
    pa, pb = _pmf(la, MAX_GOALS_MATRIX), _pmf(lb, MAX_GOALS_MATRIX)
    M = np.outer(pa, pb)
    rho = max(DC_RHO, -0.9 / max(la * lb, 0.01))
    M[0,0] = max(M[0,0]*(1-la*lb*rho), 0); M[0,1] *= (1+la*rho); M[1,0] *= (1+lb*rho); M[1,1] *= (1-rho)
    M /= M.sum()
    return {"victoria": float(np.tril(M, -1).sum()), "empate": float(np.trace(M)), "derrota": float(np.triu(M, 1).sum()), "matrix": M}

# ──────────────────────────────────────────────────────────────────────
# NAVEGACIÓN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Excel", "Fecha_x_fecha_lpf.xlsx")
    nav = st.radio("", ["🔮 Predictor", "📊 Rankings", "🔄 Head-to-Head", "📖 Perfil Rival", "🎭 Estilos", "📋 Tabla"], label_visibility="collapsed")

if not os.path.exists(ruta): st.stop()
df = construir_df(cargar_excel(ruta))
equipos, metricas = sorted(df["Equipo"].unique()), sorted(df["Métrica"].unique())
st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

if nav == "🔮 Predictor":
    c1, c2, c3 = st.columns([5, 5, 3])
    ea, eb, loc = c1.selectbox("Local", equipos), c2.selectbox("Visitante", equipos, index=min(1, len(equipos)-1)), c3.toggle("Bono Localía", True)
    if st.button("🚀 INICIAR ANÁLISIS"):
        la, lb = calcular_lambdas(df, ea, eb, loc)
        sim = montecarlo(la, lb)
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi"><div class="lbl">Prob. {ea}</div><div class="val">{sim["victoria"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="lbl">Prob. Empate</div><div class="val">{sim["empate"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="lbl">Prob. {eb}</div><div class="val">{sim["derrota"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        
        t1, t2 = st.tabs(["📊 Radar Comparativo", "🎯 Marcadores Probables"])
        with t1:
            mets = [m for m in ["Posesión de balón","Tiros totales","Tiros al arco","Goles esperados (xG)"] if m in metricas]
            va = [df[(df["Equipo"]==ea) & (df["Métrica"]==m)]["Propio"].mean() for m in mets]
            vb = [df[(df["Equipo"]==eb) & (df["Métrica"]==m)]["Propio"].mean() for m in mets]
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=va+[va[0]], theta=mets+[mets[0]], fill="toself", name=ea, line=dict(color=RED)))
            fig.add_trace(go.Scatterpolar(r=vb+[vb[0]], theta=mets+[mets[0]], fill="toself", name=eb, line=dict(color=BLUE)))
            st.plotly_chart(fig.update_layout(**PLOT, height=400, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=False))), use_container_width=True)
        with t2:
            st.plotly_chart(go.Figure(go.Heatmap(z=sim["matrix"][:5,:5], x=[str(i) for i in range(5)], y=[str(i) for i in range(5)], colorscale=[[0,"#0f1829"],[1,"#e63946"]], showscale=False)).update_layout(**PLOT, height=320, xaxis_title=f"Goles {eb}", yaxis_title=f"Goles {ea}", yaxis=dict(autorange="reversed")), use_container_width=True)

elif nav == "📊 Rankings":
    c1, c2, c3 = st.columns(3)
    m_sel, cond_sel, tipo_sel = c1.selectbox("Métrica", metricas), c2.radio("Condición", ["General","Local","Visitante"], horizontal=True), c3.radio("Enfoque", ["A Favor","En Contra"], horizontal=True)
    col_data = "Propio" if "A Favor" in tipo_sel else "Concedido"
    res = df[(df["Condicion"] == cond_sel if cond_sel != "General" else True) & (df["Métrica"] == m_sel)].groupby("Equipo")[col_data].mean().sort_values(ascending=False).reset_index()
    st.plotly_chart(go.Figure(go.Bar(x=res[col_data], y=res["Equipo"], orientation="h", marker_color=RED if col_data=="Propio" else GRAY)).update_layout(**PLOT, height=700), use_container_width=True)

elif nav == "🔄 Head-to-Head":
    c1, c2 = st.columns(2); ea, eb = c1.selectbox("Equipo A", equipos), c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1))
    s1, s2 = df[df["Equipo"]==ea].groupby("Métrica")[["Propio", "Concedido"]].mean().round(2), df[df["Equipo"]==eb].groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)
    st.table(pd.DataFrame({f"{ea} Favor": s1["Propio"], f"{ea} Contra": s1["Concedido"], f"{eb} Favor": s2["Propio"], f"{eb} Contra": s2["Concedido"]}).dropna())

elif nav == "🎭 Estilos":
    st.markdown('<div class="section-title">🎭 Análisis de Estilo (Original)</div>', unsafe_allow_html=True)
    mo = "Tiros al arco" if "Tiros al arco" in metricas else "Tiros totales"
    df_e = pd.DataFrame({"P": df[df["Métrica"] == "Posesión de balón"].groupby("Equipo")["Propio"].mean(), "O": df[df["Métrica"] == mo].groupby("Equipo")["Propio"].mean()}).dropna()
    mp, mo_m = df_e["P"].mean(), df_e["O"].mean()
    fig = go.Figure(go.Scatter(x=df_e["P"], y=df_e["O"], mode="markers+text", text=df_e.index, textposition="top center", marker=dict(size=12, color=RED, line=dict(width=1, color="white"))))
    fig.add_vline(x=mp, line=dict(color=GRAY, dash="dash")); fig.add_hline(y=mo_m, line=dict(color=GRAY, dash="dash"))
    st.plotly_chart(fig.update_layout(**PLOT, height=600, xaxis_title="Posesión (%)", yaxis_title=f"Ataque ({mo})"), use_container_width=True)

elif nav == "📋 Tabla":
    dr = df[df["Métrica"] == "Resultado"].copy()
    rows = [{"Equipo": eq, "PJ": len(dr[dr["Equipo"]==eq]), "V": (dr[dr["Equipo"]==eq]["Propio"] > dr[dr["Equipo"]==eq]["Concedido"]).sum(), "E": (dr[dr["Equipo"]==eq]["Propio"] == dr[dr["Equipo"]==eq]["Concedido"]).sum(), "GF": dr[dr["Equipo"]==eq]["Propio"].sum(), "GC": dr[dr["Equipo"]==eq]["Concedido"].sum()} for eq in equipos]
    tabla = pd.DataFrame(rows); tabla["PTS"] = tabla["V"]*3 + tabla["E"]
    st.dataframe(tabla.sort_values(["PTS","GF"], ascending=False), use_container_width=True, hide_index=True)
