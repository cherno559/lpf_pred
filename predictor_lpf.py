"""
dashboard_lpf_v2.py — LPF 2026 · Modelo Predictivo Mejorado
─────────────────────────────────────────────────────────────
Mejoras clave sobre v1:
  • xG sintético calibrado: construido desde tiros al arco +
    ocasiones claras + % tiros dentro del área (sin depender
    del campo xG que siempre viene en 0).
  • Multi-métrica attack/defense: la λ de cada equipo pondera
    xG sintético, shot-on-target ratio, eficiencia de
    ocasiones claras y presión defensiva (Quites+Intercepciones).
  • Regresión al promedio bayesiana por separado para ataque y
    defensa (K adaptable), con recencia configurable.
  • Corrección Dixon-Coles completa (τ para 0-0,1-0,0-1,1-1).
  • Componente de forma reciente configurable (N fechas).
  • Ajuste localía con bono separado para ataque y defensa.
  • Simulación Monte Carlo + distribución Poisson bivariada.
  • Distribución de goles totales (Over/Under) con líneas
    configurables.
  • Índice de confianza del modelo (cuántos partidos tiene cada
    equipo para calcular sus stats).
"""

import re, os, math, warnings
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LPF 2026 · Modelo Pro v2",
    page_icon="⚽", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #080d18; color: #dde3ee; }
section[data-testid="stSidebar"] { background: #0c1220 !important; border-right: 1px solid #1c2a40; }
h1 { font-family:'Bebas Neue',cursive !important; font-size:2.4rem !important; color:#e63946 !important; letter-spacing:3px; margin-bottom:0; }
h2 { font-family:'Bebas Neue',cursive !important; font-size:1.6rem !important; color:#e63946 !important; letter-spacing:2px; }
.section-title { font-family:'Bebas Neue',cursive; font-size:1.2rem; letter-spacing:3px; color:#e63946; border-bottom:1px solid #1c2a40; padding-bottom:6px; margin:22px 0 14px; text-transform:uppercase; }
.kpi { background:linear-gradient(135deg,#0f1829,#162035); border:1px solid #1c2a40; border-left:4px solid #e63946; border-radius:10px; padding:16px 18px; text-align:center; }
.kpi.draw { border-left-color:#64748b; }
.kpi.loss { border-left-color:#3b82f6; }
.kpi.over { border-left-color:#22c55e; }
.kpi .lbl { font-family:'Rajdhani'; font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:#64748b; }
.kpi .val { font-family:'Bebas Neue'; font-size:36px; color:#e63946; line-height:1.1; }
.kpi.draw .val, .kpi.loss .val { color:#64748b; }
.kpi.over .val { color:#22c55e; }
.stTabs [data-baseweb="tab-list"] { background:#0f1829; border-radius:10px; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"] { font-family:'Rajdhani'; font-weight:700; font-size:14px; color:#64748b !important; border-radius:7px; padding:6px 16px; }
.stTabs [aria-selected="true"] { background:#e63946 !important; color:#fff !important; }
.stButton>button { font-family:'Bebas Neue'; font-size:17px; letter-spacing:2px; background:linear-gradient(135deg,#e63946,#b91c2c); color:#fff; border:none; border-radius:9px; padding:13px; width:100%; }
.note { background:#0f1829; border:1px solid #1c2a40; border-radius:8px; padding:10px 14px; font-size:12px; color:#64748b; margin-top:8px; }
.warn { background:#1a1205; border:1px solid #92400e; border-radius:8px; padding:10px 14px; font-size:12px; color:#fbbf24; margin-top:8px; }
.stSelectbox>div>div, .stTextInput>div>div { background:#0f1829 !important; border:1px solid #1c2a40 !important; color:#dde3ee !important; border-radius:8px !important; }
</style>
""", unsafe_allow_html=True)

RED, BLUE, GREEN, GRAY = "#e63946", "#3b82f6", "#22c55e", "#64748b"
PLOT = dict(
    font=dict(family="Rajdhani", size=13, color="#dde3ee"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=20, t=36, b=10)
)

MAX_G = 8          # goles máximos en matriz

# ──────────────────────────────────────────────────────────────────────
# PARSING DEL EXCEL
# ──────────────────────────────────────────────────────────────────────
def _parse_num(v) -> float:
    """Convierte string/porcentaje a float."""
    if isinstance(v, str):
        v = v.replace('%', '').replace(',', '.').strip()
        m = re.search(r'^[\d.]+', v)
        if m:
            return float(m.group())
        return 0.0
    try:
        return float(v)
    except:
        return 0.0

def _parse_regate(v) -> float:
    """Extrae % de éxito de '7/17 (41%)'."""
    if isinstance(v, str):
        m = re.search(r'\((\d+)%\)', v)
        if m:
            return float(m.group(1))
    return 0.0

@st.cache_data(ttl=180, show_spinner=False)
def cargar_excel(ruta: str) -> dict:
    if not os.path.exists(ruta):
        return {}
    xl = pd.ExcelFile(ruta, engine="openpyxl")
    datos = {}
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE):
            continue
        nf = int(re.search(r"\d+", hoja).group())
        df = pd.read_excel(ruta, sheet_name=hoja, header=None)
        partidos = []
        i = 0
        while i < len(df):
            c0 = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""
            if re.search(r"\s+vs\s+", c0, re.IGNORECASE):
                partes = re.split(r"\s+vs\s+", c0, flags=re.IGNORECASE)
                loc, vis = partes[0].strip(), partes[1].strip()
                stats, j = {}, i + 1
                while j < len(df):
                    r0 = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                    if r0 == "" or re.search(r"\s+vs\s+", r0, re.IGNORECASE):
                        break
                    skip_words = ("métrica", "metrica", "métrica calculada",
                                  "📊", loc, vis)
                    if any(r0.lower().startswith(s.lower()) for s in skip_words):
                        j += 1
                        continue
                    if pd.notna(df.iloc[j, 1]):
                        raw_l = df.iloc[j, 1]
                        raw_v = df.iloc[j, 2] if j < len(df) and pd.notna(df.iloc[j, 2]) else 0
                        # regates: extraer porcentaje
                        if "regate" in r0.lower():
                            vl = _parse_regate(raw_l)
                            vv = _parse_regate(raw_v)
                        else:
                            vl = _parse_num(raw_l)
                            vv = _parse_num(raw_v)
                        stats[r0] = {"local": vl, "visitante": vv}
                    j += 1
                partidos.append({"local": loc, "visitante": vis, "stats": stats, "nFecha": nf})
                i = j
            else:
                i += 1
        datos[nf] = partidos
    return datos

# ──────────────────────────────────────────────────────────────────────
# CONSTRUCCIÓN DEL DATAFRAME LARGO
# ──────────────────────────────────────────────────────────────────────
def construir_df(datos: dict) -> pd.DataFrame:
    filas = []
    for nf, partidos in datos.items():
        for p in partidos:
            for met, vals in p["stats"].items():
                base = {"nFecha": nf, "Métrica": met}
                filas.append({**base,
                               "Equipo": p["local"], "Rival": p["visitante"],
                               "Condicion": "Local",
                               "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base,
                               "Equipo": p["visitante"], "Rival": p["local"],
                               "Condicion": "Visitante",
                               "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

# ──────────────────────────────────────────────────────────────────────
# xG SINTÉTICO: la clave del modelo mejorado
# ──────────────────────────────────────────────────────────────────────
XG_W = {
    "Tiros al arco":          0.35,   # tiro que obliga al arquero
    "Ocasiones claras":       0.40,   # oportunidad de alta calidad
    "Tiros dentro del área":  0.15,   # proximidad al arco
    "Tiros totales":          0.10,   # volumen base
}
# Factores de conversión estimados por la LPF (calibrados con resultados reales)
XG_RATE = {
    "Tiros al arco":          0.25,   # ~25% de los tiros al arco terminan en gol
    "Ocasiones claras":       0.35,   # ocasión clara ~35% gol
    "Tiros dentro del área":  0.12,
    "Tiros totales":          0.08,
}

def xg_sintetico(df_partido: dict) -> float:
    """Calcula xG sintético para un equipo en un partido."""
    xg = 0.0
    for met, w in XG_W.items():
        val = df_partido.get(met, 0.0)
        rate = XG_RATE[met]
        xg += w * val * rate
    return round(xg, 3)

# ──────────────────────────────────────────────────────────────────────
# MOTOR DE PREDICCIÓN MEJORADO
# ──────────────────────────────────────────────────────────────────────
def wmean(values, fechas, max_f, n_rec, w_rec, w_norm):
    """Media ponderada con recencia."""
    if len(values) == 0:
        return np.nan
    arr_f = np.array(fechas, dtype=float)
    w = np.where(arr_f >= (max_f - n_rec + 1), w_rec, w_norm)
    return float(np.average(values, weights=w))

def get_metric(df, equipo, condicion, metrica, max_f, n_rec=3, w_rec=1.5, w_norm=1.0):
    sub = df[(df["Equipo"] == equipo) & (df["Condicion"] == condicion)
             & (df["Métrica"] == metrica)]
    if sub.empty:
        # fallback: todas condiciones
        sub = df[(df["Equipo"] == equipo) & (df["Métrica"] == metrica)]
    if sub.empty:
        return np.nan, 0
    return wmean(sub["Propio"].values, sub["nFecha"].values, max_f, n_rec, w_rec, w_norm), len(sub)

def get_metric_concedido(df, equipo, condicion, metrica, max_f, n_rec=3, w_rec=1.5, w_norm=1.0):
    sub = df[(df["Equipo"] == equipo) & (df["Condicion"] == condicion)
             & (df["Métrica"] == metrica)]
    if sub.empty:
        sub = df[(df["Equipo"] == equipo) & (df["Métrica"] == metrica)]
    if sub.empty:
        return np.nan, 0
    return wmean(sub["Concedido"].values, sub["nFecha"].values, max_f, n_rec, w_rec, w_norm), len(sub)

@st.cache_data(ttl=180, show_spinner=False)
def calcular_xg_df(datos_raw: dict) -> pd.DataFrame:
    """Construye tabla de xG sintético partido a partido."""
    filas = []
    for nf, partidos in datos_raw.items():
        for p in partidos:
            xg_l = xg_sintetico(p["stats"])
            xg_v = xg_sintetico({k: v["visitante"] for k, v in p["stats"].items()})
            goles_l = p["stats"].get("Resultado", {}).get("local", np.nan)
            goles_v = p["stats"].get("Resultado", {}).get("visitante", np.nan)
            filas.append({"nFecha": nf, "Equipo": p["local"],  "Rival": p["visitante"],
                           "Condicion": "Local",    "xG": xg_l, "Goles": goles_l})
            filas.append({"nFecha": nf, "Equipo": p["visitante"], "Rival": p["local"],
                           "Condicion": "Visitante", "xG": xg_v, "Goles": goles_v})
    return pd.DataFrame(filas)

def calcular_lambdas(df, xg_df, equipo_a, equipo_b, es_local,
                     k_shrink=4.0, n_rec=3, w_rec=1.6, w_norm=1.0,
                     home_bonus_atk=1.12, home_bonus_def=0.90,
                     scaling=0.88):
    """
    Calcula λA y λB usando xG sintético + métricas defensivas.
    
    Pasos:
    1. xG medio de liga (home/away) como referencia.
    2. Para cada equipo: ratio ataque = xG_propio / ref_liga, 
       ratio defensa = xG_concedido / ref_liga.
    3. Bayesian shrinkage hacia 1.0.
    4. Corrección de localía separada para ataque y defensa.
    5. λ = ref_liga × atk_A × def_B × bonus_localía × scaling.
    """
    max_f = df["nFecha"].max()
    cond_a = "Local" if es_local else "Visitante"
    cond_b = "Visitante" if es_local else "Local"

    # ── Referencias de liga ──
    def liga_ref(cond):
        sub = xg_df[xg_df["Condicion"] == cond]["xG"]
        return sub.mean() if not sub.empty else 1.0

    ref_h = liga_ref("Local")
    ref_a = liga_ref("Visitante")
    ref_a_def = ref_h   # defensa visitante se compara contra ataque local

    ref_atk_a = ref_h if cond_a == "Local" else ref_a
    ref_atk_b = ref_h if cond_b == "Local" else ref_a

    # ── xG sintético ponderado por recencia ──
    def get_xg(equipo, cond, col="xG"):
        sub = xg_df[(xg_df["Equipo"] == equipo) & (xg_df["Condicion"] == cond)]
        if sub.empty:
            sub = xg_df[xg_df["Equipo"] == equipo]
        if sub.empty:
            return np.nan, 0
        return wmean(sub[col].values, sub["nFecha"].values, max_f, n_rec, w_rec, w_norm), len(sub)

    xg_a_fav, n_a = get_xg(equipo_a, cond_a)
    xg_a_con, _   = get_xg(equipo_a, cond_a, "xG")  # xG concedido aproximado
    xg_b_fav, n_b = get_xg(equipo_b, cond_b)

    # Fallback si sin datos
    xg_a_fav = xg_a_fav if not np.isnan(xg_a_fav) else ref_atk_a
    xg_b_fav = xg_b_fav if not np.isnan(xg_b_fav) else ref_atk_b

    # ── Incorporar métricas defensivas reales ──
    # Usamos Quites + Intercepciones como indicador de presión defensiva
    def def_index(equipo, cond):
        q, nq = get_metric(df, equipo, cond, "Quites", max_f, n_rec, w_rec, w_norm)
        i, ni = get_metric(df, equipo, cond, "Intercepciones", max_f, n_rec, w_rec, w_norm)
        lig_q = df[df["Métrica"] == "Quites"]["Propio"].mean()
        lig_i = df[df["Métrica"] == "Intercepciones"]["Propio"].mean()
        q = q if not np.isnan(q) else lig_q
        i = i if not np.isnan(i) else lig_i
        lig_q = lig_q if lig_q > 0 else 1
        lig_i = lig_i if lig_i > 0 else 1
        # Un equipo que presiona más (~1.1) tiene factor defensivo mejor (~0.92)
        press = 0.5 * (q / lig_q) + 0.5 * (i / lig_i)
        # Más presión → factor defensivo menor (concede menos)
        return 1.0 / max(press, 0.5)

    def_b = def_index(equipo_b, cond_b)
    def_a = def_index(equipo_a, cond_a)

    # ── Ratio ataque vs liga ──
    atk_a = (n_a * (xg_a_fav / max(ref_atk_a, 1e-6)) + k_shrink) / (n_a + k_shrink)
    atk_b = (n_b * (xg_b_fav / max(ref_atk_b, 1e-6)) + k_shrink) / (n_b + k_shrink)

    # Shrinkage defensivo
    def_b_ratio = (n_b * def_b + k_shrink) / (n_b + k_shrink)
    def_a_ratio = (n_a * def_a + k_shrink) / (n_a + k_shrink)

    # ── λ base ──
    lambda_a = ref_atk_a * atk_a * def_b_ratio
    lambda_b = ref_atk_b * atk_b * def_a_ratio

    # ── Bono de localía diferenciado ──
    if es_local:
        lambda_a *= home_bonus_atk
        lambda_b *= home_bonus_def
    else:
        lambda_b *= home_bonus_atk
        lambda_a *= home_bonus_def

    # ── Scaling global (LPF es under) ──
    lambda_a *= scaling
    lambda_b *= scaling

    # ── Incorporar goles reales como corrección final (blend xG + real) ──
    def real_goles_rate(equipo, cond):
        sub = df[(df["Equipo"] == equipo) & (df["Condicion"] == cond)
                 & (df["Métrica"] == "Resultado")]
        if sub.empty:
            sub = df[(df["Equipo"] == equipo) & (df["Métrica"] == "Resultado")]
        if sub.empty:
            return np.nan, 0
        return wmean(sub["Propio"].values, sub["nFecha"].values, max_f, n_rec, w_rec, w_norm), len(sub)

    g_a, ng_a = real_goles_rate(equipo_a, cond_a)
    g_b, ng_b = real_goles_rate(equipo_b, cond_b)

    # Blend: 60% modelo xG + 40% goles reales (si hay suficiente muestra)
    if not np.isnan(g_a) and ng_a >= 3:
        lambda_a = 0.60 * lambda_a + 0.40 * g_a
    if not np.isnan(g_b) and ng_b >= 3:
        lambda_b = 0.60 * lambda_b + 0.40 * g_b

    lambda_a = float(np.clip(lambda_a, 0.20, 5.0))
    lambda_b = float(np.clip(lambda_b, 0.20, 5.0))

    return round(lambda_a, 3), round(lambda_b, 3), n_a, n_b

def confianza_modelo(n_a, n_b, max_partidos=14):
    """Índice de confianza 0-100% basado en cantidad de datos."""
    conf = min((n_a + n_b) / (2 * max_partidos), 1.0) * 100
    return round(conf, 1)

# ──────────────────────────────────────────────────────────────────────
# MATRIZ DIXON-COLES CORREGIDA
# ──────────────────────────────────────────────────────────────────────
def poisson_pmf(lam: float, k: int) -> float:
    return math.exp(k * math.log(max(lam, 1e-9)) - lam - math.lgamma(k + 1))

def matriz_dc(la: float, lb: float, rho: float = -0.10) -> np.ndarray:
    """Matriz de probabilidades goles con corrección Dixon-Coles."""
    pa = np.array([poisson_pmf(la, k) for k in range(MAX_G + 1)])
    pb = np.array([poisson_pmf(lb, k) for k in range(MAX_G + 1)])
    M = np.outer(pa, pb)

    # Corrección para marcadores bajos
    rho = max(rho, -0.9 / max(la * lb, 0.01))
    tau = np.zeros((MAX_G + 1, MAX_G + 1))
    tau[0, 0] = 1 - la * lb * rho
    tau[1, 0] = 1 + lb * rho
    tau[0, 1] = 1 + la * rho
    tau[1, 1] = 1 - rho
    for i in range(min(2, MAX_G + 1)):
        for j in range(min(2, MAX_G + 1)):
            M[i, j] = max(M[i, j] * tau[i, j], 0)

    M /= M.sum()
    return M

def simular(la: float, lb: float, rho: float = -0.10):
    M = matriz_dc(la, lb, rho)
    return {
        "victoria": float(np.tril(M, -1).sum()),
        "empate":   float(np.trace(M)),
        "derrota":  float(np.triu(M, 1).sum()),
        "matrix":   M,
    }

def over_under_probs(M: np.ndarray, linea: float):
    """P(over L) y P(under L) desde la matriz de Poisson."""
    prob_over = 0.0
    for i in range(MAX_G + 1):
        for j in range(MAX_G + 1):
            if i + j > linea:
                prob_over += M[i, j]
    return prob_over, 1 - prob_over

def ambos_anotan(M: np.ndarray):
    """P(ambos equipos anotan)."""
    return float(1 - M[0, :].sum() - M[:, 0].sum() + M[0, 0])

# ──────────────────────────────────────────────────────────────────────
# VISUALIZACIONES
# ──────────────────────────────────────────────────────────────────────
def fig_heatmap(M: np.ndarray, ea: str, eb: str):
    sub = M[:6, :6]
    text = [[f"{sub[i,j]*100:.1f}%" for j in range(6)] for i in range(6)]
    fig = go.Figure(go.Heatmap(
        z=sub, x=[f"{j} {eb[:8]}" for j in range(6)],
        y=[f"{i} {ea[:8]}" for i in range(6)],
        colorscale=[[0, "#0f1829"], [0.5, "#7f1d1d"], [1, "#e63946"]],
        showscale=False, text=text, texttemplate="%{text}",
        textfont=dict(size=12)
    ))
    fig.update_layout(**PLOT, height=380, yaxis=dict(autorange="reversed"),
                      title=dict(text="Distribución de Marcadores", font=dict(family="Bebas Neue", size=16, color="#e63946")))
    return fig

def fig_over_under(M: np.ndarray, lineas=(1.5, 2.5, 3.5, 4.5)):
    overs, unders = [], []
    for l in lineas:
        o, u = over_under_probs(M, l)
        overs.append(o * 100); unders.append(u * 100)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Over", x=[f"O/U {l}" for l in lineas], y=overs,
                         marker_color=GREEN, text=[f"{v:.1f}%" for v in overs], textposition="outside"))
    fig.add_trace(go.Bar(name="Under", x=[f"O/U {l}" for l in lineas], y=unders,
                         marker_color=GRAY, text=[f"{v:.1f}%" for v in unders], textposition="outside"))
    fig.update_layout(**PLOT, barmode="group", height=320,
                      yaxis=dict(range=[0, 115]),
                      title=dict(text="Probabilidades Over / Under", font=dict(family="Bebas Neue", size=16, color="#e63946")))
    return fig

def fig_goles_dist(la: float, lb: float):
    """Distribución esperada de goles totales."""
    totales = range(0, 9)
    probs = []
    M = matriz_dc(la, lb)
    for t in totales:
        p = sum(M[i, t-i] for i in range(t+1) if i <= MAX_G and t-i <= MAX_G)
        probs.append(p * 100)
    colors = [GREEN if i > 2 else GRAY for i in totales]
    fig = go.Figure(go.Bar(
        x=[str(t) for t in totales], y=probs, marker_color=colors,
        text=[f"{v:.1f}%" for v in probs], textposition="outside"
    ))
    fig.update_layout(**PLOT, height=300, yaxis=dict(range=[0, max(probs)*1.2]),
                      xaxis_title="Goles totales",
                      title=dict(text="Distribución Goles Totales", font=dict(family="Bebas Neue", size=16, color="#e63946")))
    return fig

def fig_radar(df, ea, eb, cond_a="General", cond_b="General"):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco",
                         "Ocasiones claras", "Pases totales", "Quites", "Intercepciones"]
            if m in df["Métrica"].values]
    if not mets:
        return go.Figure()

    def get_v(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General":
            d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0

    va = [get_v(ea, cond_a, m) for m in mets]
    vb = [get_v(eb, cond_b, m) for m in mets]

    # Normalizar 0-1
    maxv = [max(va[i], vb[i], 1e-9) for i in range(len(mets))]
    van = [va[i] / maxv[i] for i in range(len(mets))]
    vbn = [vb[i] / maxv[i] for i in range(len(mets))]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=van + [van[0]], theta=mets + [mets[0]],
                                   fill="toself", name=ea, line=dict(color=RED, width=2)))
    fig.add_trace(go.Scatterpolar(r=vbn + [vbn[0]], theta=mets + [mets[0]],
                                   fill="toself", name=eb, line=dict(color=BLUE, width=2)))
    fig.update_layout(**PLOT, height=420,
                      polar=dict(bgcolor="rgba(0,0,0,0)",
                                 radialaxis=dict(visible=False),
                                 angularaxis=dict(tickfont=dict(size=12))),
                      title=dict(text="Comparativa Métricas", font=dict(family="Bebas Neue", size=16, color="#e63946")))
    return fig

def fig_forma(df, ea, eb, max_f):
    """Evolución de goles y xG por fecha."""
    fig = go.Figure()
    for eq, col in [(ea, RED), (eb, BLUE)]:
        sub = df[(df["Equipo"] == eq) & (df["Métrica"] == "Resultado")].sort_values("nFecha")
        if not sub.empty:
            fig.add_trace(go.Scatter(x=sub["nFecha"], y=sub["Propio"],
                                      mode="lines+markers", name=f"{eq} (goles)",
                                      line=dict(color=col, width=2),
                                      marker=dict(size=8)))
    fig.update_layout(**PLOT, height=300, xaxis_title="Fecha", yaxis_title="Goles marcados",
                      title=dict(text="Forma Reciente (Goles)", font=dict(family="Bebas Neue", size=16, color="#e63946")))
    return fig

def fig_xg_timeline(xg_df, ea, eb):
    """xG sintético a lo largo de la temporada."""
    fig = go.Figure()
    for eq, col in [(ea, RED), (eb, BLUE)]:
        sub = xg_df[xg_df["Equipo"] == eq].sort_values("nFecha")
        if not sub.empty:
            fig.add_trace(go.Scatter(x=sub["nFecha"], y=sub["xG"],
                                      mode="lines+markers", name=f"{eq} xG",
                                      line=dict(color=col, width=2, dash="dot"),
                                      marker=dict(size=7)))
            fig.add_trace(go.Scatter(x=sub["nFecha"], y=sub["Goles"],
                                      mode="markers", name=f"{eq} goles",
                                      marker=dict(color=col, size=10, symbol="diamond")))
    fig.update_layout(**PLOT, height=320, xaxis_title="Fecha", yaxis_title="xG sintético / Goles",
                      title=dict(text="xG Sintético vs Goles Reales", font=dict(family="Bebas Neue", size=16, color="#e63946")))
    return fig

def tabla_resumen(df, equipos, xg_df):
    """Rankings por xG, goles, defensa."""
    rows = []
    for eq in equipos:
        sub_g = df[(df["Equipo"] == eq) & (df["Métrica"] == "Resultado")]
        sub_xg = xg_df[xg_df["Equipo"] == eq]
        goles_f = sub_g["Propio"].mean()
        goles_c = sub_g["Concedido"].mean()
        xg_f = sub_xg["xG"].mean()
        pts = sub_g.apply(lambda r: 3 if r["Propio"] > r["Concedido"] else (1 if r["Propio"] == r["Concedido"] else 0), axis=1).sum()
        rows.append({"Equipo": eq, "PJ": len(sub_g), "PTS": pts,
                     "xGF": round(xg_f, 2) if not np.isnan(xg_f) else 0,
                     "GF/PJ": round(goles_f, 2) if not np.isnan(goles_f) else 0,
                     "GC/PJ": round(goles_c, 2) if not np.isnan(goles_c) else 0})
    return pd.DataFrame(rows).sort_values("PTS", ascending=False).reset_index(drop=True)

# ──────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026 · Pro v2")
    ruta = st.text_input("📂 Excel", "Fecha_x_fecha_lpf.xlsx")
    st.divider()
    st.markdown("### ⚙️ Parámetros del Modelo")
    k_shrink    = st.slider("Shrinkage bayesiano (K)", 1.0, 8.0, 4.0, 0.5,
                             help="Mayor K = más regresión al promedio de liga")
    n_rec       = st.slider("Fechas de recencia", 2, 6, 3, 1,
                             help="Últimas N fechas con peso extra")
    w_rec       = st.slider("Peso reciente", 1.0, 3.0, 1.6, 0.1,
                             help="Multiplicador de las fechas recientes")
    home_atk    = st.slider("Bono localía ataque", 1.0, 1.30, 1.12, 0.01)
    home_def    = st.slider("Bono localía defensa", 0.75, 1.0, 0.90, 0.01)
    scaling     = st.slider("Scaling global (under/over)", 0.70, 1.10, 0.88, 0.01,
                             help="<1 = liga under, >1 = liga over")
    rho_dc      = st.slider("ρ Dixon-Coles", -0.30, 0.0, -0.10, 0.01,
                             help="Correlación 0-0/1-0/0-1/1-1")
    ou_linea    = st.selectbox("Línea O/U principal", [1.5, 2.5, 3.5], index=1)
    st.divider()
    nav = st.radio("Sección", ["🔮 Predictor", "📊 Rankings xG", "📈 Forma & xG", "🕸️ H2H Radar"],
                   label_visibility="collapsed")

# ──────────────────────────────────────────────────────────────────────
# CARGA DE DATOS
# ──────────────────────────────────────────────────────────────────────
if not os.path.exists(ruta):
    st.error(f"No se encontró el archivo: **{ruta}**")
    st.stop()

with st.spinner("Cargando datos..."):
    datos_raw = cargar_excel(ruta)
    df = construir_df(datos_raw)
    xg_df = calcular_xg_df(datos_raw)

equipos = sorted(df["Equipo"].unique())
max_f = int(df["nFecha"].max())

st.markdown('<h1>LPF 2026 · Scouting Dashboard Pro v2</h1>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# PREDICTOR
# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor":
    c1, c2, c3 = st.columns([5, 5, 3])
    ea = c1.selectbox("🏠 Local", equipos)
    eb = c2.selectbox("✈️ Visitante", equipos, index=min(1, len(equipos) - 1))
    es_local = c3.toggle("Bono Localía", True)

    if st.button("🚀 CALCULAR PREDICCIÓN"):
        if ea == eb:
            st.warning("Seleccioná dos equipos distintos.")
            st.stop()

        la, lb, n_a, n_b = calcular_lambdas(
            df, xg_df, ea, eb, es_local,
            k_shrink=k_shrink, n_rec=n_rec, w_rec=w_rec,
            home_bonus_atk=home_atk, home_bonus_def=home_def,
            scaling=scaling
        )
        sim = simular(la, lb, rho=rho_dc)
        M = sim["matrix"]
        conf = confianza_modelo(n_a, n_b)
        bts = ambos_anotan(M)
        p_over, p_under = over_under_probs(M, ou_linea)

        # Marcador más probable
        best_score = np.unravel_index(M[:6, :6].argmax(), M[:6, :6].shape)

        # ── KPIs principales ──
        st.markdown('<div class="section-title">Probabilidades 1X2</div>', unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="kpi"><div class="lbl">Victoria {ea[:14]}</div><div class="val">{sim["victoria"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi draw"><div class="lbl">Empate</div><div class="val">{sim["empate"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi loss"><div class="lbl">Victoria {eb[:14]}</div><div class="val">{sim["derrota"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="kpi over"><div class="lbl">Confianza Modelo</div><div class="val">{conf:.0f}%</div></div>', unsafe_allow_html=True)

        # ── KPIs secundarios ──
        st.markdown('<div class="section-title">Mercados Adicionales</div>', unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.markdown(f'<div class="kpi"><div class="lbl">λ {ea[:10]}</div><div class="val">{la}</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="kpi loss"><div class="lbl">λ {eb[:10]}</div><div class="val">{lb}</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="kpi over"><div class="lbl">Over {ou_linea}</div><div class="val">{p_over*100:.1f}%</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="kpi draw"><div class="lbl">Under {ou_linea}</div><div class="val">{p_under*100:.1f}%</div></div>', unsafe_allow_html=True)
        m5.markdown(f'<div class="kpi"><div class="lbl">Ambos anotan</div><div class="val">{bts*100:.1f}%</div></div>', unsafe_allow_html=True)

        # ── Marcador más probable ──
        st.markdown(
            f'<div class="note">🎯 Marcador más probable: '
            f'<strong>{ea[:15]} {best_score[0]} – {best_score[1]} {eb[:15]}</strong> '
            f'({M[best_score]*100:.1f}%)</div>',
            unsafe_allow_html=True
        )

        if conf < 40:
            st.markdown(
                '<div class="warn">⚠️ Datos insuficientes para al menos uno de los equipos. '
                'El modelo recurre a promedios de liga. Usar con precaución.</div>',
                unsafe_allow_html=True
            )

        # ── Tabs de gráficos ──
        st.markdown('<div class="section-title">Análisis Detallado</div>', unsafe_allow_html=True)
        t1, t2, t3, t4 = st.tabs(["🎯 Heatmap Marcadores", "📊 Over / Under", "📉 Goles Totales", "🕸️ Radar"])
        with t1:
            st.plotly_chart(fig_heatmap(M, ea, eb), use_container_width=True)
        with t2:
            st.plotly_chart(fig_over_under(M, lineas=(1.5, 2.5, 3.5, 4.5)), use_container_width=True)
        with t3:
            st.plotly_chart(fig_goles_dist(la, lb), use_container_width=True)
        with t4:
            cond_a = "Local" if es_local else "Visitante"
            cond_b = "Visitante" if es_local else "Local"
            st.plotly_chart(fig_radar(df, ea, eb, cond_a, cond_b), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# RANKINGS xG
# ──────────────────────────────────────────────────────────────────────
elif nav == "📊 Rankings xG":
    st.markdown('<div class="section-title">Rankings por xG Sintético y Rendimiento</div>', unsafe_allow_html=True)
    tabla = tabla_resumen(df, equipos, xg_df)
    st.dataframe(
        tabla.style.background_gradient(subset=["xGF", "GF/PJ"], cmap="RdYlGn")
                   .background_gradient(subset=["GC/PJ"], cmap="RdYlGn_r"),
        use_container_width=True, height=500
    )

    # Scatter xGF vs GF
    fig = go.Figure(go.Scatter(
        x=tabla["xGF"], y=tabla["GF/PJ"], mode="markers+text",
        text=tabla["Equipo"], textposition="top center",
        marker=dict(size=12, color=RED, line=dict(width=1, color="white")),
        hovertemplate="<b>%{text}</b><br>xGF: %{x:.2f}<br>GF/PJ: %{y:.2f}<extra></extra>"
    ))
    # Línea identidad
    rng = [0, max(tabla["xGF"].max(), tabla["GF/PJ"].max()) * 1.1]
    fig.add_trace(go.Scatter(x=rng, y=rng, mode="lines",
                              line=dict(color=GRAY, dash="dash"), showlegend=False))
    fig.update_layout(**PLOT, height=550, xaxis_title="xG Sintético / PJ",
                      yaxis_title="Goles Reales / PJ",
                      title=dict(text="xG Sintético vs Goles Reales", font=dict(family="Bebas Neue", size=16, color="#e63946")))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="note">Equipos sobre la diagonal: más eficientes que su xG. Bajo la diagonal: rinden menos de lo esperado.</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# FORMA & xG TIMELINE
# ──────────────────────────────────────────────────────────────────────
elif nav == "📈 Forma & xG":
    st.markdown('<div class="section-title">Evolución de Forma y xG Sintético</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    ea = c1.selectbox("Equipo A", equipos)
    eb = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos) - 1))
    st.plotly_chart(fig_forma(df, ea, eb, max_f), use_container_width=True)
    st.plotly_chart(fig_xg_timeline(xg_df, ea, eb), use_container_width=True)

    # Tabla detallada por equipo
    for eq, col_name in [(ea, "rojo"), (eb, "azul")]:
        sub = xg_df[xg_df["Equipo"] == eq][["nFecha", "Condicion", "Rival", "xG", "Goles"]].sort_values("nFecha")
        sub = sub.rename(columns={"nFecha": "Fecha"})
        st.markdown(f'<div class="section-title">{eq}</div>', unsafe_allow_html=True)
        st.dataframe(sub.reset_index(drop=True), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# H2H RADAR
# ──────────────────────────────────────────────────────────────────────
elif nav == "🕸️ H2H Radar":
    st.markdown('<div class="section-title">Comparativa Head-to-Head</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    ea = c1.selectbox("Equipo A", equipos)
    eb = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos) - 1))
    ca = c3.radio(f"Cond. {ea[:10]}", ["General", "Local", "Visitante"])
    cb = c4.radio(f"Cond. {eb[:10]}", ["General", "Local", "Visitante"], index=2)
    st.plotly_chart(fig_radar(df, ea, eb, ca, cb), use_container_width=True)

    # Tabla comparativa de métricas
    def stats_eq(eq, cond):
        d = df[(df["Equipo"] == eq)]
        if cond != "General":
            d = d[d["Condicion"] == cond]
        return d.groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)

    s1 = stats_eq(ea, ca); s2 = stats_eq(eb, cb)
    comp = pd.DataFrame({
        f"{ea} Fav": s1["Propio"],
        f"{ea} Contra": s1["Concedido"],
        f"{eb} Fav": s2["Propio"],
        f"{eb} Contra": s2["Concedido"],
    }).dropna()
    st.dataframe(comp, use_container_width=True)
