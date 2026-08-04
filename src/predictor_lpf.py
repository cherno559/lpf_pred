"""
Plataforma de Rendimiento LPF 2026 - Completa (Etapas 1, 2, Value Betting y Guion Técnico Nativo)
"""
import re, os, math, textwrap
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILOS
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LPF Analytics | Rendimiento",
    page_icon="⚽",
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
# PARÁMETROS DEL MOTOR Y JERARQUÍAS
# ──────────────────────────────────────────────────────────────────────
W_XG = 0.60
K_SHRINK = 6.0
K_PRIOR  = 5.0
PRIOR_ATK_SCALE = 0.40
PRIOR_DEF_SCALE = 0.30
DC_RHO = -0.10
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 3, 1.8, 1.0
PESO_HISTORICO = 0.4
LAM_MIN, LAM_MAX = 0.30, 5.00

# ──────────────────────────────────────────────────────────────────────
# JERARQUÍAS DE MERCADO (Clausura 2026 - Actualizado con Damping)
# Media de liga: 33.76 M€ = 1.000
# ──────────────────────────────────────────────────────────────────────
JERARQUIA_EQUIPOS = {
    "River Plate": 1.149,
    "Boca Juniors": 1.126,
    "Racing Club": 1.059,
    "Rosario Central": 1.037,
    "Estudiantes de La Plata": 1.027,
    "Talleres": 1.018,
    "San Lorenzo": 1.013,
    "Lanús": 1.010,
    "Argentinos Juniors": 1.006,
    "Independiente": 1.006,
    "Tigre": 1.005,
    "Vélez Sarsfield": 1.002,
    "Independiente Rivadavia": 1.001,
    "Platense": 0.996,
    "Newell's Old Boys": 0.992,
    "Belgrano": 0.989,
    "Gimnasia y Esgrima La Plata": 0.988,
    "Defensa y Justicia": 0.977,
    "Huracán": 0.977,
    "Instituto": 0.977,
    "Unión": 0.974,
    "Barracas Central": 0.971,
    "Banfield": 0.969,
    "Sarmiento": 0.967,
    "Gimnasia de Mendoza": 0.965,
    "Atlético Tucumán": 0.964,
    "Deportivo Riestra": 0.962,
    "Central Córdoba": 0.958,
    "Aldosivi": 0.957,
    "Estudiantes de Río Cuarto": 0.955
}

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
def cargar_excel(archivos_seleccionados: list):
    res = {}
    for ruta_archivo in archivos_seleccionados:
        if not os.path.exists(ruta_archivo):
            continue
        
        nombre_torneo = os.path.basename(ruta_archivo).split('.')[0]
        categoria = "Histórico" if "historico" in ruta_archivo else "Actual"
        
        if ruta_archivo.endswith(('.xlsx', '.xls')):
            xl = pd.ExcelFile(ruta_archivo, engine="openpyxl")
            for hoja in xl.sheet_names:
                if re.search(r"fecha\s*\d+|octavo|cuarto|semi|final|playoff", hoja, re.IGNORECASE):
                    df = pd.read_excel(xl, sheet_name=hoja, header=None)
                    res[f"{categoria}||{nombre_torneo}||{hoja}"] = _procesar_dataframe(df)
        elif ruta_archivo.endswith('.csv'):
            hoja = nombre_torneo.split(" - ")[-1] if " - " in nombre_torneo else nombre_torneo
            if re.search(r"fecha\s*\d+|octavo|cuarto|semi|final|playoff", hoja, re.IGNORECASE):
                df = pd.read_csv(ruta_archivo, header=None)
                res[f"{categoria}||{nombre_torneo}||{hoja}"] = _procesar_dataframe(df)
    return res

def construir_df(datos: dict) -> pd.DataFrame:
    filas = []
    MAX_FECHAS_REGULARES = 16 
    current_playoff_nf = MAX_FECHAS_REGULARES + 1

    for clave, partidos in datos.items():
        if "||" in clave:
            partes = clave.split("||")
            if len(partes) == 3:
                categoria, torneo, fecha = partes
            else:
                categoria, torneo, fecha = "Actual", partes[0], partes[1]
        else:
            categoria, torneo, fecha = "Actual", "General", clave
            
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
                base = {"nFecha": nf, "Fase": fase, "Métrica": met, "Torneo": torneo, "Categoria": categoria}
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
    
    # ETAPA 2: Aplicamos el factor de jerarquía de mercado
    for eq in tabla.index:
        nombre_eq = tabla.loc[eq, "Equipo"]
        factor = JERARQUIA_EQUIPOS.get(nombre_eq, 1.0)
        tabla.loc[eq, "prior_atk"] = tabla.loc[eq, "prior_atk"] * factor

    return tabla.set_index("Equipo")

def _get_prior(tabla: pd.DataFrame, eq: str):
    if tabla is None or eq not in tabla.index:
        return 1.0, 1.0
    return float(tabla.loc[eq, "prior_atk"]), float(tabla.loc[eq, "prior_def"])

def _adjusted_rate(d_spec, metrica, col, max_fecha_torneo, tabla, is_attack):
    df_m = d_spec[d_spec["Métrica"] == metrica]
    if df_m.empty:
        return np.nan
    fechas    = df_m["nFecha"].values
    categoria = df_m["Categoria"].values
    valores   = df_m[col].values
    rivales   = df_m["Rival"].values
    valores_ajustados = []
    
    for v, r in zip(valores, rivales):
        pa_r, pd_r = _get_prior(tabla, r)
        adj = v / pd_r if (is_attack and pd_r > 0) else v / pa_r if (not is_attack and pa_r > 0) else v
        valores_ajustados.append(adj)
        
    w = np.where(categoria == "Histórico", PESO_HISTORICO, 
         np.where(fechas >= (max_fecha_torneo - N_RECENCIA + 1), PESO_RECIENTE, PESO_NORMAL))
         
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
    df_actual = df[df["Categoria"] == "Actual"]
    if not df_actual.empty:
        max_fecha_torneo = int(df_actual["nFecha"].max())
    else:
        max_fecha_torneo = int(df["nFecha"].max())
        
    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")
    aa, da, na = _strength(df, eq_a, ca, l, max_fecha_torneo, tabla)
    ab, db, nb = _strength(df, eq_b, cb, l, max_fecha_torneo, tabla)
    
    la = (l["ref_home"] if ca == "Local" else l["ref_away"]) * aa * db
    lb = (l["ref_home"] if cb == "Local" else l["ref_away"]) * ab * da

    # --- ETAPA 2: MODIFICADORES POR CHOQUE DE ESTILOS ---
    adn_temp = calcular_adn_tactico(df)
    if not adn_temp.empty and eq_a in adn_temp.index and eq_b in adn_temp.index:
        tags_a = set(t for t, _ in adn_temp.loc[eq_a, "Tags"]) if isinstance(adn_temp.loc[eq_a, "Tags"], list) else set()
        tags_b = set(t for t, _ in adn_temp.loc[eq_b, "Tags"]) if isinstance(adn_temp.loc[eq_b, "Tags"], list) else set()
        
        if "POSESIÓN DOMINANTE" in tags_a and "BLOQUE BAJO" in tags_b:
            la += 0.12  
            lb -= 0.08  
        if "DÉFICIT DEFENSIVO" in tags_a:
            lb += 0.10
        if "DÉFICIT DEFENSIVO" in tags_b:
            la += 0.10
    # ----------------------------------------------------

    return (round(float(np.clip(la, LAM_MIN, LAM_MAX)), 3),
            round(float(np.clip(lb, LAM_MIN, LAM_MAX)), 3))

def proyectar_metrica(df, eq_a, eq_b, metrica, es_loc, tabla):
    df_m = df[df["Métrica"] == metrica]
    if df_m.empty:
        return 0.0, 0.0
    
    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")
    
    # 1. Promedio ofensivo propio del equipo A y B según condición
    d_a = df_m[(df_m["Equipo"] == eq_a) & (df_m["Condicion"] == ca)]
    base_a = d_a["Propio"].mean() if not d_a.empty else df_m["Propio"].mean()
    
    d_b = df_m[(df_m["Equipo"] == eq_b) & (df_m["Condicion"] == cb)]
    base_b = d_b["Propio"].mean() if not d_b.empty else df_m["Propio"].mean()
    
    # 2. Promedio de tiros CONCEDIDOS por el rival
    d_b_conc = df_m[(df_m["Equipo"] == eq_b) & (df_m["Condicion"] == cb)]
    concede_b = d_b_conc["Concedido"].mean() if not d_b_conc.empty else df_m["Concedido"].mean()
    
    d_a_conc = df_m[(df_m["Equipo"] == eq_a) & (df_m["Condicion"] == ca)]
    concede_a = d_a_conc["Concedido"].mean() if not d_a_conc.empty else df_m["Concedido"].mean()
    
    # Promedio general de la liga
    media_liga = df_m["Propio"].mean() if not df_m.empty else 1.0
    if media_liga == 0: media_liga = 1.0

    # 3. Factor defensivo con SUAVIZADO (damping) para evitar inflar las métricas
    factor_crudo_b = concede_b / media_liga if media_liga > 0 else 1.0
    factor_def_b = 1.0 + (factor_crudo_b - 1.0) * 0.5  # Suavizado al 50%

    factor_crudo_a = concede_a / media_liga if media_liga > 0 else 1.0
    factor_def_a = 1.0 + (factor_crudo_a - 1.0) * 0.5  # Suavizado al 50%

    # 4. Proyección final con regresión a la media
    val_a = base_a * factor_def_b
    val_b = base_b * factor_def_a
    
    return max(0.0, float(val_a)), max(0.0, float(val_b))

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

    # FIX: textwrap.dedent() evita que Streamlit interprete la indentación de
    # esta función (4 espacios, por estar dentro del cuerpo de la función)
    # como un bloque de código Markdown en vez de HTML.
    return textwrap.dedent(f"""
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
    </div>""")

# ══════════════════════════════════════════════════════════════════════════════
#  ★  RACHAS Y MOMENTUM
# ══════════════════════════════════════════════════════════════════════════════
def calcular_rachas(df: pd.DataFrame) -> pd.DataFrame:
    dr = df[df["Métrica"] == "Resultado"].copy()
    dx = df[df["Métrica"] == "xG_Estimado"].copy()
    
    # Creamos una columna de orden lógico (Histórico primero = 0, Actual = 1)
    dr["Orden_Cat"] = np.where(dr["Categoria"] == "Histórico", 0, 1)
    dx["Orden_Cat"] = np.where(dx["Categoria"] == "Histórico", 0, 1)
    
    equipos = sorted(dr["Equipo"].unique())
    rows = []

    for eq in equipos:
        # Ordenamos primero por Categoría y después por Fecha
        d_eq = dr[dr["Equipo"] == eq].sort_values(["Orden_Cat", "nFecha"])
        if d_eq.empty: continue

        resultados = []
        for _, row in d_eq.iterrows():
            if row["Propio"] > row["Concedido"]: resultados.append("V")
            elif row["Propio"] == row["Concedido"]: resultados.append("E")
            else: resultados.append("D")

        ultimas6 = resultados[-6:]
        pts6 = sum(3 if r == "V" else (1 if r == "E" else 0) for r in ultimas6)
        pts3 = sum(3 if r == "V" else (1 if r == "E" else 0) for r in resultados[-3:])

        # También corregimos el ordenamiento acá
        dxg = dx[dx["Equipo"] == eq].sort_values(["Orden_Cat", "nFecha"])
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
    dr = df[(df["Equipo"] == equipo) & (df["Métrica"] == "Resultado")].copy()
    dx = df[(df["Equipo"] == equipo) & (df["Métrica"] == "xG_Estimado")].copy()
    
    if dr.empty: return go.Figure()

    # Aplicamos el mismo parche de ordenamiento para el gráfico temporal
    dr["Orden_Cat"] = np.where(dr["Categoria"] == "Histórico", 0, 1)
    dx["Orden_Cat"] = np.where(dx["Categoria"] == "Histórico", 0, 1)
    
    dr = dr.sort_values(["Orden_Cat", "nFecha"])
    dx = dx.sort_values(["Orden_Cat", "nFecha"])

    # Generamos etiquetas dinámicas para el Eje X para no repetir los números (Ej: APE-14, CLA-1)
    fechas_labels = dr.apply(lambda r: f"{r['Torneo'][:3].upper()}-{r['nFecha']}", axis=1).tolist()
    
    pts_parciales = []
    for _, row in dr.iterrows():
        if row["Propio"] > row["Concedido"]: pts_parciales.append(3)
        elif row["Propio"] == row["Concedido"]: pts_parciales.append(1)
        else: pts_parciales.append(0)
        
    xg_vals = dx["Propio"].values
    
    # Alinear longitudes de los datos por seguridad
    min_len = min(len(fechas_labels), len(xg_vals))
    fechas_labels = fechas_labels[:min_len]
    pts_parciales = pts_parciales[:min_len]
    xg_vals = xg_vals[:min_len]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=fechas_labels, y=pts_parciales, name="Pts/Fecha", marker_color=[RED if p == 3 else ("#888890" if p == 1 else "#1e1e24") for p in pts_parciales], yaxis="y1"))
    fig.add_trace(go.Scatter(x=fechas_labels, y=xg_vals, name="xG Propio", mode="lines+markers", line=dict(color=WHITE, width=2), marker=dict(size=6), yaxis="y2"))
    fig.update_layout(**PLOT, height=320, yaxis=dict(title="Puntos", showgrid=False, color="#555560"), yaxis2=dict(title="xG", overlaying="y", side="right", showgrid=False, color="#888890"), legend=dict(orientation="h", x=0, y=1.12), xaxis=dict(title="Torneo y Fecha", color="#555560", tickmode="linear"))
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
    
    rutas_base = {
        "Histórico": "data/historico",
        "Actual": "data/actual"
    }
    
    opciones_archivos = {}
    for categoria, ruta_carpeta in rutas_base.items():
        if os.path.exists(ruta_carpeta):
            for archivo in os.listdir(ruta_carpeta):
                if archivo.endswith(('.xlsx', '.xls', '.csv')):
                    nombre_amigable = f"{categoria} | {archivo}"
                    opciones_archivos[nombre_amigable] = os.path.join(ruta_carpeta, archivo)
    
    opciones_disponibles = list(opciones_archivos.keys())
    defaults = [opt for opt in opciones_disponibles if "clausura" in opt.lower() or "apertura" in opt.lower()]
    
    torneos_seleccionados_nombres = st.multiselect(
        "Bases de Datos a Utilizar:",
        options=opciones_disponibles,
        default=defaults if defaults else (opciones_disponibles[:1] if opciones_disponibles else [])
    )
    
    archivos_a_cargar = [opciones_archivos[nombre] for nombre in torneos_seleccionados_nombres]

    st.markdown("<br>", unsafe_allow_html=True)
    nav = st.radio(
        "MÓDULOS DE ANÁLISIS",
        [
            "Predicción de Partidos",
            "Simulador de Jornada",
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

datos    = cargar_excel(archivos_a_cargar)
df       = construir_df(datos)

if not opciones_disponibles:
    st.error(
        "⚠️ **No se encontró ninguna base de datos.**\n\n"
        "Este sistema espera los archivos Excel en:\n"
        "- `data/actual/` (temporada en curso, ej. `clausura26.xlsx`)\n"
        "- `data/historico/` (temporadas pasadas, ej. `apertura26.xlsx`)\n\n"
        "Creá esas carpetas junto a este script y colocá ahí tus archivos."
    )
    st.stop()

if df.empty:
    st.warning("⚠️ Elegí al menos una base de datos en la barra lateral para continuar.")
    st.stop()

torneos_cargados = list(df["Torneo"].unique())
if len(torneos_cargados) > 1 and nav not in ["Predicción de Partidos", "Simulador de Jornada"]:
    st.sidebar.markdown("<hr style='border-color:#2a2a30; margin-top: 10px;'>", unsafe_allow_html=True)
    torneo_analisis = st.sidebar.selectbox(
        "📊 Ver estadísticas de:", 
        ["Todos los seleccionados"] + torneos_cargados
    )
    if torneo_analisis != "Todos los seleccionados":
        df = df[df["Torneo"] == torneo_analisis]

tabla    = calcular_tabla(df, "General")
equipos  = sorted(df["Equipo"].unique())
metricas = sorted(df["Métrica"].unique())

@st.cache_data(ttl=120, show_spinner=False)
def _cached_adn(dataframe): return calcular_adn_tactico(dataframe)
@st.cache_data(ttl=120, show_spinner=False)
def _cached_rachas(dataframe): return calcular_rachas(dataframe)

adn_df    = _cached_adn(df)
rachas_df = _cached_rachas(df)

_ultima_actualizacion = max(
    (os.path.getmtime(a) for a in archivos_a_cargar if os.path.exists(a)),
    default=None
)
_fecha_datos = (
    datetime.fromtimestamp(_ultima_actualizacion).strftime("%d/%m/%Y %H:%M")
    if _ultima_actualizacion else "sin datos cargados"
)

st.markdown(f"""
<div class="hero-banner">
    <div class="hero-subtitle">Liga Profesional de Fútbol · Argentina 2026</div>
    <h1 class="hero-title">PLATAFORMA DE RENDIMIENTO</h1>
    <div style="color:#888890;font-size:0.8rem;margin-top:8px;">
        📅 Datos actualizados: {_fecha_datos} &nbsp;|&nbsp; 🗂️ Fuentes activas: {len(archivos_a_cargar)}
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("ℹ️ Metodología del modelo"):
    st.markdown("""
**Motor de predicción:** distribución de Poisson bivariada con ajuste
Dixon-Coles (`ρ`) para corregir la subestimación de empates y resultados
bajos (0-0, 1-0, 0-1, 1-1), típica del Poisson independiente puro.

**Fuerza de ataque/defensa (`λ`):** se calcula combinando el rendimiento
observado del equipo (goles reales + xG estimado a partir de tiros y
ocasiones claras) con un *prior* bayesiano basado en la jerarquía de
mercado del plantel — así un equipo con pocos partidos jugados no queda
sub o sobre-representado por una muestra chica.

**Ajustes de estilo:** el modelo suma modificadores cuando detecta un
choque de perfiles tácticos claro (ej. posesión dominante vs. bloque
bajo, o déficit defensivo marcado).

**Cuotas "Real" vs. "Casa":** la columna "Real" es la probabilidad pura
del modelo convertida a cuota (1 / probabilidad); "Casa" le aplica un
margen (*overround*) típico de casa de apuestas, solo a fines
comparativos/educativos.

⚠️ *Esta es una herramienta de análisis estadístico, no una recomendación
de apuesta. Los resultados deportivos tienen variables que ningún modelo
captura por completo (lesiones de último momento, decisiones arbitrales,
clima, etc.). Jugá con responsabilidad.*
""")

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
        
        # --- CÁLCULO DE CUOTAS: REAL vs CASA (Realidad LPF) ---
        margen = 1.11
        
        r_loc = 1 / sim['victoria'] if sim['victoria'] > 0 else 0.0
        r_emp = 1 / sim['empate']   if sim['empate'] > 0   else 0.0
        r_vis = 1 / sim['derrota']  if sim['derrota'] > 0  else 0.0
        
        m_loc = margen if sim['victoria'] >= 0.45 else margen + 0.02
        m_emp = margen + 0.04
        m_vis = margen if sim['derrota'] >= 0.45 else margen + 0.02
        
        c_loc = 1 / (sim['victoria'] * m_loc) if sim['victoria'] > 0 else 0.0
        c_emp = 1 / (sim['empate'] * m_emp)   if sim['empate'] > 0   else 0.0
        c_vis = 1 / (sim['derrota'] * m_vis)  if sim['derrota'] > 0  else 0.0
        
        st.markdown(f"""
        <div class="broadcast-board">
            <div class="team-block home">
                <div class="t-name">{ea}</div>
                <div class="t-prob">{sim['victoria']*100:.1f}%</div>
                <div class="t-label">Victoria Local</div>
                <div style="display:flex; justify-content:center; gap:8px; margin-top:12px;">
                    <div style="font-size:0.75rem; color:#a0a0a8; background:#111115; padding:4px 8px; border-radius:4px; border: 1px solid #2a2a35;">
                        ⚖️ REAL: {r_loc:.2f}
                    </div>
                    <div style="font-size:0.75rem; color:#cfb45e; background:#2a2a1a; padding:4px 8px; border-radius:4px; border: 1px solid #cfb45e;">
                        🏦 CASA: {c_loc:.2f}
                    </div>
                </div>
            </div>
            <div class="draw-block">
                <div class="t-label" style="margin-bottom:5px;">Empate</div>
                <div class="draw-prob">{sim['empate']*100:.1f}%</div>
                <div style="display:flex; justify-content:center; gap:8px; margin-top:12px;">
                    <div style="font-size:0.75rem; color:#a0a0a8; background:#111115; padding:4px 8px; border-radius:4px; border: 1px solid #2a2a35;">
                        ⚖️ REAL: {r_emp:.2f}
                    </div>
                    <div style="font-size:0.75rem; color:#cfb45e; background:#2a2a1a; padding:4px 8px; border-radius:4px; border: 1px solid #cfb45e;">
                        🏦 CASA: {c_emp:.2f}
                    </div>
                </div>
            </div>
            <div class="team-block away">
                <div class="t-name">{eb}</div>
                <div class="t-prob" style="color:#ffffff;">{sim['derrota']*100:.1f}%</div>
                <div class="t-label">Victoria Visitante</div>
                <div style="display:flex; justify-content:center; gap:8px; margin-top:12px;">
                    <div style="font-size:0.75rem; color:#a0a0a8; background:#111115; padding:4px 8px; border-radius:4px; border: 1px solid #2a2a35;">
                        ⚖️ REAL: {r_vis:.2f}
                    </div>
                    <div style="font-size:0.75rem; color:#cfb45e; background:#2a2a1a; padding:4px 8px; border-radius:4px; border: 1px solid #cfb45e;">
                        🏦 CASA: {c_vis:.2f}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">Marcadores Más Probables</div>', unsafe_allow_html=True)
        st.markdown(top3_marcadores(sim["matrix"], ea, eb), unsafe_allow_html=True)
        ctx = contexto_tactica_clash(adn_df, ea, eb)
        if ctx: st.markdown(ctx, unsafe_allow_html=True)

      # --- GUION TÉCNICO Y PROYECCIÓN DE MÉTRICAS (Separado por Equipo) ---
        tiros_a, tiros_b = proyectar_metrica(df, ea, eb, "Tiros totales", loc, tabla)
        arco_a, arco_b   = proyectar_metrica(df, ea, eb, "Tiros al arco", loc, tabla)
        ocas_a, ocas_b   = proyectar_metrica(df, ea, eb, "Ocasiones claras", loc, tabla)
        pos_a, pos_b     = proyectar_metrica(df, ea, eb, "Posesión de balón", loc, tabla)
        
        tot_pos = pos_a + pos_b
        if tot_pos > 0:
            pos_a = (pos_a / tot_pos) * 100
            pos_b = (pos_b / tot_pos) * 100
        else:
            pos_a, pos_b = 50.0, 50.0

        flat = [(sim["matrix"][i, j], i, j) for i in range(sim["matrix"].shape[0]) for j in range(sim["matrix"].shape[1])]
        flat.sort(reverse=True)
        top_score_prob, i_top, j_top = flat[0]
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📝 GUION Y PROYECCIÓN TÉCNICA DE RENDIMIENTO")
        
        with st.container():
            st.info("⚡ ESTIMACIÓN MATEMÁTICA DE MÉTRICAS CLAVE PARA EL ENCUENTRO")
            
            # Dos columnas principales: Izquierda Local, Derecha Visitante
            col_local, col_vis = st.columns(2)
            
            with col_local:
                st.markdown(f"<h4 style='color: #ED1A3B; border-bottom: 2px solid #ED1A3B; padding-bottom: 5px;'>🏠 {ea} (Local)</h4>", unsafe_allow_html=True)
                st.metric("Tiros Totales Proyectados", f"{tiros_a:.1f}")
                st.metric("Tiros al Arco Proyectados", f"{arco_a:.1f}")
                st.metric("Ocasiones Claras", f"{ocas_a:.1f}")
                st.metric("Goles Esperados (xG)", f"{la:.2f}")
                st.metric("Posesión Estimada", f"{pos_a:.0f}%")
                
            with col_vis:
                st.markdown(f"<h4 style='color: #ffffff; border-bottom: 2px solid #2a2a35; padding-bottom: 5px;'>✈️ {eb} (Visitante)</h4>", unsafe_allow_html=True)
                st.metric("Tiros Totales Proyectados", f"{tiros_b:.1f}")
                st.metric("Tiros al Arco Proyectados", f"{arco_b:.1f}")
                st.metric("Ocasiones Claras", f"{ocas_b:.1f}")
                st.metric("Goles Esperados (xG)", f"{lb:.2f}")
                st.metric("Posesión Estimada", f"{pos_b:.0f}%")

            st.markdown(f"""
            <p style="color: #a0a0a8; font-size: 0.85rem; margin-top: 15px; margin-bottom: 0; line-height: 1.5; border-top: 1px solid #2a2a35; padding-top: 12px;">
                <strong>💡 Lectura analítica:</strong> El modelo proyecta un desarrollo donde el marcador más probable es el <strong>{i_top}-{j_top}</strong> ({top_score_prob*100:.1f}%). Las tasas de remates y conversión esperadas reflejan el impacto de los bloques defensivos y las jerarquías de plantel configuradas.
            </p>
            """, unsafe_allow_html=True)

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
            st.code(f"λ {ea}: {la:.3f} (Atk Prior: {pa_a:.2f})\nλ {eb}: {lb:.3f} (Atk Prior: {pd_b:.2f})")
            
        st.markdown('<div class="section-header">Matriz de Resultados</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_score_matrix(sim["matrix"], ea, eb), use_container_width=True)

elif nav == "Simulador de Jornada":
    st.markdown('<div class="section-header">Simulador de Jornada Automático</div>', unsafe_allow_html=True)
    
    # 1. Filtramos solo los datos del Apertura (Histórico)
    df_historico = df[df["Categoria"] == "Histórico"]
    
    if df_historico.empty:
        st.warning("⚠️ No hay datos históricos (Apertura) cargados para invertir el fixture. Revisá la selección en la barra lateral.")
    else:
        # 2. Obtenemos las fechas disponibles
        fechas_disponibles = sorted(df_historico["nFecha"].unique())
        
        c1, c2 = st.columns([1, 3])
        jornada_elegida = c1.selectbox("Seleccionar Fecha a Simular:", fechas_disponibles)
        
        # 3. Filtramos los partidos de esa fecha exacta
        df_fecha_apertura = df_historico[
            (df_historico["nFecha"] == jornada_elegida) & 
            (df_historico["Condicion"] == "Local") &
            (df_historico["Métrica"] == "Resultado")
        ].drop_duplicates(subset=["Equipo", "Rival"])
        
        # 4. Invertimos las localías para el Clausura
        cruces_validos = pd.DataFrame({
            "Local": df_fecha_apertura["Rival"].values,      
            "Visitante": df_fecha_apertura["Equipo"].values  
        })
        
        c2.write(f"**Partidos de la Fecha {jornada_elegida}**")
        c2.dataframe(cruces_validos, hide_index=True, use_container_width=True)
        
        if st.button("SIMULAR JORNADA COMPLETA"):
            if len(cruces_validos) == 0:
                st.warning("⚠️ No hay partidos para simular.")
            else:
                resultados_jornada = []
                
                with st.spinner(f"Procesando simulaciones matemáticas para la Fecha {jornada_elegida}..."):
                    for idx, row in cruces_validos.iterrows():
                        ea = row["Local"]
                        eb = row["Visitante"]
                        
                        if ea == eb: continue
                            
                        # Cálculos matemáticos del motor
                        la, lb = calcular_lambdas(df, ea, eb, True, tabla)
                        sim = montecarlo(la, lb) 
                        
                        tiros_a, tiros_b = proyectar_metrica(df, ea, eb, "Tiros totales", True, tabla)
                        arco_a, arco_b   = proyectar_metrica(df, ea, eb, "Tiros al arco", True, tabla)
                        ocas_a, ocas_b   = proyectar_metrica(df, ea, eb, "Ocasiones claras", True, tabla)
                        pos_a, pos_b     = proyectar_metrica(df, ea, eb, "Posesión de balón", True, tabla)
                        
                        tot_pos = pos_a + pos_b
                        if tot_pos > 0:
                            pos_a = (pos_a / tot_pos) * 100
                            pos_b = (pos_b / tot_pos) * 100
                        else:
                            pos_a, pos_b = 50.0, 50.0
                            
                        # Guardamos resultados del Local
                        resultados_jornada.append({
                            "Equipo": ea, "Condición": "Local", "Rival": eb,
                            "Prob_Victoria": sim["victoria"],
                            "xG_Favor": la, "xG_Contra": lb, "Tiros_Favor": tiros_a, "Tiros_Contra": tiros_b,
                            "Arco_Favor": arco_a, "Arco_Contra": arco_b, "Ocasiones_Favor": ocas_a, "Ocasiones_Contra": ocas_b,
                            "Posesion": pos_a
                        })
                        
                        # Guardamos resultados del Visitante
                        resultados_jornada.append({
                            "Equipo": eb, "Condición": "Visitante", "Rival": ea,
                            "Prob_Victoria": sim["derrota"],
                            "xG_Favor": lb, "xG_Contra": la, "Tiros_Favor": tiros_b, "Tiros_Contra": tiros_a,
                            "Arco_Favor": arco_b, "Arco_Contra": arco_a, "Ocasiones_Favor": ocas_b, "Ocasiones_Contra": ocas_a,
                            "Posesion": pos_b
                        })
                
                df_res = pd.DataFrame(resultados_jornada)
                
                # Índice para el arquero (Relación entre tiros recibidos al arco y xG concedido)
                df_res["Indice_Arquero"] = df_res["Arco_Contra"] / (df_res["xG_Contra"] + 0.5)
                
                # Función auxiliar para formatear tablas y poner la estrella a los 5 primeros
                def format_ranking(df_temp, sort_col, ascending, cols_to_show, rename_dict=None):
                    temp = df_temp.sort_values(by=sort_col, ascending=ascending).reset_index(drop=True)
                    temp["Pos"] = temp.index + 1
                    # Agregar la estrella a los primeros 5
                    temp["Equipo"] = temp.apply(lambda r: f"⭐ {r['Equipo']}" if r["Pos"] <= 5 else r["Equipo"], axis=1)
                    # Reordenar las columnas
                    final_cols = ["Pos", "Equipo"] + [c for c in cols_to_show if c != "Equipo"]
                    temp = temp[final_cols]
                    if rename_dict:
                        temp = temp.rename(columns=rename_dict)
                    return temp

                st.markdown('<div class="section-header">📊 Rankings de la Jornada (Clasificación General)</div>', unsafe_allow_html=True)
                
                # Creamos las pestañas (Tabs) para separar cada análisis
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📈 Prob. Victoria", "🧤 Mejor Arquero", "🛡️ Mejor Defensa", "🧭 Mejor Medio", "⚔️ Mejor Delantera"
                ])
                
                with tab1:
                    st.markdown("### 📈 Probabilidad de Victoria")
                    st.caption("Ordenado por la probabilidad matemática de ganar el encuentro.")
                    df_vic = format_ranking(df_res, "Prob_Victoria", False, 
                                            ["Prob_Victoria", "xG_Favor", "xG_Contra", "Condición", "Rival"],
                                            {"Prob_Victoria": "Prob. de Ganar"})
                    st.dataframe(df_vic.style.format({"Prob. de Ganar": "{:.1%}", "xG_Favor": "{:.2f}", "xG_Contra": "{:.2f}"}), 
                                 hide_index=True, use_container_width=True)

                with tab2:
                    st.markdown("### 🧤 Posible Mejor Arquero")
                    st.caption("Ordenado por el 'Índice Arquero': premia atajadas proyectadas en relación a la calidad de los tiros (xG).")
                    df_arq = format_ranking(df_res, "Indice_Arquero", False, 
                                            ["Indice_Arquero", "Arco_Contra", "xG_Contra", "Rival"],
                                            {"Indice_Arquero": "Índice", "Arco_Contra": "Tiros Arco en Contra", "xG_Contra": "xG Concedido"})
                    st.dataframe(df_arq.style.format({"Índice": "{:.2f}", "Tiros Arco en Contra": "{:.1f}", "xG Concedido": "{:.2f}"}), 
                                 hide_index=True, use_container_width=True)

                with tab3:
                    st.markdown("### 🛡️ Posible Mejor Defensa")
                    st.caption("Ordenado por solidez: los que menos Goles Esperados (xG) y tiros van a conceder.")
                    df_def = format_ranking(df_res, "xG_Contra", True, 
                                            ["xG_Contra", "Ocasiones_Contra", "Tiros_Contra", "Rival"],
                                            {"xG_Contra": "xG Concedido", "Ocasiones_Contra": "Ocasiones Concedidas", "Tiros_Contra": "Tiros Concedidos"})
                    st.dataframe(df_def.style.format({"xG Concedido": "{:.2f}", "Ocasiones Concedidas": "{:.1f}", "Tiros Concedidos": "{:.1f}"}), 
                                 hide_index=True, use_container_width=True)

                with tab4:
                    st.markdown("### 🧭 Posible Mejor Mediocampo")
                    st.caption("Ordenado por proyección de dominio territorial (Posesión).")
                    df_med = format_ranking(df_res, "Posesion", False, 
                                            ["Posesion", "xG_Favor", "xG_Contra", "Rival"],
                                            {"Posesion": "Posesión %", "xG_Favor": "xG Generado", "xG_Contra": "xG Concedido"})
                    st.dataframe(df_med.style.format({"Posesión %": "{:.1f}%", "xG Generado": "{:.2f}", "xG Concedido": "{:.2f}"}), 
                                 hide_index=True, use_container_width=True)

                with tab5:
                    st.markdown("### ⚔️ Posible Mejor Delantera")
                    st.caption("Ordenado por volumen y peligro ofensivo (xG a favor).")
                    df_del = format_ranking(df_res, "xG_Favor", False, 
                                            ["xG_Favor", "Ocasiones_Favor", "Arco_Favor", "Rival"],
                                            {"xG_Favor": "xG Generado", "Ocasiones_Favor": "Ocasiones Creadas", "Arco_Favor": "Tiros al Arco a Favor"})
                    st.dataframe(df_del.style.format({"xG Generado": "{:.2f}", "Ocasiones Creadas": "{:.1f}", "Tiros al Arco a Favor": "{:.1f}"}), 
                                 hide_index=True, use_container_width=True)

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
                cards_html += f"""<div class="momentum-card"><div class="momentum-team">{eq}</div><div style="margin-bottom:8px;">{dots}</div><div style="display:flex;gap:18px;flex-wrap:wrap;"><div><div class="momentum-label">Forma</div><div class="{row['EstadoCls']}">{row["Estado"]}</div></div><div><div class="momentum-label">Pts últ 3</div><div style="font-size:1rem;font-weight:800;color:#e0e0e0;">{row["Pts3"]}</div></div><div><div class="momentum-label">Δ xG</div><div style="font-size:1.1rem;font-weight:800;color:{delta_color};">{delta_str}</div></div></div></div>"""
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
# ──────────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────────
st.markdown("<hr style='border-color:#1f1f24; margin-top:50px;'>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center; color:#555560; font-size:0.75rem; padding:10px 0 30px;'>"
    "LPF Analytics v1.1 &nbsp;·&nbsp; Modelo estadístico propio (Poisson + Dixon-Coles) &nbsp;·&nbsp; "
    "Uso analítico/educativo — no constituye asesoramiento de apuestas"
    "</div>",
    unsafe_allow_html=True,
)