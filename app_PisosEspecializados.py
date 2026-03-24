import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("📦 Optimización Inteligente de Portafolio")

# =========================
# CARGA ARCHIVOS
# =========================
archivos = st.file_uploader(
    "Sube archivos (Ventas, BDCF, BTCF, MIX)",
    type=["xlsx"],
    accept_multiple_files=True
)

if archivos:

    df_ventas, df_bdcf, df_btcf, df_mix = None, None, None, None

    for archivo in archivos:
        nombre = archivo.name.lower()

        if "venta" in nombre:
            df_ventas = pd.read_excel(archivo)

        elif "bdcf" in nombre:
            df_bdcf = pd.read_excel(archivo)

        elif "btcf" in nombre:
            df_btcf = pd.read_excel(archivo)

        elif "mix" in nombre:
            df_mix = pd.read_excel(archivo)

    if df_ventas is None or df_bdcf is None:
        st.error("⚠️ Debes subir Ventas y BDCF")
        st.stop()

    # =========================
    # LIMPIEZA
    # =========================
    for df in [df_ventas, df_bdcf, df_btcf, df_mix]:
        if df is not None:
            df.columns = df.columns.astype(str).str.strip()

    # =========================
    # CRUCE
    # =========================
    df = df_ventas.merge(df_bdcf, on="Cod. Tienda", how="left")

    if df_btcf is not None:
        df = df.merge(df_btcf[['Cod. Tienda','Sigla BTCF']], on="Cod. Tienda", how="left")

    df_base = df.copy()

    # =========================
    # FILTROS
    # =========================
    st.sidebar.header("🔎 Filtros")

    df = df_base.copy()

    if 'Departamento' in df.columns:
        dep = st.sidebar.multiselect("Departamento", sorted(df['Departamento'].dropna().unique()))
        if dep:
            df = df[df['Departamento'].isin(dep)]

    if 'Clima' in df.columns:
        clima = st.sidebar.multiselect("Clima", sorted(df['Clima'].dropna().unique()))
        if clima:
            df = df[df['Clima'].isin(clima)]

    if 'Sigla BDCF' in df.columns:
        cluster = st.sidebar.multiselect("Cluster BDCF", sorted(df['Sigla BDCF'].dropna().unique()))
        if cluster:
            df = df[df['Sigla BDCF'].isin(cluster)]

    if 'Sigla BTCF' in df.columns:
        cluster_btcf = st.sidebar.multiselect("Cluster BTCF", sorted(df['Sigla BTCF'].dropna().unique()))
        if cluster_btcf:
            df = df[df['Sigla BTCF'].isin(cluster_btcf)]

    if 'SEGMENTO' in df.columns:
        segmento = st.sidebar.multiselect("Segmento", sorted(df['SEGMENTO'].dropna().unique()))
        if segmento:
            df = df[df['SEGMENTO'].isin(segmento)]

    # =========================
    # VENTAS
    # =========================
    cols_num = df.select_dtypes(include=[np.number]).columns.tolist()
    cols_num = [c for c in cols_num if c != 'Cod. Tienda']

    valor_cols = [c for c in cols_num if df[c].mean() > 1000]
    unidades_cols = [c for c in cols_num if df[c].mean() <= 1000]

    valor_12 = valor_cols[-12:]
    unidades_12 = unidades_cols[-12:]

    df['venta_valor_12'] = df[valor_12].fillna(0).sum(axis=1)
    df['venta_unidades_12'] = df[unidades_12].fillna(0).sum(axis=1)

    # =========================
    # AGRUPAR
    # =========================
    df_group = df.groupby('EAN').agg({
        'venta_valor_12':'sum',
        'venta_unidades_12':'sum',
        'Cod. Tienda':'nunique'
    }).reset_index()

    df_group.rename(columns={'Cod. Tienda':'tiendas_activas'}, inplace=True)

    df_group = df_group[
        (df_group['venta_valor_12'] > 0) &
        (df_group['venta_unidades_12'] > 0)
    ]

    if df_group.empty:
        st.warning("No hay datos")
        st.stop()

    # =========================
    # DISTRIBUCIÓN
    # =========================
    total_tiendas = df_bdcf['Cod. Tienda'].nunique()
    df_group['distribucion_actual'] = df_group['tiendas_activas'] / total_tiendas

    # =========================
    # BOSTON
    # =========================
    df_group['x'] = df_group['venta_valor_12']
    df_group['y'] = df_group['venta_unidades_12']

    df_group = df_group.sort_values(by='x', ascending=False)

    df_group['acum'] = df_group['x'].cumsum()
    total = df_group['x'].sum()

    corte_valor = df_group[df_group['acum'] >= 0.8 * total]['x'].iloc[0]
    corte_unidades = df_group['y'].mean()

    def cuadrante(r):
        if r['x'] >= corte_valor and r['y'] >= corte_unidades:
            return "CORE"
        elif r['x'] >= corte_valor:
            return "PREMIUM"
        elif r['y'] >= corte_unidades:
            return "OPORTUNIDAD"
        else:
            return "ELIMINAR"

    df_group['cuadrante'] = df_group.apply(cuadrante, axis=1)

    # =========================
    # ESCALA
    # =========================
    escala = st.sidebar.radio("Tipo de visualización", ["Logarítmica", "Lineal"])

    # =========================
    # MIX INFO PARA ETIQUETAS
    # =========================
    if df_mix is not None:
        df_mix.columns = df_mix.columns.astype(str)

        df_group = df_group.merge(df_mix, on='EAN', how='left')

    # =========================
    # GRAFICA
    # =========================
    fig, ax = plt.subplots(figsize=(8,5), dpi=100)

    size = np.sqrt(df_group['venta_valor_12'])
    size = (size / size.max()) * 800

    colores = df_group['cuadrante'].map({
        "CORE": "green",
        "PREMIUM": "blue",
        "OPORTUNIDAD": "orange",
        "ELIMINAR": "red"
    })

    ax.scatter(df_group['x'], df_group['y'], s=size, c=colores, alpha=0.6)

    ax.axvline(corte_valor, linestyle='--')
    ax.axhline(corte_unidades, linestyle='--')

    if escala == "Logarítmica":
        ax.set_xscale('log')
        ax.set_yscale('log')
    else:
        ax.set_ylim(bottom=0)

        max_y = df_group['y'].max()
        step = 100
        yticks = np.arange(0, max_y + step, step)
        ax.set_yticks(yticks)

    ax.set_xlabel("Ventas Valor ($)")
    ax.set_ylabel("Ventas Unidades")

    # =========================
    # ETIQUETAS COMPLETAS
    # =========================
    for _, row in df_group.iterrows():

        desc = str(row.get('Descripción producto', ''))
        marca = str(row.get('MARCA', ''))

        label = f"""
{row['EAN']}
{marca}
{desc[:25]}
$ {int(row['venta_valor_12'])}
U {int(row['venta_unidades_12'])}
"""

        ax.text(row['x'], row['y'], label, fontsize=6)

    st.pyplot(fig)
    plt.close(fig)

    # =========================
    # DECISIONES
    # =========================
    def decision(q):
        if q in ["CORE","OPORTUNIDAD"]:
            return "Expandir"
        elif q == "ELIMINAR":
            return "Reducir"
        else:
            return "Mantener"

    df_group['decision'] = df_group['cuadrante'].apply(decision)

    # =========================
    # TABLA FINAL
    # =========================
    st.subheader("📋 Resultado final")

    st.dataframe(df_group)

    # =========================
    # DESCARGA
    # =========================
    archivo_salida = "OPTIMIZACION_PORTAFOLIO_PRO.xlsx"
    df_group.to_excel(archivo_salida, index=False)

    with open(archivo_salida, "rb") as f:
        st.download_button("📥 Descargar análisis PRO", f, file_name=archivo_salida)