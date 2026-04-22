```python
# dashboard_lpf_v8.py — LPF 2026 Scouting Dashboard (V8 - Market Realism)

import re, os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="LPF 2026 · Scouting", layout="wide")

MONTECARLO_N = 15000
N_RECENCIA = 3
PESO_RECIENTE = 2.5
PESO_NORMAL = 1.0

# NUEVO
RHO_DC = 0.08
DRAW_BIAS = 1.06

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def num(v):
    try:
        return float(str(v).replace("%","").replace(",","."))
    except:
        return 0.0

def soft_clip(x):
    if x > 1.25: return 1.25 + (x - 1.25) * 0.35
    if x < 0.75: return 0.75 - (0.75 - x) * 0.35
    return x

def final_clip(lam):
    return 0.25 + (lam - 0.25) * 0.75

# ─────────────────────────────────────────────────────────────
# DIXON COLES
# ─────────────────────────────────────────────────────────────
def dc_adj(a, b):
    if a==0 and b==0: return 1 - RHO_DC
    if a==1 and b==0: return 1 + RHO_DC
    if a==0 and b==1: return 1 + RHO_DC
    if a==1 and b==1: return 1 - RHO_DC
    return 1

# ─────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────
@st.cache_data
def cargar_excel(path):
    xl = pd.ExcelFile(path)
    res = {}
    for hoja in xl.sheet_names:
        if not re.search(r"fecha", hoja, re.I): continue
        df = pd.read_excel(path, sheet_name=hoja, header=None)
        partidos, i = [], 0
        while i < len(df):
            c = str(df.iloc[i,0])
            if "vs" in c:
                loc, vis = c.split("vs")
                loc, vis = loc.strip(), vis.strip()
                stats, j = {}, i+1
                while j < len(df):
                    r = str(df.iloc[j,0])
                    if "vs" in r or r=="": break
                    stats[r] = {
                        "local": num(df.iloc[j,1]),
                        "visitante": num(df.iloc[j,2])
                    }
                    j+=1
                partidos.append({"local":loc,"visitante":vis,"metricas":stats})
                i=j
            else:
                i+=1
        if partidos: res[hoja]=partidos
    return res

def construir_df(data):
    rows=[]
    for f,partidos in data.items():
        nf=int(re.search(r"\d+",f).group())
        for p in partidos:
            for m,v in p["metricas"].items():
                rows.append([nf,p["local"],p["visitante"],"Local",m,v["local"],v["visitante"]])
                rows.append([nf,p["visitante"],p["local"],"Visitante",m,v["visitante"],v["local"]])
    return pd.DataFrame(rows,columns=["nFecha","Equipo","Rival","Condicion","Métrica","Propio","Concedido"])

# ─────────────────────────────────────────────────────────────
# LAMBDAS (MEJORADO)
# ─────────────────────────────────────────────────────────────
def calcular_lambdas(df, a, b, local=True):

    df_r = df[df["Métrica"]=="Resultado"]

    def stats(eq):
        d = df_r[df_r["Equipo"]==eq]
        gf = d["Propio"].mean()
        gc = d["Concedido"].mean()
        return gf, gc

    gfa, gca = stats(a)
    gfb, gcb = stats(b)

    base = df_r["Propio"].mean()

    lam_a = soft_clip(gfa/base) * soft_clip(gcb/base) * base
    lam_b = soft_clip(gfb/base) * soft_clip(gca/base) * base

    # ── xG ──
    df_xg = df[df["Métrica"].str.contains("xG", na=False)]

    if not df_xg.empty:
        xa = df_xg[df_xg["Equipo"]==a]["Propio"].mean()
        xb = df_xg[df_xg["Equipo"]==b]["Propio"].mean()

        if xa>0:
            conv_a = soft_clip(gfa/max(xa,0.01))
            lam_a *= (0.85 + 0.30*conv_a)

        if xb>0:
            conv_b = soft_clip(gfb/max(xb,0.01))
            lam_b *= (0.85 + 0.30*conv_b)

    # localía
    if local:
        lam_a *= 1.08
        lam_b *= 0.92

    lam_a = final_clip(lam_a)
    lam_b = final_clip(lam_b)

    return lam_a, lam_b

# ─────────────────────────────────────────────────────────────
# MONTECARLO (MEJORADO)
# ─────────────────────────────────────────────────────────────
def montecarlo(lam_a, lam_b):

    rng = np.random.default_rng(42)
    ga = rng.poisson(lam_a, MONTECARLO_N)
    gb = rng.poisson(lam_b, MONTECARLO_N)

    probs=[]
    for r in range(8):
        for v in range(8):
            base = np.mean((ga==r)&(gb==v))
            probs.append([r,v,base*dc_adj(r,v)])

    df = pd.DataFrame(probs,columns=["A","B","prob"])
    df["prob"] /= df["prob"].sum()

    win = df[df.A>df.B]["prob"].sum()
    draw = df[df.A==df.B]["prob"].sum()
    loss = df[df.A<df.B]["prob"].sum()

    # ajuste empate
    draw *= DRAW_BIAS

    tot = win+draw+loss
    win/=tot; draw/=tot; loss/=tot

    return win, draw, loss, df

# ─────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────
st.title("LPF Predictor V8")

file = st.text_input("Excel", "Fecha_x_fecha_lpf.xlsx")

if os.path.exists(file):
    data = cargar_excel(file)
    df = construir_df(data)

    equipos = sorted(df["Equipo"].unique())

    a = st.selectbox("Local", equipos)
    b = st.selectbox("Visitante", equipos)

    if st.button("Simular"):

        lam_a, lam_b = calcular_lambdas(df, a, b, True)
        win, draw, loss, dist = montecarlo(lam_a, lam_b)

        st.write("λ:", lam_a, lam_b)
        st.write("Local:", round(win*100,1),"%")
        st.write("Empate:", round(draw*100,1),"%")
        st.write("Visitante:", round(loss*100,1),"%")

        top = dist.sort_values("prob",ascending=False).head(10)
        st.dataframe(top)
```
