import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("📦 Optimización Inteligente de Portafolio")

archivo = st.file_uploader("Sube archivo Excel", type=["xlsx"])

if archivo:

    df = pd.read_excel(archivo)
    df.columns = df.columns.astype(str).str.strip()

    # =========================
    # DETECTAR COLUMNAS
    # =========================
    cols_num = df.select_dtypes(include=[np.number]).columns.tolist()
    cols_num = [c for c in cols_num if c != 'Cod. Tienda']

    valor_cols = [c for c in cols_num if df[c].mean() > 1000]
    unidades_cols = [c for c in cols_num if df[c].mean() <= 1000]

    valor_12 = valor_cols[-12:]
    unidades_12 = unidades_cols[-12:]

    df[valor_12] = df[valor_12].fillna(0)
    df[unidades_12] = df[unidades_12].fillna(0)

    df['venta_valor_12'] = df[valor_12].sum(axis=1)
    df['venta_unidades_12'] = df[unidades_12].sum(axis=1)

    # =========================
    # FILTROS
    # =========================
    st.sidebar.header("🔎 Filtros")

    if 'Clima' in df.columns:
        clima = st.sidebar.multiselect("Clima", df['Clima'].dropna().unique())
        if clima:
            df = df[df['Clima'].isin(clima)]

    if 'Sigla BDCF' in df.columns:
        cluster = st.sidebar.multiselect("Cluster BDCF", df['Sigla BDCF'].dropna().unique())
        if cluster:
            df = df[df['Sigla BDCF'].isin(cluster)]

    if 'SEGMENTO' in df.columns:
        segmento = st.sidebar.multiselect("Segmento", df['SEGMENTO'].dropna().unique())
        if segmento:
            df = df[df['SEGMENTO'].isin(segmento)]

    if 'Formato' in df.columns:
        formato = st.sidebar.multiselect("Formato", df['Formato'].dropna().unique())
        if formato:
            df = df[df['Formato'].isin(formato)]

    # =========================
    # AGRUPAR A NIVEL PRODUCTO
    # =========================
    df_group = df.groupby('EAN').agg({
        'venta_valor_12':'sum',
        'venta_unidades_12':'sum',
        'Cod. Tienda':'nunique'
    }).reset_index()

    df_group.rename(columns={'Cod. Tienda':'tiendas'}, inplace=True)

    df_group['rotacion'] = df_group['venta_unidades_12'] / (df_group['tiendas'] + 1)
    df_group['valor'] = df_group['venta_valor_12'] / (df_group['tiendas'] + 1)

    df_group['venta_total'] = df_group['venta_valor_12']

    # =========================
    # BOSTON
    # =========================
    df_group = df_group.sort_values(by='valor', ascending=False)
    df_group['acum'] = df_group['valor'].cumsum()
    total = df_group['valor'].sum()

    corte_valor = df_group[df_group['acum'] >= 0.8 * total]['valor'].iloc[0]
    corte_rotacion = df_group['rotacion'].mean()

    def cuadrante(r):
        if r['valor'] >= corte_valor and r['rotacion'] >= corte_rotacion:
            return "CORE"
        elif r['valor'] >= corte_valor:
            return "PREMIUM"
        elif r['rotacion'] >= corte_rotacion:
            return "OPORTUNIDAD"
        else:
            return "ELIMINAR"

    df_group['cuadrante'] = df_group.apply(cuadrante, axis=1)

    # =========================
    # TAMAÑO BURBUJA
    # =========================
    size = np.sqrt(df_group['venta_total'])
    size = (size / size.max()) * 1000

    # =========================
    # FILTRO DE ETIQUETAS
    # =========================
    st.sidebar.subheader("🏷️ Etiquetas")

    top_n = st.sidebar.selectbox("Mostrar top", [20,30,50,60])
    rango_min = st.sidebar.number_input("Desde ranking", 1, 100, 1)
    rango_max = st.sidebar.number_input("Hasta ranking", 1, 100, top_n)

    df_group = df_group.sort_values(by='venta_total', ascending=False)
    df_group['rank'] = range(1, len(df_group)+1)

    df_labels = df_group[
        (df_group['rank'] >= rango_min) &
        (df_group['rank'] <= rango_max)
    ]

    # =========================
    # GRAFICA
    # =========================
    fig, ax = plt.subplots(figsize=(12,8))

    colores = df_group['cuadrante'].map({
        "CORE":"green",
        "PREMIUM":"blue",
        "OPORTUNIDAD":"orange",
        "ELIMINAR":"red"
    })

    ax.scatter(
        df_group['rotacion']+0.01,
        df_group['valor']+0.01,
        s=size,
        c=colores,
        alpha=0.6
    )

    ax.axvline(corte_rotacion, linestyle='--')
    ax.axhline(corte_valor, linestyle='--')

    ax.set_xscale('log')
    ax.set_yscale('log')

    # auto zoom
    ax.set_xlim(
        df_group['rotacion'].quantile(0.02),
        df_group['rotacion'].quantile(0.98)
    )
    ax.set_ylim(
        df_group['valor'].quantile(0.02),
        df_group['valor'].quantile(0.98)
    )

    # =========================
    # ETIQUETAS
    # =========================
    for _, row in df_labels.iterrows():
        ax.text(
            row['rotacion'],
            row['valor'],
            str(row['EAN']),
            fontsize=8
        )

    st.pyplot(fig)

    # =========================
    # RESUMEN
    # =========================
    st.subheader("📊 Resumen por cuadrante")

    resumen = df_group.groupby('cuadrante').agg({
        'EAN':'count',
        'venta_valor_12':'sum',
        'venta_unidades_12':'sum'
    })

    st.dataframe(resumen)