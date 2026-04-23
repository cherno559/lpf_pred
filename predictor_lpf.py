"""
dashboard_lpf_v2.py — LPF 2026 · Modelo Predictivo Mejorado
─────────────────────────────────────────────────────────────
"""

import re, os, math, warnings
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILOS UI
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LPF 2026 · Scouting & Predictor",
    page_icon="⚽", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
h1, h2, h3 { font-family: 'Arial', sans-serif; color: #e63946; }
.section-title { 
    font-size: 1.4rem; font-weight: bold; color: #e63946; 
    border-bottom: 2px solid #1c2a40; padding-bottom: 8px; margin: 30px 0 20px; text-transform: uppercase; 
}
.kpi-container {
    background-color: #111827; border-radius: 10px; padding: 20px; 
    border-left: 5px solid #e63946; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}
.kpi-title { font-size: 0.9rem; color: #9ca3af; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;}
.kpi-value { font-size: 2.2rem; color: #ffffff; font-weight: bold; margin-top: 5px;}
.kpi-draw { border-left-color: #6b7280; }
.kpi-loss { border-left-color: #3b82f6; }
.kpi-green { border-left-color: #10b981; }
.stTabs [data-baseweb="tab-list"] { gap: 10px; }
.stTabs [data-baseweb="tab"] { border-radius: 5px; padding: 10px 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

RED, BLUE, GREEN, GRAY = "#e63946", "#3b82f6", "#10b981", "#6b7280"
PLOT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=40, b=10))
MAX_G = 8

# ──────────────────────────────────────────────────────────────────────
# LECTURA DE DATOS MULTIFORMATO (CSV / EXCEL)
# ──────────────────────────────────────────────────────────────────────
def _parse_num(v) -> float:
    if isinstance(v, str):
        v = v.replace('%', '').replace(',', '.').strip()
        m = re.search(r'^[\d.]+', v)
        if m: return float(m.group())
        return 0.0
    try: return float(v)
    except: return 0.0

def _parse_regate(v) -> float:
    if isinstance(v, str):
        m = re.search(r'\((\d+)%\)', v)
        if m: return float(m.group(1))
    return 0.0

def parse_dataframe(df, nf):
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
                # Si encontramos línea en blanco u otro partido, terminamos este bloque
                if r0 == "" or re.search(r"\s+vs\s+", r0, re.IGNORECASE): break
                
                # Ignorar encabezados o la parte de métricas calculadas
                if any(r0.lower().startswith(s) for s in ("métrica", "metrica", "📊", loc.lower(), vis.lower())):
                    j += 1; continue
                
                # Extraer datos protegiéndonos de columnas vacías
                raw_l = df.iloc[j, 1] if df.shape[1] > 1 and pd.notna(df.iloc[j, 1]) else 0
                raw_v = df.iloc[j, 2] if df.shape[1] > 2 and pd.notna(df.iloc[j, 2]) else 0
                
                stats[r0] = {
                    "local": _parse_regate(raw_l) if "regate" in r0.lower() else _parse_num(raw_l),
                    "visitante": _parse_regate(raw_v) if "regate" in r0.lower() else _parse_num(raw_v)
                }
                j += 1
            partidos.append({"local": loc, "visitante": vis, "stats": stats, "nFecha": nf})
            i = j
        else: i += 1
    return partidos

@st.cache_data(ttl=180, show_spinner=False)
def procesar_archivos_subidos(archivos) -> dict:
    datos = {}
    for file in archivos:
        name = file.name.lower()
        # Intentar extraer el número de fecha del nombre del archivo
        m = re.search(r"fecha\s*(\d+)", name, re.IGNORECASE)
        nf_base = int(m.group(1)) if m else 1
        
        try:
            if name.endswith('.csv'):
                df = pd.read_csv(file, header=None)
                datos[nf_base] = parse_dataframe(df, nf_base)
            elif name.endswith('.xlsx'):
                xl = pd.ExcelFile(file, engine="openpyxl")
                for hoja in xl.sheet_names:
                    if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE): continue
                    nf = int(re.search(r"\d+", hoja).group())
                    df = pd.read_excel(xl, sheet_name=hoja, header=None)
                    datos[nf] = parse_dataframe(df, nf)
        except Exception as e:
            st.error(f"Error procesando {file.name}: {e}")
    return datos

def construir_df(datos: dict) -> pd.DataFrame:
    filas = []
    for nf, partidos in datos.items():
        for p in partidos:
            for met, vals in p["stats"].items():
                base = {"nFecha": nf, "Métrica": met}
                filas.append({**base, "Equipo": p["local"], "Rival": p["visitante"], "Condicion": "Local", "Propio": vals["local"], "Concedido": vals["visitante"]})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"], "Condicion": "Visitante", "Propio": vals["visitante"], "Concedido": vals["local"]})
    return pd.DataFrame(filas)

# ──────────────────────────────────────────────────────────────────────
# xG SINTÉTICO & CÁLCULOS
# ──────────────────────────────────────────────────────────────────────
XG_W = {"Tiros al arco": 0.35, "Ocasiones claras": 0.40, "Tiros dentro del área": 0.15, "Tiros totales": 0.10}
XG_RATE = {"Tiros al arco": 0.25, "Ocasiones claras": 0.35, "Tiros dentro del área": 0.12, "Tiros totales": 0.08}

def xg_sintetico(df_partido: dict) -> float:
    return round(sum(df_partido.get(m, 0.0) * XG_W[m] * XG_RATE[m] for m in XG_W), 3)

def wmean(values, fechas, max_f, n_rec, w_rec, w_norm):
    if len(values) == 0: return np.nan
    w = np.where(np.array(fechas, dtype=float) >= (max_f - n_rec + 1), w_rec, w_norm)
    return float(np.average(values, weights=w))

def get_metric(df, equipo, condicion, metrica, max_f, n_rec=3, w_rec=1.5, w_norm=1.0):
    sub = df[(df["Equipo"] == equipo) & (df["Condicion"] == condicion) & (df["Métrica"] == metrica)]
    if sub.empty: sub = df[(df["Equipo"] == equipo) & (df["Métrica"] == metrica)]
    return (np.nan, 0) if sub.empty else (wmean(sub["Propio"].values, sub["nFecha"].values, max_f, n_rec, w_rec, w_norm), len(sub))

@st.cache_data(ttl=180, show_spinner=False)
def calcular_xg_df(datos_raw: dict) -> pd.DataFrame:
    filas = []
    for nf, partidos in datos_raw.items():
        for p in partidos:
            xg_l = xg_sintetico({k: v["local"] for k, v in p["stats"].items()})
            xg_v = xg_sintetico({k: v["visitante"] for k, v in p["stats"].items()})
            g_l = p["stats"].get("Resultado", {}).get("local", np.nan)
            g_v = p["stats"].get("Resultado", {}).get("visitante", np.nan)
            filas.append({"nFecha": nf, "Equipo": p["local"], "Rival": p["visitante"], "Condicion": "Local", "xG": xg_l, "Goles": g_l})
            filas.append({"nFecha": nf, "Equipo": p["visitante"], "Rival": p["local"], "Condicion": "Visitante", "xG": xg_v, "Goles": g_v})
    return pd.DataFrame(filas)

def tabla_resumen(df, equipos, xg_df):
    rows = []
    for eq in equipos:
        sub_g = df[(df["Equipo"] == eq) & (df["Métrica"] == "Resultado")]
        sub_xg = xg_df[xg_df["Equipo"] == eq]
        goles_f, goles_c = sub_g["Propio"].mean(), sub_g["Concedido"].mean()
        xg_f = sub_xg["xG"].mean()
        pts = sub_g.apply(lambda r: 3 if r["Propio"] > r["Concedido"] else (1 if r["Propio"] == r["Concedido"] else 0), axis=1).sum()
        rows.append({"Equipo": eq, "PJ": len(sub_g), "PTS": pts, "xGF/PJ": round(xg_f, 2) if pd.notna(xg_f) else 0,
                     "GF/PJ": round(goles_f, 2) if pd.notna(goles_f) else 0, "GC/PJ": round(goles_c, 2) if pd.notna(goles_c) else 0})
    return pd.DataFrame(rows).sort_values("PTS", ascending=False).reset_index(drop=True)

# MOTOR DE PREDICCIÓN
def calcular_lambdas(df, xg_df, ea, eb, es_local, k, nr, wr, wn, h_atk, h_def, sc):
    max_f = df["nFecha"].max()
    ca, cb = ("Local", "Visitante") if es_local else ("Visitante", "Local")
    
    ref_h = xg_df[xg_df["Condicion"] == "Local"]["xG"].mean() if not xg_df.empty else 1.0
    ref_a = xg_df[xg_df["Condicion"] == "Visitante"]["xG"].mean() if not xg_df.empty else 1.0
    ra_a, ra_b = (ref_h, ref_a) if es_local else (ref_a, ref_h)

    def gxg(eq, cond):
        s = xg_df[(xg_df["Equipo"] == eq) & (xg_df["Condicion"] == cond)]
        s = xg_df[xg_df["Equipo"] == eq] if s.empty else s
        return (wmean(s["xG"].values, s["nFecha"].values, max_f, nr, wr, wn), len(s)) if not s.empty else (np.nan, 0)
    
    xga, na = gxg(ea, ca); xgb, nb = gxg(eb, cb)
    xga = xga if pd.notna(xga) else ra_a; xgb = xgb if pd.notna(xgb) else ra_b

    def def_idx(eq, cond):
        q, _ = get_metric(df, eq, cond, "Quites", max_f, nr, wr, wn)
        i, _ = get_metric(df, eq, cond, "Intercepciones", max_f, nr, wr, wn)
        lq, li = df[df["Métrica"] == "Quites"]["Propio"].mean(), df[df["Métrica"] == "Intercepciones"]["Propio"].mean()
        q = q if pd.notna(q) else lq; i = i if pd.notna(i) else li
        pr = 0.5 * (q/max(lq,1)) + 0.5 * (i/max(li,1))
        return 1.0 / max(pr, 0.5) if pd.notna(pr) else 1.0

    atk_a = (na * (xga / max(ra_a, 1e-6)) + k) / (na + k)
    atk_b = (nb * (xgb / max(ra_b, 1e-6)) + k) / (nb + k)
    def_a, def_b = (na * def_idx(ea, ca) + k) / (na + k), (nb * def_idx(eb, cb) + k) / (nb + k)

    la, lb = ra_a * atk_a * def_b, ra_b * atk_b * def_a
    la, lb = (la * h_atk * sc, lb * h_def * sc) if es_local else (la * h_def * sc, lb * h_atk * sc)

    g_a, _ = get_metric(df, ea, ca, "Resultado", max_f, nr, wr, wn)
    g_b, _ = get_metric(df, eb, cb, "Resultado", max_f, nr, wr, wn)
    if pd.notna(g_a) and na >= 3: la = 0.6 * la + 0.4 * g_a
    if pd.notna(g_b) and nb >= 3: lb = 0.6 * lb + 0.4 * g_b

    return round(np.clip(la, 0.2, 5.0), 3), round(np.clip(lb, 0.2, 5.0), 3), na, nb

def simular(la: float, lb: float, rho: float):
    pa = np.array([math.exp(k*math.log(max(la,1e-9))-la-math.lgamma(k+1)) for k in range(MAX_G+1)])
    pb = np.array([math.exp(k*math.log(max(lb,1e-9))-lb-math.lgamma(k+1)) for k in range(MAX_G+1)])
    M = np.outer(pa, pb)
    tau = np.zeros((2, 2))
    tau[0,0], tau[1,0], tau[0,1], tau[1,1] = 1-la*lb*rho, 1+lb*rho, 1+la*rho, 1-rho
    for i in range(2): 
        for j in range(2): M[i,j] = max(M[i,j]*tau[i,j], 0)
    M /= M.sum()
    return {"vic": float(np.tril(M,-1).sum()), "emp": float(np.trace(M)), "der": float(np.triu(M,1).sum()), "mat": M}

# ──────────────────────────────────────────────────────────────────────
# GRÁFICOS
# ──────────────────────────────────────────────────────────────────────
def plot_radar(df, ea, eb):
    mets = ["Posesión de balón", "Tiros totales", "Tiros al arco", "Ocasiones claras", "Pases totales", "Quites", "Intercepciones"]
    mets = [m for m in mets if m in df["Métrica"].values]
    if not mets: return go.Figure()
    
    def gv(eq, m): 
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        return d["Propio"].mean() if not d.empty else 0.0

    va, vb = [gv(ea, m) for m in mets], [gv(eb, m) for m in mets]
    maxv = [max(va[i], vb[i], 1e-9) for i in range(len(mets))]
    van, vbn = [va[i]/maxv[i] for i in range(len(mets))], [vb[i]/maxv[i] for i in range(len(mets))]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=van+[van[0]], theta=mets+[mets[0]], fill="toself", name=ea, line=dict(color=RED)))
    fig.add_trace(go.Scatterpolar(r=vbn+[vbn[0]], theta=mets+[mets[0]], fill="toself", name=eb, line=dict(color=BLUE)))
    fig.update_layout(**PLOT, height=400, polar=dict(radialaxis=dict(visible=False)), title="Radar de Rendimiento Promedio")
    return fig

# ──────────────────────────────────────────────────────────────────────
# SIDEBAR Y FLUJO PRINCIPAL
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ LPF Scouting 2026")
    
    # NUEVO: Subir múltiples archivos en vez de buscar una ruta de texto
    archivos_subidos = st.file_uploader(
        "📂 Subir archivo(s) de datos (.csv o .xlsx)", 
        type=["csv", "xlsx"], 
        accept_multiple_files=True
    )
    
    st.divider()
    nav = st.radio("Navegación", ["🔮 Predictor de Partidos", "📊 Métricas y Rankings", "🕸️ Head to Head", "🛡️ Análisis vs Nivel de Rival"])
    
    with st.expander("⚙️ Parámetros Avanzados (Modelo)"):
        k_shrink = st.slider("Shrinkage (K)", 1.0, 8.0, 4.0)
        n_rec = st.slider("Fechas Recencia", 2, 6, 3)
        h_atk = st.slider("Bono Local (Atk)", 1.0, 1.3, 1.12)
        h_def = st.slider("Bono Local (Def)", 0.75, 1.0, 0.90)
        scaling = st.slider("Scaling (Under/Over)", 0.7, 1.1, 0.88)
        rho_dc = st.slider("ρ Dixon-Coles", -0.3, 0.0, -0.1)

# Verificación de que haya archivos cargados
if not archivos_subidos:
    st.info("👈 Por favor, subí tus archivos CSV (Ej: Fecha 1.csv, Fecha 2.csv) desde el menú lateral izquierdo para comenzar el análisis.")
    st.stop()

with st.spinner("Procesando matriz de datos..."):
    datos_raw = procesar_archivos_subidos(archivos_subidos)
    df = construir_df(datos_raw)
    
if df.empty:
    st.error("⚠️ No se pudieron extraer datos. Asegúrate de que los archivos tengan el formato correcto de SofaScore/Scouting.")
    st.stop()
    
xg_df = calcular_xg_df(datos_raw)
equipos = sorted(df["Equipo"].unique())
tabla_pos = tabla_resumen(df, equipos, xg_df)

# ──────────────────────────────────────────────────────────────────────
# 1. PREDICTOR DE PARTIDOS
# ──────────────────────────────────────────────────────────────────────
if nav == "🔮 Predictor de Partidos":
    st.markdown('<div class="section-title">🔮 Simulación de Partido</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([4, 4, 2])
    ea = c1.selectbox("🏠 Equipo Local", equipos)
    eb = c2.selectbox("✈️ Equipo Visitante", equipos, index=min(1, len(equipos)-1))
    es_local = c3.toggle("Aplicar factor localía", True)

    if st.button("Simular Escenarios", use_container_width=True, type="primary"):
        if ea == eb: st.warning("Seleccioná equipos distintos."); st.stop()
        la, lb, na, nb = calcular_lambdas(df, xg_df, ea, eb, es_local, k_shrink, n_rec, 1.6, 1.0, h_atk, h_def, scaling)
        s = simular(la, lb, rho_dc)
        M = s["mat"]
        
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi-container"><div class="kpi-title">Gana {ea}</div><div class="kpi-value">{s["vic"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-container kpi-draw"><div class="kpi-title">Empate</div><div class="kpi-value">{s["emp"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-container kpi-loss"><div class="kpi-title">Gana {eb}</div><div class="kpi-value">{s["der"]*100:.1f}%</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Distribución de Goles (Matriz)", "Líneas Over/Under"])
        
        with t1:
            best = np.unravel_index(M[:6, :6].argmax(), M[:6, :6].shape)
            st.success(f"**Marcador más probable:** {ea} {best[0]} - {best[1]} {eb} (Probabilidad: {M[best]*100:.1f}%)")
            fig = go.Figure(go.Heatmap(z=M[:6,:6], x=[f"{j} {eb[:5]}" for j in range(6)], y=[f"{i} {ea[:5]}" for i in range(6)], colorscale="Reds"))
            fig.update_layout(**PLOT, height=350, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
            
        with t2:
            o25 = sum(M[i,j] for i in range(MAX_G) for j in range(MAX_G) if i+j > 2.5)
            bts = 1 - M[0, :].sum() - M[:, 0].sum() + M[0, 0]
            m1, m2 = st.columns(2)
            m1.metric("Over 2.5 Goles", f"{o25*100:.1f}%")
            m2.metric("Ambos Anotan (BTTS)", f"{bts*100:.1f}%")

# ──────────────────────────────────────────────────────────────────────
# 2. MÉTRICAS Y RANKINGS
# ──────────────────────────────────────────────────────────────────────
elif nav == "📊 Métricas y Rankings":
    st.markdown('<div class="section-title">📊 Tablas y Eficiencia Ofensiva</div>', unsafe_allow_html=True)
    st.dataframe(tabla_pos.style.background_gradient(subset=["xGF/PJ", "GF/PJ"], cmap="Greens").background_gradient(subset=["GC/PJ"], cmap="Reds"), use_container_width=True, height=400)
    
    st.markdown("### xG Sintético vs Realidad")
    fig = go.Figure(go.Scatter(
        x=tabla_pos["xGF/PJ"], y=tabla_pos["GF/PJ"], mode="markers+text", text=tabla_pos["Equipo"], textposition="top center",
        marker=dict(size=12, color=RED)
    ))
    max_val = max(tabla_pos["xGF/PJ"].max(), tabla_pos["GF/PJ"].max()) * 1.1
    fig.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val], mode="lines", line=dict(color=GRAY, dash="dash"), name="Identidad"))
    fig.update_layout(**PLOT, xaxis_title="xG Esperado por Partido", yaxis_title="Goles Reales por Partido", height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# 3. HEAD TO HEAD (H2H)
# ──────────────────────────────────────────────────────────────────────
elif nav == "🕸️ Head to Head":
    st.markdown('<div class="section-title">🕸️ Comparativa Directa (H2H)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    ea = c1.selectbox("Equipo 1", equipos, key="h2h_1")
    eb = c2.selectbox("Equipo 2", equipos, index=min(1, len(equipos)-1), key="h2h_2")
    
    st.plotly_chart(plot_radar(df, ea, eb), use_container_width=True)
    
    def get_promedios(eq):
        return df[df["Equipo"] == eq].groupby("Métrica")["Propio"].mean().round(2)
    
    comp = pd.DataFrame({ea: get_promedios(ea), eb: get_promedios(eb)}).dropna()
    st.dataframe(comp.T, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────
# 4. ANÁLISIS VS TIPO DE RIVAL
# ──────────────────────────────────────────────────────────────────────
elif nav == "🛡️ Análisis vs Nivel de Rival":
    st.markdown('<div class="section-title">🛡️ Rendimiento según Jerarquía del Rival</div>', unsafe_allow_html=True)
    st.info("Divide a los oponentes en 3 niveles (Top, Medio, Bajo) según la tabla general actual para ver cómo rinde un equipo dependiendo de la exigencia del partido.")
    
    n_teams = len(equipos)
    tabla_pos['Rank'] = tabla_pos['PTS'].rank(method='min', ascending=False)
    
    def asignar_tier(rank):
        if rank <= n_teams / 3: return "1. Nivel Top"
        elif rank <= (2 * n_teams) / 3: return "2. Nivel Medio"
        else: return "3. Nivel Bajo"
        
    tabla_pos['Tier'] = tabla_pos['Rank'].apply(asignar_tier)
    tier_map = dict(zip(tabla_pos['Equipo'], tabla_pos['Tier']))
    
    eq_analisis = st.selectbox("Seleccionar Equipo para Analizar:", equipos)
    
    partidos_eq = df[(df["Equipo"] == eq_analisis) & (df["Métrica"] == "Resultado")].copy()
    partidos_eq['Nivel_Rival'] = partidos_eq['Rival'].map(tier_map)
    
    xg_fav = xg_df[xg_df["Equipo"] == eq_analisis][['nFecha', 'Rival', 'xG']].rename(columns={'xG': 'xGF'})
    xg_con = xg_df[xg_df["Rival"] == eq_analisis][['nFecha', 'Equipo', 'xG']].rename(columns={'xG': 'xGC', 'Equipo': 'Rival'})
    
    completo = partidos_eq.merge(xg_fav, on=['nFecha', 'Rival'], how='left').merge(xg_con, on=['nFecha', 'Rival'], how='left')
    
    if not completo.empty:
        res_tier = completo.groupby("Nivel_Rival").agg(
            PJ=("nFecha", "count"),
            Goles_AFavor=("Propio", "mean"),
            Goles_EnContra=("Concedido", "mean"),
            xG_Generado=("xGF", "mean"),
            xG_Concedido=("xGC", "mean")
        ).round(2).reset_index()
        
        st.dataframe(res_tier, use_container_width=True)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name='xG Generado', x=res_tier['Nivel_Rival'], y=res_tier['xG_Generado'], marker_color=BLUE))
        fig.add_trace(go.Bar(name='xG Concedido', x=res_tier['Nivel_Rival'], y=res_tier['xG_Concedido'], marker_color=RED))
        fig.update_layout(**PLOT, barmode='group', title=f"xG de {eq_analisis} según exigencia", yaxis_title="xG Promedio")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay suficientes partidos registrados para generar este reporte.")
