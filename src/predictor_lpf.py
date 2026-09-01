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
from scipy.optimize import minimize

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
# PARÁMETROS DEL MOTOR MATEMÁTICO
# ──────────────────────────────────────────────────────────────────────
W_XG = 0.70  
K_PRIOR_BASE, K_PRIOR_MIN = 15.0, 4.0
MAX_GOALS_MATRIX = 7
N_RECENCIA, PESO_RECIENTE, PESO_NORMAL = 5, 2.0, 1.0   
PESO_HISTORICO = 0.50   
LAM_MIN, LAM_MAX = 0.20, 5.00

RED, WHITE, GRAY = "#ED1A3B", "#ffffff", "#4a4a52"
PLOT = dict(font=dict(family="Manrope", size=12, color="#a0a0a8"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=20, t=36, b=10))

# ──────────────────────────────────────────────────────────────────────
# PROCESAMIENTO DE DATOS
# ──────────────────────────────────────────────────────────────────────
def num(v) -> float:
    if pd.isna(v): return 0.0
    if isinstance(v, (int, float)): return float(v)
    v = str(v).strip()
    m_complex = re.match(r'^(\d+)\s*/', v)
    if m_complex: return float(m_complex.group(1))
    m = re.match(r'^(-?\d+(?:\.\d+)?)\s*\(', v)
    if m: return float(m.group(1))
    v = v.replace('%', '').replace(',', '.').strip()
    try: return float(v)
    except (ValueError, TypeError): return 0.0

def _procesar_dataframe(df):
    partidos = []
    col_0 = df.iloc[:, 0].astype(str)
    mask_partidos = col_0.str.contains(r'\s+vs\s+', case=False, na=False)
    
    df_partidos = df.copy()
    df_partidos['partido_id'] = mask_partidos.cumsum()
    df_partidos = df_partidos[df_partidos['partido_id'] > 0]
    
    for _, grupo in df_partidos.groupby('partido_id'):
        titulo = str(grupo.iloc[0, 0])
        partes = re.split(r'\s+vs\s+', titulo, flags=re.IGNORECASE)
        if len(partes) < 2: continue
        
        loc, vis = partes[0].strip(), partes[1].strip()
        stats = {}
        grupo_datos = grupo.iloc[1:]
        
        idx_derivadas = grupo_datos.index[grupo_datos.iloc[:, 0].astype(str).str.contains(r'métricas derivadas|métrica calculada', case=False, na=False)]
        if not idx_derivadas.empty:
            grupo_datos = grupo_datos.loc[:idx_derivadas[0]-1]
            
        for _, row in grupo_datos.iterrows():
            metrica = str(row[0]).strip()
            if not metrica or metrica.lower() in ("métrica", "metrica", loc.lower(), "nan"):
                continue
                
            v_loc = row[1]
            v_vis = row[2] if len(row) > 2 else 0.0
            
            if isinstance(v_loc, str) and "/" in v_loc and "(" in v_loc:
                m_loc = re.match(r'(\d+)\s*/\s*(\d+)\s*\(\s*(\d+)', str(v_loc))
                m_vis = re.match(r'(\d+)\s*/\s*(\d+)\s*\(\s*(\d+)', str(v_vis))
                if m_loc:
                    stats[metrica + " (Éxito)"] = {"local": float(m_loc.group(1)), "visitante": float(m_vis.group(1)) if m_vis else 0.0}
                    stats[metrica + " (Total)"] = {"local": float(m_loc.group(2)), "visitante": float(m_vis.group(2)) if m_vis else 0.0}
                    stats[metrica + " (%)"] = {"local": float(m_loc.group(3)), "visitante": float(m_vis.group(3)) if m_vis else 0.0}
                    continue

            if pd.notna(v_loc):
                stats[metrica] = {"local": num(v_loc), "visitante": num(v_vis) if pd.notna(v_vis) else 0.0}
                
        partidos.append({"local": loc, "visitante": vis, "metricas": stats})
        
    return partidos

@st.cache_data(ttl=120, show_spinner=False)
def cargar_excel(archivos_seleccionados: list):
    res = {}
    for ruta_archivo in archivos_seleccionados:
        if not os.path.exists(ruta_archivo): continue
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
        partes = clave.split("||")
        categoria, torneo, fecha = partes if len(partes) == 3 else ("Actual", "General", clave)
            
        match_fecha = re.search(r"\d+", fecha)
        if match_fecha and not re.search(r"(octavo|cuarto|semi|final|playoff)", fecha, re.IGNORECASE):
            nf = int(match_fecha.group())
            fase = "Regular" if nf <= MAX_FECHAS_REGULARES else "Playoff"
        else:
            nf = current_playoff_nf
            current_playoff_nf += 1 
            fase = "Playoff"

        for p in partidos:
            xg_loc = p["metricas"].get("Goles esperados (xG)", {}).get("local")
            if xg_loc is None: 
                tt = p["metricas"].get("Tiros totales", {"local": 0, "visitante": 0})
                oc = p["metricas"].get("Ocasiones claras", {"local": 0, "visitante": 0})
                xg_loc = (oc["local"] * 0.38) + (max(0, tt["local"] - oc["local"]) * 0.05)
                xg_vis = (oc["visitante"] * 0.38) + (max(0, tt["visitante"] - oc["visitante"]) * 0.05)
                p["metricas"]["xG_Model"] = {"local": xg_loc, "visitante": xg_vis}
            else:
                p["metricas"]["xG_Model"] = p["metricas"]["Goles esperados (xG)"]

            for met, vals in p["metricas"].items():
                base = {"nFecha": nf, "Fase": fase, "Métrica": met, "Torneo": torneo, "Categoria": categoria}
                filas.append({**base, "Equipo": p["local"], "Rival": p["visitante"], "Condicion": "Local", "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"], "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

# ──────────────────────────────────────────────────────────────────────
# MOTOR MATEMÁTICO: ELO DINÁMICO Y MLE PARA DIXON-COLES
# ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def calcular_elo_dinamico(df: pd.DataFrame) -> dict:
    dr = df[df["Métrica"] == "Resultado"].copy()
    if dr.empty: return {}
    
    # Ordenamos cronológicamente para simular el paso del tiempo
    dr['Torneo_Order'] = dr['Torneo'].apply(lambda x: 1 if 'apertura' in str(x).lower() else (2 if 'clausura' in str(x).lower() else 3))
    dr = dr.sort_values(["Torneo_Order", "nFecha"])
    partidos = dr[dr["Condicion"] == "Local"]
    
    # 1. ANCLA ESTRUCTURAL: Inicialización con jerarquía de mercado
    JERARQUIA_EQUIPOS = {
        "River Plate": 1.250, "Boca Juniors": 1.150, "Racing Club": 1.080, "Rosario Central": 1.065,             
        "Estudiantes de La Plata": 1.050, "San Lorenzo": 1.045, "CA Talleres": 1.040, "Independiente Rivadavia": 1.035,     
        "CA Independiente": 1.030, "Argentinos Juniors": 1.025, "CA Lanús": 1.025, "Tigre": 1.020,                       
        "Club Atlético Platense": 1.000, "Newell's Old Boys": 0.995, "Gimnasia y Esgrima": 0.990, 
        "Club Atlético Belgrano": 0.990, "Defensa y Justicia": 0.985, "Vélez Sarsfield": 0.970,             
        "Huracán": 0.965, "Club Atlético Unión de Santa Fe": 0.960, "Barracas Central": 0.955,            
        "Instituto De Córdoba": 0.950, "Gimnasia y Esgrima Mendoza": 0.945, "Sarmiento": 0.940,                   
        "Banfield": 0.935, "Atlético Tucumán": 0.930, "Aldosivi": 0.925, "Deportivo Riestra": 0.925,           
        "Central Córdoba": 0.920, "Estudiantes de Río Cuarto": 0.915    
    }
    
    BASE_ELO = 1500.0
    elos = {}
    for eq in dr["Equipo"].unique():
        factor = JERARQUIA_EQUIPOS.get(eq, 1.0)
        # Sembramos el puntaje escalonado
        elos[eq] = BASE_ELO * factor  
        
    K = 25.0
    HGA_ELO = 45.0
    
    # 2. ACTUALIZACIÓN DINÁMICA: Partido a partido
    for _, row in partidos.iterrows():
        loc, vis = row["Equipo"], row["Rival"]
        gl, gv = row["Propio"], row["Concedido"]
        
        elo_l, elo_v = elos.get(loc, BASE_ELO), elos.get(vis, BASE_ELO)
        
        # Probabilidad de victoria esperada
        e_loc = 1 / (1 + 10 ** ((elo_v - (elo_l + HGA_ELO)) / 400))
        e_vis = 1 - e_loc
        
        # Resultado real
        if gl > gv: s_loc, s_vis = 1.0, 0.0
        elif gl == gv: s_loc, s_vis = 0.5, 0.5
        else: s_loc, s_vis = 0.0, 1.0
            
        # Sistema de suma cero: el que gana absorbe puntos del perdedor
        elos[loc] = elo_l + K * (s_loc - e_loc)
        elos[vis] = elo_v + K * (s_vis - e_vis)
        
    return elos
def estimar_rho_mle(df: pd.DataFrame) -> float:
    dr = df[(df["Métrica"] == "Resultado") & (df["Condicion"] == "Local")]
    if dr.empty: return -0.15
    
    hg, ag = dr["Propio"].values, dr["Concedido"].values
    mean_hg = np.mean(hg) if np.mean(hg) > 0 else 1.17
    mean_ag = np.mean(ag) if np.mean(ag) > 0 else 0.90
    
    def neg_log_likelihood(rho_val):
        r = rho_val[0]
        ll = 0.0
        for x, y in zip(hg, ag):
            if x == 0 and y == 0: corr = 1 - mean_hg * mean_ag * r
            elif x == 0 and y == 1: corr = 1 + mean_hg * r
            elif x == 1 and y == 0: corr = 1 + mean_ag * r
            elif x == 1 and y == 1: corr = 1 - r
            else: corr = 1.0
            corr = max(1e-5, corr)
            ll += np.log(corr)
        return -ll
        
    res = minimize(neg_log_likelihood, [0.0], bounds=[(-0.3, 0.3)])
    return float(res.x[0]) if res.success else -0.15

@st.cache_data(ttl=120, show_spinner=False)
def calcular_tabla(df: pd.DataFrame, condicion: str = "General") -> pd.DataFrame:
    if df.empty: return pd.DataFrame()
    dr = df[df["Métrica"] == "Resultado"].copy()
    if "Fase" in dr.columns: dr = dr[dr["Fase"] == "Regular"]
    if condicion != "General": dr = dr[dr["Condicion"] == condicion]
    if dr.empty: return pd.DataFrame()
        
    equipos = sorted(df["Equipo"].unique())
    rows = []
    for eq in equipos:
        d = dr[dr["Equipo"] == eq]
        pj = len(d)
        if pj == 0:
            rows.append({"Equipo": eq, "PJ": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0, "PTS": 0, "PPJ": 0.0, "EFEC%": 0.0})
            continue
        v  = (d["Propio"] > d["Concedido"]).sum()
        e  = (d["Propio"] == d["Concedido"]).sum()
        d_ = (d["Propio"] < d["Concedido"]).sum()
        pts = int(v * 3 + e)
        rows.append({"Equipo": eq, "PJ": pj, "V": int(v), "E": int(e), "D": int(d_),
                     "GF": d["Propio"].sum(), "GC": d["Concedido"].sum(), "PTS": pts, "PPJ": pts / pj, "EFEC%": (pts / (pj * 3)) * 100})
    
    tabla = pd.DataFrame(rows).sort_values(["EFEC%", "PTS", "GF"], ascending=[False, False, False]).reset_index(drop=True)
    tabla["Pos"] = tabla.index + 1
    
    elos = calcular_elo_dinamico(df)
    tabla["prior_atk"], tabla["prior_def"] = 1.0, 1.0
    for eq in tabla.index:
        factor = elos.get(tabla.loc[eq, "Equipo"], 1500.0) / 1500.0
        tabla.loc[eq, "prior_atk"] = factor
        tabla.loc[eq, "prior_def"] = (1 / factor) if factor > 0 else 1.0
    return tabla.set_index("Equipo")

def _get_prior(tabla: pd.DataFrame, eq: str):
    if tabla is None or eq not in tabla.index: return 1.0, 1.0
    return float(tabla.loc[eq, "prior_atk"]), float(tabla.loc[eq, "prior_def"])

def _adjusted_rate(d_all, metrica, col, max_fecha_torneo, tabla, is_attack, target_cond):
    df_m = d_all[d_all["Métrica"] == metrica]
    if df_m.empty: return np.nan
        
    fechas, categoria, valores, rivales, condiciones = df_m["nFecha"].values, df_m["Categoria"].values, df_m[col].values, df_m["Rival"].values, df_m["Condicion"].values
    valores_ajustados, pesos = [], []
    
    for v, r, c_match, f, cat in zip(valores, rivales, condiciones, fechas, categoria):
        pa_r, pd_r = _get_prior(tabla, r)
        pd_r_safe, pa_r_safe = max(pd_r, 0.80), max(pa_r, 0.80)
        adj = v / pd_r_safe if (is_attack and pd_r_safe > 0) else v / pa_r_safe if (not is_attack and pa_r_safe > 0) else v
        valores_ajustados.append(min(adj, 3.5))
        
        w = PESO_HISTORICO if cat == "Histórico" else (PESO_RECIENTE if f >= (max_fecha_torneo - N_RECENCIA + 1) else PESO_NORMAL)
        if c_match == target_cond: w *= 1.15
        pesos.append(w)
        
    return float(np.average(valores_ajustados, weights=pesos)) if valores_ajustados and sum(pesos) > 0 else np.nan

@st.cache_data(ttl=120, show_spinner=False)
def _league_stats(df):
    dr = df[df["Métrica"] == "Resultado"]
    dx = df[df["Métrica"] == "xG_Model"]
    def get_avg(d, cond):
        v = d[d["Condicion"] == cond]["Propio"].mean() if not d.empty else np.nan
        return v if not np.isnan(v) else 1.0
    gh, gv = get_avg(dr, "Local"), get_avg(dr, "Visitante")
    xh, xv = get_avg(dx, "Local"), get_avg(dx, "Visitante")
    if dx.empty: rh, rv = gh, gv
    else: rh, rv = W_XG * xh + (1 - W_XG) * gh, W_XG * xv + (1 - W_XG) * gv
    return {"ref_home": rh, "ref_away": rv, "ref_all": (rh + rv) / 2}

def _strength(df_actual, eq, target_cond, league, max_fecha_torneo: int, tabla: pd.DataFrame):
    d_eq = df_actual[df_actual["Equipo"] == eq]
    
    g_atk = _adjusted_rate(d_eq, "Resultado", "Propio", max_fecha_torneo, tabla, is_attack=True, target_cond=target_cond)
    x_atk = _adjusted_rate(d_eq, "xG_Model", "Propio", max_fecha_torneo, tabla, is_attack=True, target_cond=target_cond)
    g_def = _adjusted_rate(d_eq, "Resultado", "Concedido", max_fecha_torneo, tabla, is_attack=False, target_cond=target_cond)
    x_def = _adjusted_rate(d_eq, "xG_Model", "Concedido", max_fecha_torneo, tabla, is_attack=False, target_cond=target_cond)
    
    n_s = len(d_eq[d_eq["Métrica"] == "Resultado"])

    def combine(g, x):
        if np.isnan(g) and np.isnan(x): return np.nan
        if np.isnan(x): return g
        if np.isnan(g): return x
        return W_XG * x + (1 - W_XG) * g

    atk_val, def_val = combine(g_atk, x_atk), combine(g_def, x_def)
    
    rh, ra = league["ref_home"], league["ref_away"]
    ref_f, ref_a = (rh, ra) if target_cond == "Local" else (ra, rh)
    
    atk_obs = (atk_val / ref_f) if (not np.isnan(atk_val) and ref_f > 0) else np.nan
    def_obs = (def_val / ref_a) if (not np.isnan(def_val) and ref_a > 0) else np.nan
    
    prior_atk, prior_def = _get_prior(tabla, eq)
    
    n = n_s if n_s > 0 else 0
    n_effective = min(n, 15)
    
    atk_obs = atk_obs if not np.isnan(atk_obs) else prior_atk
    def_obs = def_obs if not np.isnan(def_obs) else prior_def
    
    k_prior = max(K_PRIOR_MIN, K_PRIOR_BASE - max_fecha_torneo)
    atk_post = (n_effective * atk_obs  + k_prior * prior_atk) / (n_effective + k_prior)
    def_post = (n_effective * def_obs  + k_prior * prior_def) / (n_effective + k_prior)
    
    return atk_post, def_post, n

def calcular_lambdas(df, eq_a, eq_b, es_loc, tabla):
    df_actual = df[df["Categoria"] == "Actual"]
    if df_actual.empty: df_actual = df
        
    l = _league_stats(df_actual)
    max_fecha_torneo = int(df_actual["nFecha"].max()) if not df_actual.empty else 1
    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")
    
    aa, da, _ = _strength(df_actual, eq_a, ca, l, max_fecha_torneo, tabla)
    ab, db, _ = _strength(df_actual, eq_b, cb, l, max_fecha_torneo, tabla)
    
    # La ventaja de localía (HGA) ya viene embebida dinámicamente en l["ref_home"] y l["ref_away"]
    la = (l["ref_home"] if ca == "Local" else l["ref_away"]) * aa * db
    lb = (l["ref_home"] if cb == "Local" else l["ref_away"]) * ab * da

    # Se eliminaron los modificadores heurísticos de HGA (**1.10 y *=0.95), 
    # de táctica (+0.05) y de penalización a grandes equipos (*0.85).
    # Ahora todo depende puramente del xG y del Elo Tracker.

    if not es_loc:
        la, lb = lb, la
        
    return (round(float(np.clip(la, LAM_MIN, LAM_MAX)), 3), round(float(np.clip(lb, LAM_MIN, LAM_MAX)), 3))

def proyectar_metrica(df, eq_a, eq_b, metrica, es_loc, tabla):
    df_m = df[df["Métrica"] == metrica]
    if df_m.empty: return 0.0, 0.0
    
    ca, cb = ("Local", "Visitante") if es_loc else ("Visitante", "Local")
    
    def _mean_with_cond(d_eq, target_cond, col):
        if d_eq.empty: return df_m[col].mean()
        conds = d_eq["Condicion"].values
        vals = d_eq[col].values
        w = np.where(conds == target_cond, 1.20, 1.0)
        return np.average(vals, weights=w)
        
    d_a, d_b = df_m[df_m["Equipo"] == eq_a], df_m[df_m["Equipo"] == eq_b]
    base_a, concede_a = _mean_with_cond(d_a, ca, "Propio"), _mean_with_cond(d_a, ca, "Concedido")
    base_b, concede_b = _mean_with_cond(d_b, cb, "Propio"), _mean_with_cond(d_b, cb, "Concedido")
    
    media_liga = df_m["Propio"].mean() if not df_m.empty else 1.0
    if media_liga == 0: media_liga = 1.0

    factor_def_b = 1.0 + ((concede_b / media_liga) - 1.0) * 0.5 
    factor_def_a = 1.0 + ((concede_a / media_liga) - 1.0) * 0.5 
    
    val_a = base_a * factor_def_b
    val_b = base_b * factor_def_a
    
    if metrica == "Goles evitados (arquero)":
        return float(val_a), float(val_b)
    
    return max(0.0, float(val_a)), max(0.0, float(val_b))

def montecarlo(la, lb, rho_dinamico):
    def _pmf(lam, kmax):
        k = np.arange(kmax + 1)
        return np.exp(k * np.log(max(lam, 1e-9)) - lam - np.array([math.log(math.factorial(x)) for x in k]))
    pa, pb = _pmf(la, MAX_GOALS_MATRIX), _pmf(lb, MAX_GOALS_MATRIX)
    M = np.outer(pa, pb)
    rho = max(rho_dinamico, -0.9 / max(la * lb, 0.01))
    M[0, 0] = max(M[0, 0] * (1 - la * lb * rho), 0.0)
    M[0, 1] = max(M[0, 1] * (1 + la * rho),       0.0)
    M[1, 0] = max(M[1, 0] * (1 + lb * rho),        0.0)
    M[1, 1] = max(M[1, 1] * (1 - rho),             0.0)
    M /= M.sum()
    return {"victoria": float(np.tril(M, -1).sum()), "empate": float(np.trace(M)), "derrota": float(np.triu(M, 1).sum()), "matrix": M}

def top3_marcadores(M, ea, eb):
    flat = [(M[i, j], i, j) for i in range(M.shape[0]) for j in range(M.shape[1]) if not (i == 1 and j == 1)]
    flat.sort(reverse=True)
    medallas, clases = ["🥇 MÁS PROBABLE", "🥈 2°", "🥉 3°"], ["first", "second", "third"]
    cards = "".join(f"""<div class="score-card {clases[idx]}"><div class="score-rank">{medallas[idx]}</div><div class="score-result">{ea[:3].upper()} {i} – {j} {eb[:3].upper()}</div><div class="score-pct">{prob * 100:.1f}%</div></div>""" for idx, (prob, i, j) in enumerate(flat[:3]))
    return f'<div class="top3-container">{cards}</div>'

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
        tiros_prop   = _safe_mean(df, eq, "Tiros totales")
        tiros_conc   = _safe_mean(df, eq, "Tiros totales", col="Concedido")
        xg_prop      = _safe_mean(df, eq, "xG_Model")
        xg_conc      = _safe_mean(df, eq, "xG_Model", col="Concedido")
        quites       = _safe_mean(df, eq, "Quites")
        intercep     = _safe_mean(df, eq, "Intercepciones")
        despejes     = _safe_mean(df, eq, "Despejes")
        
        efic_ofens = (xg_prop / tiros_prop) if (not np.isnan(xg_prop) and not np.isnan(tiros_prop) and tiros_prop > 0) else np.nan
        act_def = (quites + intercep + despejes) if not np.isnan(quites) else np.nan
        
        rows.append({"Equipo": eq, "Posesion": pos_propia, "TirosProp": tiros_prop, "TirosConc": tiros_conc, 
                     "xGProp": xg_prop, "xGConc": xg_conc, "EficOfens": efic_ofens, "ActDefensiva": act_def, "Despejes": despejes})
                     
    adn = pd.DataFrame(rows).set_index("Equipo")
    def pct(col): return {eq: float(np.mean(adn[col].dropna() <= v)) for eq, v in adn[col].dropna().items()} if not adn[col].dropna().empty else {}

    pct_pos, pct_tprop, pct_tconc, pct_xgc, pct_efic = pct("Posesion"), pct("TirosProp"), pct("TirosConc"), pct("xGConc"), pct("EficOfens")
    pct_def, pct_desp = pct("ActDefensiva"), pct("Despejes")

    tags_dict, insights = {}, {}
    for eq in adn.index:
        tags, frases = [], []
        pos_p, tp_p, tc_p, xgc_p, ef_p = pct_pos.get(eq, 0.5), pct_tprop.get(eq, 0.5), pct_tconc.get(eq, 0.5), pct_xgc.get(eq, 0.5), pct_efic.get(eq, 0.5)
        def_p, desp_p = pct_def.get(eq, 0.5), pct_desp.get(eq, 0.5)

        if pos_p >= 0.70:
            tags.append(("POSESIÓN DOMINANTE", "tag-posesion"))
            frases.append("Controla el juego con posesión elevada.")
        elif pos_p <= 0.30:
            tags.append(("JUEGO DIRECTO", "tag-directo"))
            frases.append("Cede la pelota y busca aprovechar los espacios.")

        if tc_p <= 0.30 and def_p >= 0.65:
            tags.append(("PRESSING INTENSO", "tag-pressing"))
            frases.append("Recupera rápido y asfixia al rival: alta actividad defensiva.")
        elif desp_p >= 0.75:
            tags.append(("BLOQUE HUNDIDO", "tag-bloque"))
            frases.append("Defiende cerca de su área, acumula muchísimos despejes.")

        if ef_p >= 0.70:
            tags.append(("ALTA EFICIENCIA", "tag-posesion"))
            frases.append("Letal arriba: genera ocasiones de alta calidad por tiro.")
        
        if xgc_p >= 0.75:
            tags.append(("DÉFICIT DEFENSIVO", "tag-bloque"))
            frases.append("Línea muy frágil, le generan mucho volumen de xG.")

        if not tags:
            tags.append(("PERFIL EQUILIBRADO", "tag-neutral"))
            frases.append("Sin tendencias extremas: estilo balanceado.")

        tags_dict[eq], insights[eq] = tags, " ".join(frases)

    adn["Tags"], adn["Insight"] = adn.index.map(tags_dict), adn.index.map(insights)
    return adn

def render_tags_html(tags: list) -> str: return "".join(f'<span class="tag-badge {clase}">{texto}</span>' for texto, clase in tags)

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

def calcular_rachas(df: pd.DataFrame) -> pd.DataFrame:
    dr = df[df["Métrica"] == "Resultado"].copy()
    dx = df[df["Métrica"] == "xG_Model"].copy()
    
    dr["Orden_Cat"] = np.where(dr["Categoria"] == "Histórico", 0, 1)
    dx["Orden_Cat"] = np.where(dx["Categoria"] == "Histórico", 0, 1)
    
    equipos = sorted(dr["Equipo"].unique())
    rows = []

    for eq in equipos:
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
    dx = df[(df["Equipo"] == equipo) & (df["Métrica"] == "xG_Model")].copy()
    
    if dr.empty: return go.Figure()

    dr["Orden_Cat"] = np.where(dr["Categoria"] == "Histórico", 0, 1)
    dx["Orden_Cat"] = np.where(dx["Categoria"] == "Histórico", 0, 1)
    
    dr = dr.sort_values(["Orden_Cat", "nFecha"])
    dx = dx.sort_values(["Orden_Cat", "nFecha"])

    fechas_labels = dr.apply(lambda r: f"{r['Torneo'][:3].upper()}-{r['nFecha']}", axis=1).tolist()
    
    pts_parciales = []
    for _, row in dr.iterrows():
        if row["Propio"] > row["Concedido"]: pts_parciales.append(3)
        elif row["Propio"] == row["Concedido"]: pts_parciales.append(1)
        else: pts_parciales.append(0)
        
    xg_vals = dx["Propio"].values
    
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
    defaults = [opt for opt in opciones_disponibles if ("clausura" in opt.lower() or "histórico" in opt.lower())]
    
    torneos_seleccionados_nombres = st.multiselect(
        "Bases de Datos a Utilizar (Actual + Histórico por defecto):",
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
    st.error("⚠️ **No se encontró ninguna base de datos.**")
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
rho_dinamico = estimar_rho_mle(df)

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
Dixon-Coles (`ρ`) optimizado mediante Maximum Likelihood Estimation (MLE) sobre datos históricos.
**Fuerza de ataque/defensa (`λ`):** se calcula combinando el rendimiento observado (xG/Goles reales)
con un *prior* bayesiano impulsado por un sistema ELO que rankea a los equipos de forma dinámica.
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
        sim    = montecarlo(la, lb, rho_dinamico)
        
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

        tiros_a, tiros_b = proyectar_metrica(df, ea, eb, "Tiros totales", loc, tabla)
        arco_a, arco_b   = proyectar_metrica(df, ea, eb, "Tiros al arco", loc, tabla)
        ocas_a, ocas_b   = proyectar_metrica(df, ea, eb, "Ocasiones claras", loc, tabla)
        pos_a, pos_b     = proyectar_metrica(df, ea, eb, "Posesión de balón", loc, tabla)
        corn_a, corn_b   = proyectar_metrica(df, ea, eb, "Córners", loc, tabla)
        reg_a, reg_b     = proyectar_metrica(df, ea, eb, "Regates intentados (Total)", loc, tabla)
        pp_a, pp_b       = proyectar_metrica(df, ea, eb, "Pases precisos", loc, tabla)
        pt_a, pt_b       = proyectar_metrica(df, ea, eb, "Pases totales", loc, tabla)
        gev_a, gev_b     = proyectar_metrica(df, ea, eb, "Goles evitados (arquero)", loc, tabla)
        xgot_a, xgot_b   = proyectar_metrica(df, ea, eb, "xG al arco (xGOT)", loc, tabla)
        ataj_a, ataj_b   = proyectar_metrica(df, ea, eb, "Atajadas del arquero", loc, tabla)
        quit_a, quit_b   = proyectar_metrica(df, ea, eb, "Quites", loc, tabla)
        inter_a, inter_b = proyectar_metrica(df, ea, eb, "Intercepciones", loc, tabla)
        desp_a, desp_b   = proyectar_metrica(df, ea, eb, "Despejes", loc, tabla)
        tda_a, tda_b     = proyectar_metrica(df, ea, eb, "Tiros dentro del área", loc, tabla)
        
        t_afuera_a, t_afuera_b     = proyectar_metrica(df, ea, eb, "Tiros afuera", loc, tabla)
        t_bloq_a, t_bloq_b         = proyectar_metrica(df, ea, eb, "Tiros bloqueados", loc, tabla)
        offside_a, offside_b       = proyectar_metrica(df, ea, eb, "Fueras de juego", loc, tabla)
        faltas_a, faltas_b         = proyectar_metrica(df, ea, eb, "Faltas", loc, tabla)
        amarillas_a, amarillas_b   = proyectar_metrica(df, ea, eb, "Tarjetas amarillas", loc, tabla)
        rojas_a, rojas_b           = proyectar_metrica(df, ea, eb, "Tarjetas rojas", loc, tabla)
        ocas_fall_a, ocas_fall_b   = proyectar_metrica(df, ea, eb, "Ocasiones claras falladas", loc, tabla)
        tfa_a, tfa_b               = proyectar_metrica(df, ea, eb, "Tiros fuera del área", loc, tabla)

        tot_pos = pos_a + pos_b
        if tot_pos > 0:
            pos_a = (pos_a / tot_pos) * 100
            pos_b = (pos_b / tot_pos) * 100
        else:
            pos_a, pos_b = 50.0, 50.0
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📝 PROYECCIÓN DE MÉTRICAS")
        
        df_comparativa = pd.DataFrame({
            "Métrica": [
                "Posesión de balón", "Goles esperados (xG)", "Tiros totales", 
                "Tiros al arco", "Tiros afuera", "Tiros bloqueados", "Córners", 
                "Fueras de juego", "Faltas", "Tarjetas amarillas", "Tarjetas rojas", 
                "Pases totales", "Pases precisos", "Atajadas del arquero", "Quites", 
                "Intercepciones", "Despejes", "Ocasiones claras", "Ocasiones claras falladas", 
                "Regates intentados", "Tiros dentro del área", "Tiros fuera del área", 
                "xG al arco (xGOT)", "Goles evitados (arquero)"
            ],
            ea: [
                f"{pos_a:.0f}%", f"{la:.2f}", f"{tiros_a:.0f}", 
                f"{arco_a:.0f}", f"{t_afuera_a:.0f}", f"{t_bloq_a:.0f}", f"{corn_a:.0f}", 
                f"{offside_a:.0f}", f"{faltas_a:.0f}", f"{amarillas_a:.0f}", f"{rojas_a:.0f}", 
                f"{pt_a:.0f}", f"{pp_a:.0f}", f"{ataj_a:.0f}", f"{quit_a:.0f}", 
                f"{inter_a:.0f}", f"{desp_a:.0f}", f"{ocas_a:.0f}", f"{ocas_fall_a:.0f}", 
                f"{reg_a:.0f}", f"{tda_a:.0f}", f"{tfa_a:.0f}", 
                f"{xgot_a:.2f}", f"{gev_a:.2f}"
            ],
            eb: [
                f"{pos_b:.0f}%", f"{lb:.2f}", f"{tiros_b:.0f}", 
                f"{arco_b:.0f}", f"{t_afuera_b:.0f}", f"{t_bloq_b:.0f}", f"{corn_b:.0f}", 
                f"{offside_b:.0f}", f"{faltas_b:.0f}", f"{amarillas_b:.0f}", f"{rojas_b:.0f}", 
                f"{pt_b:.0f}", f"{pp_b:.0f}", f"{ataj_b:.0f}", f"{quit_b:.0f}", 
                f"{inter_b:.0f}", f"{desp_b:.0f}", f"{ocas_b:.0f}", f"{ocas_fall_b:.0f}", 
                f"{reg_b:.0f}", f"{tda_b:.0f}", f"{tfa_b:.0f}", 
                f"{xgot_b:.2f}", f"{gev_b:.2f}"
            ]
        })

        st.dataframe(df_comparativa, hide_index=True, use_container_width=True, height=900)

        if not rachas_df.empty and ea in rachas_df.index and eb in rachas_df.index:
            st.markdown('<div class="section-header">Forma Reciente</div>', unsafe_allow_html=True)
            mc1, mc2 = st.columns(2)
            for col_ui, eq_m in [(mc1, ea), (mc2, eb)]:
                with col_ui:
                    row_m = rachas_df.loc[eq_m]
                    dots  = render_racha_dots(row_m["Ultimas6"])
                    col_ui.markdown(f"""<div class="momentum-card"><div class="momentum-team">{eq_m}</div><div class="momentum-label">Últimas {len(row_m["Ultimas6"])} fechas</div><div style="margin-bottom:10px;">{dots}</div><div class="momentum-label">Estado de forma</div><div class="{row_m["EstadoCls"]}">{row_m["Estado"]}</div><div style="font-size:0.78rem;color:#555560;margin-top:6px;">xG reciente: {row_m["xGRec"]:.2f} &nbsp;|&nbsp; Pts últimas 3: {row_m["Pts3"]}</div></div>""", unsafe_allow_html=True)
            
        st.markdown('<div class="section-header">Matriz de Resultados</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_score_matrix(sim["matrix"], ea, eb), use_container_width=True)

elif nav == "Simulador de Jornada":
    st.markdown('<div class="section-header">Simulador de Jornada Automático (Inversión de Fixture)</div>', unsafe_allow_html=True)
    
    ruta_apertura_fija = "data/historico/apertura26.xlsx"
    df_fixture_temp = None
    
    if os.path.exists(ruta_apertura_fija):
        xl_apertura = pd.ExcelFile(ruta_apertura_fija, engine="openpyxl")
        datos_fixture = {}
        for hoja in xl_apertura.sheet_names:
            if re.search(r"fecha\s*\d+", hoja, re.IGNORECASE):
                df_h = pd.read_excel(xl_apertura, sheet_name=hoja, header=None)
                datos_fixture[f"Histórico||Apertura||{hoja}"] = _procesar_dataframe(df_h)
        if datos_fixture:
            df_fixture_temp = construir_df(datos_fixture)

    if df_fixture_temp is None or df_fixture_temp.empty:
        df_fixture_temp = df

    fechas_disponibles = sorted(df_fixture_temp["nFecha"].unique())
    
    c1, c2 = st.columns([1, 3])
    jornada_elegida = c1.selectbox("Seleccionar Fecha del Fixture a Invertir:", fechas_disponibles)
    
    df_fecha_apertura = df_fixture_temp[
        (df_fixture_temp["nFecha"] == jornada_elegida) & 
        (df_fixture_temp["Condicion"] == "Local") &
        (df_fixture_temp["Métrica"] == "Resultado")
    ].drop_duplicates(subset=["Equipo", "Rival"])
    
    cruces_validos = pd.DataFrame({
        "Rotación L": False,                             
        "Local": df_fecha_apertura["Rival"].values,      
        "Visitante": df_fecha_apertura["Equipo"].values, 
        "Rotación V": False                              
    })
    
    c2.write(f"**Partidos de la Fecha {jornada_elegida} (Localías Invertidas para el Clausura)**")
    
    cruces_editados = c2.data_editor(
        cruces_validos,
        column_config={
            "Rotación L": st.column_config.CheckboxColumn("Rotación 🔄", default=False),
            "Rotación V": st.column_config.CheckboxColumn("Rotación 🔄", default=False),
        },
        hide_index=True,
        use_container_width=True
    )
    
    PENALIDAD_XG = 0.35 

    if st.button("SIMULAR JORNADA COMPLETA"):
        if len(cruces_editados) == 0:
            st.warning("⚠️ No hay partidos para simular.")
        else:
            resultados_jornada = []
            
            with st.spinner(f"Procesando simulaciones matemáticas para la Fecha {jornada_elegida}..."):
                for idx, row in cruces_editados.iterrows():
                    ea = row["Local"]
                    eb = row["Visitante"]
                    rota_local = row["Rotación L"]
                    rota_visitante = row["Rotación V"]
                    
                    if ea == eb: continue
                        
                    la, lb = calcular_lambdas(df, ea, eb, True, tabla)

                    if rota_local: la = max(0.1, la - PENALIDAD_XG)
                    if rota_visitante: lb = max(0.1, lb - PENALIDAD_XG)

                    sim = montecarlo(la, lb, rho_dinamico) 
                    
                    tiros_a, tiros_b = proyectar_metrica(df, ea, eb, "Tiros totales", True, tabla)
                    arco_a, arco_b   = proyectar_metrica(df, ea, eb, "Tiros al arco", True, tabla)
                    ocas_a, ocas_b   = proyectar_metrica(df, ea, eb, "Ocasiones claras", True, tabla)
                    pos_a, pos_b     = proyectar_metrica(df, ea, eb, "Posesión de balón", True, tabla)
                    corn_a, corn_b   = proyectar_metrica(df, ea, eb, "Córners", True, tabla)
                    reg_a, reg_b     = proyectar_metrica(df, ea, eb, "Regates intentados", True, tabla)
                    pp_a, pp_b       = proyectar_metrica(df, ea, eb, "Pases precisos", True, tabla)
                    pt_a, pt_b       = proyectar_metrica(df, ea, eb, "Pases totales", True, tabla)
                    gev_a, gev_b     = proyectar_metrica(df, ea, eb, "Goles evitados (arquero)", True, tabla)
                    xgot_a, xgot_b   = proyectar_metrica(df, ea, eb, "xG al arco (xGOT)", True, tabla)
                    ataj_a, ataj_b   = proyectar_metrica(df, ea, eb, "Atajadas del arquero", True, tabla)
                    quit_a, quit_b   = proyectar_metrica(df, ea, eb, "Quites", True, tabla)
                    inter_a, inter_b = proyectar_metrica(df, ea, eb, "Intercepciones", True, tabla)
                    desp_a, desp_b   = proyectar_metrica(df, ea, eb, "Despejes", True, tabla)
                    tda_a, tda_b     = proyectar_metrica(df, ea, eb, "Tiros dentro del área", True, tabla)

                    if rota_local:
                        pos_a *= 0.9  
                        tiros_a *= 0.8 
                    if rota_visitante:
                        pos_b *= 0.9
                        tiros_b *= 0.8
                    
                    tot_pos = pos_a + pos_b
                    if tot_pos > 0:
                        pos_a = (pos_a / tot_pos) * 100
                        pos_b = (pos_b / tot_pos) * 100
                    else:
                        pos_a, pos_b = 50.0, 50.0
                        
                    resultados_jornada.append({
                        "Equipo": ea, "Condición": "Local", "Rival": eb,
                        "Prob_Victoria": sim["victoria"],
                        "xG_Favor": la, "xG_Contra": lb, "Tiros_Favor": tiros_a, "Tiros_Contra": tiros_b,
                        "Arco_Favor": arco_a, "Arco_Contra": arco_b, "Ocasiones_Favor": ocas_a, "Ocasiones_Contra": ocas_b,
                        "Posesion": pos_a, "Corners_Favor": corn_a, "Regates_pct": reg_a,
                        "Precision_Pases": (pp_a / pt_a * 100) if pt_a > 0 else 0.0,
                        "Goles_Evitados": gev_a, "xGOT_Contra": xgot_b, "Atajadas": ataj_a,
                        "Quites": quit_a, "Intercepciones": inter_a, "Despejes": desp_a,
                        "Tiros_Area_Favor": tda_a,
                    })
                    
                    resultados_jornada.append({
                        "Equipo": eb, "Condición": "Visitante", "Rival": ea,
                        "Prob_Victoria": sim["derrota"],
                        "xG_Favor": lb, "xG_Contra": la, "Tiros_Favor": tiros_b, "Tiros_Contra": tiros_a,
                        "Arco_Favor": arco_b, "Arco_Contra": arco_a, "Ocasiones_Favor": ocas_b, "Ocasiones_Contra": ocas_a,
                        "Posesion": pos_b, "Corners_Favor": corn_b, "Regates_pct": reg_b,
                        "Precision_Pases": (pp_b / pt_b * 100) if pt_b > 0 else 0.0,
                        "Goles_Evitados": gev_b, "xGOT_Contra": xgot_a, "Atajadas": ataj_b,
                        "Quites": quit_b, "Intercepciones": inter_b, "Despejes": desp_b,
                        "Tiros_Area_Favor": tda_b,
                    })
            
            df_res = pd.DataFrame(resultados_jornada)
            df_res["Indice_Arquero"] = df_res["Goles_Evitados"] - (df_res["xGOT_Contra"] * 0.1)
            
            def format_ranking(df_temp, sort_col, ascending, cols_to_show, rename_dict=None):
                temp = df_temp.sort_values(by=sort_col, ascending=ascending).reset_index(drop=True)
                temp["Pos"] = temp.index + 1
                temp["Equipo"] = temp.apply(lambda r: f"⭐ {r['Equipo']}" if r["Pos"] <= 5 else r["Equipo"], axis=1)
                final_cols = ["Pos", "Equipo"] + [c for c in cols_to_show if c != "Equipo"]
                temp = temp[final_cols]
                if rename_dict:
                    temp = temp.rename(columns=rename_dict)
                return temp

            st.markdown('<div class="section-header">📊 Rankings de la Jornada — Por Zona de Cancha</div>', unsafe_allow_html=True)

            tab_gen, tab_ark, tab_def, tab_med, tab_ata = st.tabs(["🏆 General", "🧤 Portería", "🛡️ Defensa", "🧭 Mediocampo", "⚔️ Ataque"])

            with tab_gen:
                df_vic = format_ranking(df_res, "Prob_Victoria", False,
                                        ["Prob_Victoria", "xG_Favor", "xG_Contra", "Condición", "Rival"],
                                        {"Prob_Victoria": "Prob. de Ganar"})
                st.dataframe(df_vic.style.format({"Prob. de Ganar": "{:.1%}", "xG_Favor": "{:.2f}", "xG_Contra": "{:.2f}"}),
                             hide_index=True, use_container_width=True, height=320)

            with tab_ark:
                df_arq = format_ranking(df_res, "Atajadas", False,
                                        ["Atajadas", "Arco_Contra", "xG_Contra", "xGOT_Contra", "Rival"],
                                        {"Atajadas": "Atajadas Proyectadas", "Arco_Contra": "Tiros al Arco Recibidos",
                                         "xG_Contra": "xG en Contra", "xGOT_Contra": "xGOT en Contra"})
                st.dataframe(df_arq.style.format({"Atajadas Proyectadas": "{:.1f}", "Tiros al Arco Recibidos": "{:.1f}",
                                                  "xG en Contra": "{:.2f}", "xGOT en Contra": "{:.2f}"}), 
                             hide_index=True, use_container_width=True, height=320)
            with tab_def:
                df_def = format_ranking(df_res, "xG_Contra", True,
                                        ["xG_Contra", "Ocasiones_Contra", "Arco_Contra", "Tiros_Contra", "Quites", "Intercepciones", "Despejes", "Rival"],
                                        {"xG_Contra": "xG Concedido", "Ocasiones_Contra": "Ocasiones Conced.", "Arco_Contra": "Tiros al Arco Recibidos",
                                         "Tiros_Contra": "Tiros Tot. Recibidos"})
                st.dataframe(df_def.style.format({"xG Concedido": "{:.2f}", "Ocasiones Conced.": "{:.1f}", "Tiros al Arco Recibidos": "{:.1f}",
                                                  "Tiros Tot. Recibidos": "{:.1f}", "Quites": "{:.1f}", "Intercepciones": "{:.1f}", "Despejes": "{:.1f}"}), 
                             hide_index=True, use_container_width=True, height=320)
            with tab_med:
                df_med = format_ranking(df_res, "Posesion", False,
                                        ["Posesion", "Precision_Pases", "Quites", "Ocasiones_Favor", "Rival"],
                                        {"Posesion": "Posesión %", "Precision_Pases": "Precisión %", "Quites": "Quites (Recuperación)", "Ocasiones_Favor": "Ocasiones Creadas"})
                st.dataframe(df_med.style.format({"Posesión %": "{:.1f}%", "Precisión %": "{:.1f}%", "Quites (Recuperación)": "{:.1f}", "Ocasiones Creadas": "{:.1f}"}), 
                             hide_index=True, use_container_width=True, height=320)

            with tab_ata:
                df_del = format_ranking(df_res, "xG_Favor", False,
                                        ["xG_Favor", "Ocasiones_Favor", "Tiros_Area_Favor", "Arco_Favor", "Corners_Favor", "Rival"],
                                        {"xG_Favor": "xG Generado", "Ocasiones_Favor": "Ocasiones Claras", "Tiros_Area_Favor": "Tiros en Área", "Arco_Favor": "Tiros al Arco", "Corners_Favor": "Córners Proyectados"})
                st.dataframe(df_del.style.format({"xG Generado": "{:.2f}", "Ocasiones Claras": "{:.1f}", "Tiros en Área": "{:.1f}", "Tiros al Arco": "{:.1f}", "Córners Proyectados": "{:.1f}"}), 
                             hide_index=True, use_container_width=True, height=320)

elif nav in ["Métricas Globales", "Comparativa H2H", "Análisis de Rival", "Análisis de Estilos", "Posiciones", "ADN Táctico", "Rachas y Momentum"]:
    st.info("Visualizaciones secundarias conservadas en su formato original. Navega por el menú para verlas.")