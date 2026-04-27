import streamlit as st
import pandas as pd
import numpy as np

# Configuración de la página
st.set_page_config(page_title="Modelo Predictivo LPF", layout="wide")
st.title("🏆 Dashboard de Análisis - Liga Profesional Argentina")

# 1. FUNCIÓN PARA SIMULAR/CARGAR EL DATASET APLANADO
# En la práctica, aquí deberás iterar sobre tus CSVs y transformarlos
@st.cache_data
def cargar_datos_procesados():
    # Estructura ideal de tu base de datos tras procesar los CSVs:
    # Equipo | Condicion (Local/Visitante) | Goles_Favor | Goles_Contra | Posesion (%) | Tiros_Arco
    
    # Datos simulados basados en la estructura de tus CSVs para arrancar:
    data = {
        'Equipo': ['River Plate', 'River Plate', 'San Lorenzo', 'San Lorenzo', 'Platense', 'Platense'],
        'Condicion': ['Local', 'Visitante', 'Local', 'Visitante', 'Local', 'Visitante'],
        'Goles_Favor': [2, 1, 1, 0, 2, 0],
        'Goles_Contra': [0, 1, 0, 1, 1, 2],
        'Posesion': [65.0, 58.0, 53.0, 45.0, 45.0, 41.0],
        'Tiros_Totales': [15, 12, 11, 8, 10, 3]
    }
    return pd.DataFrame(data)

df = cargar_datos_procesados()

# ==========================================
# SECCIÓN 1: TABLA GENERAL (GOLES)
# ==========================================
st.header("📊 Tabla Acumulada de Equipos")

# Agrupamos por equipo sin importar la condición para la tabla larga
tabla_general = df.groupby('Equipo').agg(
    Partidos_Jugados=('Condicion', 'count'),
    Goles_Favor=('Goles_Favor', 'sum'),
    Goles_Contra=('Goles_Contra', 'sum')
).reset_index()

# Calculamos diferencia de gol
tabla_general['Diferencia_Gol'] = tabla_general['Goles_Favor'] - tabla_general['Goles_Contra']
tabla_general = tabla_general.sort_values('Diferencia_Gol', ascending=False).reset_index(drop=True)

st.dataframe(tabla_general, use_container_width=True)

st.divider()

# ==========================================
# SECCIÓN 2: RANKINGS ESTADÍSTICOS
# ==========================================
st.header("📈 Rankings de Rendimiento")

col1, col2 = st.columns(2)

with col1:
    condicion_filtro = st.radio("Seleccionar Condición:", ['Todas', 'Local', 'Visitante'], horizontal=True)

with col2:
    metrica_ranking = st.selectbox("Seleccionar Métrica:", ['Posesion', 'Tiros_Totales'])

# Filtramos según la condición elegida
if condicion_filtro != 'Todas':
    df_filtrado = df[df['Condicion'] == condicion_filtro]
else:
    df_filtrado = df

# Agrupamos calculando el promedio de la métrica seleccionada
ranking_metrica = df_filtrado.groupby('Equipo')[metrica_ranking].mean().reset_index()
ranking_metrica = ranking_metrica.sort_values(metrica_ranking, ascending=False).reset_index(drop=True)

st.subheader(f"Ranking de {metrica_ranking.replace('_', ' ')} ({condicion_filtro})")
st.dataframe(ranking_metrica.style.format({metrica_ranking: "{:.1f}"}), use_container_width=True)

# Opcional: Mostrar un gráfico de barras rápido
st.bar_chart(data=ranking_metrica.set_index('Equipo')[metrica_ranking])
