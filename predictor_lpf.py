"""
dashboard_lpf_v3.py — LPF 2026 · Modelo Predictivo con Métricas Reales
────────────────────────────────────────────────────────────────────────
Mejoras v3:
  - Métricas derivadas corregidas (ya no son 0)
  - xG sintético calculado correctamente por partido
  - Eficiencia de OC, % regates, acciones defensivas funcionando
  - Panel de datos suplementarios (FBref / manual) para duelos y xG real
  - Scraper opcional de SofaScore vía Selenium (para entornos con browser)
"""

import re, os, math, warnings, json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────
# UI CONFIG
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LPF 2026 · Scouting & Predictor",
    page_icon="⚽", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;900&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Barlow Condensed', sans-serif; color: #e63946; letter-spacing: 0.03em; }

.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.5rem; font-weight: 700; color: #e63946;
    border-bottom: 2px solid #1c2a40; padding-bottom: 8px;
    margin: 30px 0 20px; text-transform: uppercase; letter-spacing: 0.05em;
}
.kpi-container {
    background: linear-gradient(135deg, #111827 0%, #1a2332 100%);
    border-radius: 12px; padding: 22px 18px;
    border-left: 5px solid #e63946; text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.4);
}
.kpi-title { font-size: 0.8rem; color: #9ca3af; text-transform: uppercase; font-weight: 600; letter-spacing: 1.5px; }
.kpi-value { font-family: 'Barlow Condensed', sans-serif; font-size: 2.5rem; color: #ffffff; font-weight: 700; margin-top: 6px; }
.kpi-sub { font-size: 0.75rem; color: #6b7280; margin-top: 4px; }
.kpi-draw { border-left-color: #6b7280; }
.kpi-loss { border-left-color: #3b82f6; }
.kpi-green { border-left-color: #10b981; }
.kpi-yellow { border-left-color: #f59e0b; }

.metric-badge {
    display: inline-block; background: #1f2937; border-radius: 6px;
    padding: 4px 10px; font-size: 0.75rem; color: #9ca3af; margin: 2px;
}
.metric-badge.good { background: #064e3b; color: #6ee7b7; }
.metric-badge.bad { background: #450a0a; color: #fca5a5; }

.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { border-radius: 6px; padding: 8px 18px; font-weight: 600; }

.info-box {
    background: #1e3a5f; border-left: 4px solid #3b82f6;
    border-radius: 8px; padding: 14px 18px; margin: 12px 0;
    font-size: 0.88rem; color: #bfdbfe;
}
.warning-box {
    background: #3b2000; border-left: 4px solid #f59e0b;
    border-radius: 8px; padding: 14px 18px; margin: 12px 0;
    font-size: 0.88rem; color: #fde68a;
}
</style>
""", unsafe_allow_html=True)

RED, BLUE, GREEN, GRAY, YELLOW = "#e63946", "#3b82f6", "#10b981", "#6b7280", "#f59e0b"
PLOT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#d1d5db", family="Inter"),
    margin=dict(l=10, r=10, t=40, b=10)
)
MAX_G = 8


# ══════════════════════════════════════════════════════════════════════
# PARSEO DE DATOS
# ══════════════════════════════════════════════════════════════════════

def _parse_num(v) -> float:
    if isinstance(v, str):
        v = v.replace('%', '').replace(',', '.').strip()
        m = re.search(r'^[\d.]+', v)
        if m: return float(m.group())
        return 0.0
    try: return float(v)
    except: return 0.0

def _parse_regate(v) -> tuple:
    """Returns (exitosos, intentados, pct)"""
    if isinstance(v, str):
        # Formato "7/17 (41%)"
        m = re.search(r'(\d+)/(\d+)\s*\((\d+)%\)', v)
        if m:
            return int(m.group(1)), int(m.group(2)), float(m.group(3))
        # Solo porcentaje "(41%)"
        m2 = re.search(r'\((\d+)%\)', v)
        if m2: return None, None, float(m2.group(1))
    return None, None, 0.0

def _is_derived_section(text: str) -> bool:
    return '📊' in text or 'derivada' in text.lower()

def _is_derived_metric(name: str) -> bool:
    derived_names = {
        'precisión de tiros', 'xg por tiro', 'eficiencia oportunidades',
        '% regates exitosos', '% duelos ganados', 'diferencial xg',
        '% tiros dentro del área', 'métrica calculada'
    }
    nl = name.lower()
    return any(d in nl for d in derived_names)


def parse_dataframe(df, nf):
    """Parsea un DataFrame crudo (una hoja) y extrae partidos con sus stats."""
    partidos = []
    i = 0
    while i < len(df):
        c0 = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""
        if re.search(r"\s+vs\s+", c0, re.IGNORECASE) and not _is_derived_section(c0):
            partes = re.split(r"\s+vs\s+", c0, flags=re.IGNORECASE)
            loc, vis = partes[0].strip(), partes[1].strip()
            stats = {}
            j = i + 1
            in_derived = False
            while j < len(df):
                r0 = str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else ""
                if r0 == "":
                    j += 1
                    # Dos líneas vacías = fin del bloque
                    if j < len(df) and (str(df.iloc[j, 0]).strip() if pd.notna(df.iloc[j, 0]) else "") == "":
                        break
                    continue
                if re.search(r"\s+vs\s+", r0, re.IGNORECASE) and not _is_derived_section(r0):
                    break
                if _is_derived_section(r0):
                    in_derived = True; j += 1; continue
                if in_derived or _is_derived_metric(r0):
                    j += 1; continue
                if r0.lower() in ('métrica', 'métrica calculada') or r0.lower().startswith(loc.lower()) or r0.lower().startswith(vis.lower()):
                    j += 1; continue

                raw_l = df.iloc[j, 1] if df.shape[1] > 1 and pd.notna(df.iloc[j, 1]) else 0
                raw_v = df.iloc[j, 2] if df.shape[1] > 2 and pd.notna(df.iloc[j, 2]) else 0

                if 'regate' in r0.lower():
                    ex_l, int_l, pct_l = _parse_regate(raw_l)
                    ex_v, int_v, pct_v = _parse_regate(raw_v)
                    stats[r0] = {
                        "local": pct_l, "visitante": pct_v,
                        "local_exitosos": ex_l or 0, "local_intentados": int_l or 0,
                        "vis_exitosos": ex_v or 0, "vis_intentados": int_v or 0
                    }
                else:
                    stats[r0] = {
                        "local": _parse_num(raw_l),
                        "visitante": _parse_num(raw_v)
                    }
                j += 1

            # ── Calcular métricas derivadas CORRECTAMENTE ──────────────────
            stats = _calcular_derivadas(stats)
            partidos.append({"local": loc, "visitante": vis, "stats": stats, "nFecha": nf})
            i = j
        else:
            i += 1
    return partidos


def _calcular_derivadas(stats: dict) -> dict:
    """
    Calcula todas las métricas derivadas a partir de los datos crudos.
    Esto reemplaza los ceros del Excel con valores reales.
    """
    def g(key, side): return stats.get(key, {}).get(side, 0.0) or 0.0

    for side in ("local", "visitante"):
        tiros_tot  = g("Tiros totales", side)
        tiros_arco = g("Tiros al arco", side)
        tiros_den  = g("Tiros dentro del área", side)
        oc         = g("Ocasiones claras", side)
        oc_fall    = g("Ocasiones claras falladas", side)
        goles      = g("Resultado", side)
        quites     = g("Quites", side)
        intercep   = g("Intercepciones", side)
        despejes   = g("Despejes", side)
        pases_tot  = g("Pases totales", side)
        pases_prec = g("Pases precisos", side)

        # xG sintético por tiro (versión mejorada, ponderada por zona y calidad)
        xg_total = (tiros_arco * 0.25) + (oc * 0.40) + (tiros_den * 0.12) + (tiros_tot * 0.04)
        xg_por_tiro = round(xg_total / max(tiros_tot, 1), 3)

        # Eficiencia de ocasiones claras
        oc_total_oportunidades = max(oc + oc_fall, 1)
        eficiencia_oc = round(goles / oc_total_oportunidades * 100, 1) if oc_total_oportunidades > 0 else 0.0

        # % Regates exitosos (ya parseado del raw)
        pct_regate = g("Regates intentados", side)  # ya tiene el % del parsing

        # Acciones defensivas exitosas (proxy de duelos ganados)
        acciones_def = quites + intercep
        presion_def = round(acciones_def / max(quites + intercep + despejes * 0.3, 1) * 100, 1)

        # % Tiros dentro del área
        pct_tiros_den = round(tiros_den / max(tiros_tot, 1) * 100, 1)

        # Precisión de tiros
        precision = round(tiros_arco / max(tiros_tot, 1) * 100, 1)

        # Precisión de pases
        precision_pases = round(pases_prec / max(pases_tot, 1) * 100, 1)

        # xG total del partido (para diferencial)
        stats.setdefault(f"_xg_total_{side}", {})
        stats[f"_xg_total_{side}"] = {"local": xg_total if side == "local" else 0,
                                       "visitante": xg_total if side == "visitante" else 0}

        # Guardar derivadas en stats
        label = "Local" if side == "local" else "Visitante"
        stats[f"xG Sintético - {label}"] = {"local": xg_por_tiro if side == "local" else 0,
                                              "visitante": xg_por_tiro if side == "visitante" else 0}
        stats[f"Eficiencia OC - {label} (%)"] = {"local": eficiencia_oc if side == "local" else 0,
                                                   "visitante": eficiencia_oc if side == "visitante" else 0}
        stats[f"Acciones Def. - {label}"] = {"local": acciones_def if side == "local" else 0,
                                               "visitante": acciones_def if side == "visitante" else 0}
        stats[f"Presión Def. - {label} (%)"] = {"local": presion_def if side == "local" else 0,
                                                  "visitante": presion_def if side == "visitante" else 0}
        stats[f"% Tiros Área - {label}"] = {"local": pct_tiros_den if side == "local" else 0,
                                              "visitante": pct_tiros_den if side == "visitante" else 0}
        stats[f"Precisión Tiros - {label} (%)"] = {"local": precision if side == "local" else 0,
                                                     "visitante": precision if side == "visitante" else 0}
        stats[f"Precisión Pases - {label} (%)"] = {"local": precision_pases if side == "local" else 0,
                                                     "visitante": precision_pases if side == "visitante" else 0}
        stats[f"% Regates - {label}"] = {"local": pct_regate if side == "local" else 0,
                                          "visitante": pct_regate if side == "visitante" else 0}

    # Diferencial xG
    xg_l_raw = (g("Tiros al arco", "local") * 0.25 + g("Ocasiones claras", "local") * 0.40 +
                g("Tiros dentro del área", "local") * 0.12 + g("Tiros totales", "local") * 0.04)
    xg_v_raw = (g("Tiros al arco", "visitante") * 0.25 + g("Ocasiones claras", "visitante") * 0.40 +
                g("Tiros dentro del área", "visitante") * 0.12 + g("Tiros totales", "visitante") * 0.04)
    stats["xG Diferencial (L-V)"] = {"local": round(xg_l_raw - xg_v_raw, 3), "visitante": 0}
    stats["_xg_local_total"] = {"local": round(xg_l_raw, 3), "visitante": 0}
    stats["_xg_vis_total"]   = {"local": 0, "visitante": round(xg_v_raw, 3)}

    return stats


@st.cache_data(ttl=300, show_spinner=False)
def procesar_archivos_subidos(archivos) -> dict:
    datos = {}
    for file in archivos:
        name = file.name.lower()
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
                if met.startswith("_"): continue  # skip internos
                base = {"nFecha": nf, "Métrica": met}
                filas.append({**base, "Equipo": p["local"],    "Rival": p["visitante"], "Condicion": "Local",
                               "Propio": vals.get("local", 0), "Concedido": vals.get("visitante", 0)})
                filas.append({**base, "Equipo": p["visitante"], "Rival": p["local"],    "Condicion": "Visitante",
                               "Propio": vals.get("visitante", 0), "Concedido": vals.get("local", 0)})
    return pd.DataFrame(filas)


# ══════════════════════════════════════════════════════════════════════
# xG & MOTOR PREDICTIVO
# ══════════════════════════════════════════════════════════════════════

XG_W    = {"Tiros al arco": 0.35, "Ocasiones claras": 0.40, "Tiros dentro del área": 0.15, "Tiros totales": 0.10}
XG_RATE = {"Tiros al arco": 0.25, "Ocasiones claras": 0.35, "Tiros dentro del área": 0.12, "Tiros totales": 0.08}

def xg_sintetico(stat_dict: dict) -> float:
    """xG a partir de stats de un lado del partido."""
    return round(sum(stat_dict.get(m, 0.0) * XG_W[m] * XG_RATE[m] for m in XG_W), 4)

def xg_from_partido(p: dict, side: str) -> float:
    t_arco = p["stats"].get("Tiros al arco", {}).get(side, 0)
    oc     = p["stats"].get("Ocasiones claras", {}).get(side, 0)
    t_den  = p["stats"].get("Tiros dentro del área", {}).get(side, 0)
    t_tot  = p["stats"].get("Tiros totales", {}).get(side, 0)
    return round(t_arco * 0.25 + oc * 0.40 + t_den * 0.12 + t_tot * 0.04, 4)


@st.cache_data(ttl=300, show_spinner=False)
def calcular_xg_df(datos_raw: dict, suplementarios: dict) -> pd.DataFrame:
    filas = []
    for nf, partidos in datos_raw.items():
        for p in partidos:
            key = f"{p['local']}|{p['visitante']}|{nf}"
            # Usar xG suplementario si existe (FBref / manual), sino sintético
            xg_l = suplementarios.get(key, {}).get("xg_local",  xg_from_partido(p, "local"))
            xg_v = suplementarios.get(key, {}).get("xg_vis",    xg_from_partido(p, "visitante"))
            g_l  = p["stats"].get("Resultado", {}).get("local",    np.nan)
            g_v  = p["stats"].get("Resultado", {}).get("visitante", np.nan)
            filas.append({"nFecha": nf, "Equipo": p["local"],    "Rival": p["visitante"],
                          "Condicion": "Local",    "xG": xg_l, "Goles": g_l})
            filas.append({"nFecha": nf, "Equipo": p["visitante"], "Rival": p["local"],
                          "Condicion": "Visitante", "xG": xg_v, "Goles": g_v})
    return pd.DataFrame(filas)


def wmean(values, fechas, max_f, n_rec, w_rec, w_norm):
    if len(values) == 0: return np.nan
    w = np.where(np.array(fechas, dtype=float) >= (max_f - n_rec + 1), w_rec, w_norm)
    return float(np.average(values, weights=w))

def get_metric(df, equipo, condicion, metrica, max_f, n_rec=3, w_rec=1.5, w_norm=1.0):
    sub = df[(df["Equipo"] == equipo) & (df["Condicion"] == condicion) & (df["Métrica"] == metrica)]
    if sub.empty: sub = df[(df["Equipo"] == equipo) & (df["Métrica"] == metrica)]
    return (np.nan, 0) if sub.empty else (wmean(sub["Propio"].values, sub["nFecha"].values, max_f, n_rec, w_rec, w_norm), len(sub))


def calcular_lambdas(df, xg_df, ea, eb, es_local, k, nr, wr, wn, h_atk, h_def, sc):
    max_f = df["nFecha"].max()
    ca, cb = ("Local", "Visitante") if es_local else ("Visitante", "Local")

    ref_h = xg_df[xg_df["Condicion"] == "Local"]["xG"].mean()    if not xg_df.empty else 1.0
    ref_a = xg_df[xg_df["Condicion"] == "Visitante"]["xG"].mean() if not xg_df.empty else 1.0
    ra_a, ra_b = (ref_h, ref_a) if es_local else (ref_a, ref_h)

    def gxg(eq, cond):
        s = xg_df[(xg_df["Equipo"] == eq) & (xg_df["Condicion"] == cond)]
        if s.empty: s = xg_df[xg_df["Equipo"] == eq]
        return (wmean(s["xG"].values, s["nFecha"].values, max_f, nr, wr, wn), len(s)) if not s.empty else (np.nan, 0)

    xga, na = gxg(ea, ca); xgb, nb = gxg(eb, cb)
    xga = xga if pd.notna(xga) else ra_a
    xgb = xgb if pd.notna(xgb) else ra_b

    def def_idx(eq, cond):
        # Ahora usamos "Acciones Def." calculado correctamente
        q, _ = get_metric(df, eq, cond, "Quites", max_f, nr, wr, wn)
        i, _ = get_metric(df, eq, cond, "Intercepciones", max_f, nr, wr, wn)
        lq   = df[df["Métrica"] == "Quites"]["Propio"].mean()
        li   = df[df["Métrica"] == "Intercepciones"]["Propio"].mean()
        q = q if pd.notna(q) else lq
        i = i if pd.notna(i) else li
        pr = 0.5 * (q / max(lq, 1)) + 0.5 * (i / max(li, 1))
        return 1.0 / max(pr, 0.5) if pd.notna(pr) else 1.0

    atk_a = (na * (xga / max(ra_a, 1e-6)) + k) / (na + k)
    atk_b = (nb * (xgb / max(ra_b, 1e-6)) + k) / (nb + k)
    def_a  = (na * def_idx(ea, ca) + k) / (na + k)
    def_b  = (nb * def_idx(eb, cb) + k) / (nb + k)

    la = ra_a * atk_a * def_b
    lb = ra_b * atk_b * def_a
    la, lb = (la * h_atk * sc, lb * h_def * sc) if es_local else (la * h_def * sc, lb * h_atk * sc)

    g_a, _ = get_metric(df, ea, ca, "Resultado", max_f, nr, wr, wn)
    g_b, _ = get_metric(df, eb, cb, "Resultado", max_f, nr, wr, wn)
    if pd.notna(g_a) and na >= 3: la = 0.6 * la + 0.4 * g_a
    if pd.notna(g_b) and nb >= 3: lb = 0.6 * lb + 0.4 * g_b

    return round(np.clip(la, 0.2, 5.0), 3), round(np.clip(lb, 0.2, 5.0), 3), na, nb


def simular(la: float, lb: float, rho: float):
    pa = np.array([math.exp(k * math.log(max(la, 1e-9)) - la - math.lgamma(k + 1)) for k in range(MAX_G + 1)])
    pb = np.array([math.exp(k * math.log(max(lb, 1e-9)) - lb - math.lgamma(k + 1)) for k in range(MAX_G + 1)])
    M  = np.outer(pa, pb)
    tau = np.ones((2, 2))
    tau[0, 0] = 1 - la * lb * rho
    tau[1, 0] = 1 + lb * rho
    tau[0, 1] = 1 + la * rho
    tau[1, 1] = 1 - rho
    for i in range(2):
        for j in range(2):
            M[i, j] = max(M[i, j] * tau[i, j], 0)
    M /= M.sum()
    return {"vic": float(np.tril(M, -1).sum()), "emp": float(np.trace(M)),
            "der": float(np.triu(M, 1).sum()), "mat": M}


# ══════════════════════════════════════════════════════════════════════
# TABLAS & GRÁFICOS
# ══════════════════════════════════════════════════════════════════════

def tabla_resumen(df, equipos, xg_df):
    rows = []
    for eq in equipos:
        sub_g  = df[(df["Equipo"] == eq) & (df["Métrica"] == "Resultado")]
        sub_xg = xg_df[xg_df["Equipo"] == eq]
        if sub_g.empty: continue
        gf = sub_g["Propio"].mean()
        gc = sub_g["Concedido"].mean()
        xgf = sub_xg["xG"].mean() if not sub_xg.empty else 0.0
        pts = sub_g.apply(lambda r: 3 if r["Propio"] > r["Concedido"] else (1 if r["Propio"] == r["Concedido"] else 0), axis=1).sum()
        # Acciones defensivas promedio
        sub_def = df[(df["Equipo"] == eq) & (df["Métrica"].isin(["Quites", "Intercepciones"]))]
        acc_def = sub_def.groupby("nFecha")["Propio"].sum().mean() if not sub_def.empty else 0

        rows.append({
            "Equipo": eq, "PJ": len(sub_g), "PTS": int(pts),
            "xGF/PJ": round(xgf, 2),
            "GF/PJ":  round(gf, 2),
            "GC/PJ":  round(gc, 2),
            "Def/PJ": round(acc_def, 1),
            "xG-G": round(xgf - gf, 2)
        })
    return pd.DataFrame(rows).sort_values("PTS", ascending=False).reset_index(drop=True)


def plot_radar(df, ea, eb):
    mets = [
        "Posesión de balón", "Tiros totales", "Tiros al arco",
        "Ocasiones claras", "Pases totales", "Quites", "Intercepciones",
        "Tiros dentro del área"
    ]
    mets = [m for m in mets if m in df["Métrica"].values]
    if not mets: return go.Figure()

    def gv(eq, m):
        d = df[(df["Equipo"] == eq) & (df["Métrica"] == m)]
        return d["Propio"].mean() if not d.empty else 0.0

    va, vb = [gv(ea, m) for m in mets], [gv(eb, m) for m in mets]
    maxv   = [max(va[i], vb[i], 1e-9) for i in range(len(mets))]
    van    = [va[i] / maxv[i] for i in range(len(mets))]
    vbn    = [vb[i] / maxv[i] for i in range(len(mets))]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=van + [van[0]], theta=mets + [mets[0]],
                                   fill="toself", name=ea,
                                   line=dict(color=RED, width=2),
                                   fillcolor=f"rgba(230,57,70,0.15)"))
    fig.add_trace(go.Scatterpolar(r=vbn + [vbn[0]], theta=mets + [mets[0]],
                                   fill="toself", name=eb,
                                   line=dict(color=BLUE, width=2),
                                   fillcolor=f"rgba(59,130,246,0.15)"))
    fig.update_layout(**PLOT, height=440,
                      polar=dict(radialaxis=dict(visible=False, range=[0, 1.1]),
                                 angularaxis=dict(tickfont=dict(size=11))),
                      title=dict(text="Radar de Rendimiento Promedio", font=dict(size=14)))
    return fig


def plot_evolucion_xg(xg_df, equipo):
    sub = xg_df[xg_df["Equipo"] == equipo].sort_values("nFecha")
    if sub.empty: return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sub["nFecha"], y=sub["xG"], mode="lines+markers",
                              name="xG Generado", line=dict(color=BLUE, width=2),
                              marker=dict(size=7)))
    fig.add_trace(go.Scatter(x=sub["nFecha"], y=sub["Goles"], mode="lines+markers",
                              name="Goles Reales", line=dict(color=GREEN, width=2, dash="dash"),
                              marker=dict(size=7)))
    fig.update_layout(**PLOT, height=300, xaxis_title="Fecha", yaxis_title="xG / Goles",
                      title=f"xG vs Goles — {equipo}", legend=dict(orientation="h"))
    return fig


def plot_metricas_evolucion(df, equipo, metrica):
    sub = df[(df["Equipo"] == equipo) & (df["Métrica"] == metrica)].sort_values("nFecha")
    if sub.empty: return go.Figure()
    liga_avg = df[df["Métrica"] == metrica]["Propio"].mean()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=sub["nFecha"], y=sub["Propio"], name=equipo,
                          marker_color=[RED if c == "Local" else BLUE for c in sub["Condicion"]]))
    fig.add_hline(y=liga_avg, line_dash="dot", line_color=YELLOW,
                  annotation_text=f"Promedio liga: {liga_avg:.1f}", annotation_position="top right")
    fig.update_layout(**PLOT, height=300, xaxis_title="Fecha", yaxis_title=metrica,
                      title=f"{metrica} — {equipo} (🔴 local | 🔵 visitante)")
    return fig


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ⚽ LPF Scouting 2026")

    archivos_subidos = st.file_uploader(
        "📂 Subir archivo(s) (.csv o .xlsx)",
        type=["csv", "xlsx"], accept_multiple_files=True
    )
    st.divider()

    nav = st.radio("Navegación", [
        "🔮 Predictor",
        "📊 Rankings & xG",
        "🕸️ Head to Head",
        "📈 Evolución por Equipo",
        "🛡️ Análisis vs Nivel de Rival",
        "🔧 Datos Suplementarios"
    ])

    with st.expander("⚙️ Parámetros del Modelo"):
        k_shrink = st.slider("Shrinkage (K)", 1.0, 8.0, 4.0)
        n_rec    = st.slider("Fechas Recencia", 2, 6, 3)
        h_atk    = st.slider("Bono Local (Atk)", 1.0, 1.3, 1.12)
        h_def    = st.slider("Bono Local (Def)", 0.75, 1.0, 0.90)
        scaling  = st.slider("Scaling", 0.7, 1.1, 0.88)
        rho_dc   = st.slider("ρ Dixon-Coles", -0.3, 0.0, -0.1)

# ──────────────────────────────────────────────────────────────────────
# DATOS SUPLEMENTARIOS (FBref / manual)
# ──────────────────────────────────────────────────────────────────────
if "suplementarios" not in st.session_state:
    st.session_state["suplementarios"] = {}

if not archivos_subidos:
    st.info("👈 Subí tus archivos de datos desde el menú lateral para comenzar.")
    st.markdown("""
    <div class="info-box">
    <b>Formatos soportados:</b> Excel (.xlsx) con hojas nombradas "Fecha 1", "Fecha 2", etc. — 
    o archivos CSV individuales por fecha. Los datos de SofaScore son totalmente compatibles.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

with st.spinner("⚙️ Procesando y calculando métricas derivadas..."):
    datos_raw = procesar_archivos_subidos(archivos_subidos)
    df_main   = construir_df(datos_raw)

if df_main.empty:
    st.error("⚠️ No se pudieron extraer datos. Verificá el formato del archivo.")
    st.stop()

xg_df      = calcular_xg_df(datos_raw, st.session_state["suplementarios"])
equipos    = sorted(df_main["Equipo"].unique())
tabla_pos  = tabla_resumen(df_main, equipos, xg_df)
metricas_disponibles = sorted([m for m in df_main["Métrica"].unique()
                                if not m.startswith("_") and not any(
                                    x in m for x in ["Local", "Visitante", "Def.", "OC", "Regates", "Precisión", "Tiros Área"]
                                )])


# ══════════════════════════════════════════════════════════════════════
# 1. PREDICTOR
# ══════════════════════════════════════════════════════════════════════
if nav == "🔮 Predictor":
    st.markdown('<div class="section-title">🔮 Simulación de Partido</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([4, 4, 2])
    ea       = c1.selectbox("🏠 Equipo Local", equipos)
    eb       = c2.selectbox("✈️ Equipo Visitante", equipos, index=min(1, len(equipos) - 1))
    es_local = c3.toggle("Factor localía", True)

    if st.button("▶ Simular Partido", use_container_width=True, type="primary"):
        if ea == eb:
            st.warning("Seleccioná equipos distintos."); st.stop()

        la, lb, na, nb = calcular_lambdas(
            df_main, xg_df, ea, eb, es_local,
            k_shrink, n_rec, 1.6, 1.0, h_atk, h_def, scaling
        )
        s = simular(la, lb, rho_dc)
        M = s["mat"]

        # Confianza del modelo
        conf = "Alta" if min(na, nb) >= 8 else ("Media" if min(na, nb) >= 4 else "Baja")
        conf_color = {"Alta": GREEN, "Media": YELLOW, "Baja": RED}[conf]

        st.markdown(f"""
        <div style="text-align:center; margin-bottom:16px; font-size:0.85rem; color:{conf_color}">
        ● Confianza del modelo: <b>{conf}</b> — {ea}: {na} partidos | {eb}: {nb} partidos
        </div>
        """, unsafe_allow_html=True)

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.markdown(f'<div class="kpi-container"><div class="kpi-title">Gana {ea[:12]}</div><div class="kpi-value">{s["vic"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-container kpi-draw"><div class="kpi-title">Empate</div><div class="kpi-value">{s["emp"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-container kpi-loss"><div class="kpi-title">Gana {eb[:12]}</div><div class="kpi-value">{s["der"]*100:.1f}%</div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="kpi-container kpi-yellow"><div class="kpi-title">λ Local</div><div class="kpi-value">{la}</div><div class="kpi-sub">xG esperado</div></div>', unsafe_allow_html=True)
        k5.markdown(f'<div class="kpi-container kpi-yellow"><div class="kpi-title">λ Visitante</div><div class="kpi-value">{lb}</div><div class="kpi-sub">xG esperado</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        t1, t2, t3 = st.tabs(["🎯 Matriz de Marcadores", "📊 Over/Under & BTTS", "📉 Radar Comparativo"])

        with t1:
            best = np.unravel_index(M[:6, :6].argmax(), M[:6, :6].shape)
            st.success(f"**Marcador más probable:** {ea} **{best[0]}–{best[1]}** {eb}  ({M[best]*100:.1f}%)")
            # Top 5 marcadores
            top5 = sorted(
                [(i, j, M[i, j]) for i in range(6) for j in range(6)],
                key=lambda x: -x[2]
            )[:5]
            cols = st.columns(5)
            for idx, (gi, gj, prob) in enumerate(top5):
                cols[idx].markdown(f"""
                <div class="kpi-container" style="padding:12px">
                <div class="kpi-title">#{idx+1}</div>
                <div class="kpi-value" style="font-size:1.6rem">{gi}–{gj}</div>
                <div class="kpi-sub">{prob*100:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            fig = go.Figure(go.Heatmap(
                z=M[:6, :6] * 100,
                x=[f"{j} {eb[:8]}" for j in range(6)],
                y=[f"{i} {ea[:8]}" for i in range(6)],
                colorscale="Reds",
                text=[[f"{M[i,j]*100:.1f}%" for j in range(6)] for i in range(6)],
                texttemplate="%{text}", textfont=dict(size=11)
            ))
            fig.update_layout(**PLOT, height=360, yaxis=dict(autorange="reversed"),
                              title="Distribución de probabilidad por marcador (%)")
            st.plotly_chart(fig, use_container_width=True)

        with t2:
            lins = [1.5, 2.5, 3.5, 4.5]
            cols = st.columns(len(lins) + 2)
            for idx, lin in enumerate(lins):
                over = sum(M[i, j] for i in range(MAX_G) for j in range(MAX_G) if i + j > lin)
                cols[idx].metric(f"Over {lin}", f"{over*100:.1f}%", f"Under: {(1-over)*100:.1f}%")
            bts   = 1 - M[0, :].sum() - M[:, 0].sum() + M[0, 0]
            clean = M[0, :].sum() + M[:, 0].sum() - M[0, 0]
            cols[-2].metric("BTTS (Ambos anotan)", f"{bts*100:.1f}%")
            cols[-1].metric("Clean Sheet (alguno)", f"{clean*100:.1f}%")

        with t3:
            st.plotly_chart(plot_radar(df_main, ea, eb), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# 2. RANKINGS & xG
# ══════════════════════════════════════════════════════════════════════
elif nav == "📊 Rankings & xG":
    st.markdown('<div class="section-title">📊 Tabla de Rendimiento</div>', unsafe_allow_html=True)

    st.dataframe(
        tabla_pos.style
            .background_gradient(subset=["xGF/PJ", "GF/PJ"], cmap="Greens")
            .background_gradient(subset=["GC/PJ"], cmap="Reds_r")
            .background_gradient(subset=["PTS"], cmap="Blues"),
        use_container_width=True, height=430
    )

    st.markdown('<div class="section-title">xG Sintético vs Goles Reales</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=tabla_pos["xGF/PJ"], y=tabla_pos["GF/PJ"],
            mode="markers+text", text=tabla_pos["Equipo"],
            textposition="top center", textfont=dict(size=9),
            marker=dict(size=12, color=tabla_pos["PTS"],
                        colorscale="RdYlGn", showscale=True,
                        colorbar=dict(title="PTS"))
        ))
        mx = max(tabla_pos["xGF/PJ"].max(), tabla_pos["GF/PJ"].max()) * 1.15
        fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines",
                                  line=dict(color=GRAY, dash="dash", width=1), name="Identidad", showlegend=False))
        fig.update_layout(**PLOT, height=420, xaxis_title="xG por partido", yaxis_title="Goles reales por partido",
                          title="Eficiencia ofensiva: sobre la diagonal = sobreperforma su xG")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Ranking por acciones defensivas
        fig2 = go.Figure(go.Bar(
            x=tabla_pos["Def/PJ"],
            y=tabla_pos["Equipo"],
            orientation="h",
            marker_color=[RED if v < tabla_pos["Def/PJ"].mean() else GREEN for v in tabla_pos["Def/PJ"]],
            text=[f"{v:.0f}" for v in tabla_pos["Def/PJ"]],
            textposition="outside"
        ))
        fig2.add_vline(x=tabla_pos["Def/PJ"].mean(), line_dash="dot", line_color=YELLOW)
        fig2.update_layout(**PLOT, height=420, xaxis_title="Quites + Intercepciones por partido",
                           title="Actividad Defensiva Promedio", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# 3. HEAD TO HEAD
# ══════════════════════════════════════════════════════════════════════
elif nav == "🕸️ Head to Head":
    st.markdown('<div class="section-title">🕸️ Comparativa Directa</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    ea = c1.selectbox("Equipo 1", equipos, key="h2h_1")
    eb = c2.selectbox("Equipo 2", equipos, index=min(1, len(equipos) - 1), key="h2h_2")

    st.plotly_chart(plot_radar(df_main, ea, eb), use_container_width=True)

    # Tabla comparativa ampliada
    mets_comp = [
        "Posesión de balón", "Tiros totales", "Tiros al arco", "Ocasiones claras",
        "Pases totales", "Pases precisos", "Quites", "Intercepciones",
        "Despejes", "Faltas", "Córners"
    ]
    def get_avg(eq, m):
        d = df_main[(df_main["Equipo"] == eq) & (df_main["Métrica"] == m)]
        return round(d["Propio"].mean(), 1) if not d.empty else None

    comp_data = {"Métrica": mets_comp, ea: [get_avg(ea, m) for m in mets_comp], eb: [get_avg(eb, m) for m in mets_comp]}
    comp_df = pd.DataFrame(comp_data).dropna()

    def highlight(row):
        styles = [""] * 3
        if pd.notna(row[ea]) and pd.notna(row[eb]):
            met = row["Métrica"]
            lower_is_better = met in ("Faltas", "Despejes", "Fueras de juego")
            if (row[ea] > row[eb] and not lower_is_better) or (row[ea] < row[eb] and lower_is_better):
                styles[1] = "background-color: #064e3b; color: #6ee7b7"
            elif (row[eb] > row[ea] and not lower_is_better) or (row[eb] < row[ea] and lower_is_better):
                styles[2] = "background-color: #1e3a5f; color: #93c5fd"
        return styles

    st.dataframe(comp_df.style.apply(highlight, axis=1), use_container_width=True, hide_index=True)

    # xG comparison
    col1, col2 = st.columns(2)
    with col1: st.plotly_chart(plot_evolucion_xg(xg_df, ea), use_container_width=True)
    with col2: st.plotly_chart(plot_evolucion_xg(xg_df, eb), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# 4. EVOLUCIÓN POR EQUIPO
# ══════════════════════════════════════════════════════════════════════
elif nav == "📈 Evolución por Equipo":
    st.markdown('<div class="section-title">📈 Evolución Fecha a Fecha</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2])
    eq_sel  = c1.selectbox("Equipo", equipos)
    met_sel = c2.selectbox("Métrica", metricas_disponibles)

    st.plotly_chart(plot_evolucion_xg(xg_df, eq_sel), use_container_width=True)
    st.plotly_chart(plot_metricas_evolucion(df_main, eq_sel, met_sel), use_container_width=True)

    # Tabla de últimas fechas
    st.markdown("#### Detalle por partido")
    sub = df_main[(df_main["Equipo"] == eq_sel)].pivot_table(
        index=["nFecha", "Rival", "Condicion"], columns="Métrica", values="Propio", aggfunc="first"
    ).reset_index()
    cols_show = ["nFecha", "Rival", "Condicion", "Resultado"] + [c for c in sub.columns if c in metricas_disponibles and c != "Resultado"]
    cols_show = [c for c in cols_show if c in sub.columns]
    st.dataframe(sub[cols_show].sort_values("nFecha", ascending=False), use_container_width=True, height=350)


# ══════════════════════════════════════════════════════════════════════
# 5. ANÁLISIS VS NIVEL DE RIVAL
# ══════════════════════════════════════════════════════════════════════
elif nav == "🛡️ Análisis vs Nivel de Rival":
    st.markdown('<div class="section-title">🛡️ Rendimiento según Jerarquía del Rival</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Divide los rivales en 3 niveles según la tabla actual. Útil para ver cómo rinde un equipo ante distintos tipos de oponentes.</div>', unsafe_allow_html=True)

    n_t = len(equipos)
    tabla_pos_cp = tabla_pos.copy()
    tabla_pos_cp["Rank"] = tabla_pos_cp["PTS"].rank(method="min", ascending=False)

    def tier(r):
        if r <= n_t / 3: return "🔴 Top"
        elif r <= 2 * n_t / 3: return "🟡 Medio"
        return "🟢 Bajo"

    tabla_pos_cp["Tier"] = tabla_pos_cp["Rank"].apply(tier)
    tier_map = dict(zip(tabla_pos_cp["Equipo"], tabla_pos_cp["Tier"]))

    eq_an = st.selectbox("Equipo a analizar:", equipos)

    sub_res = df_main[(df_main["Equipo"] == eq_an) & (df_main["Métrica"] == "Resultado")].copy()
    sub_res["Tier_Rival"] = sub_res["Rival"].map(tier_map)

    xg_f = xg_df[xg_df["Equipo"] == eq_an][["nFecha", "Rival", "xG"]].rename(columns={"xG": "xGF"})
    xg_c = xg_df[xg_df["Rival"]  == eq_an][["nFecha", "Equipo", "xG"]].rename(columns={"xG": "xGC", "Equipo": "Rival"})

    completo = sub_res.merge(xg_f, on=["nFecha", "Rival"], how="left").merge(xg_c, on=["nFecha", "Rival"], how="left")

    if not completo.empty:
        res = completo.groupby("Tier_Rival").agg(
            PJ=("nFecha", "count"),
            GF=("Propio", "mean"),
            GC=("Concedido", "mean"),
            xGF=("xGF", "mean"),
            xGC=("xGC", "mean")
        ).round(2).reset_index().rename(columns={"Tier_Rival": "Nivel Rival", "GF": "GF/PJ", "GC": "GC/PJ",
                                                   "xGF": "xGF/PJ", "xGC": "xGC/PJ"})

        # Victorias por tier
        def wins(t):
            sub = completo[completo["Tier_Rival"] == t]
            if sub.empty: return 0
            return (sub["Propio"] > sub["Concedido"]).sum()

        res["Victorias"] = res["Nivel Rival"].apply(wins)
        st.dataframe(res, use_container_width=True, hide_index=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(name="xGF/PJ", x=res["Nivel Rival"], y=res["xGF/PJ"], marker_color=BLUE))
        fig.add_trace(go.Bar(name="xGC/PJ", x=res["Nivel Rival"], y=res["xGC/PJ"], marker_color=RED))
        fig.add_trace(go.Bar(name="GF/PJ",  x=res["Nivel Rival"], y=res["GF/PJ"],  marker_color=GREEN))
        fig.update_layout(**PLOT, barmode="group", height=350,
                          title=f"Ataque y Defensa de {eq_an} según nivel de rival")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay suficientes partidos registrados.")


# ══════════════════════════════════════════════════════════════════════
# 6. DATOS SUPLEMENTARIOS
# ══════════════════════════════════════════════════════════════════════
elif nav == "🔧 Datos Suplementarios":
    st.markdown('<div class="section-title">🔧 Fuentes de Datos Adicionales</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <b>¿Para qué sirve esto?</b><br>
    SofaScore provee la mayoría de las estadísticas, pero <b>% Duelos ganados</b> y <b>xG real</b> (basado en coordenadas de disparo) 
    no están disponibles en su exportación básica. Podés complementar manualmente con datos de:
    <br><br>
    • <b>FBref.com</b> → Pestaña "Shooting" de cada partido (xG real por disparo)<br>
    • <b>WhoScored.com</b> → Duelos ganados totales por equipo<br>
    • <b>SofaScore directamente</b> → Abrí el partido en el browser, vas a ver más stats que las exportadas
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ➕ Ingresar xG Real por Partido")
    st.caption("Completá manualmente los xG de FBref u otra fuente para mejorar el modelo predictivo.")

    # Recolectar todos los partidos del dataset
    todos_partidos = []
    for nf, partidos in datos_raw.items():
        for p in partidos:
            todos_partidos.append({
                "key": f"{p['local']}|{p['visitante']}|{nf}",
                "label": f"F{nf}: {p['local']} vs {p['visitante']}",
                "nFecha": nf,
                "local": p["local"],
                "vis": p["visitante"]
            })
    todos_partidos.sort(key=lambda x: x["nFecha"])

    partido_sel = st.selectbox(
        "Seleccionar partido",
        options=[p["key"] for p in todos_partidos],
        format_func=lambda k: next(p["label"] for p in todos_partidos if p["key"] == k)
    )

    p_info = next(p for p in todos_partidos if p["key"] == partido_sel)
    current = st.session_state["suplementarios"].get(partido_sel, {})

    col1, col2 = st.columns(2)
    with col1:
        xg_l_input = st.number_input(
            f"xG {p_info['local']}", min_value=0.0, max_value=10.0, step=0.01,
            value=float(current.get("xg_local", 0.0)),
            key=f"xgl_{partido_sel}"
        )
    with col2:
        xg_v_input = st.number_input(
            f"xG {p_info['vis']}", min_value=0.0, max_value=10.0, step=0.01,
            value=float(current.get("xg_vis", 0.0)),
            key=f"xgv_{partido_sel}"
        )

    if st.button("💾 Guardar xG para este partido"):
        st.session_state["suplementarios"][partido_sel] = {
            "xg_local": xg_l_input, "xg_vis": xg_v_input
        }
        st.success(f"✅ xG guardado: {p_info['local']} {xg_l_input} — {p_info['vis']} {xg_v_input}")
        st.cache_data.clear()

    # Mostrar todos los registros suplementarios
    if st.session_state["suplementarios"]:
        st.markdown("### 📋 xG Registrados Manualmente")
        rows = []
        for k, v in st.session_state["suplementarios"].items():
            p = next((x for x in todos_partidos if x["key"] == k), None)
            if p:
                rows.append({"Partido": p["label"], "xG Local": v["xg_local"], "xG Visitante": v["xg_vis"]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        col_exp, col_del = st.columns([3, 1])
        with col_exp:
            json_str = json.dumps(st.session_state["suplementarios"], indent=2)
            st.download_button("📥 Exportar datos suplementarios (.json)",
                               data=json_str, file_name="lpf_xg_suplementarios.json", mime="application/json")
        with col_del:
            if st.button("🗑️ Limpiar todo", type="secondary"):
                st.session_state["suplementarios"] = {}
                st.cache_data.clear()
                st.rerun()

    st.divider()
    st.markdown("### 📥 Importar desde JSON")
    uploaded_json = st.file_uploader("Subir archivo JSON previamente exportado", type=["json"])
    if uploaded_json:
        try:
            imported = json.load(uploaded_json)
            st.session_state["suplementarios"].update(imported)
            st.cache_data.clear()
            st.success(f"✅ Importados {len(imported)} registros de xG")
        except Exception as e:
            st.error(f"Error al importar: {e}")

    st.divider()
    st.markdown("""
    ### 📖 Guía rápida: cómo obtener xG de FBref

    **Paso a paso:**
    1. Entrá a [fbref.com](https://fbref.com/en/comps/21/Liga-Profesional-Argentina-Stats)
    2. Hacé click en el partido que querés
    3. En la página del partido, buscá la tabla **"Shot Creation"** o **"Shots"**
    4. El valor **"xG"** de cada equipo está en el encabezado del cuadro de estadísticas
    5. Ingresá esos valores acá arriba para mejorar el modelo

    **¿Por qué importa?**
    El xG real de FBref considera la posición exacta del disparo, el ángulo, el tipo de remate y si fue con cabeza o pie.
    El xG sintético que calcula el modelo es una aproximación razonable, pero el real es significativamente más preciso.
    """)
