"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v9.0 · Correcciones estructurales)
─────────────────────────────────────────────────────────────────────────────
Fixes v9.0:
  [F1] Filtro "General" en Rankings: usa slice neutral en lugar de True suelto
  [F2] _effective_rate: fallback NaN no contagia 1.0 falso; usa solo la fuente disponible
  [F3] Recencia: fechas.max() calculado sobre TODO el torneo, no sobre el subconjunto
  [F4] Dixon-Coles rho: clip de toda la corrección para que M[i,j] >= 0 siempre
  [F5] K_SHRINK subido a 6.0 para mejor regulación con 12-20 fechas
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
# [F5] Subido de 3.0 → 6.0: con 12-20 fechas el shrinkage a 3.0 era insuficiente
# y equipos con rachas cortas inflaban/desinflaban sus lambdas sin regulación
K_SHRINK = 6.0
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.5, 1.0
MAX_ROTATION_PENALTY, LAM_MIN, LAM_MAX = 0.12, 0.25, 4.50
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
                filas.append({**base, "Equipo": p["local"], "Rival": p["visitante"], "Condicion": "Local", "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"], "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

# [F3] max_fecha_torneo se calcula UNA SOLA VEZ sobre todo el df y se pasa como parámetro
# para que la ventana de recencia sea consistente entre todos los equipos
def _weighted_mean(values, fechas, max_fecha_torneo: int):
    if len(values) == 0: return np.nan
    w = np.where(fechas >= (max_fecha_torneo - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(values, weights=w))

# [F2] Si solo existe una de las dos fuentes (xG o resultado real), se usa esa sin mezcla
# En lugar de retornar 1.0 cuando xG no existe, retorna NaN para que _strength lo maneje
def _effective_rate(sub, col, max_fecha_torneo: int):
    dr = sub[sub["Métrica"] == "Resultado"]
    dx = sub[sub["Métrica"] == "Goles esperados (xG)"]
    g = _weighted_mean(dr[col].values, dr["nFecha"].values, max_fecha_torneo) if not dr.empty else np.nan
    x = _weighted_mean(dx[col].values, dx["nFecha"].values, max_fecha_torneo) if not dx.empty else np.nan
    n = len(dr)  # cantidad de partidos con resultado (más confiable para shrinkage)
    if np.isnan(g) and np.isnan(x):
        return np.nan, 0  # sin datos: se usará puro shrinkage en _strength
    if np.isnan(x):
        return g, n       # solo resultado real disponible
    if np.isnan(g):
        return x, n       # solo xG disponible
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
    # Si no hay xG en el torneo, usar solo goles reales
    if dx.empty:
        rh, rv = gh, gv
    else:
        rh = W_XG * xh + (1-W_XG) * gh
        rv = W_XG * xv + (1-W_XG) * gv
    return {"ref_home": rh, "ref_away": rv, "ref_all": (rh+rv)/2}

def _strength(df, eq, cond, league, max_fecha_torneo: int):
    d_eq   = df[df["Equipo"] == eq]
    d_spec = d_eq[d_eq["Condicion"] == cond]

    gf_s, n_s = _effective_rate(d_spec, "Propio",    max_fecha_torneo)
    gc_s, _   = _effective_rate(d_spec, "Concedido", max_fecha_torneo)

    rh, ra = league["ref_home"], league["ref_away"]
    ref_f, ref_a = (rh, ra) if cond == "Local" else (ra, rh)

    # [F2] Si rate es NaN (sin datos para esa condición), shrinkage completo → fuerza = 1.0
    atk  = (gf_s / ref_f)  if (not np.isnan(gf_s)  and ref_f  > 0) else 1.0
    deff = (gc_s / ref_a)  if (not np.isnan(gc_s)   and ref_a  > 0) else 1.0

    # [F5] K_SHRINK=6.0: shrinkage más agresivo para equipos con pocas apariciones
    n = n_s if n_s > 0 else 0
    atk  = (n * atk  + K_SHRINK * 1.0) / (n + K_SHRINK)
    deff = (n * deff + K_SHRINK * 1.0) / (n + K_SHRINK)
    return atk, deff, n

def calcular_lambdas(df, eq_a, eq_b, es_loc):
    l = _league_stats(df)
    # [F3] max_fecha_torneo global, no por subconjunto
    max_fecha_torneo = int(df["nFecha"].max())
    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")
    aa, da, _ = _strength(df, eq_a, ca, l, max_fecha_torneo)
    ab, db, _ = _strength(df, eq_b, cb, l, max_fecha_torneo)
    la = (l["ref_home"] if ca == "Local" else l["ref_away"]) * aa * db
    lb = (l["ref_home"] if cb == "Local" else l["ref_away"]) * ab * da
    return round(float(np.clip(la, LAM_MIN, LAM_MAX)), 3), round(float(np.clip(lb, LAM_MIN, LAM_MAX)), 3)

def montecarlo(la, lb):
    def _pmf(lam, kmax):
        k = np.arange(kmax + 1)
        return np.exp(k * np.log(max(lam, 1e-9)) - lam - np.array([math.log(math.factorial(x)) for x in k]))

    pa, pb = _pmf(la, MAX_GOALS_MATRIX), _pmf(lb, MAX_GOALS_MATRIX)
    M = np.outer(pa, pb)

    # [F4] Corrección Dixon-Coles aplicada celda por celda con clip a [0, inf)
    # para garantizar que ninguna probabilidad sea negativa antes de normalizar
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
        "lambda_a": la,
        "lambda_b": lb,
    }

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
# NAVEGACIÓN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Excel", "Fecha_x_fecha_lpf.xlsx")
    nav = st.radio("", ["🔮 Predictor", "📊 Rankings", "🔄 Head-to-Head", "📖 Perfil Rival", "🎭 Estilos"], label_visibility="collapsed")

if not os.path.exists(ruta): st.stop()
datos = cargar_excel(ruta); df = construir_df(datos)
equipos, metricas = sorted(df["Equipo"].unique()), sorted(df["Métrica"].unique())
st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Predictor (v9.0)</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    ea  = c1.selectbox("Local", equipos)
    eb  = c2.selectbox("Visitante", equipos, index=min(1, len(equipos)-1))
    loc = c3.toggle("Bono Localía", True)
    if st.button("🚀 INICIAR ANÁLISIS"):
        la, lb = calcular_lambdas(df, ea, eb, loc)
        sim = montecarlo(la, lb)
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi"><div class="lbl">Prob. {ea}</div><div class="val">{sim["victoria"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="lbl">Prob. Empate</div><div class="val">{sim["empate"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="lbl">Prob. {eb}</div><div class="val">{sim["derrota"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="note">λ {ea} = {la:.3f} · λ {eb} = {lb:.3f}</div>', unsafe_allow_html=True)

elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings: Favor vs Concedido</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    m_sel    = c1.selectbox("Métrica", metricas)
    cond_sel = c2.radio("Condición", ["General", "Local", "Visitante"], horizontal=True)
    tipo_sel = c3.radio("Enfoque", ["A Favor", "En Contra"], horizontal=True)
    col_data = "Propio" if "A Favor" in tipo_sel else "Concedido"

    # [F1] Filtro corregido: slice neutral df.index.notna() en lugar de True suelto
    mask_cond = (df["Condicion"] == cond_sel) if cond_sel != "General" else df.index.notna()
    res = (
        df[mask_cond & (df["Métrica"] == m_sel)]
        .groupby("Equipo")[col_data]
        .mean()
        .sort_values(ascending=False)
        .reset_index()
    )
    st.plotly_chart(
        go.Figure(go.Bar(x=res[col_data], y=res["Equipo"], orientation="h",
                         marker_color=RED if col_data == "Propio" else GRAY))
          .update_layout(**PLOT, height=700),
        use_container_width=True
    )

elif nav == "🔄 Head-to-Head":
    st.markdown('<div class="section-title">🔄 Head-to-Head Comparativo</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    ea = c1.selectbox("Equipo A", equipos)
    eb = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1))
    t1, t2 = st.tabs(["🕸️ Comparativa Radar", "📊 Datos Crudos"])
    with t1:
        st.plotly_chart(fig_radar(df, ea, eb, "General", "General"), use_container_width=True)
    with t2:
        s1 = df[df["Equipo"]==ea].groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)
        s2 = df[df["Equipo"]==eb].groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)
        h2h_df = pd.DataFrame({
            f"{ea} Favor":  s1["Propio"],
            f"{ea} Contra": s1["Concedido"],
            f"{eb} Favor":  s2["Propio"],
            f"{eb} Contra": s2["Concedido"],
        }).dropna()
        st.dataframe(h2h_df, use_container_width=True)

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
            x=df_e["P"], y=df_e["O"],
            mode="markers+text", text=df_e.index, textposition="top center",
            marker=dict(size=12, color=RED, line=dict(width=1, color="white")),
        ))
        fig.add_vline(x=mp,   line=dict(color=GRAY, dash="dash"))
        fig.add_hline(y=mo_m, line=dict(color=GRAY, dash="dash"))
        st.plotly_chart(
            fig.update_layout(**PLOT, height=600, xaxis_title="Posesión (%)", yaxis_title=f"Ataque ({mo})"),
            use_container_width=True,
        )
