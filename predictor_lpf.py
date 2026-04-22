"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v8 · Dixon-Coles + Shrinkage)
─────────────────────────────────────────────────────────────────────────────
Cambios clave vs V7 (para alinear con casas de apuestas):

1. Motor Dixon-Coles "estilo bookie":
     λ_home = μ_home · α_home(cond=Local) · β_away(cond=Visitante)
     λ_away = μ_away · α_away(cond=Visitante) · β_home(cond=Local)
   donde α (ataque) y β (defensa) tienen media 1 en la liga.

2. Ventaja de localía GLOBAL (μ_home / μ_away), no por equipo.
   Evita ruido de splits con pocas fechas.

3. Se eliminó el soft-clip + el calibrador anti-empate.
   En su lugar, shrinkage Bayesiano hacia la media de liga con K=3
   pseudo-partidos. Preserva la separación entre fuertes y débiles
   (el problema que generaba predicciones 40/30/30 cuando la casa da
   60/20/20 era la doble compresión soft_clip + xG-blend).

4. Corrección Dixon-Coles (τ) en la matriz de marcadores para
   capturar la frecuencia real de 0-0, 1-1, 1-0, 0-1 en LPF.

5. xG con recencia ponderada como señal principal (W_XG=0.60).
   Se usa como proxy de "fuerza real", blended con goles reales.

6. Matriz de marcadores ANALÍTICA (sin Monte Carlo): más precisa y
   reproducible. Se mantiene la firma `montecarlo(lam_a, lam_b)`.
"""
import re, os, math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y CONSTANTES
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Scouting", page_icon="⚽",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@500;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #080d18; color: #dde3ee; }
section[data-testid="stSidebar"] { background: #0c1220 !important; border-right: 1px solid #1c2a40; }
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: #8899aa !important; font-size:13px !important; }
h1 { font-family:'Bebas Neue',cursive !important; font-size:2.6rem !important; color:#e63946 !important; letter-spacing:3px; margin-bottom:0; }
h2 { font-family:'Bebas Neue',cursive !important; font-size:1.6rem !important; color:#dde3ee !important; letter-spacing:2px; }
h3 { font-family:'Rajdhani',sans-serif !important; font-size:1.1rem !important; color:#8899aa !important; font-weight:700; }
.section-title { font-family:'Bebas Neue',cursive; font-size:1.3rem; letter-spacing:3px; color:#e63946; border-bottom:1px solid #1c2a40; padding-bottom:8px; margin:28px 0 18px; text-transform:uppercase; }
.kpi { background:linear-gradient(135deg,#0f1829,#162035); border:1px solid #1c2a40; border-left:4px solid #e63946; border-radius:10px; padding:16px 18px; text-align:center; }
.kpi.draw { border-left-color:#64748b; } .kpi.loss { border-left-color:#3b82f6; } .kpi.info { border-left-color:#22c55e; }
.kpi .lbl { font-family:'Rajdhani'; font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:#64748b; }
.kpi .val { font-family:'Bebas Neue'; font-size:38px; color:#e63946; line-height:1.05; }
.kpi.draw .val { color:#94a3b8; } .kpi.loss .val { color:#60a5fa; } .kpi.info .val { color:#4ade80; }
.badge { display:inline-block; padding:3px 14px; border-radius:20px; font-family:'Rajdhani'; font-size:12px; font-weight:700; background:#0d2b1a; color:#4ade80; margin-bottom:14px; }
.stTabs [data-baseweb="tab-list"] { background:#0f1829; border-radius:10px; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"] { font-family:'Rajdhani'; font-weight:700; font-size:14px; color:#64748b !important; border-radius:7px; padding:6px 16px; }
.stTabs [aria-selected="true"] { background:#e63946 !important; color:#fff !important; }
.stButton>button { font-family:'Bebas Neue'; font-size:17px; letter-spacing:2px; background:linear-gradient(135deg,#e63946,#b91c2c); color:#fff; border:none; border-radius:9px; padding:13px; width:100%; transition:all .2s; }
.stButton>button:hover { transform:translateY(-1px); box-shadow:0 6px 20px rgba(230,57,70,.45); }
.stSelectbox>div>div, .stMultiSelect>div>div, .stTextInput>div>div { background:#0f1829 !important; border:1px solid #1c2a40 !important; color:#dde3ee !important; border-radius:8px !important; }
.stDataFrame { border-radius:10px !important; }
.note { background:#0f1829; border:1px solid #1c2a40; border-radius:8px; padding:10px 14px; font-size:12px; color:#64748b; margin-top:8px; }
.odds-box { background:#0f1829; border:1px solid #1c2a40; border-radius:10px; padding:12px 16px; font-family:'Rajdhani'; }
.odds-box b { color:#e63946; }
</style>
""", unsafe_allow_html=True)

RED, BLUE, GRAY, AMBER = "#e63946", "#3b82f6", "#64748b", "#f59e0b"
PLOT = dict(font=dict(family="Rajdhani", size=13, color="#dde3ee"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=20, t=36, b=10))
GRID = dict(showgrid=True, gridcolor="#1c2a40", zeroline=False)
NO_GRID = dict(showgrid=False, zeroline=False)

METRICAS_MENOS_ES_MEJOR = {"Faltas", "Tarjetas amarillas", "Tarjetas rojas", "Fueras de juego"}

# ── Motor predictor V8 ────────────────────────────────────────────────
W_XG                  = 0.60   # peso xG vs goles reales en la fuerza
K_SHRINK              = 3.0    # pseudo-partidos hacia la media (menor = más spread)
DC_RHO                = -0.10  # Dixon-Coles: favorece 0-0 y 1-1 (empates chicos)
MAX_GOALS_MATRIX      = 7

PESO_ESPECIFICO_MIN_N = 3      # n mínimo para dar 70% al split Local/Vis
PESO_ESP_ALTO         = 0.70
PESO_ESP_BAJO         = 0.40

N_RECENCIA            = 3      # últimas N fechas con más peso
PESO_RECIENTE         = 2.5
PESO_NORMAL           = 1.0

MAX_ROTATION_PENALTY  = 0.12

LAM_MIN, LAM_MAX      = 0.25, 4.50

BOOK_OVERROUND        = 1.06   # 6% de margen típico de casas (para display)

# ──────────────────────────────────────────────────────────────────────
# PARSEO DEL EXCEL
# ──────────────────────────────────────────────────────────────────────
def num(v) -> float:
    if isinstance(v, str):
        v = v.replace('%', '').replace(',', '.').strip()
    try:
        return float(v)
    except Exception:
        return 0.0

@st.cache_data(ttl=120, show_spinner=False)
def cargar_excel(ruta: str):
    try:
        xl = pd.ExcelFile(ruta, engine="openpyxl")
    except Exception:
        return {}
    resultado = {}
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE):
            continue
        df = pd.read_excel(ruta, sheet_name=hoja, header=None, engine="openpyxl")
        partidos, i = [], 0
        while i < len(df):
            c0 = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""
            if re.search(r"\s+vs\s+", c0, re.IGNORECASE):
                partes = re.split(r"\s+vs\s+", c0, flags=re.IGNORECASE)
                if len(partes) == 2:
                    loc, vis, stats, j = partes[0].strip(), partes[1].strip(), {}, i + 1
                    while j < len(df):
                        r0 = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                        r1 = df.iloc[j, 1] if df.shape[1] > 1 else None
                        r2 = df.iloc[j, 2] if df.shape[1] > 2 else None
                        if r0 == "" and (pd.isna(r1) if r1 is not None else True):
                            break
                        if re.search(r"\s+vs\s+", r0, re.IGNORECASE):
                            break
                        if r0.lower() in ("métrica", "metrica") or r0 == loc:
                            j += 1; continue
                        if pd.notna(r1):
                            stats[r0] = {"local": num(r1), "visitante": num(r2) if pd.notna(r2) else 0}
                        j += 1
                    if stats:
                        partidos.append({"local": loc, "visitante": vis, "metricas": stats})
                    i = j
                else:
                    i += 1
            else:
                i += 1
        if partidos:
            resultado[hoja] = partidos
    return resultado

def construir_df(datos: dict) -> pd.DataFrame:
    filas = []
    for fecha, partidos in datos.items():
        nf = int(re.search(r"\d+", fecha).group())
        for p in partidos:
            loc, vis = p["local"], p["visitante"]
            for met, vals in p["metricas"].items():
                base = {"Fecha": fecha, "nFecha": nf, "Métrica": met}
                filas.append({**base, "Equipo": loc, "Rival": vis, "Condicion": "Local",
                              "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": vis, "Rival": loc, "Condicion": "Visitante",
                              "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

def ranking(df: pd.DataFrame, metrica: str, columna="Propio", ascendente=False) -> pd.DataFrame:
    return (df[df["Métrica"] == metrica]
            .groupby("Equipo")[columna]
            .agg(Promedio="mean", Total="sum", Partidos="count")
            .reset_index().round(2)
            .sort_values("Promedio", ascending=ascendente))

# ──────────────────────────────────────────────────────────────────────
# MOTOR PREDICTOR V8 — Dixon-Coles + Shrinkage + xG-recencia
# ──────────────────────────────────────────────────────────────────────
def _weighted_mean(values: np.ndarray, fechas: np.ndarray) -> float:
    """Media ponderada con más peso a las N_RECENCIA últimas fechas."""
    if len(values) == 0:
        return float("nan")
    max_f = fechas.max()
    w = np.where(fechas >= (max_f - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(values, weights=w))

def _effective_rate(sub: pd.DataFrame, col: str) -> tuple[float, int]:
    """Tasa efectiva (xG + goles reales, blended) ponderada por recencia.
    Devuelve (rate, n_partidos_resultado)."""
    dr = sub[sub["Métrica"] == "Resultado"]
    dx = sub[sub["Métrica"] == "Goles esperados (xG)"]
    g = _weighted_mean(dr[col].values, dr["nFecha"].values) if not dr.empty else float("nan")
    x = _weighted_mean(dx[col].values, dx["nFecha"].values) if not dx.empty else float("nan")
    n = len(dr)
    if np.isnan(g) and np.isnan(x):
        return float("nan"), 0
    if np.isnan(x):
        return g, n
    if np.isnan(g):
        return x, n
    return W_XG * x + (1 - W_XG) * g, n

@st.cache_data(ttl=120, show_spinner=False)
def _league_stats(df: pd.DataFrame) -> dict:
    """Promedios globales de liga (referencia μ_home / μ_away)."""
    dr = df[df["Métrica"] == "Resultado"]
    dx = df[df["Métrica"] == "Goles esperados (xG)"]
    mu_home_g = dr[dr["Condicion"] == "Local"]["Propio"].mean()
    mu_away_g = dr[dr["Condicion"] == "Visitante"]["Propio"].mean()
    mu_home_g = 1.30 if np.isnan(mu_home_g) else float(mu_home_g)
    mu_away_g = 1.00 if np.isnan(mu_away_g) else float(mu_away_g)

    if not dx.empty:
        mh_x = dx[dx["Condicion"] == "Local"]["Propio"].mean()
        ma_x = dx[dx["Condicion"] == "Visitante"]["Propio"].mean()
        mh_x = mu_home_g if np.isnan(mh_x) else float(mh_x)
        ma_x = mu_away_g if np.isnan(ma_x) else float(ma_x)
        ref_home = W_XG * mh_x + (1 - W_XG) * mu_home_g
        ref_away = W_XG * ma_x + (1 - W_XG) * mu_away_g
    else:
        ref_home = mu_home_g
        ref_away = mu_away_g

    return {
        "mu_home_g": mu_home_g, "mu_away_g": mu_away_g,
        "ref_home": ref_home,   # goles "efectivos" (xG blend) que anotan los locales
        "ref_away": ref_away,   # goles "efectivos" que anotan los visitantes
        "ref_all":  (ref_home + ref_away) / 2.0,
        "has_xg":   not dx.empty,
    }

def _strength(df: pd.DataFrame, eq: str, cond: str, league: dict) -> tuple[float, float, int]:
    """Fuerza de ataque α y defensa β de `eq` jugando en `cond` ("Local" / "Visitante").
    Normalizadas a media 1 en la liga.
    Blended (split específico + general) + shrinkage Bayesiano hacia 1.0 con K_SHRINK."""
    d_eq   = df[df["Equipo"] == eq]
    d_spec = d_eq[d_eq["Condicion"] == cond]
    d_gen  = d_eq

    gf_spec, n_spec = _effective_rate(d_spec, "Propio")
    gc_spec, _      = _effective_rate(d_spec, "Concedido")
    gf_gen,  n_gen  = _effective_rate(d_gen,  "Propio")
    gc_gen,  _      = _effective_rate(d_gen,  "Concedido")

    # Referencias de liga según condición
    if cond == "Local":
        ref_for, ref_against = league["ref_home"], league["ref_away"]
    else:
        ref_for, ref_against = league["ref_away"], league["ref_home"]
    ref_all = league["ref_all"]

    def _ratio(x, ref):
        return (x / ref) if (not np.isnan(x) and ref > 0.01) else float("nan")

    atk_spec = _ratio(gf_spec, ref_for)
    atk_gen  = _ratio(gf_gen,  ref_all)
    def_spec = _ratio(gc_spec, ref_against)
    def_gen  = _ratio(gc_gen,  ref_all)

    # Peso específico vs general según tamaño muestral del split
    w_s, w_g = (PESO_ESP_ALTO, 1 - PESO_ESP_ALTO) if n_spec >= PESO_ESPECIFICO_MIN_N \
               else (PESO_ESP_BAJO, 1 - PESO_ESP_BAJO)

    def _blend(s, g):
        if np.isnan(s) and np.isnan(g): return 1.0
        if np.isnan(s): return g
        if np.isnan(g): return s
        return w_s * s + w_g * g

    atk = _blend(atk_spec, atk_gen)
    deff = _blend(def_spec, def_gen)

    # Shrinkage Bayesiano hacia la media de liga (1.0)
    n_eff = max(n_spec, 0)
    atk  = (n_eff * atk  + K_SHRINK * 1.0) / (n_eff + K_SHRINK)
    deff = (n_eff * deff + K_SHRINK * 1.0) / (n_eff + K_SHRINK)

    return float(atk), float(deff), int(n_spec)

def calcular_lambdas(df: pd.DataFrame, eq_a: str, eq_b: str,
                     a_es_local: bool, rot_a: float = 0.0, rot_b: float = 0.0):
    """Devuelve (λ_a, λ_b, debug) con modelo Dixon-Coles multiplicativo."""
    league = _league_stats(df)
    cond_a = "Local"     if a_es_local else "Visitante"
    cond_b = "Visitante" if a_es_local else "Local"

    atk_a, def_a, n_a = _strength(df, eq_a, cond_a, league)
    atk_b, def_b, n_b = _strength(df, eq_b, cond_b, league)

    base_a = league["ref_home"] if cond_a == "Local" else league["ref_away"]
    base_b = league["ref_home"] if cond_b == "Local" else league["ref_away"]

    lam_a = base_a * atk_a * def_b
    lam_b = base_b * atk_b * def_a

    # Penalización por rotación / copa (simétrica, sin soft-clip)
    if rot_a > 0:
        lam_a *= (1 - rot_a * MAX_ROTATION_PENALTY)
        lam_b *= (1 + rot_a * MAX_ROTATION_PENALTY * 0.4)
    if rot_b > 0:
        lam_b *= (1 - rot_b * MAX_ROTATION_PENALTY)
        lam_a *= (1 + rot_b * MAX_ROTATION_PENALTY * 0.4)

    lam_a = round(float(np.clip(lam_a, LAM_MIN, LAM_MAX)), 3)
    lam_b = round(float(np.clip(lam_b, LAM_MIN, LAM_MAX)), 3)

    return lam_a, lam_b

# ── Matriz de marcadores analítica (Poisson + corrección Dixon-Coles) ─
def _poisson_pmf(lam: float, kmax: int) -> np.ndarray:
    lam = max(lam, 1e-9)
    k = np.arange(kmax + 1)
    log_factorial = np.concatenate([[0.0], np.cumsum(np.log(np.arange(1, kmax + 1)))])
    logp = k * np.log(lam) - lam - log_factorial
    return np.exp(logp)

def _dc_tau_correction(M: np.ndarray, lam_a: float, lam_b: float, rho: float) -> np.ndarray:
    """Aplica la τ de Dixon-Coles a los cuadrantes (0,0), (0,1), (1,0), (1,1)."""
    # Evitar τ negativo si los λ son grandes
    rho_safe = max(rho, -0.9 / max(lam_a * lam_b, 0.01))
    M[0, 0] *= max(1.0 - lam_a * lam_b * rho_safe, 1e-9)
    M[0, 1] *= max(1.0 + lam_a * rho_safe, 1e-9)
    M[1, 0] *= max(1.0 + lam_b * rho_safe, 1e-9)
    M[1, 1] *= max(1.0 - rho_safe, 1e-9)
    return M

def montecarlo(lam_a: float, lam_b: float) -> dict:
    """Nombre heredado. Internamente es cálculo ANALÍTICO (más preciso)."""
    kmax = MAX_GOALS_MATRIX
    pa = _poisson_pmf(lam_a, kmax)
    pb = _poisson_pmf(lam_b, kmax)
    M = np.outer(pa, pb)
    M = _dc_tau_correction(M, lam_a, lam_b, DC_RHO)
    M = np.clip(M, 0.0, None)
    total = M.sum()
    if total > 0:
        M = M / total

    # 1X2: M[i,j] = P(A=i, B=j)  →  A gana si i>j, empate si i==j
    win_a = float(np.tril(M, -1).sum())
    draw  = float(np.trace(M))
    win_b = float(np.triu(M,  1).sum())

    scores = [{"A": r, "B": v, "prob": float(M[r, v])}
              for r in range(kmax + 1) for v in range(kmax + 1)]
    return {
        "victoria": win_a, "empate": draw, "derrota": win_b,
        "df": pd.DataFrame(scores),
        "lam_a": lam_a, "lam_b": lam_b,
    }

def odds_europeas(prob: float, overround: float = BOOK_OVERROUND) -> float:
    """Cuota europea implícita con margen de casa (para comparar directo)."""
    if prob <= 0: return 99.0
    return round(overround / prob, 2)

# ──────────────────────────────────────────────────────────────────────
# COMPONENTES VISUALES
# ──────────────────────────────────────────────────────────────────────
def fig_probs(sim, na, nb):
    fig = go.Figure(go.Bar(
        x=[sim["victoria"]*100, sim["empate"]*100, sim["derrota"]*100],
        y=[f"Victoria {na}", "Empate", f"Victoria {nb}"],
        orientation="h", marker_color=[RED, GRAY, BLUE],
        text=[f"{sim['victoria']*100:.1f}%", f"{sim['empate']*100:.1f}%",
              f"{sim['derrota']*100:.1f}%"],
        textposition="outside"))
    fig.update_layout(**PLOT, height=200,
                      xaxis=dict(**GRID, range=[0, 105], ticksuffix="%"),
                      showlegend=False)
    return fig

def fig_marcadores(sim, na, nb):
    df = sim["df"].copy()
    df["label"] = na + " " + df["A"].astype(str) + "–" + df["B"].astype(str) + " " + nb
    top = df.nlargest(8, "prob").iloc[::-1]
    fig = go.Figure(go.Bar(
        x=top["prob"]*100, y=top["label"], orientation="h", marker_color=RED,
        text=(top["prob"]*100).map(lambda x: f"{x:.1f}%"), textposition="auto",
        textfont=dict(color="white", size=14, family="Rajdhani")))
    fig.update_layout(**PLOT, height=340,
                      xaxis=dict(**GRID, ticksuffix="%"),
                      yaxis=dict(**NO_GRID, tickfont=dict(size=13, family="Rajdhani")))
    return fig

def fig_radar(df, eq_a, eq_b, cond_a="General", cond_b="General"):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco",
                        "Pases totales", "Goles esperados (xG)", "Córners",
                        "Quites", "Intercepciones"] if m in df["Métrica"].values]
    if not mets: return go.Figure()
    def get_val(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General":
            d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0
    va = [get_val(eq_a, cond_a, m) for m in mets]
    vb = [get_val(eq_b, cond_b, m) for m in mets]
    mx = [max(abs(a), abs(b), 1e-6) for a, b in zip(va, vb)]
    van, vbn = [a / m for a, m in zip(va, mx)], [b / m for b, m in zip(vb, mx)]
    fig = go.Figure()
    for v, n, c in [(van, f"{eq_a} ({cond_a})", RED), (vbn, f"{eq_b} ({cond_b})", BLUE)]:
        fig.add_trace(go.Scatterpolar(
            r=v+[v[0]], theta=mets+[mets[0]], fill="toself", name=n,
            line=dict(color=c, width=2),
            fillcolor=f"rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},0.2)"))
    fig.update_layout(**PLOT, height=400,
                      polar=dict(bgcolor="rgba(0,0,0,0)",
                                 radialaxis=dict(visible=True, range=[0, 1], gridcolor="#1c2a40")))
    return fig

def fig_matriz_ranking(df, metrica, condicion):
    d = df[df["Métrica"] == metrica].copy()
    if condicion != "General":
        d = d[d["Condicion"] == condicion]
    res = d.groupby("Equipo").agg(Propio=("Propio", "mean"),
                                   Concedido=("Concedido", "mean")).reset_index()
    if res.empty: return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=res["Concedido"], y=res["Propio"], mode="markers+text",
        text=res["Equipo"], textposition="top center",
        marker=dict(size=12, color=RED, opacity=0.8, line=dict(width=1, color="white"))))
    fig.add_vline(x=res["Concedido"].mean(), line=dict(color=GRAY, dash="dot"))
    fig.add_hline(y=res["Propio"].mean(),    line=dict(color=GRAY, dash="dot"))
    fig.update_layout(**PLOT, height=500,
                      xaxis_title=f"{metrica} Concedido", yaxis_title=f"{metrica} Propio",
                      xaxis=dict(**GRID), yaxis=dict(**GRID))
    return fig

# ──────────────────────────────────────────────────────────────────────
# SIDEBAR / NAVEGACIÓN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF 2026")
    ruta = st.text_input("📂 Excel", value="Fecha_x_fecha_lpf.xlsx")
    st.markdown("---")
    nav = st.radio("", ["🔮 Predictor", "📊 Rankings", "🔄 Head-to-Head",
                        "📖 Perfil por Rival", "🎭 Estilos de Juego"],
                   label_visibility="collapsed")

if not os.path.exists(ruta):
    st.warning("No se encontró el Excel."); st.stop()
datos = cargar_excel(ruta)
if not datos:
    st.error("Sin datos."); st.stop()

df = construir_df(datos)
equipos  = sorted(df["Equipo"].unique())
metricas = sorted(df["Métrica"].unique())

st.markdown('<h1>LPF 2026 · Scouting Dashboard</h1>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# PREDICTOR
# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Predictor de Partidos</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([5, 5, 3])
    eq_a  = c1.selectbox("Local", equipos)
    eq_b  = c2.selectbox("Visitante", equipos, index=min(1, len(equipos) - 1))
    es_loc = c3.toggle("Ventaja local", value=True)

    st.markdown('<div class="section-title">🔄 Penalización por Rotación / Copa</div>', unsafe_allow_html=True)
    rc1, rc2 = st.columns(2)
    with rc1:
        rot_a_int = st.slider("Rotación Local", 1, 5, 2, key="rot_a") / 5.0 if st.checkbox(f"⚠️ {eq_a} rota") else 0.0
    with rc2:
        rot_b_int = st.slider("Rotación Visit.", 1, 5, 2, key="rot_b") / 5.0 if st.checkbox(f"⚠️ {eq_b} rota") else 0.0

    if st.button("🚀 SIMULAR"):
        if eq_a == eq_b:
            st.warning("Elegí equipos distintos.")
        else:
            lam_a, lam_b = calcular_lambdas(df, eq_a, eq_b, es_loc, rot_a_int, rot_b_int)
            sim = montecarlo(lam_a, lam_b)

            k1, k2, k3 = st.columns(3)
            k1.markdown(f'<div class="kpi"><div class="lbl">V. {eq_a}</div><div class="val">{sim["victoria"]*100:.1f}%</div></div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kpi draw"><div class="lbl">Empate</div><div class="val">{sim["empate"]*100:.1f}%</div></div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi loss"><div class="lbl">V. {eq_b}</div><div class="val">{sim["derrota"]*100:.1f}%</div></div>', unsafe_allow_html=True)

            # Cuotas europeas implícitas (con overround típico de casas)
            o_a = odds_europeas(sim["victoria"])
            o_x = odds_europeas(sim["empate"])
            o_b = odds_europeas(sim["derrota"])
            st.markdown(
                f'<div class="odds-box">💰 <b>Cuotas implícitas</b> (overround {int((BOOK_OVERROUND-1)*100)}%) · '
                f'{eq_a} <b>{o_a}</b> · Empate <b>{o_x}</b> · {eq_b} <b>{o_b}</b></div>',
                unsafe_allow_html=True)

            st.markdown(
                f'<div class="note">⚙️ Modelo V8 · Dixon-Coles (ρ={DC_RHO}) · '
                f'Shrinkage K={K_SHRINK:g} · W_xG={W_XG:g} · '
                f'λ {eq_a} = <b>{lam_a}</b> · λ {eq_b} = <b>{lam_b}</b></div>',
                unsafe_allow_html=True)

            t1, t2, t3 = st.tabs(["📊 Probabilidades", "🎯 Marcadores exactos", "🕸️ Radar"])
            with t1:
                st.plotly_chart(fig_probs(sim, eq_a, eq_b), use_container_width=True)
            with t2:
                st.plotly_chart(fig_marcadores(sim, eq_a, eq_b), use_container_width=True)
            with t3:
                st.plotly_chart(fig_radar(df, eq_a, eq_b,
                                          "Local" if es_loc else "Visitante",
                                          "Visitante" if es_loc else "Local"),
                                use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# RANKINGS
# ──────────────────────────────────────────────────────────────────────
elif nav == "📊 Rankings":
    st.markdown('<div class="section-title">📊 Rankings y Matriz de Eficiencia</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([4, 3, 3])
    met_sel  = c1.selectbox("Métrica", metricas)
    cond_sel = c2.radio("Condición", ["General", "Local", "Visitante"], horizontal=True)
    vista_sel = c3.radio("Vista", ["Barras", "Matriz"], horizontal=True)

    if vista_sel == "Barras":
        p_sel = st.radio("Enfoque", ["Propio 🟢", "Concedido 🔴"], horizontal=True)
        df_r = ranking(df[df["Condicion"] == cond_sel] if cond_sel != "General" else df,
                       met_sel, "Propio" if "Propio" in p_sel else "Concedido",
                       met_sel in METRICAS_MENOS_ES_MEJOR)
        st.plotly_chart(go.Figure(go.Bar(
            x=df_r["Promedio"], y=df_r["Equipo"], orientation="h",
            marker_color=RED, text=df_r["Promedio"], textposition="outside"
        )).update_layout(**PLOT, height=500), use_container_width=True)
    else:
        st.plotly_chart(fig_matriz_ranking(df, met_sel, cond_sel), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# HEAD-TO-HEAD
# ──────────────────────────────────────────────────────────────────────
elif nav == "🔄 Head-to-Head":
    st.markdown('<div class="section-title">🔄 Head-to-Head Comparativo</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    ea = c1.selectbox("Equipo A", equipos, key="ea")
    ca = c1.selectbox("Condición A", ["General", "Local", "Visitante"], key="ca")
    eb = c2.selectbox("Equipo B", equipos, index=min(1, len(equipos)-1), key="eb")
    cb = c2.selectbox("Condición B", ["General", "Local", "Visitante"], key="cb")
    if ea == eb and ca == cb:
        st.info("⚠️ Seleccioná equipos o condiciones diferentes.")
    else:
        def get_fs(eq, cond):
            base = df[df["Equipo"] == eq]
            if cond != "General":
                base = base[base["Condicion"] == cond]
            return base.groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)
        sa, sb = get_fs(ea, ca), get_fs(eb, cb)
        idx = sa.index.intersection(sb.index)
        if not idx.empty:
            df_h2h = pd.DataFrame({
                f"{ea} (A Favor)":   sa.loc[idx, "Propio"].values,
                f"{eb} (A Favor)":   sb.loc[idx, "Propio"].values,
                f"{ea} (En Contra)": sa.loc[idx, "Concedido"].values,
                f"{eb} (En Contra)": sb.loc[idx, "Concedido"].values,
            }, index=idx)
            def hw(r):
                m = r.name
                stl = ["", "", "", ""]
                v1, v2 = r.iloc[0], r.iloc[1]
                if v1 != v2:
                    win = (v1 > v2) if m not in METRICAS_MENOS_ES_MEJOR else (v1 < v2)
                    stl[0 if win else 1] = "background-color: rgba(34, 197, 94, 0.2)"
                return stl
            st.dataframe(df_h2h.style.apply(hw, axis=1), use_container_width=True)
            st.plotly_chart(fig_radar(df, ea, eb, ca, cb), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# PERFIL POR RIVAL
# ──────────────────────────────────────────────────────────────────────
elif nav == "📖 Perfil por Rival":
    st.markdown('<div class="section-title">📖 Perfil por Rival</div>', unsafe_allow_html=True)
    eq_sel  = st.selectbox("Equipo", equipos)
    met_sel = st.selectbox("Métrica", metricas)
    d_eq = df[(df["Equipo"] == eq_sel) & (df["Métrica"] == met_sel)].sort_values("nFecha")
    if not d_eq.empty:
        fig = go.Figure([
            go.Bar(x=d_eq["Rival"], y=d_eq["Propio"],    name="A favor",    marker_color=RED),
            go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], name="En contra", marker_color=GRAY),
        ])
        fig.update_layout(**PLOT, barmode="group")
        st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# ESTILOS DE JUEGO
# ──────────────────────────────────────────────────────────────────────
elif nav == "🎭 Estilos de Juego":
    st.markdown('<div class="section-title">🎭 Matriz de Estilos de Juego</div>', unsafe_allow_html=True)
    mo = "Goles esperados (xG)" if "Goles esperados (xG)" in metricas else "Tiros totales"
    if "Posesión de balón" in metricas and mo in metricas:
        df_e = pd.DataFrame({
            "P": df[df["Métrica"] == "Posesión de balón"].groupby("Equipo")["Propio"].mean(),
            "O": df[df["Métrica"] == mo].groupby("Equipo")["Propio"].mean()
        }).dropna()
        mp, mo_m = df_e["P"].mean(), df_e["O"].mean()
        fig = go.Figure(go.Scatter(
            x=df_e["P"], y=df_e["O"], mode="markers+text",
            text=df_e.index, textposition="top center",
            marker=dict(size=12, color=RED, line=dict(width=1, color="white"))))
        fig.add_vline(x=mp, line=dict(color=GRAY, dash="dash"))
        fig.add_hline(y=mo_m, line=dict(color=GRAY, dash="dash"))
        fig.update_layout(**PLOT, height=600,
                          xaxis_title="Posesión (%)", yaxis_title=f"Ataque ({mo})",
                          xaxis=dict(**GRID), yaxis=dict(**GRID))
        st.plotly_chart(fig, use_container_width=True)

        def categorizar(row):
            if row["P"] > mp and row["O"] > mo_m:   return "🟢 Ofensivo de Posesión"
            if row["P"] <= mp and row["O"] > mo_m:  return "🟠 Ofensivo Directo"
            if row["P"] > mp and row["O"] <= mo_m:  return "🔵 Defensivo de Posesión"
            return "🔴 Defensivo Reactivo"
        df_e["Categoría Asignada"] = df_e.apply(categorizar, axis=1)
        st.dataframe(df_e.sort_values(["Categoría Asignada", "O"], ascending=[True, False]),
                     use_container_width=True)
    else:
        st.warning("Faltan métricas de Posesión o Tiros/xG en el Excel para armar la matriz.")
