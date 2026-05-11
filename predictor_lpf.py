"""
Plataforma de Scouting LPF 2026 — CON MÓDULO CAZADOR DE VALUE BETS
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

html, body, [class*="css"] {
    font-family: 'Manrope', sans-serif;
    background-color: #0a0a0c;
    color: #e0e0e0;
}
.stApp { background-color: #0a0a0c; }
#MainMenu, footer,{visibility: hidden;}

.hero-banner {
    background: linear-gradient(to right, rgba(10,10,12,1) 0%, rgba(10,10,12,0.4) 50%, rgba(10,10,12,1) 100%),
                url('https://images.unsplash.com/photo-1518605368461-1eb7678b871c?q=80&w=2000&auto=format&fit=crop');
    background-size: cover;
    background-position: center 30%;
    padding: 50px 40px;
    border-radius: 12px;
    margin-bottom: 40px;
    border-bottom: 4px solid #ED1A3B;
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
.section-header {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: #ffffff;
    letter-spacing: 1.5px;
    border-left: 4px solid #ED1A3B;
    padding-left: 15px;
    margin: 40px 0 20px 0;
}
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
.team-block { flex: 1; text-align: center; }
.team-block.home { border-right: 1px solid #2a2a30; }
.team-block.away { border-left: 1px solid #2a2a30; }
.t-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.2rem;
    color: #ffffff;
    letter-spacing: 1px;
    margin-bottom: 5px;
}
.t-prob { font-size: 3.5rem; font-weight: 800; color: #ED1A3B; line-height: 1; }
.t-label { font-size: 0.8rem; color: #888890; text-transform: uppercase; letter-spacing: 2px; margin-top: 5px; }
.draw-block { flex: 0.8; text-align: center; }
.draw-prob { font-size: 2.2rem; font-weight: 800; color: #888890; }

/* TOP 3 marcadores */
.top3-container {
    display: flex;
    gap: 12px;
    margin-top: 14px;
}
.score-card {
    flex: 1;
    background: #141417;
    border: 1px solid #2a2a30;
    border-radius: 8px;
    padding: 18px 12px;
    text-align: center;
}
.score-card.first { border-color: #ED1A3B; }
.score-rank {
    font-size: 0.7rem;
    color: #888890;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 6px;
}
.score-card.first .score-rank { color: #ED1A3B; }
.score-result {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.4rem;
    color: #ffffff;
    line-height: 1;
}
.score-card.first .score-result { color: #ED1A3B; font-size: 2.8rem; }
.score-pct {
    font-size: 0.85rem;
    color: #888890;
    margin-top: 4px;
}
.score-card.first .score-pct { color: #ffffff; font-weight: 600; }

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
.stButton>button:hover { background-color: #c41530; color: #fff; }
.stSelectbox>div>div, .stTextInput>div>div, .stRadio>div>div {
    background-color: #141417 !important;
    border: 1px solid #2a2a30 !important;
    color: #ffffff !important;
    border-radius: 4px !important;
}
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
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 8px; }
.stTabs [data-baseweb="tab"] { font-family: 'Manrope', sans-serif !important; background: #141417 !important; border: 1px solid #2a2a30 !important; border-radius: 4px !important; color: #888890 !important; }
.stTabs [aria-selected="true"] { background: #ED1A3B !important; color: white !important; border-color: #ED1A3B !important; }

/* ── Cazador de Value Bets ─────────────────────────────────────── */
.vb-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
    gap: 14px;
    margin-top: 18px;
}
.vb-card {
    background: #111115;
    border: 1px solid #2a2a35;
    border-radius: 10px;
    padding: 20px 22px 16px;
    position: relative;
    transition: transform 0.2s, box-shadow 0.2s;
}
.vb-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.vb-card.value {
    border-color: #ED1A3B;
    background: linear-gradient(135deg, #1a0a0d 0%, #111115 60%);
    box-shadow: 0 0 20px rgba(237, 26, 59, 0.15);
}
.vb-badge {
    position: absolute;
    top: 14px;
    right: 14px;
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 3px 8px;
    border-radius: 3px;
    text-transform: uppercase;
}
.vb-badge.value { background: #ED1A3B; color: #fff; }
.vb-badge.neutral { background: #2a2a35; color: #888890; }
.vb-cat {
    font-size: 0.68rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #555560;
    margin-bottom: 4px;
}
.vb-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.55rem;
    color: #e8e8e8;
    letter-spacing: 1px;
    line-height: 1.1;
    margin-bottom: 14px;
}
.vb-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 8px;
}
.vb-col { flex: 1; text-align: center; }
.vb-col-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #55555f;
    margin-bottom: 4px;
}
.vb-col-value {
    font-size: 1.25rem;
    font-weight: 800;
    color: #c0c0c8;
    line-height: 1;
}
.vb-col-value.justa { color: #888890; font-size: 1.1rem; font-weight: 600; }
.vb-col-value.casa  { color: #e0e0e0; }
.vb-col-value.ev-pos { color: #3ecf6b; font-size: 1.45rem; }
.vb-col-value.ev-neg { color: #555560; font-size: 1.1rem; font-weight: 600; }
.vb-divider {
    width: 1px;
    height: 36px;
    background: #2a2a35;
    align-self: center;
}
.vb-prob-bar-wrap {
    margin-top: 14px;
    height: 4px;
    background: #1e1e24;
    border-radius: 2px;
    overflow: hidden;
}
.vb-prob-bar {
    height: 100%;
    border-radius: 2px;
    background: #ED1A3B;
    transition: width 0.5s ease;
}
.vb-prob-bar.neutral-bar { background: #3a3a44; }
.vb-alert {
    border-radius: 8px;
    padding: 16px 22px;
    margin-bottom: 20px;
    border-left: 4px solid;
    display: flex;
    align-items: center;
    gap: 16px;
}
.vb-alert.found { border-color: #ED1A3B; background: rgba(237,26,59,0.08); }
.vb-alert.none  { border-color: #2a2a35; background: #111115; }
.vb-alert-icon { font-size: 1.8rem; }
.vb-alert-text { flex: 1; }
.vb-alert-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.3rem;
    letter-spacing: 1.5px;
    color: #fff;
    line-height: 1;
}
.vb-alert-sub { font-size: 0.8rem; color: #888890; margin-top: 3px; }
.corner-summary {
    background: #111115;
    border: 1px solid #2a2a35;
    border-radius: 10px;
    padding: 22px 28px;
    display: flex;
    align-items: center;
    gap: 30px;
    margin-bottom: 20px;
}
.corner-team { flex: 1; text-align: center; }
.corner-team-name {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #555560;
    margin-bottom: 4px;
}
.corner-lambda {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    color: #ED1A3B;
    line-height: 1;
}
.corner-sep {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.5rem;
    color: #2a2a35;
}
.corner-total { text-align: center; }
.corner-total-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #555560;
    margin-bottom: 4px;
}
.corner-total-val {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: #ffffff;
    line-height: 1;
}
</style>
""", unsafe_allow_html=True)

# ── Parámetros de Motor ───────────────────────────────────────────────
W_XG = 0.60
K_SHRINK = 6.0
K_PRIOR  = 5.0
PRIOR_ATK_SCALE = 0.40
PRIOR_DEF_SCALE = 0.30
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.8, 1.0
LAM_MIN, LAM_MAX = 0.30, 5.00

RED, BLUE, GRAY = "#ED1A3B", "#ffffff", "#4a4a52"
PLOT = dict(font=dict(family="Manrope", size=12, color="#a0a0a8"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=20, t=36, b=10))

# ──────────────────────────────────────────────────────────────────────
# PROCESAMIENTO
# ──────────────────────────────────────────────────────────────────────

def num(v) -> float:
    """
    Convierte un valor a float de forma robusta.
    Maneja casos especiales:
      - Porcentajes: "56%" → 56.0
      - Penales/alargues: "2(4)" → 2.0  (toma el gol reglamentario, ignora penales)
      - Fracciones de regates: "7/18 (39%)" → 0.0 (no es métrica numérica simple)
      - Guiones "-" → 0.0
    """
    if isinstance(v, str):
        v = v.strip()
        # Penales o alargue: "2(4)", "1(3)" → extraer el primer número
        m = re.match(r'^(-?\d+(?:\.\d+)?)\s*\(', v)
        if m:
            return float(m.group(1))
        v = v.replace('%', '').replace(',', '.').strip()
    try:
        return float(v)
    except:
        return 0.0


# Sentinel que marca el inicio de la sección de métricas derivadas (no cargar)
_SENTINEL_DERIVADAS = re.compile(r'métricas derivadas|métrica calculada', re.IGNORECASE)


@st.cache_data(ttl=120, show_spinner=False)
def cargar_excel(ruta: str):
    if not os.path.exists(ruta):
        return {}
    xl = pd.ExcelFile(ruta, engine="openpyxl")
    res = {}
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+|octavos", hoja, re.IGNORECASE):
            continue
        df = pd.read_excel(ruta, sheet_name=hoja, header=None)
        partidos, i = [], 0
        while i < len(df):
            c0 = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""
            if re.search(r"\s+vs\s+", c0, re.IGNORECASE):
                p = re.split(r"\s+vs\s+", c0, flags=re.IGNORECASE)
                loc, vis, stats, j = p[0].strip(), p[1].strip(), {}, i + 1
                while j < len(df):
                    r0 = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                    # Parar al encontrar otro partido o fila vacía
                    if re.search(r"\s+vs\s+", r0, re.IGNORECASE):
                        break
                    if r0 == "":
                        j += 1
                        continue
                    # Parar al encontrar la sección de métricas derivadas
                    if _SENTINEL_DERIVADAS.search(r0):
                        # Avanzar hasta la siguiente fila vacía o nuevo partido
                        j += 1
                        while j < len(df):
                            r_check = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                            if r_check == "" or re.search(r"\s+vs\s+", r_check, re.IGNORECASE):
                                break
                            j += 1
                        break
                    # Saltar encabezados de columnas
                    if r0.lower() in ("métrica", "metrica") or r0 == loc:
                        j += 1
                        continue
                    if pd.notna(df.iloc[j, 1]):
                        stats[r0] = {
                            "local":     num(df.iloc[j, 1]),
                            "visitante": num(df.iloc[j, 2]) if pd.notna(df.iloc[j, 2]) else 0.0,
                        }
                    j += 1
                partidos.append({"local": loc, "visitante": vis, "metricas": stats})
                i = j
            else:
                i += 1
        res[hoja] = partidos
    return res


def construir_df(datos: dict) -> pd.DataFrame:
    filas = []

    # Identificar cuál fue la última fecha regular
    max_fecha_reg = 0
    for f in datos.keys():
        m = re.search(r"\d+", f)
        if m:
            max_fecha_reg = max(max_fecha_reg, int(m.group()))

    for fecha, partidos in datos.items():
        match_fecha = re.search(r"\d+", fecha)
        if match_fecha:
            nf   = int(match_fecha.group())
            fase = "Regular"
        else:
            nf   = max_fecha_reg + 1
            fase = "Playoff"

        for p in partidos:
            tt = p["metricas"].get("Tiros totales",    {"local": 0, "visitante": 0})
            oc = p["metricas"].get("Ocasiones claras", {"local": 0, "visitante": 0})
            xg_loc = (oc["local"]     * 0.38) + (max(0, tt["local"]     - oc["local"])     * 0.05)
            xg_vis = (oc["visitante"] * 0.38) + (max(0, tt["visitante"] - oc["visitante"]) * 0.05)
            p["metricas"]["xG_Estimado"] = {"local": xg_loc, "visitante": xg_vis}
            for met, vals in p["metricas"].items():
                base = {"nFecha": nf, "Fase": fase, "Métrica": met}
                filas.append({**base, "Equipo": p["local"],     "Rival": p["visitante"], "Condicion": "Local",     "Propio": vals["local"],     "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"],     "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)


@st.cache_data(ttl=120, show_spinner=False)
def calcular_tabla(df: pd.DataFrame, condicion: str = "General") -> pd.DataFrame:
    dr = df[df["Métrica"] == "Resultado"].copy()
    # Excluir playoffs de la tabla
    if "Fase" in dr.columns:
        dr = dr[dr["Fase"] == "Regular"]
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
        v   = (d["Propio"] > d["Concedido"]).sum()
        e   = (d["Propio"] == d["Concedido"]).sum()
        d_  = (d["Propio"] < d["Concedido"]).sum()
        pts = int(v * 3 + e)
        gf  = d["Propio"].sum()
        gc  = d["Concedido"].sum()
        ppj  = pts / pj
        efec = (pts / (pj * 3)) * 100
        rows.append({"Equipo": eq, "PJ": pj, "V": int(v), "E": int(e), "D": int(d_),
                     "GF": gf, "GC": gc, "PTS": pts, "PPJ": ppj, "EFEC%": efec})
    tabla = pd.DataFrame(rows).sort_values(["EFEC%", "PTS", "GF"], ascending=[False, False, False]).reset_index(drop=True)
    tabla["Pos"] = tabla.index + 1
    ppj_mean = tabla["PPJ"].mean()
    tabla["PPJ_norm"]  = tabla["PPJ"] / ppj_mean if ppj_mean > 0 else 1.0
    tabla["prior_atk"] = (1.0 + (tabla["PPJ_norm"] - 1.0) * PRIOR_ATK_SCALE).clip(0.4, 2.5)
    tabla["prior_def"] = (1.0 - (tabla["PPJ_norm"] - 1.0) * PRIOR_DEF_SCALE).clip(0.4, 2.5)
    return tabla.set_index("Equipo")


def _get_prior(tabla: pd.DataFrame, eq: str):
    if tabla is None or eq not in tabla.index:
        return 1.0, 1.0
    return float(tabla.loc[eq, "prior_atk"]), float(tabla.loc[eq, "prior_def"])


def _adjusted_rate(d_spec, metrica, col, max_fecha_torneo, tabla, is_attack):
    df_m = d_spec[d_spec["Métrica"] == metrica]
    if df_m.empty:
        return np.nan
    fechas   = df_m["nFecha"].values
    valores  = df_m[col].values
    rivales  = df_m["Rival"].values
    valores_ajustados = []
    for v, r in zip(valores, rivales):
        pa_r, pd_r = _get_prior(tabla, r)
        adj = v / pd_r if (is_attack and pd_r > 0) else v / pa_r if (not is_attack and pa_r > 0) else v
        valores_ajustados.append(adj)
    w = np.where(fechas >= (max_fecha_torneo - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL)
    return float(np.average(valores_ajustados, weights=w))


@st.cache_data(ttl=120, show_spinner=False)
def _league_stats(df):
    dr = df[df["Métrica"] == "Resultado"]
    dx = df[df["Métrica"] == "xG_Estimado"]
    def get_avg(d, cond):
        v = d[d["Condicion"] == cond]["Propio"].mean() if not d.empty else np.nan
        return v if not np.isnan(v) else 1.0
    gh, gv = get_avg(dr, "Local"), get_avg(dr, "Visitante")
    xh, xv = get_avg(dx, "Local"), get_avg(dx, "Visitante")
    if dx.empty:
        rh, rv = gh, gv
    else:
        rh, rv = W_XG * xh + (1 - W_XG) * gh, W_XG * xv + (1 - W_XG) * gv
    return {"ref_home": rh, "ref_away": rv, "ref_all": (rh + rv) / 2}


def _strength(df, eq, cond, league, max_fecha_torneo: int, tabla: pd.DataFrame):
    d_eq   = df[df["Equipo"] == eq]
    d_spec = d_eq[d_eq["Condicion"] == cond]
    g_atk = _adjusted_rate(d_spec, "Resultado",   "Propio",    max_fecha_torneo, tabla, is_attack=True)
    x_atk = _adjusted_rate(d_spec, "xG_Estimado", "Propio",    max_fecha_torneo, tabla, is_attack=True)
    g_def = _adjusted_rate(d_spec, "Resultado",   "Concedido", max_fecha_torneo, tabla, is_attack=False)
    x_def = _adjusted_rate(d_spec, "xG_Estimado", "Concedido", max_fecha_torneo, tabla, is_attack=False)
    n_s   = len(d_spec[d_spec["Métrica"] == "Resultado"])

    def combine(g, x):
        if np.isnan(g) and np.isnan(x): return np.nan
        if np.isnan(x): return g
        if np.isnan(g): return x
        return W_XG * x + (1 - W_XG) * g

    atk_val, def_val = combine(g_atk, x_atk), combine(g_def, x_def)
    rh, ra   = league["ref_home"], league["ref_away"]
    ref_f, ref_a = (rh, ra) if cond == "Local" else (ra, rh)
    atk_obs = (atk_val / ref_f) if (not np.isnan(atk_val) and ref_f > 0) else np.nan
    def_obs = (def_val / ref_a) if (not np.isnan(def_val) and ref_a > 0) else np.nan
    prior_atk, prior_def = _get_prior(tabla, eq)
    n = n_s if n_s > 0 else 0
    atk_obs = atk_obs if not np.isnan(atk_obs) else prior_atk
    def_obs = def_obs if not np.isnan(def_obs) else prior_def
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
    M[0, 0] = max(M[0, 0] * (1 - la * lb * rho), 0.0)
    M[0, 1] = max(M[0, 1] * (1 + la * rho),       0.0)
    M[1, 0] = max(M[1, 0] * (1 + lb * rho),        0.0)
    M[1, 1] = max(M[1, 1] * (1 - rho),             0.0)
    M /= M.sum()
    return {
        "victoria": float(np.tril(M, -1).sum()),
        "empate":   float(np.trace(M)),
        "derrota":  float(np.triu(M, 1).sum()),
        "matrix":   M,
    }


def top3_marcadores(M, ea, eb):
    flat = [(M[i, j], i, j) for i in range(M.shape[0]) for j in range(M.shape[1])]
    flat.sort(reverse=True)
    top3 = flat[:3]
    medallas = ["🥇 MÁS PROBABLE", "🥈 2°", "🥉 3°"]
    clases   = ["first", "second", "third"]
    cards = ""
    for idx, (prob, i, j) in enumerate(top3):
        cards += f"""
        <div class="score-card {clases[idx]}">
            <div class="score-rank">{medallas[idx]}</div>
            <div class="score-result">{ea[:3].upper()} {i} – {j} {eb[:3].upper()}</div>
            <div class="score-pct">{prob * 100:.1f}%</div>
        </div>"""
    return f'<div class="top3-container">{cards}</div>'


# ══════════════════════════════════════════════════════════════════════════════
#  ★ MÓDULO VALUE BETS — FUNCIONES MATEMÁTICAS ★
# ══════════════════════════════════════════════════════════════════════════════

def calcular_mercados_matriz(M: np.ndarray) -> dict:
    n = M.shape[0]
    total_goals = np.zeros_like(M)
    for i in range(n):
        for j in range(n):
            total_goals[i, j] = i + j
    over25   = float(M[total_goals > 2.5].sum())
    under25  = 1.0 - over25
    btts_yes = float(M[1:, 1:].sum())
    btts_no  = 1.0 - btts_yes
    return {
        "over25":   round(over25,   4),
        "under25":  round(under25,  4),
        "btts_yes": round(btts_yes, 4),
        "btts_no":  round(btts_no,  4),
    }


def calcular_lambdas_corners(df: pd.DataFrame, eq_a: str, eq_b: str,
                              es_loc: bool, tabla: pd.DataFrame) -> tuple:
    LAM_C_MIN, LAM_C_MAX = 1.0, 15.0
    W_RECIENTE_C = 1.8
    W_NORMAL_C   = 1.0
    N_RECENCIA_C = 3
    K_C          = 4.0

    candidatos = ["Córners", "Corners", "Córners a favor", "Tiros de esquina",
                  "córners", "corners"]
    metrica_usada = next((c for c in candidatos if c in df["Métrica"].values), None)

    if metrica_usada is None:
        return (5.5, 4.5)

    max_fecha = int(df["nFecha"].max())
    df_c = df[df["Métrica"] == metrica_usada]

    ref_loc = df_c[df_c["Condicion"] == "Local"]["Propio"].mean()
    ref_vis = df_c[df_c["Condicion"] == "Visitante"]["Propio"].mean()
    if np.isnan(ref_loc) or ref_loc == 0: ref_loc = 5.5
    if np.isnan(ref_vis) or ref_vis == 0: ref_vis = 4.5

    def weighted_avg_c(equipo: str, condicion: str, col: str) -> float:
        d = df_c[(df_c["Equipo"] == equipo) & (df_c["Condicion"] == condicion)]
        if d.empty:
            d = df_c[df_c["Equipo"] == equipo]
        if d.empty:
            return np.nan
        fechas  = d["nFecha"].values
        valores = d[col].values
        w = np.where(fechas >= (max_fecha - N_RECENCIA_C + 1), W_RECIENTE_C, W_NORMAL_C)
        return float(np.average(valores, weights=w))

    def strength_c(equipo: str, condicion: str, ref_atk: float, ref_def: float):
        atk_raw = weighted_avg_c(equipo, condicion, "Propio")
        def_raw = weighted_avg_c(equipo, condicion, "Concedido")
        n = len(df_c[(df_c["Equipo"] == equipo) & (df_c["Condicion"] == condicion)])
        atk_norm = (atk_raw / ref_atk) if (not np.isnan(atk_raw) and ref_atk > 0) else 1.0
        def_norm = (def_raw / ref_def) if (not np.isnan(def_raw) and ref_def > 0) else 1.0
        atk_post = (n * atk_norm + K_C * 1.0) / (n + K_C)
        def_post = (n * def_norm + K_C * 1.0) / (n + K_C)
        return atk_post, def_post

    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")

    atk_a, def_a = strength_c(eq_a, ca,
                               ref_loc if ca == "Local" else ref_vis,
                               ref_vis if ca == "Local" else ref_loc)
    atk_b, def_b = strength_c(eq_b, cb,
                               ref_loc if cb == "Local" else ref_vis,
                               ref_vis if cb == "Local" else ref_loc)

    lc_a = (ref_loc if ca == "Local" else ref_vis) * atk_a * def_b
    lc_b = (ref_loc if cb == "Local" else ref_vis) * atk_b * def_a

    return (round(float(np.clip(lc_a, LAM_C_MIN, LAM_C_MAX)), 2),
            round(float(np.clip(lc_b, LAM_C_MIN, LAM_C_MAX)), 2))


def prob_corners_mercados(lc_a: float, lc_b: float) -> dict:
    MAX_C = 25

    def pmf_poisson(lam: float, kmax: int) -> np.ndarray:
        k = np.arange(kmax + 1)
        return np.exp(k * np.log(max(lam, 1e-9)) - lam -
                      np.array([math.log(math.factorial(x)) for x in k]))

    pa = pmf_poisson(lc_a, MAX_C)
    pb = pmf_poisson(lc_b, MAX_C)
    total_probs = np.convolve(pa, pb)[:MAX_C * 2 + 1]
    total_probs /= total_probs.sum()

    over85  = float(sum(total_probs[k] for k in range(len(total_probs)) if k > 8.5))
    under85 = 1.0 - over85
    over95  = float(sum(total_probs[k] for k in range(len(total_probs)) if k > 9.5))
    under95 = 1.0 - over95

    return {
        "lc_a":     lc_a,
        "lc_b":     lc_b,
        "lc_total": round(lc_a + lc_b, 2),
        "over85":   round(over85,  4),
        "under85":  round(under85, 4),
        "over95":   round(over95,  4),
        "under95":  round(under95, 4),
    }


def calcular_ev(prob_modelo: float, cuota_casa: float) -> float:
    if cuota_casa <= 1.0 or prob_modelo <= 0.0:
        return -999.0
    return round((prob_modelo * cuota_casa) - 1.0, 4)


def cuota_justa(prob: float) -> float:
    if prob <= 0.0:
        return 999.0
    return round(1.0 / prob, 3)


def analizar_mercado_completo(prob_1, prob_x, prob_2,
                               cuota_1, cuota_x, cuota_2,
                               mercados_extra, cuotas_extra) -> list:
    resultados = []

    for etiqueta, prob, cuota in [
        ("Victoria Local (1)",      prob_1, cuota_1),
        ("Empate (X)",              prob_x, cuota_x),
        ("Victoria Visitante (2)",  prob_2, cuota_2),
    ]:
        ev = calcular_ev(prob, cuota)
        resultados.append({
            "Mercado":     etiqueta,
            "Prob Modelo": prob,
            "Cuota Justa": cuota_justa(prob),
            "Cuota Casa":  cuota,
            "EV":          ev,
            "Value Bet":   ev > 0.0,
            "Categoria":   "1X2",
        })

    for etiqueta, clave in [("Over 2.5 Goles", "over25"), ("Under 2.5 Goles", "under25")]:
        prob  = mercados_extra.get(clave, 0.0)
        cuota = cuotas_extra.get(clave, 0.0)
        ev    = calcular_ev(prob, cuota) if cuota > 1.0 else -999.0
        resultados.append({
            "Mercado":     etiqueta,
            "Prob Modelo": prob,
            "Cuota Justa": cuota_justa(prob),
            "Cuota Casa":  cuota,
            "EV":          ev,
            "Value Bet":   ev > 0.0,
            "Categoria":   "Goles",
        })

    for etiqueta, clave in [("BTTS — Ambos Marcan", "btts_yes"),
                             ("BTTS — No Ambos",     "btts_no")]:
        prob  = mercados_extra.get(clave, 0.0)
        cuota = cuotas_extra.get(clave, 0.0)
        ev    = calcular_ev(prob, cuota) if cuota > 1.0 else -999.0
        resultados.append({
            "Mercado":     etiqueta,
            "Prob Modelo": prob,
            "Cuota Justa": cuota_justa(prob),
            "Cuota Casa":  cuota,
            "EV":          ev,
            "Value Bet":   ev > 0.0,
            "Categoria":   "BTTS",
        })

    for etiqueta, clave in [
        ("Córners Over 8.5",  "over85"),
        ("Córners Under 8.5", "under85"),
        ("Córners Over 9.5",  "over95"),
        ("Córners Under 9.5", "under95"),
    ]:
        prob  = mercados_extra.get(clave, 0.0)
        cuota = cuotas_extra.get(clave, 0.0)
        ev    = calcular_ev(prob, cuota) if cuota > 1.0 else -999.0
        resultados.append({
            "Mercado":     etiqueta,
            "Prob Modelo": prob,
            "Cuota Justa": cuota_justa(prob),
            "Cuota Casa":  cuota,
            "EV":          ev,
            "Value Bet":   ev > 0.0,
            "Categoria":   "Córners",
        })

    return resultados


# ── Gráficos ─────────────────────────────────────────────────────────

def fig_score_matrix(M, ea, eb, n=5):
    sub    = M[:n, :n]
    z_text = [[f"{sub[i, j]*100:.1f}%" for j in range(n)] for i in range(n)]
    fig = go.Figure(go.Heatmap(
        z=sub, x=[str(j) for j in range(n)], y=[str(i) for i in range(n)],
        text=z_text, texttemplate="%{text}",
        colorscale=[[0, "#0a0a0c"], [0.5, "#590f19"], [1, "#ED1A3B"]],
        showscale=False,
    ))
    fig.update_layout(**PLOT, height=350,
        xaxis_title=f"GOLES {eb.upper()}",
        yaxis_title=f"GOLES {ea.upper()}",
        yaxis=dict(autorange="reversed"))
    return fig


def fig_radar_pro(df, eq_a, eq_b, cond_a, cond_b):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco",
                         "Goles esperados (xG)", "Pases totales"]
            if m in df["Métrica"].values]
    if not mets:
        return go.Figure()

    def gv(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General":
            d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0

    def get_league_max(m):
        return df[df["Métrica"] == m].groupby("Equipo")["Propio"].mean().max()

    va = [gv(eq_a, cond_a, m) for m in mets]
    vb = [gv(eq_b, cond_b, m) for m in mets]
    mx = [max(get_league_max(m), 1e-6) for m in mets]
    text_a = [f"{m}: <b>{v:.1f}</b>" for m, v in zip(mets, va)]
    text_b = [f"{m}: <b>{v:.1f}</b>" for m, v in zip(mets, vb)]
    r_a   = [a / m for a, m in zip(va, mx)] + [va[0] / mx[0]]
    r_b   = [b / m for b, m in zip(vb, mx)] + [vb[0] / mx[0]]
    theta = mets + [mets[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r_a, theta=theta, fill="toself", name=eq_a, line=dict(color="#ED1A3B"), hoverinfo="text+name", text=text_a + [text_a[0]]))
    fig.add_trace(go.Scatterpolar(r=r_b, theta=theta, fill="toself", name=eq_b, line=dict(color="#ffffff"), hoverinfo="text+name", text=text_b + [text_b[0]]))
    layout_args = PLOT.copy()
    layout_args.update(height=400,
        polar=dict(bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, showticklabels=False, gridcolor="#2a2a30", range=[0, 1]),
            angularaxis=dict(gridcolor="#2a2a30", linecolor="#2a2a30")),
        margin=dict(l=40, r=40, t=36, b=40))
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
                   ["Predicción de Partidos", "Métricas Globales", "Comparativa H2H",
                    "Análisis de Rival", "Análisis de Estilos", "Posiciones",
                    "Cazador de Value Bets"],
                   label_visibility="collapsed")

if not os.path.exists(ruta):
    st.stop()

datos   = cargar_excel(ruta)
df      = construir_df(datos)
tabla   = calcular_tabla(df, "General")
equipos = sorted(df["Equipo"].unique())
metricas = sorted(df["Métrica"].unique())

# DataFrame filtrado sólo con datos de fase Regular (para módulos que no deben ver playoffs)
df_regular = df[df["Fase"] == "Regular"].copy()

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
    ea  = c1.selectbox("Equipo Local",     equipos, index=idx_river)
    eb  = c2.selectbox("Equipo Visitante", equipos, index=min(1, len(equipos) - 1))
    loc = c3.selectbox("Ajuste Localía",   ["Aplicar Ventaja", "Terreno Neutral"]) == "Aplicar Ventaja"
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("CALCULAR PROBABILIDADES"):
        la, lb = calcular_lambdas(df, ea, eb, loc, tabla)
        sim    = montecarlo(la, lb)

        st.markdown(f"""<div class="broadcast-board">
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
</div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Marcadores Más Probables</div>', unsafe_allow_html=True)
        st.markdown(top3_marcadores(sim["matrix"], ea, eb), unsafe_allow_html=True)

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
    ea     = c1.selectbox("Escuadra A", equipos)
    cond_a = c1.selectbox(f"Condición de {ea}", ["General", "Local", "Visitante"])
    eb     = c2.selectbox("Escuadra B", equipos, index=min(1, len(equipos) - 1))
    cond_b = c2.selectbox(f"Condición de {eb}", ["General", "Local", "Visitante"])
    t1, t2 = st.tabs(["Comparativa Visual (Radar)", "Métricas Crudas"])
    with t1:
        st.plotly_chart(fig_radar_pro(df, ea, eb, cond_a, cond_b), use_container_width=True)
    with t2:
        df_a = df[df["Equipo"] == ea]
        if cond_a != "General": df_a = df_a[df_a["Condicion"] == cond_a]
        df_b = df[df["Equipo"] == eb]
        if cond_b != "General": df_b = df_b[df_b["Condicion"] == cond_b]
        s1 = df_a.groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)
        s2 = df_b.groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)
        h2h_df = pd.DataFrame({
            f"{ea} ({cond_a[:3]}) Favor":  s1["Propio"],
            f"{ea} ({cond_a[:3]}) Contra": s1["Concedido"],
            f"{eb} ({cond_b[:3]}) Favor":  s2["Propio"],
            f"{eb} ({cond_b[:3]}) Contra": s2["Concedido"],
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
            go.Bar(x=d_eq["Rival"], y=d_eq["Propio"],    name="Generado",  marker_color=RED),
            go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], name="Concedido", marker_color=GRAY),
        ])
        st.plotly_chart(fig.update_layout(**PLOT, barmode="group"), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
elif nav == "Análisis de Estilos":
    # FIX: usar df_regular para que los playoffs no distorsionen la matriz de estilos
    st.markdown('<div class="section-header">Matriz de Estilos de Juego</div>', unsafe_allow_html=True)
    mo = "Goles esperados (xG)" if "Goles esperados (xG)" in df_regular["Métrica"].values else "Tiros totales"
    if "Posesión de balón" in df_regular["Métrica"].values:
        df_e = pd.DataFrame({
            "P": df_regular[df_regular["Métrica"] == "Posesión de balón"].groupby("Equipo")["Propio"].mean(),
            "O": df_regular[df_regular["Métrica"] == mo].groupby("Equipo")["Propio"].mean(),
        }).dropna()
        mp, mo_m = df_e["P"].mean(), df_e["O"].mean()
        fig = go.Figure(go.Scatter(
            x=df_e["P"], y=df_e["O"], mode="markers+text",
            text=df_e.index, textposition="top center",
            marker=dict(size=14, color=RED, line=dict(width=2, color="#141417")),
            textfont=dict(family="Manrope", size=11, color="#ffffff")
        ))
        fig.add_vline(x=mp, line=dict(color=GRAY, dash="dash", width=1))
        fig.add_hline(y=mo_m, line=dict(color=GRAY, dash="dash", width=1))
        fig.add_annotation(x=df_e["P"].max(), y=df_e["O"].max(), text="DOMINIO & ATAQUE",     showarrow=False, font=dict(color=GRAY, size=10), xanchor="right", yanchor="bottom")
        fig.add_annotation(x=df_e["P"].min(), y=df_e["O"].min(), text="REACTIVO & DEFENSIVO", showarrow=False, font=dict(color=GRAY, size=10), xanchor="left",  yanchor="top")
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
    t_dinamica  = calcular_tabla(df, vista_tabla)
    if not t_dinamica.empty:
        t_show = t_dinamica.reset_index()[["Pos", "Equipo", "PJ", "V", "E", "D", "GF", "GC", "PTS", "EFEC%"]].copy()
        t_show.columns = ["#", "Equipo", "PJ", "V", "E", "D", "GF", "GC", "PTS", "Efectividad %"]
        t_show["GF"] = t_show["GF"].astype(int)
        t_show["GC"] = t_show["GC"].astype(int)
        t_show["Efectividad %"] = t_show["Efectividad %"].round(1)
        st.dataframe(t_show.style.format({"Efectividad %": "{:.1f}%"}),
                     use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  ★ MÓDULO: CAZADOR DE VALUE BETS ★
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "Cazador de Value Bets":

    st.markdown('<div class="section-header">Cazador de Value Bets</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([4, 4, 2])
    ea_vb  = c1.selectbox("Equipo Local",     equipos, key="vb_ea")
    eb_vb  = c2.selectbox("Equipo Visitante", equipos,
                           index=min(1, len(equipos) - 1), key="vb_eb")
    loc_vb = c3.selectbox("Localía", ["Aplicar Ventaja", "Terreno Neutral"],
                           key="vb_loc") == "Aplicar Ventaja"

    st.markdown("---")

    fuente = st.radio("Fuente de Cuotas",
                      ["Ingresar Manualmente", "Subir CSV (cuotas_fecha.csv)"],
                      horizontal=True, key="vb_fuente")

    cuotas_validas = False
    cuota_1 = cuota_x = cuota_2 = 0.0
    cuotas_extra = {}

    if fuente == "Ingresar Manualmente":
        st.markdown("#### Cuotas 1X2")
        c1, c2, c3 = st.columns(3)
        cuota_1 = c1.number_input(f"Cuota Local ({ea_vb[:15]})",
                                   min_value=1.01, value=2.20, step=0.05, key="q1")
        cuota_x = c2.number_input("Cuota Empate",
                                   min_value=1.01, value=3.10, step=0.05, key="qx")
        cuota_2 = c3.number_input(f"Cuota Visitante ({eb_vb[:12]})",
                                   min_value=1.01, value=3.50, step=0.05, key="q2")

        with st.expander("➕ Cuotas de Goles y Córners (opcional — dejar en 0 si no disponés)"):
            cg1, cg2 = st.columns(2)
            cuotas_extra["over25"]  = cg1.number_input("Over 2.5 Goles",  min_value=0.0, value=0.0, step=0.05, key="qo25")
            cuotas_extra["under25"] = cg2.number_input("Under 2.5 Goles", min_value=0.0, value=0.0, step=0.05, key="qu25")
            cb1, cb2 = st.columns(2)
            cuotas_extra["btts_yes"] = cb1.number_input("BTTS — Ambos Marcan", min_value=0.0, value=0.0, step=0.05, key="qby")
            cuotas_extra["btts_no"]  = cb2.number_input("BTTS — No Ambos",     min_value=0.0, value=0.0, step=0.05, key="qbn")
            cc1, cc2, cc3, cc4 = st.columns(4)
            cuotas_extra["over85"]  = cc1.number_input("Córners O 8.5", min_value=0.0, value=0.0, step=0.05, key="qco85")
            cuotas_extra["under85"] = cc2.number_input("Córners U 8.5", min_value=0.0, value=0.0, step=0.05, key="qcu85")
            cuotas_extra["over95"]  = cc3.number_input("Córners O 9.5", min_value=0.0, value=0.0, step=0.05, key="qco95")
            cuotas_extra["under95"] = cc4.number_input("Córners U 9.5", min_value=0.0, value=0.0, step=0.05, key="qcu95")

        cuotas_validas = (cuota_1 > 1.0 and cuota_x > 1.0 and cuota_2 > 1.0)

    else:
        st.markdown("""
        **Formato del CSV esperado** — dos columnas: `mercado` y `cuota`:
        ```
        mercado,cuota
        1,2.20
        X,3.10
        2,3.50
        over25,1.85
        under25,1.95
        btts_yes,1.80
        btts_no,2.05
        over85,1.90
        under85,1.90
        over95,2.10
        under95,1.72
        ```
        """)
        csv_file = st.file_uploader("Subir cuotas_fecha.csv", type=["csv"])
        if csv_file:
            try:
                df_csv  = pd.read_csv(csv_file)
                mapping = df_csv.set_index(df_csv.columns[0])[df_csv.columns[1]].to_dict()
                cuota_1 = float(mapping.get("1", mapping.get("local",     0.0)))
                cuota_x = float(mapping.get("X", mapping.get("empate",    0.0)))
                cuota_2 = float(mapping.get("2", mapping.get("visitante", 0.0)))
                for clave in ["over25", "under25", "btts_yes", "btts_no",
                               "over85", "under85", "over95",  "under95"]:
                    cuotas_extra[clave] = float(mapping.get(clave, 0.0))
                cuotas_validas = (cuota_1 > 1.0 and cuota_x > 1.0 and cuota_2 > 1.0)
                if cuotas_validas:
                    st.success(f"✔ CSV cargado | 1 = {cuota_1} | X = {cuota_x} | 2 = {cuota_2}")
            except Exception as e:
                st.error(f"Error al leer el CSV: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔍 ANALIZAR VALUE BETS", key="vb_run"):
        if not cuotas_validas:
            st.error("Ingresá cuotas válidas (> 1.00) para los tres resultados (1, X, 2).")
            st.stop()

        la_vb, lb_vb = calcular_lambdas(df, ea_vb, eb_vb, loc_vb, tabla)
        sim_vb       = montecarlo(la_vb, lb_vb)
        M_vb         = sim_vb["matrix"]

        prob_1_vb = sim_vb["victoria"]
        prob_x_vb = sim_vb["empate"]
        prob_2_vb = sim_vb["derrota"]

        mercados_goles = calcular_mercados_matriz(M_vb)

        lc_a, lc_b  = calcular_lambdas_corners(df, ea_vb, eb_vb, loc_vb, tabla)
        corner_data = prob_corners_mercados(lc_a, lc_b)
        mercados_todos = {
            **mercados_goles,
            "over85":  corner_data["over85"],
            "under85": corner_data["under85"],
            "over95":  corner_data["over95"],
            "under95": corner_data["under95"],
        }

        analisis   = analizar_mercado_completo(
            prob_1_vb, prob_x_vb, prob_2_vb,
            cuota_1, cuota_x, cuota_2,
            mercados_todos, cuotas_extra
        )
        value_bets = [r for r in analisis if r["Value Bet"]]
        n_value    = len(value_bets)

        if n_value > 0:
            st.markdown(f"""
            <div class="vb-alert found">
                <div class="vb-alert-icon">🎯</div>
                <div class="vb-alert-text">
                    <div class="vb-alert-title">
                        {n_value} VALUE BET{"S" if n_value > 1 else ""} DETECTADA{"S" if n_value > 1 else ""}
                    </div>
                    <div class="vb-alert-sub">
                        El mercado está subestimando estas probabilidades vs. tu modelo.
                        EV positivo indica ventaja estadística a largo plazo — no garantía de ganancia inmediata.
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="vb-alert none">
                <div class="vb-alert-icon">📊</div>
                <div class="vb-alert-text">
                    <div class="vb-alert-title">SIN VALUE BETS EN ESTE PARTIDO</div>
                    <div class="vb-alert-sub">
                        Las cuotas del mercado reflejan o superan las probabilidades del modelo.
                        El mercado parece eficiente para este encuentro.
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

        def render_cards(items):
            cards_html = '<div class="vb-grid">'
            for r in items:
                is_value  = r["Value Bet"]
                ev_pct    = r["EV"] * 100
                ev_class  = "ev-pos" if is_value else "ev-neg"
                ev_str    = f"+{ev_pct:.1f}%" if is_value else (
                             f"{ev_pct:.1f}%" if r["EV"] > -99 else "—")
                badge_cls = "value" if is_value else "neutral"
                badge_txt = "✦ VALUE BET" if is_value else "SIN VALUE"
                bar_pct   = min(r["Prob Modelo"] * 100, 100)
                bar_cls   = "" if is_value else "neutral-bar"
                cuota_str = f'{r["Cuota Casa"]:.2f}' if r["Cuota Casa"] > 1.0 else "—"

                cards_html += f"""
                <div class="vb-card {"value" if is_value else ""}">
                    <span class="vb-badge {badge_cls}">{badge_txt}</span>
                    <div class="vb-cat">{r["Categoria"]}</div>
                    <div class="vb-name">{r["Mercado"]}</div>
                    <div class="vb-row">
                        <div class="vb-col">
                            <div class="vb-col-label">Prob Modelo</div>
                            <div class="vb-col-value">{r["Prob Modelo"]*100:.1f}%</div>
                        </div>
                        <div class="vb-divider"></div>
                        <div class="vb-col">
                            <div class="vb-col-label">Cuota Justa</div>
                            <div class="vb-col-value justa">{r["Cuota Justa"]:.2f}</div>
                        </div>
                        <div class="vb-divider"></div>
                        <div class="vb-col">
                            <div class="vb-col-label">Cuota Casa</div>
                            <div class="vb-col-value casa">{cuota_str}</div>
                        </div>
                        <div class="vb-divider"></div>
                        <div class="vb-col">
                            <div class="vb-col-label">EV</div>
                            <div class="vb-col-value {ev_class}">{ev_str}</div>
                        </div>
                    </div>
                    <div class="vb-prob-bar-wrap">
                        <div class="vb-prob-bar {bar_cls}" style="width:{bar_pct:.1f}%"></div>
                    </div>
                </div>"""
            cards_html += "</div>"
            st.markdown(cards_html, unsafe_allow_html=True)

        tab_labels = ["📋 Todos", "🏆 1X2", "⚽ Goles", "🔄 BTTS", "📐 Córners"]
        tabs_ui    = st.tabs(tab_labels)

        categorias_filtro = [None, "1X2", "Goles", "BTTS", "Córners"]
        for i, cat in enumerate(categorias_filtro):
            with tabs_ui[i]:
                items = analisis if cat is None else [r for r in analisis if r["Categoria"] == cat]
                render_cards(items)

        st.markdown('<div class="section-header">Motor de Córners — Detalle</div>',
                    unsafe_allow_html=True)
        st.markdown(f"""
        <div class="corner-summary">
            <div class="corner-team">
                <div class="corner-team-name">{ea_vb}</div>
                <div class="corner-lambda">{lc_a:.1f}</div>
                <div class="corner-team-name" style="margin-top:4px;">córners esperados</div>
            </div>
            <div class="corner-sep">VS</div>
            <div class="corner-team">
                <div class="corner-team-name">{eb_vb}</div>
                <div class="corner-lambda" style="color:#ffffff;">{lc_b:.1f}</div>
                <div class="corner-team-name" style="margin-top:4px;">córners esperados</div>
            </div>
            <div class="corner-sep">│</div>
            <div class="corner-total">
                <div class="corner-total-label">Total Esperado</div>
                <div class="corner-total-val">{corner_data["lc_total"]:.1f}</div>
            </div>
            <div class="corner-sep">│</div>
            <div class="corner-total">
                <div class="corner-total-label">Prob Over 8.5</div>
                <div class="corner-total-val" style="color:#ED1A3B;">{corner_data["over85"]*100:.1f}%</div>
            </div>
            <div class="corner-total">
                <div class="corner-total-label">Prob Over 9.5</div>
                <div class="corner-total-val" style="color:#888890;">{corner_data["over95"]*100:.1f}%</div>
            </div>
        </div>""", unsafe_allow_html=True)

        with st.expander("📥 Tabla Resumen Completa (exportable)"):
            df_out = pd.DataFrame(analisis).copy()
            df_out["Prob Modelo"] = (df_out["Prob Modelo"] * 100).round(2).astype(str) + "%"
            df_out["EV"]          = df_out["EV"].apply(
                lambda x: f"+{x*100:.2f}%" if x > 0 else (f"{x*100:.2f}%" if x > -99 else "—"))
            df_out["Value Bet"]   = df_out["Value Bet"].map({True: "✦ SÍ", False: "No"})
            st.dataframe(
                df_out[["Categoria", "Mercado", "Prob Modelo",
                         "Cuota Justa", "Cuota Casa", "EV", "Value Bet"]],
                use_container_width=True, hide_index=True
            )

        with st.expander("⚙ Parámetros del Motor (debug)"):
            pa_a, pd_a = _get_prior(tabla, ea_vb)
            pa_b, pd_b = _get_prior(tabla, eb_vb)
            st.code(
                f"GOLES\n"
                f"  λ {ea_vb}: {la_vb:.3f}  (Prior Atk: {pa_a:.2f} | Prior Def: {pd_a:.2f})\n"
                f"  λ {eb_vb}: {lb_vb:.3f}  (Prior Atk: {pa_b:.2f} | Prior Def: {pd_b:.2f})\n\n"
                f"CÓRNERS\n"
                f"  λc {ea_vb}: {lc_a:.2f}\n"
                f"  λc {eb_vb}: {lc_b:.2f}\n"
                f"  Total esperado: {corner_data['lc_total']:.2f}\n\n"
                f"MERCADOS DERIVADOS DE LA MATRIZ\n"
                f"  Over 2.5:  {mercados_goles['over25']*100:.1f}%  |  Under 2.5: {mercados_goles['under25']*100:.1f}%\n"
                f"  BTTS Sí:   {mercados_goles['btts_yes']*100:.1f}%  |  BTTS No:   {mercados_goles['btts_no']*100:.1f}%"
            )
