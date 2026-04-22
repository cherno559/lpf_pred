"""
dashboard_lpf.py — LPF 2026 Scouting Dashboard (v8 - Log-Smoothing)
────────────────────────────────────────────────────
Mejoras Finales:
  · Sustitución de Clipping por Transformación Logarítmica Suavizada.
  · Calibrador Anti-Empate optimizado para la nueva escala.
  · Blend 70/30 (Local-General) se mantiene como base de datos sólida.
"""

import re, os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Scouting", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp { background: #080d18; color: #dde3ee; }
h1 { font-family:'Bebas Neue',cursive !important; color:#e63946 !important; letter-spacing:3px; }
.section-title { font-family:'Bebas Neue',cursive; font-size:1.3rem; color:#e63946; border-bottom:1px solid #1c2a40; padding-bottom:8px; margin:28px 0 18px; }
.kpi { background:linear-gradient(135deg,#0f1829,#162035); border:1px solid #1c2a40; border-left:4px solid #e63946; border-radius:10px; padding:16px 18px; text-align:center; }
.kpi.draw { border-left-color:#64748b; }
.kpi.loss { border-left-color:#3b82f6; }
.val { font-family:'Bebas Neue'; font-size:38px; color:#e63946; }
.kpi.draw .val { color:#94a3b8; }
.kpi.loss .val { color:#60a5fa; }
.note { background:#0f1829; border:1px solid #1c2a40; border-radius:8px; padding:10px 14px; font-size:12px; color:#64748b; margin-top:8px; }
</style>
""", unsafe_allow_html=True)

MONTECARLO_N = 15_000
RED, BLUE, GRAY = "#e63946", "#3b82f6", "#64748b"
PLOT = dict(font=dict(family="Inter", size=13, color="#dde3ee"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

# ──────────────────────────────────────────────────────────────────────
# PROCESAMIENTO DE DATOS
# ──────────────────────────────────────────────────────────────────────
def num(v):
    if isinstance(v, str): v = v.replace('%', '').replace(',', '.').strip()
    try: return float(v)
    except: return 0.0

@st.cache_data(ttl=120)
def cargar_y_limpiar(ruta):
    if not os.path.exists(ruta): return None
    xl = pd.ExcelFile(ruta, engine="openpyxl")
    filas = []
    for hoja in xl.sheet_names:
        if not re.search(r"fecha\s*\d+", hoja, re.IGNORECASE): continue
        nf = int(re.search(r"\d+", hoja).group())
        df = pd.read_excel(ruta, sheet_name=hoja, header=None)
        i = 0
        while i < len(df):
            c0 = str(df.iloc[i, 0])
            if " vs " in c0.lower():
                loc, vis = re.split(r" vs ", c0, flags=re.IGNORECASE)
                j = i + 1
                while j < len(df):
                    r0 = str(df.iloc[j, 0]).strip()
                    if r0 == "" or " vs " in r0.lower(): break
                    r1, r2 = df.iloc[j, 1], df.iloc[j, 2]
                    if pd.notna(r1):
                        filas.append({"nFecha": nf, "Equipo": loc.strip(), "Rival": vis.strip(), "Condicion": "Local", "Métrica": r0, "Propio": num(r1), "Concedido": num(r2)})
                        filas.append({"nFecha": nf, "Equipo": vis.strip(), "Rival": loc.strip(), "Condicion": "Visitante", "Métrica": r0, "Propio": num(r2), "Concedido": num(r1)})
                    j += 1
                i = j
            else: i += 1
    return pd.DataFrame(filas)

# ──────────────────────────────────────────────────────────────────────
# MOTOR MATEMÁTICO V8
# ──────────────────────────────────────────────────────────────────────
def log_smooth(x, factor=0.65):
    """ Compresión logarítmica para evitar explosión de Poisson """
    if x <= 0: return 0.01
    # Mantiene el 1.0 intacto, comprime los valores > 1 y < 1 suavemente
    return np.exp(factor * np.log(x))

def calcular_lambdas(df, eq_a, eq_b, es_local):
    df_r = df[df["Métrica"] == "Resultado"]
    if df_r.empty: return 1.2, 1.0
    
    # Agregados
    agg = df_r.groupby(["Equipo", "Condicion"]).agg(GF=("Propio", "mean"), GC=("Concedido", "mean"), PJ=("Propio", "count")).reset_index()
    gen = df_r.groupby("Equipo").agg(GF=("Propio", "mean"), GC=("Concedido", "mean")).reset_index()
    
    m_gf_loc = df_r[df_r["Condicion"]=="Local"]["Propio"].mean()
    m_gf_vis = df_r[df_r["Condicion"]=="Visitante"]["Propio"].mean()
    m_gf_all = df_r["Propio"].mean()

    def get_strength(eq, cond):
        row_c = agg[(agg["Equipo"] == eq) & (agg["Condicion"] == cond)]
        row_g = gen[gen["Equipo"] == eq]
        if row_g.empty: return 1.0, 1.0
        
        # Blend 70/30
        w = 0.7 if (not row_c.empty and row_c.iloc[0]["PJ"] >= 3) else 0.4
        gf = (row_c.iloc[0]["GF"] if not row_c.empty else m_gf_all) * w + row_g.iloc[0]["GF"] * (1-w)
        gc = (row_c.iloc[0]["GC"] if not row_c.empty else m_gf_all) * w + row_g.iloc[0]["GC"] * (1-w)
        
        ref_f = m_gf_loc if cond == "Local" else m_gf_vis
        return gf / ref_f, gc / ref_f

    cA, cB = ("Local" if es_local else "Visitante"), ("Visitante" if es_local else "Local")
    ata_a, def_a = get_strength(eq_a, cA)
    ata_b, def_b = get_strength(eq_b, cB)

    # APLICACIÓN DE LOG-SMOOTH (La clave de la v8)
    lam_a = log_smooth(ata_a * def_b) * (m_gf_loc if es_local else m_gf_vis)
    lam_b = log_smooth(ata_b * def_a) * (m_gf_vis if es_local else m_gf_loc)

    # Calibrador Anti-Empate (solo si son muy parecidos)
    if abs(lam_a - lam_b) < 0.4:
        if lam_a > lam_b: lam_a *= 1.08; lam_b *= 0.92
        else: lam_b *= 1.08; lam_a *= 0.92

    return round(lam_a, 3), round(lam_b, 3)

def simular(la, lb):
    rng = np.random.default_rng(int((la+lb)*100))
    ga, gb = rng.poisson(la, MONTECARLO_N), rng.poisson(lb, MONTECARLO_N)
    return {"V_A": np.mean(ga > gb), "E": np.mean(ga == gb), "V_B": np.mean(ga < gb), "ga": ga, "gb": gb}

# ──────────────────────────────────────────────────────────────────────
# INTERFAZ
# ──────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## ⚽ LPF 2026")
ruta = st.sidebar.text_input("Excel", "Fecha_x_fecha_lpf.xlsx")
df = cargar_y_limpiar(ruta)

if df is not None:
    equipos = sorted(df["Equipo"].unique())
    st.markdown("<h1>LPF 2026 · Predictor Pro v8</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([4, 4, 2])
    eq_a = col1.selectbox("Local", equipos)
    eq_b = col2.selectbox("Visitante", equipos, index=1)
    es_loc = col3.toggle("Ventaja Local", True)
    
    la, lb = calcular_lambdas(df, eq_a, eq_b, es_loc)
    res = simular(la, lb)
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="kpi"><div class="val">{res["V_A"]*100:.1f}%</div><div>{eq_a}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi draw"><div class="val">{res["E"]*100:.1f}%</div><div>Empate</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi loss"><div class="val">{res["V_B"]*100:.1f}%</div><div>{eq_b}</div></div>', unsafe_allow_html=True)
    
    st.markdown(f'<div class="note">⚙️ Matemática Log-Smooth | λ {eq_a}: {la} | λ {eq_b}: {lb}</div>', unsafe_allow_html=True)
    
    # Gráfico de Marcadores
    df_m = pd.DataFrame({"A": res["ga"], "B": res["gb"]})
    top8 = df_m.value_counts().nlargest(8).reset_index()
    top8["Marcador"] = top8["A"].astype(str) + " - " + top8["B"].astype(str)
    
    fig = go.Figure(go.Bar(x=top8["Marcador"], y=(top8["count"]/MONTECARLO_N)*100, marker_color=RED))
    fig.update_layout(**PLOT, title="Top 8 Marcadores Probables (%)", height=300)
    st.plotly_chart(fig, use_container_width=True)
