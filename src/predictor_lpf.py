"""
Plataforma de Scouting LPF 2026
─────────────────────────────────────────────────────────────────────────────
Módulos:
  · Predicción de Partidos  (con contexto táctico)
  · Métricas Globales
  · Comparativa H2H
  · Análisis de Rival
  · Análisis de Estilos
  · Posiciones
  · ADN Táctico            ★ NUEVO
  · Rachas y Momentum      ★ NUEVO
"""
import re, os, math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILOS
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LPF Analytics | Scouting",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Manrope:wght@400;600;800&display=swap');

html, body, [class*="css"] { font-family: 'Manrope', sans-serif; background-color: #0a0a0c; color: #e0e0e0; }
.stApp { background-color: #0a0a0c; }
#MainMenu, footer { visibility: hidden; }

.hero-banner {
    background: linear-gradient(to right, rgba(10,10,12,1) 0%, rgba(10,10,12,0.4) 50%, rgba(10,10,12,1) 100%),
                url('https://images.unsplash.com/photo-1518605368461-1eb7678b871c?q=80&w=2000&auto=format&fit=crop');
    background-size: cover; background-position: center 30%;
    padding: 50px 40px; border-radius: 12px; margin-bottom: 40px;
    border-bottom: 4px solid #ED1A3B; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.hero-subtitle { color: #ED1A3B; font-weight: 800; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 5px; margin-bottom: 5px; }
.hero-title { font-family: 'Bebas Neue', sans-serif; font-size: 4rem; color: #ffffff; letter-spacing: 2px; line-height: 1; margin: 0; }
.section-header { font-family: 'Bebas Neue', sans-serif; font-size: 2rem; color: #ffffff; letter-spacing: 1.5px; border-left: 4px solid #ED1A3B; padding-left: 15px; margin: 40px 0 20px 0; }
.broadcast-board { display: flex; justify-content: space-between; align-items: center; background: #141417; border: 1px solid #2a2a30; border-radius: 8px; padding: 30px 40px; margin-top: 20px; }
.team-block { flex: 1; text-align: center; }
.team-block.home { border-right: 1px solid #2a2a30; }
.team-block.away { border-left: 1px solid #2a2a30; }
.t-name { font-family: 'Bebas Neue', sans-serif; font-size: 2.2rem; color: #ffffff; letter-spacing: 1px; margin-bottom: 5px; }
.t-prob { font-size: 3.5rem; font-weight: 800; color: #ED1A3B; line-height: 1; }
.t-label { font-size: 0.8rem; color: #888890; text-transform: uppercase; letter-spacing: 2px; margin-top: 5px; }
.draw-block { flex: 0.8; text-align: center; }
.draw-prob { font-size: 2.2rem; font-weight: 800; color: #888890; }

.top3-container { display: flex; gap: 12px; margin-top: 14px; }
.score-card { flex: 1; background: #141417; border: 1px solid #2a2a30; border-radius: 8px; padding: 18px 12px; text-align: center; }
.score-card.first { border-color: #ED1A3B; }
.score-rank { font-size: 0.7rem; color: #888890; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px; }
.score-card.first .score-rank { color: #ED1A3B; }
.score-result { font-family: 'Bebas Neue', sans-serif; font-size: 2.4rem; color: #ffffff; line-height: 1; }
.score-card.first .score-result { color: #ED1A3B; font-size: 2.8rem; }
.score-pct { font-size: 0.85rem; color: #888890; margin-top: 4px; }
.score-card.first .score-pct { color: #ffffff; font-weight: 600; }

.stButton>button { font-family: 'Bebas Neue', sans-serif; font-size: 1.5rem; letter-spacing: 2px; background-color: #ED1A3B; color: #fff; border: none; border-radius: 4px; padding: 10px 20px; width: 100%; transition: background-color 0.3s; }
.stButton>button:hover { background-color: #c41530; color: #fff; }
.stSelectbox>div>div, .stTextInput>div>div, .stRadio>div>div { background-color: #141417 !important; border: 1px solid #2a2a30 !important; color: #ffffff !important; border-radius: 4px !important; }
[data-testid="stSidebar"] { background-color: #0f0f12 !important; border-right: 1px solid #1f1f24 !important; }
.sidebar-logo { font-family: 'Bebas Neue', sans-serif; font-size: 2.5rem; color: #ED1A3B; letter-spacing: 2px; text-align: center; margin-bottom: 30px; border-bottom: 1px solid #1f1f24; padding-bottom: 20px; }
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 8px; }
.stTabs [data-baseweb="tab"] { font-family: 'Manrope', sans-serif !important; background: #141417 !important; border: 1px solid #2a2a30 !important; border-radius: 4px !important; color: #888890 !important; }
.stTabs [aria-selected="true"] { background: #ED1A3B !important; color: white !important; border-color: #ED1A3B !important; }

/* ── ADN Táctico ─────────────────────────────────────────── */
.tag-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; margin: 3px 4px; }
.tag-pressing   { background: #2d1a1e; color: #ED1A3B; border: 1px solid #ED1A3B; }
.tag-bloque     { background: #1a1d2d; color: #6b8cff; border: 1px solid #6b8cff; }
.tag-posesion   { background: #1d2a1a; color: #5ecf6b; border: 1px solid #5ecf6b; }
.tag-directo    { background: #2a2a1a; color: #cfb45e; border: 1px solid #cfb45e; }
.tag-neutral    { background: #1e1e24; color: #888890; border: 1px solid #2a2a35; }
.tag-contra     { background: #2a1a2a; color: #cf5ead; border: 1px solid #cf5ead; }
.adn-card { background: #111115; border: 1px solid #2a2a35; border-radius: 10px; padding: 20px 24px; margin-bottom: 12px; transition: box-shadow 0.2s; }
.adn-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.4); }
.adn-team-name { font-family: 'Bebas Neue', sans-serif; font-size: 1.6rem; color: #ffffff; letter-spacing: 1px; margin-bottom: 10px; }
.adn-perfil { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 2px; color: #555560; margin-bottom: 6px; }

/* ── Rachas ──────────────────────────────────────────────── */
.racha-dot { display: inline-block; width: 28px; height: 28px; border-radius: 50%; text-align: center; line-height: 28px; font-size: 0.75rem; font-weight: 800; margin: 2px; }
.racha-v { background: #ED1A3B; color: #fff; }
.racha-e { background: #2a2a35; color: #888890; }
.racha-d { background: #141417; color: #555560; border: 1px solid #2a2a35; }
.momentum-card { background: #111115; border: 1px solid #2a2a35; border-radius: 10px; padding: 16px 20px; margin-bottom: 10px; }
.momentum-team { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; color: #fff; letter-spacing: 1px; margin-bottom: 8px; }
.momentum-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 2px; color: #555560; margin-bottom: 4px; }
.momentum-alza  { color: #5ecf6b; font-weight: 800; font-size: 0.9rem; }
.momentum-caida { color: #ED1A3B; font-weight: 800; font-size: 0.9rem; }
.momentum-estable { color: #888890; font-weight: 800; font-size: 0.9rem; }

/* ── Contexto táctico (predictor) ──────────────────────── */
.tactica-clash { background: #111115; border: 1px solid #2a2a35; border-radius: 10px; padding: 24px 28px; margin-top: 20px; }
.tactica-title { font-family: 'Bebas Neue', sans-serif; font-size: 1.4rem; color: #ED1A3B; letter-spacing: 1.5px; margin-bottom: 16px; }
.tactica-row { display: flex; align-items: flex-start; gap: 20px; margin-bottom: 14px; }
.tactica-team-col { flex: 1; }
.tactica-vs-col { color: #2a2a35; font-family: 'Bebas Neue', sans-serif; font-size: 1.2rem; padding-top: 4px; }
.tactica-insight { background: #0f0f12; border-left: 3px solid #ED1A3B; border-radius: 0 6px 6px 0; padding: 10px 14px; margin-top: 10px; font-size: 0.82rem; color: #a0a0a8; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
# PARÁMETROS DEL MOTOR
# ──────────────────────────────────────────────────────────────────────
W_XG = 0.60
K_SHRINK = 6.0
K_PRIOR  = 5.0
PRIOR_ATK_SCALE = 0.40
PRIOR_DEF_SCALE = 0.30
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.8, 1.0
LAM_MIN, LAM_MAX = 0.30, 5.00

RED, WHITE, GRAY = "#ED1A3B", "#ffffff", "#4a4a52"
PLOT = dict(
    font=dict(family="Manrope", size=12, color="#a0a0a8"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=20, t=36, b=10),
)

# ──────────────────────────────────────────────────────────────────────
# PROCESAMIENTO DE DATOS
# ──────────────────────────────────────────────────────────────────────
def num(v) -> float:
    if isinstance(v, str):
        v = v.strip()
        m = re.match(r'^(-?\d+(?:\.\d+)?)\s*\(', v)
        if m: return float(m.group(1))
        v = v.replace('%', '').replace(',', '.').strip()
    try: return float(v)
    except: return 0.0

_SENTINEL_DERIVADAS = re.compile(r'métricas derivadas|métrica calculada', re.IGNORECASE)

def _procesar_dataframe(df):
    partidos, i = [], 0
    while i < len(df):
        c0 = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""
        if re.search(r"\s+vs\s+", c0, re.IGNORECASE):
            p = re.split(r"\s+vs\s+", c0, flags=re.IGNORECASE)
            loc, vis, stats, j = p[0].strip(), p[1].strip(), {}, i + 1
            while j < len(df):
                r0 = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                if re.search(r"\s+vs\s+", r0, re.IGNORECASE): break
                if r0 == "":
                    j += 1
                    continue
                if _SENTINEL_DERIVADAS.search(r0):
                    j += 1
                    while j < len(df):
                        r_check = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                        if r_check == "" or re.search(r"\s+vs\s+", r_check, re.IGNORECASE): break
                        j += 1
                    break
                if r0.lower() in ("métrica", "metrica") or r0 == loc:
                    j += 1
                    continue
                if pd.notna(df.iloc[j, 1]) and df.shape[1] > 2:
                    stats[r0] = {
                        "local":     num(df.iloc[j, 1]),
                        "visitante": num(df.iloc[j, 2]) if pd.notna(df.iloc[j, 2]) else 0.0,
                    }
                j += 1
            partidos.append({"local": loc, "visitante": vis, "metricas": stats})
            i = j
        else:
            i += 1
    return partidos

@st.cache_data(ttl=120, show_spinner=False)
def cargar_excel(rutas_dict: dict, seleccion: list):
    res = {}
    for nombre_torneo in seleccion:
        ruta = rutas_dict.get(nombre_torneo)
        if not ruta or not os.path.exists(ruta):
            continue
        
        if os.path.isdir(ruta):
            archivos = os.listdir(ruta)
            archivos_excel = [f for f in archivos if f.endswith(('.xlsx', '.xls'))]
            
            if archivos_excel:
                ruta_xl = os.path.join(ruta, archivos_excel[0])
                xl = pd.ExcelFile(ruta_xl, engine="openpyxl")
                for hoja in xl.sheet_names:
                    if re.search(r"fecha\s*\d+|octavo|cuarto|semi|final|playoff", hoja, re.IGNORECASE):
                        df = pd.read_excel(xl, sheet_name=hoja, header=None)
                        # Agregamos prefijo para diferenciar de dónde viene cada hoja
                        res[f"{nombre_torneo}||{hoja}"] = _procesar_dataframe(df)
            else:
                archivos_csv = [f for f in archivos if f.endswith('.csv')]
                for archivo in archivos_csv:
                    hoja = archivo.split(" - ")[-1].replace(".csv", "") if " - " in archivo else archivo.replace(".csv", "")
                    if re.search(r"fecha\s*\d+|octavo|cuarto|semi|final|playoff", hoja, re.IGNORECASE):
                        ruta_csv = os.path.join(ruta, archivo)
                        df = pd.read_csv(ruta_csv, header=None)
                        res[f"{nombre_torneo}||{hoja}"] = _procesar_dataframe(df)
    return res

def construir_df(datos: dict) -> pd.DataFrame:
    filas = []
    MAX_FECHAS_REGULARES = 16 
    current_playoff_nf = MAX_FECHAS_REGULARES + 1

    for clave, partidos in datos.items():
        if "||" in clave:
            torneo, fecha = clave.split("||", 1)
        else:
            torneo, fecha = "General", clave
            
        match_fecha = re.search(r"\d+", fecha)
        es_playoff_txt = re.search(r"(octavo|cuarto|semi|final|playoff)", fecha, re.IGNORECASE)
        
        if match_fecha and not es_playoff_txt:
            nf = int(match_fecha.group())
            fase = "Regular" if nf <= MAX_FECHAS_REGULARES else "Playoff"
        else:
            nf = current_playoff_nf
            current_playoff_nf += 1 
            fase = "Playoff"

        for p in partidos:
            tt = p["metricas"].get("Tiros totales",    {"local": 0, "visitante": 0})
            oc = p["metricas"].get("Ocasiones claras", {"local": 0, "visitante": 0})
            xg_loc = (oc["local"]     * 0.38) + (max(0, tt["local"]     - oc["local"])     * 0.05)
            xg_vis = (oc["visitante"] * 0.38) + (max(0, tt["visitante"] - oc["visitante"]) * 0.05)
            p["metricas"]["xG_Estimado"] = {"local": xg_loc, "visitante": xg_vis}
            for met, vals in p["metricas"].items():
                base = {"nFecha": nf, "Fase": fase, "Métrica": met, "Torneo": torneo}
                filas.append({**base, "Equipo": p["local"],     "Rival": p["visitante"], "Condicion": "Local",     "Propio": vals["local"],     "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"],     "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)
  @st.cache_data(ttl=120, show_spinner=False)
def calcular_tabla(df: pd.DataFrame, condicion: str = "General") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
        
    dr = df[df["Métrica"] == "Resultado"].copy()
    
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
        v  = (d["Propio"] > d["Concedido"]).sum()
        e  = (d["Propio"] == d["Concedido"]).sum()
        d_ = (d["Propio"] < d["Concedido"]).sum()
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
#  ★  ADN TÁCTICO — MOTOR DE PATRONES
# ══════════════════════════════════════════════════════════════════════════════
def _safe_mean(df, equipo, metrica, col="Propio", condicion=None):
    d = df[(df["Equipo"] == equipo) & (df["Métrica"] == metrica)]
    if condicion: d = d[d["Condicion"] == condicion]
    if d.empty: return np.nan
    return float(d[col].mean())

def calcular_adn_tactico(df: pd.DataFrame) -> pd.DataFrame:
    equipos = sorted(df["Equipo"].unique())
    rows = []
    for eq in equipos:
        pos_propia   = _safe_mean(df, eq, "Posesión de balón")
        pos_cedida   = 100.0 - pos_propia if not np.isnan(pos_propia) else np.nan
        tiros_prop   = _safe_mean(df, eq, "Tiros totales")
        tiros_conc   = _safe_mean(df, eq, "Tiros totales", col="Concedido")
        xg_prop      = _safe_mean(df, eq, "xG_Estimado")
        xg_conc      = _safe_mean(df, eq, "xG_Estimado", col="Concedido")
        oc_prop      = _safe_mean(df, eq, "Ocasiones claras")
        oc_conc      = _safe_mean(df, eq, "Ocasiones claras", col="Concedido")
        gf           = _safe_mean(df, eq, "Resultado")
        gc           = _safe_mean(df, eq, "Resultado", col="Concedido")
        efic_ofens = (xg_prop / tiros_prop) if (not np.isnan(xg_prop) and not np.isnan(tiros_prop) and tiros_prop > 0) else np.nan
        rows.append({
            "Equipo": eq, "Posesion": pos_propia, "TirosProp": tiros_prop,
            "TirosConc": tiros_conc, "xGProp": xg_prop, "xGConc": xg_conc,
            "OcProp": oc_prop, "OcConc": oc_conc, "GF": gf, "GC": gc, "EficOfens": efic_ofens,
        })
    adn = pd.DataFrame(rows).set_index("Equipo")
    def pct(col):
        s = adn[col].dropna()
        if s.empty: return {}
        return {eq: float(np.mean(s <= v)) for eq, v in adn[col].dropna().items()}

    pct_pos   = pct("Posesion")
    pct_tprop = pct("TirosProp")
    pct_tconc = pct("TirosConc")
    pct_xgc   = pct("xGConc")
    pct_efic  = pct("EficOfens")

    tags_dict = {}
    insights  = {}

    for eq in adn.index:
        tags, frases = [], []
        pos_p  = pct_pos.get(eq, 0.5)
        tp_p   = pct_tprop.get(eq, 0.5)
        tc_p   = pct_tconc.get(eq, 0.5)
        xgc_p  = pct_xgc.get(eq, 0.5)
        ef_p   = pct_efic.get(eq, 0.5)

        if pos_p >= 0.70:
            tags.append(("POSESIÓN DOMINANTE", "tag-posesion"))
            frases.append("Controla el juego con posesión elevada.")
        elif pos_p <= 0.30:
            tags.append(("JUEGO DIRECTO", "tag-directo"))
            frases.append("Cede la pelota y busca aprovechar los espacios.")

        if tc_p <= 0.30 and pos_p <= 0.55:
            tags.append(("PRESSING ALTO", "tag-pressing"))
            frases.append("Asfixia al rival sin necesitar posesión: concede pocos tiros.")
        elif tc_p >= 0.70:
            tags.append(("BLOQUE BAJO", "tag-bloque"))
            frases.append("Defiende replegado, concede muchos intentos al rival.")

        if pos_p <= 0.40 and tp_p >= 0.55:
            tags.append(("CONTRA / TRANSICIÓN", "tag-contra"))
            frases.append("Peligroso en transición: genera volumen ofensivo con poca pelota.")

        if ef_p >= 0.70:
            tags.append(("ALTA EFICIENCIA", "tag-posesion"))
            frases.append("Alta relación xG/tiro: genera ocasiones de calidad.")
        elif ef_p <= 0.30 and tp_p >= 0.60:
            tags.append(("VOLUMEN SIN PRECISIÓN", "tag-directo"))
            frases.append("Tira mucho pero con bajo xG por remate.")

        if xgc_p >= 0.75:
            tags.append(("DÉFICIT DEFENSIVO", "tag-bloque"))
            frases.append("Concede mucho xG: línea defensiva con espacios.")

        if not tags:
            tags.append(("PERFIL EQUILIBRADO", "tag-neutral"))
            frases.append("Sin tendencias extremas: estilo balanceado.")

        tags_dict[eq] = tags
        insights[eq]  = " ".join(frases)

    adn["Tags"]    = adn.index.map(tags_dict)
    adn["Insight"] = adn.index.map(insights)
    return adn

def render_tags_html(tags: list) -> str:
    html = ""
    for texto, clase in tags:
        html += f'<span class="tag-badge {clase}">{texto}</span>'
    return html

def contexto_tactica_clash(adn: pd.DataFrame, eq_a: str, eq_b: str) -> str:
    if adn is None or eq_a not in adn.index or eq_b not in adn.index: return ""
    tags_a   = adn.loc[eq_a, "Tags"]   if isinstance(adn.loc[eq_a, "Tags"],   list) else []
    tags_b   = adn.loc[eq_b, "Tags"]   if isinstance(adn.loc[eq_b, "Tags"],   list) else []
    ins_a    = adn.loc[eq_a, "Insight"] if pd.notna(adn.loc[eq_a, "Insight"]) else ""
    ins_b    = adn.loc[eq_b, "Insight"] if pd.notna(adn.loc[eq_b, "Insight"]) else ""

    tags_a_txt = set(t for t, _ in tags_a)
    tags_b_txt = set(t for t, _ in tags_b)

    clash_lines = []
    if "PRESSING ALTO" in tags_a_txt and "JUEGO DIRECTO" in tags_b_txt: clash_lines.append("⚡ <b>Pressing vs Juego Directo</b>: el local intentará robar alto, el visitante buscará saltar líneas.")
    if "POSESIÓN DOMINANTE" in tags_a_txt and "PRESSING ALTO" in tags_b_txt: clash_lines.append("🔄 <b>Batalla de control</b>: local posesivo vs visitante que presiona — partido de mediocampo intenso.")
    if "CONTRA / TRANSICIÓN" in tags_b_txt and "POSESIÓN DOMINANTE" in tags_a_txt: clash_lines.append("🎯 <b>Posesión vs Contraataque</b>: local domina la pelota, visitante espera el espacio a la espalda.")
    if "DÉFICIT DEFENSIVO" in tags_a_txt or "DÉFICIT DEFENSIVO" in tags_b_txt: clash_lines.append("⚽ <b>Partido abierto</b>: al menos un equipo tiene vulnerabilidades defensivas — esperar goles.")
    if "ALTA EFICIENCIA" in tags_a_txt and "ALTA EFICIENCIA" in tags_b_txt: clash_lines.append("🎖️ <b>Duelo de calidad</b>: ambos equipos son clínicos — los pocos errores se pagarán caro.")
    if not clash_lines: clash_lines.append("📊 Perfiles similares o complementarios — partido de resultado abierto según forma reciente.")

    tags_a_html = render_tags_html(tags_a)
    tags_b_html = render_tags_html(tags_b)
    clash_html  = "<br>".join(clash_lines)

    return f"""
    <div class="tactica-clash">
        <div class="tactica-title">Contexto Táctico del Choque</div>
        <div class="tactica-row">
            <div class="tactica-team-col">
                <div style="font-size:0.7rem;color:#555560;text-transform:uppercase;letter-spacing:2px;margin-bottom:6px;">{eq_a} (local)</div>
                {tags_a_html}
                <div style="font-size:0.8rem;color:#888890;margin-top:8px;">{ins_a}</div>
            </div>
            <div class="tactica-vs-col">VS</div>
            <div class="tactica-team-col">
                <div style="font-size:0.7rem;color:#555560;text-transform:uppercase;letter-spacing:2px;margin-bottom:6px;">{eq_b} (visitante)</div>
                {tags_b_html}
                <div style="font-size:0.8rem;color:#888890;margin-top:8px;">{ins_b}</div>
            </div>
        </div>
        <div class="tactica-insight">{clash_html}</div>
    </div>"""

# ══════════════════════════════════════════════════════════════════════════════
#  ★  RACHAS Y MOMENTUM
# ══════════════════════════════════════════════════════════════════════════════
def calcular_rachas(df: pd.DataFrame) -> pd.DataFrame:
    dr = df[df["Métrica"] == "Resultado"].copy()
    dx = df[df["Métrica"] == "xG_Estimado"].copy()
    equipos = sorted(dr["Equipo"].unique())
    rows = []

    for eq in equipos:
        d_eq = dr[dr["Equipo"] == eq].sort_values("nFecha")
        if d_eq.empty: continue

        resultados = []
        for _, row in d_eq.iterrows():
            if row["Propio"] > row["Concedido"]: resultados.append("V")
            elif row["Propio"] == row["Concedido"]: resultados.append("E")
            else: resultados.append("D")

        ultimas6 = resultados[-6:]
        pts6 = sum(3 if r == "V" else (1 if r == "E" else 0) for r in ultimas6)
        pts3 = sum(3 if r == "V" else (1 if r == "E" else 0) for r in resultados[-3:])

        dxg = dx[dx["Equipo"] == eq].sort_values("nFecha")
        xg_vals = dxg["Propio"].values
        if len(xg_vals) >= 6:
            xg_rec, xg_ant = float(np.mean(xg_vals[-3:])), float(np.mean(xg_vals[-6:-3]))
            delta_xg = xg_rec - xg_ant
        elif len(xg_vals) >= 3:
            xg_rec = float(np.mean(xg_vals[-3:]))
            xg_ant = float(np.mean(xg_vals[:-3])) if len(xg_vals) > 3 else xg_rec
            delta_xg = xg_rec - xg_ant
        else:
            xg_rec = float(np.mean(xg_vals)) if len(xg_vals) > 0 else 0.0
            xg_ant = xg_rec
            delta_xg = 0.0

        momentum_score = pts3 / 9.0 * 0.6 + (min(max(delta_xg / 1.0, -1), 1) * 0.5 + 0.5) * 0.4

        if momentum_score >= 0.65: estado, estado_cls = "EN ALZA", "momentum-alza"
        elif momentum_score <= 0.35: estado, estado_cls = "EN CAÍDA", "momentum-caida"
        else: estado, estado_cls = "ESTABLE", "momentum-estable"

        rows.append({
            "Equipo": eq, "Resultados": resultados, "Ultimas6": ultimas6, "Pts6": pts6, "Pts3": pts3,
            "xGRec": round(xg_rec, 2), "xGAnt": round(xg_ant, 2), "DeltaXG": round(delta_xg, 3),
            "MomentumScore": round(momentum_score, 3), "Estado": estado, "EstadoCls": estado_cls,
        })
    return pd.DataFrame(rows).set_index("Equipo")

def render_racha_dots(ultimas6: list) -> str:
    html = ""
    for r in ultimas6:
        cls = {"V": "racha-v", "E": "racha-e", "D": "racha-d"}[r]
        html += f'<span class="racha-dot {cls}">{r}</span>'
    return html

def fig_momentum_timeline(df: pd.DataFrame, equipo: str) -> go.Figure:
    dr = df[(df["Equipo"] == equipo) & (df["Métrica"] == "Resultado")].sort_values("nFecha")
    dx = df[(df["Equipo"] == equipo) & (df["Métrica"] == "xG_Estimado")].sort_values("nFecha")
    if dr.empty: return go.Figure()
    fechas = dr["nFecha"].values
    pts_parciales = []
    for _, row in dr.iterrows():
        if row["Propio"] > row["Concedido"]: pts_parciales.append(3)
        elif row["Propio"] == row["Concedido"]: pts_parciales.append(1)
        else: pts_parciales.append(0)
    xg_vals = dx.set_index("nFecha")["Propio"].reindex(fechas).fillna(0).values
    fig = go.Figure()
    fig.add_trace(go.Bar(x=fechas, y=pts_parciales, name="Pts/Fecha", marker_color=[RED if p == 3 else ("#888890" if p == 1 else "#1e1e24") for p in pts_parciales], yaxis="y1"))
    fig.add_trace(go.Scatter(x=fechas, y=xg_vals, name="xG Propio", mode="lines+markers", line=dict(color=WHITE, width=2), marker=dict(size=6), yaxis="y2"))
    fig.update_layout(**PLOT, height=320, yaxis=dict(title="Puntos", showgrid=False, color="#555560"), yaxis2=dict(title="xG", overlaying="y", side="right", showgrid=False, color="#888890"), legend=dict(orientation="h", x=0, y=1.12), xaxis=dict(title="Fecha", color="#555560", tickmode="linear"))
    return fig

def fig_momentum_ranking(rachas: pd.DataFrame) -> go.Figure:
    df_r = rachas.sort_values("MomentumScore", ascending=True).copy()
    colors = [RED if sc >= 0.65 else (GRAY if sc <= 0.35 else "#4a4a6a") for sc in df_r["MomentumScore"]]
    fig = go.Figure(go.Bar(x=df_r["MomentumScore"], y=df_r.index, orientation="h", marker_color=colors, text=[f"{s:.2f}" for s in df_r["MomentumScore"]], textposition="outside"))
    fig.update_layout(**PLOT, height=max(400, len(df_r) * 28), xaxis=dict(range=[0, 1.1], showgrid=False, color="#555560"), title=dict(text="ÍNDICE DE MOMENTUM", font=dict(family="Bebas Neue", size=18, color="#ffffff")))
    return fig

def fig_score_matrix(M, ea, eb, n=5):
    sub = M[:n, :n]
    z_text = [[f"{sub[i, j]*100:.1f}%" for j in range(n)] for i in range(n)]
    fig = go.Figure(go.Heatmap(z=sub, x=[str(j) for j in range(n)], y=[str(i) for i in range(n)], text=z_text, texttemplate="%{text}", colorscale=[[0, "#0a0a0c"], [0.5, "#590f19"], [1, "#ED1A3B"]], showscale=False))
    fig.update_layout(**PLOT, height=350, xaxis_title=f"GOLES {eb.upper()}", yaxis_title=f"GOLES {ea.upper()}", yaxis=dict(autorange="reversed"))
    return fig

def fig_radar_pro(df, eq_a, eq_b, cond_a, cond_b):
    mets = [m for m in ["Posesión de balón", "Tiros totales", "Tiros al arco", "Goles esperados (xG)", "Pases totales"] if m in df["Métrica"].values]
    if not mets: return go.Figure()
    def gv(eq, cond, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        if cond != "General": d = d[d["Condicion"] == cond]
        return d["Propio"].mean() if not d.empty else 0.0
    def get_league_max(m): return df[df["Métrica"] == m].groupby("Equipo")["Propio"].mean().max()
    va, vb = [gv(eq_a, cond_a, m) for m in mets], [gv(eq_b, cond_b, m) for m in mets]
    mx = [max(get_league_max(m), 1e-6) for m in mets]
    text_a, text_b = [f"{m}: <b>{v:.1f}</b>" for m, v in zip(mets, va)], [f"{m}: <b>{v:.1f}</b>" for m, v in zip(mets, vb)]
    r_a = [a / m for a, m in zip(va, mx)] + [va[0] / mx[0]]
    r_b = [b / m for b, m in zip(vb, mx)] + [vb[0] / mx[0]]
    theta = mets + [mets[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r_a, theta=theta, fill="toself", name=eq_a, line=dict(color=RED), hoverinfo="text+name", text=text_a + [text_a[0]]))
    fig.add_trace(go.Scatterpolar(r=r_b, theta=theta, fill="toself", name=eq_b, line=dict(color=WHITE), hoverinfo="text+name", text=text_b + [text_b[0]]))
    layout_args = PLOT.copy()
    layout_args.update(height=400, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, showticklabels=False, gridcolor="#2a2a30", range=[0, 1]), angularaxis=dict(gridcolor="#2a2a30", linecolor="#2a2a30")), margin=dict(l=40, r=40, t=36, b=40))
    fig.update_layout(**layout_args)
    return fig

# ──────────────────────────────────────────────────────────────────────
# NAVEGACIÓN
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">LPF SCOUTING</div>', unsafe_allow_html=True)
    
    # --- ESTA ES LA MAGIA DEL MULTISELECT DE DIRECTORIOS ---
    rutas_db = {
        "Apertura (Histórico)": "/home/sebi/Documents/futbol/lpf_pred/data/historico",
        "Clausura (Actual)": "/home/sebi/Documents/futbol/lpf_pred/data/actual"
    }
    torneos_seleccionados = st.multiselect(
        "Bases de Datos a Utilizar:",
        options=list(rutas_db.keys()),
        default=["Apertura (Histórico)"]
    )
    # -------------------------------------------------------

    st.markdown("<br>", unsafe_allow_html=True)
    nav = st.radio(
        "MÓDULOS DE ANÁLISIS",
        [
            "Predicción de Partidos",
            "Métricas Globales",
            "Comparativa H2H",
            "Análisis de Rival",
            "Análisis de Estilos",
            "Posiciones",
            "ADN Táctico",
            "Rachas y Momentum",
        ],
        label_visibility="collapsed",
    )

# Cargamos usando la nueva lógica dinámica
datos    = cargar_excel(rutas_db, torneos_seleccionados)
df       = construir_df(datos)

if df.empty:
    st.error("⚠️ No se seleccionaron datos o las carpetas están vacías. Elegí un torneo en la barra lateral.")
    st.stop()

tabla    = calcular_tabla(df, "General")
equipos  = sorted(df["Equipo"].unique())
metricas = sorted(df["Métrica"].unique())

@st.cache_data(ttl=120, show_spinner=False)
def _cached_adn(dataframe): return calcular_adn_tactico(dataframe)
@st.cache_data(ttl=120, show_spinner=False)
def _cached_rachas(dataframe): return calcular_rachas(dataframe)

adn_df    = _cached_adn(df)
rachas_df = _cached_rachas(df)

st.markdown("""
<div class="hero-banner">
    <div class="hero-subtitle">Base de Datos LPF 2026</div>
    <h1 class="hero-title">PLATAFORMA DE RENDIMIENTO</h1>
</div>
""", unsafe_allow_html=True)

if nav == "Predicción de Partidos":
    st.markdown('<div class="section-header">Módulo Predictivo</div>', unsafe_allow_html=True)
    idx_river = equipos.index("River Plate") if "River Plate" in equipos else 0
    c1, c2, c3 = st.columns([4, 4, 2])
    ea  = c1.selectbox("Equipo Local",     equipos, index=idx_river)
    eb  = c2.selectbox("Equipo Visitante", equipos, index=min(1, len(equipos) - 1))
    loc = c3.selectbox("Ajuste Localía",   ["Aplicar Ventaja", "Terreno Neutral"]) == "Aplicar Ventaja"
    
    if st.button("CALCULAR PROBABILIDADES"):
        la, lb = calcular_lambdas(df, ea, eb, loc, tabla)
        sim    = montecarlo(la, lb)
        st.markdown(f"""<div class="broadcast-board"><div class="team-block home"><div class="t-name">{ea}</div><div class="t-prob">{sim['victoria']*100:.1f}%</div><div class="t-label">Victoria Local</div></div><div class="draw-block"><div class="t-label" style="margin-bottom:5px;">Empate</div><div class="draw-prob">{sim['empate']*100:.1f}%</div></div><div class="team-block away"><div class="t-name">{eb}</div><div class="t-prob" style="color:#ffffff;">{sim['derrota']*100:.1f}%</div><div class="t-label">Victoria Visitante</div></div></div>""", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Marcadores Más Probables</div>', unsafe_allow_html=True)
        st.markdown(top3_marcadores(sim["matrix"], ea, eb), unsafe_allow_html=True)
        ctx = contexto_tactica_clash(adn_df, ea, eb)
        if ctx: st.markdown(ctx, unsafe_allow_html=True)

        if not rachas_df.empty and ea in rachas_df.index and eb in rachas_df.index:
            st.markdown('<div class="section-header">Forma Reciente</div>', unsafe_allow_html=True)
            mc1, mc2 = st.columns(2)
            for col_ui, eq_m in [(mc1, ea), (mc2, eb)]:
                with col_ui:
                    row_m = rachas_df.loc[eq_m]
                    dots  = render_racha_dots(row_m["Ultimas6"])
                    col_ui.markdown(f"""<div class="momentum-card"><div class="momentum-team">{eq_m}</div><div class="momentum-label">Últimas {len(row_m["Ultimas6"])} fechas</div><div style="margin-bottom:10px;">{dots}</div><div class="momentum-label">Estado de forma</div><div class="{row_m["EstadoCls"]}">{row_m["Estado"]}</div><div style="font-size:0.78rem;color:#555560;margin-top:6px;">xG reciente: {row_m["xGRec"]:.2f} &nbsp;|&nbsp; Pts últimas 3: {row_m["Pts3"]}</div></div>""", unsafe_allow_html=True)
        
        with st.expander("Parámetros del Motor (Lambdas y Priors)"):
            pa_a, pd_a = _get_prior(tabla, ea)
            pa_b, pd_b = _get_prior(tabla, eb)
            st.code(f"λ {ea}: {la:.3f} (Atk Prior: {pa_a:.2f})\nλ {eb}: {lb:.3f} (Atk Prior: {pa_b:.2f})")
            
        st.markdown('<div class="section-header">Matriz de Resultados</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_score_matrix(sim["matrix"], ea, eb), use_container_width=True)

elif nav == "Métricas Globales":
    st.markdown('<div class="section-header">Rankings de Rendimiento</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    m_sel    = c1.selectbox("Métrica Analizada", metricas)
    cond_sel = c2.selectbox("Filtro Condición", ["General", "Local", "Visitante"])
    tipo_sel = c3.selectbox("Enfoque", ["Producción (A Favor)", "Concesión (En Contra)"])
    col_data = "Propio" if "A Favor" in tipo_sel else "Concedido"
    mask_cond = (df["Condicion"] == cond_sel) if cond_sel != "General" else df.index.notna()
    res = (df[mask_cond & (df["Métrica"] == m_sel)].groupby("Equipo")[col_data].mean().sort_values(ascending=False).reset_index())
    st.plotly_chart(go.Figure(go.Bar(x=res[col_data], y=res["Equipo"], orientation="h", marker_color=RED if col_data == "Propio" else GRAY)).update_layout(**PLOT, height=700), use_container_width=True)

elif nav == "Comparativa H2H":
    st.markdown('<div class="section-header">Head-to-Head (H2H)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    ea     = c1.selectbox("Escuadra A", equipos)
    cond_a = c1.selectbox(f"Condición de {ea}", ["General", "Local", "Visitante"])
    eb     = c2.selectbox("Escuadra B", equipos, index=min(1, len(equipos) - 1))
    cond_b = c2.selectbox(f"Condición de {eb}", ["General", "Local", "Visitante"])
    t1, t2 = st.tabs(["Comparativa Visual (Radar)", "Métricas Crudas"])
    with t1: st.plotly_chart(fig_radar_pro(df, ea, eb, cond_a, cond_b), use_container_width=True)
    with t2:
        df_a, df_b = df[df["Equipo"] == ea], df[df["Equipo"] == eb]
        if cond_a != "General": df_a = df_a[df_a["Condicion"] == cond_a]
        if cond_b != "General": df_b = df_b[df_b["Condicion"] == cond_b]
        s1, s2 = df_a.groupby("Métrica")[["Propio", "Concedido"]].mean().round(2), df_b.groupby("Métrica")[["Propio", "Concedido"]].mean().round(2)
        h2h_df = pd.DataFrame({f"{ea} ({cond_a[:3]}) Favor": s1["Propio"], f"{ea} ({cond_a[:3]}) Contra": s1["Concedido"], f"{eb} ({cond_b[:3]}) Favor": s2["Propio"], f"{eb} ({cond_b[:3]}) Contra": s2["Concedido"]}).dropna()
        st.dataframe(h2h_df, use_container_width=True)

elif nav == "Análisis de Rival":
    st.markdown('<div class="section-header">Evolución de Rendimiento</div>', unsafe_allow_html=True)
    eq_p, met_p = st.selectbox("Seleccionar Equipo", equipos), st.selectbox("Métrica a Evaluar", metricas)
    d_eq  = df[(df["Equipo"] == eq_p) & (df["Métrica"] == met_p)].sort_values("nFecha")
    if not d_eq.empty:
        st.plotly_chart(go.Figure([go.Bar(x=d_eq["Rival"], y=d_eq["Propio"], name="Generado", marker_color=RED), go.Bar(x=d_eq["Rival"], y=d_eq["Concedido"], name="Concedido", marker_color=GRAY)]).update_layout(**PLOT, barmode="group"), use_container_width=True)

elif nav == "Análisis de Estilos":
    st.markdown('<div class="section-header">Matriz de Estilos de Juego</div>', unsafe_allow_html=True)
    mo = "Goles esperados (xG)" if "Goles esperados (xG)" in df["Métrica"].values else "Tiros totales"
    if "Posesión de balón" in df["Métrica"].values:
        df_e = pd.DataFrame({"P": df[df["Métrica"] == "Posesión de balón"].groupby("Equipo")["Propio"].mean(), "O": df[df["Métrica"] == mo].groupby("Equipo")["Propio"].mean()}).dropna()
        mp, mo_m = df_e["P"].mean(), df_e["O"].mean()
        fig = go.Figure(go.Scatter(x=df_e["P"], y=df_e["O"], mode="markers+text", text=df_e.index, textposition="top center", marker=dict(size=14, color=RED, line=dict(width=2, color="#141417")), textfont=dict(family="Manrope", size=11, color="#ffffff")))
        fig.add_vline(x=mp, line=dict(color=GRAY, dash="dash", width=1))
        fig.add_hline(y=mo_m, line=dict(color=GRAY, dash="dash", width=1))
        st.plotly_chart(fig.update_layout(**PLOT, height=600, xaxis_title="Posesión Promedio (%)", yaxis_title=f"Volumen Ofensivo ({mo})"), use_container_width=True)
    else: st.warning("No hay datos de 'Posesión de balón' para procesar la matriz.")

elif nav == "Posiciones":
    st.markdown('<div class="section-header">Clasificación por Efectividad</div>', unsafe_allow_html=True)
    vista_tabla = st.selectbox("Escenario de Tabla", ["General", "Local", "Visitante"])
    t_dinamica  = calcular_tabla(df, vista_tabla)
    if not t_dinamica.empty:
        t_show = t_dinamica.reset_index()[["Pos", "Equipo", "PJ", "V", "E", "D", "GF", "GC", "PTS", "EFEC%"]].copy()
        t_show.columns = ["#", "Equipo", "PJ", "V", "E", "D", "GF", "GC", "PTS", "Efectividad %"]
        t_show["GF"], t_show["GC"], t_show["Efectividad %"] = t_show["GF"].astype(int), t_show["GC"].astype(int), t_show["Efectividad %"].round(1)
        st.dataframe(t_show.style.format({"Efectividad %": "{:.1f}%"}), use_container_width=True, hide_index=True)

elif nav == "ADN Táctico":
    st.markdown('<div class="section-header">ADN Táctico — Patrones por Equipo</div>', unsafe_allow_html=True)
    tab_todos, tab_equipo = st.tabs(["Vista de Liga", "Detalle por Equipo"])
    with tab_todos:
        if not adn_df.empty:
            adn_sorted = adn_df.sort_values("Posesion", ascending=False, na_position="last")
            cards_html = ""
            for eq, row in adn_sorted.iterrows():
                tags_html = render_tags_html(row["Tags"]) if isinstance(row["Tags"], list) else ""
                pos_str, tp_str = f"{row['Posesion']:.0f}%" if not np.isnan(row["Posesion"]) else "—", f"{row['TirosProp']:.1f}" if not np.isnan(row["TirosProp"]) else "—"
                xg_str, xgc_str = f"{row['xGProp']:.2f}" if not np.isnan(row["xGProp"]) else "—", f"{row['xGConc']:.2f}" if not np.isnan(row["xGConc"]) else "—"
                cards_html += f"""<div class="adn-card"><div class="adn-team-name">{eq}</div><div>{tags_html}</div><div style="margin-top:12px;display:flex;gap:28px;flex-wrap:wrap;"><div><div class="adn-perfil">Posesión media</div><div style="font-size:1.1rem;font-weight:800;color:#e0e0e0;">{pos_str}</div></div><div><div class="adn-perfil">Tiros / partido</div><div style="font-size:1.1rem;font-weight:800;color:#e0e0e0;">{tp_str}</div></div><div><div class="adn-perfil">xG generado</div><div style="font-size:1.1rem;font-weight:800;color:#ED1A3B;">{xg_str}</div></div><div><div class="adn-perfil">xG concedido</div><div style="font-size:1.1rem;font-weight:800;color:#888890;">{xgc_str}</div></div></div><div style="margin-top:10px;font-size:0.78rem;color:#555560;border-top:1px solid #1e1e24;padding-top:8px;">{row["Insight"]}</div></div>"""
            st.markdown(cards_html, unsafe_allow_html=True)
    with tab_equipo:
        eq_sel = st.selectbox("Seleccionar Equipo", equipos, key="adn_eq")
        if eq_sel in adn_df.index:
            row = adn_df.loc[eq_sel]
            tags_html = render_tags_html(row["Tags"]) if isinstance(row["Tags"], list) else ""
            st.markdown(f"""<div class="adn-card" style="margin-bottom:20px;"><div class="adn-team-name">{eq_sel}</div><div>{tags_html}</div><div class="tactica-insight" style="margin-top:14px;">{row["Insight"]}</div></div>""", unsafe_allow_html=True)
            mets_adn, labels_adn = ["Posesion", "TirosProp", "xGProp", "xGConc", "EficOfens"], ["Posesión", "Tiros Prop.", "xG Generado", "xG Concedido", "Efic. Ofens."]
            liga_means, liga_stds = adn_df[mets_adn].mean(), adn_df[mets_adn].std().replace(0, 1)
            eq_vals = [(row[m] - liga_means[m]) / liga_stds[m] if not np.isnan(row[m]) else 0.0 for m in mets_adn]
            eq_norm, lig_norm = [(v + 3) / 6 for v in eq_vals], [0.5] * len(mets_adn)
            fig_adn = go.Figure()
            fig_adn.add_trace(go.Scatterpolar(r=lig_norm + [lig_norm[0]], theta=labels_adn + [labels_adn[0]], fill="toself", name="Media Liga", line=dict(color=GRAY, dash="dot"), opacity=0.5))
            fig_adn.add_trace(go.Scatterpolar(r=eq_norm + [eq_norm[0]], theta=labels_adn + [labels_adn[0]], fill="toself", name=eq_sel, line=dict(color=RED, width=2)))
            layout_r = PLOT.copy()
            layout_r.update(height=400, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, showticklabels=False, gridcolor="#2a2a30", range=[0, 1]), angularaxis=dict(gridcolor="#2a2a30", linecolor="#2a2a30")), margin=dict(l=50, r=50, t=36, b=50), legend=dict(orientation="h", x=0.3, y=-0.1))
            st.plotly_chart(fig_adn.update_layout(**layout_r), use_container_width=True)

elif nav == "Rachas y Momentum":
    st.markdown('<div class="section-header">Rachas y Momentum</div>', unsafe_allow_html=True)
    if not rachas_df.empty:
        tab_liga, tab_equipo_m = st.tabs(["Ranking de Momentum", "Detalle por Equipo"])
        with tab_liga:
            st.plotly_chart(fig_momentum_ranking(rachas_df), use_container_width=True)
            rachas_sorted = rachas_df.sort_values("MomentumScore", ascending=False)
            cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-top:10px;">'
            for eq, row in rachas_sorted.iterrows():
                dots, delta_str = render_racha_dots(row["Ultimas6"]), f"+{row['DeltaXG']:.2f}" if row["DeltaXG"] >= 0 else f"{row['DeltaXG']:.2f}"
                delta_color = "#5ecf6b" if row["DeltaXG"] > 0.05 else ("#ED1A3B" if row["DeltaXG"] < -0.05 else "#888890")
                cards_html += f"""<div class="momentum-card"><div class="momentum-team">{eq}</div><div style="margin-bottom:8px;">{dots}</div><div style="display:flex;gap:18px;flex-wrap:wrap;"><div><div class="momentum-label">Forma</div><div class="{row['EstadoCls']}">{row["Estado"]}</div></div><div><div class="momentum-label">Pts últ 3</div><div style="font-size:1rem;font-weight:800;color:#e0e0e0;">{row["Pts3"]}</div></div><div><div class="momentum-label">Δ xG</div><div style="font-size:1rem;font-weight:800;color:{delta_color};">{delta_str}</div></div></div></div>"""
            st.markdown(cards_html + "</div>", unsafe_allow_html=True)
        with tab_equipo_m:
            eq_m = st.selectbox("Seleccionar Equipo", equipos, key="racha_eq")
            if eq_m in rachas_df.index:
                row_m = rachas_df.loc[eq_m]
                dots, delta_str = render_racha_dots(row_m["Ultimas6"]), f"+{row_m['DeltaXG']:.2f}" if row_m["DeltaXG"] >= 0 else f"{row_m['DeltaXG']:.2f}"
                delta_color = "#5ecf6b" if row_m["DeltaXG"] > 0.05 else ("#ED1A3B" if row_m["DeltaXG"] < -0.05 else "#888890")
                st.markdown(f"""<div class="momentum-card" style="margin-bottom:20px;"><div class="momentum-team">{eq_m}</div><div class="momentum-label">Racha completa</div><div style="margin:8px 0 14px;">{"".join(f'<span class="racha-dot {"racha-v" if r=="V" else ("racha-e" if r=="E" else "racha-d")}">{r}</span>' for r in row_m["Resultados"])}</div><div style="display:flex;gap:30px;flex-wrap:wrap;"><div><div class="momentum-label">Estado</div><div class="{row_m["EstadoCls"]}">{row_m["Estado"]}</div></div><div><div class="momentum-label">xG reciente</div><div style="font-size:1.1rem;font-weight:800;color:#ED1A3B;">{row_m["xGRec"]:.2f}</div></div><div><div class="momentum-label">Tendencia xG</div><div style="font-size:1.1rem;font-weight:800;color:{delta_color};">{delta_str}</div></div></div></div>""", unsafe_allow_html=True)
                st.markdown('<div class="section-header">Evolución Temporal</div>', unsafe_allow_html=True)
                st.plotly_chart(fig_momentum_timeline(df, eq_m), use_container_width=True)
