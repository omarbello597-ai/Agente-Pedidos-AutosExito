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
    "Sube archivos (Ventas, BDCF, BTCF)",
    type=["xlsx"],
    accept_multiple_files=True
)

if archivos:

    df_ventas = None
    df_bdcf = None
    df_btcf = None

    for archivo in archivos:
        nombre = archivo.name.lower()

        if "venta" in nombre:
            df_ventas = pd.read_excel(archivo)

        elif "bdcf" in nombre:
            df_bdcf = pd.read_excel(archivo)

        elif "btcf" in nombre:
            df_btcf = pd.read_excel(archivo)

    if df_ventas is None or df_bdcf is None:
        st.error("⚠️ Debes subir Ventas y BDCF")
        st.stop()

    # =========================
    # LIMPIEZA
    # =========================
    df_ventas.columns = df_ventas.columns.astype(str).str.strip()
    df_bdcf.columns = df_bdcf.columns.astype(str).str.strip()

    if df_btcf is not None:
        df_btcf.columns = df_btcf.columns.astype(str).str.strip()

    # =========================
    # CRUCES
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

    if 'Clima' in df_base.columns:
        clima = st.sidebar.multiselect("Clima", sorted(df_base['Clima'].dropna().unique()))
        if clima:
            df = df[df['Clima'].isin(clima)]

    if 'Sigla BDCF' in df_base.columns:
        cluster = st.sidebar.multiselect("Cluster BDCF", sorted(df_base['Sigla BDCF'].dropna().unique()))
        if cluster:
            df = df[df['Sigla BDCF'].isin(cluster)]

    if 'Sigla BTCF' in df_base.columns:
        cluster_btcf = st.sidebar.multiselect("Cluster BTCF", sorted(df_base['Sigla BTCF'].dropna().unique()))
        if cluster_btcf:
            df = df[df['Sigla BTCF'].isin(cluster_btcf)]

    if 'SEGMENTO' in df_base.columns:
        segmento = st.sidebar.multiselect("Segmento", sorted(df_base['SEGMENTO'].dropna().unique()))
        if segmento:
            df = df[df['SEGMENTO'].isin(segmento)]

    if 'Formato' in df_base.columns:
        formato = st.sidebar.multiselect("Formato", sorted(df_base['Formato'].dropna().unique()))
        if formato:
            df = df[df['Formato'].isin(formato)]

    # =========================
    # DETECTAR COLUMNAS
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
    # DETECTAR NOMBRE Y MARCA
    # =========================
    col_nombre = None
    col_marca = None

    for col in df.columns:
        if "descripcion" in col.lower() or "producto" in col.lower():
            col_nombre = col
        if "marca" in col.lower():
            col_marca = col

    # =========================
    # AGRUPAR
    # =========================
    agg_dict = {
        'venta_valor_12': 'sum',
        'venta_unidades_12': 'sum',
        'Cod. Tienda': 'nunique'
    }

    if col_nombre:
        agg_dict[col_nombre] = 'first'

    if col_marca:
        agg_dict[col_marca] = 'first'

    df_group = df.groupby('EAN').agg(agg_dict).reset_index()
    df_group.rename(columns={'Cod. Tienda': 'tiendas'}, inplace=True)

    df_group = df_group[
        (df_group['venta_valor_12'] > 0) &
        (df_group['venta_unidades_12'] > 0)
    ]

    if df_group.empty:
        st.warning("No hay datos")
        st.stop()

    # =========================
    # 🎯 MODO BOSTON (NUEVO)
    # =========================
    modo = st.sidebar.radio(
        "Tipo de análisis",
        ["Eficiencia (por tienda)", "Valor absoluto (total)"]
    )

    if modo == "Eficiencia (por tienda)":
        df_group['x'] = df_group['venta_unidades_12'] / (df_group['tiendas'] + 1)
        df_group['y'] = df_group['venta_valor_12'] / (df_group['tiendas'] + 1)
    else:
        df_group['x'] = df_group['venta_unidades_12']
        df_group['y'] = df_group['venta_valor_12']

    df_group['venta_total'] = df_group['venta_valor_12']

    # =========================
    # BOSTON
    # =========================
    df_group = df_group.sort_values(by='y', ascending=False)
    df_group['acum'] = df_group['y'].cumsum()
    total = df_group['y'].sum()

    corte_valor = df_group[df_group['acum'] >= 0.8 * total]['y'].iloc[0]
    corte_rotacion = df_group['x'].mean()

    def cuadrante(r):
        if r['y'] >= corte_valor and r['x'] >= corte_rotacion:
            return "CORE"
        elif r['y'] >= corte_valor:
            return "PREMIUM"
        elif r['x'] >= corte_rotacion:
            return "OPORTUNIDAD"
        else:
            return "ELIMINAR"

    df_group['cuadrante'] = df_group.apply(cuadrante, axis=1)

    # =========================
    # BURBUJAS
    # =========================
    size = np.sqrt(df_group['venta_total'])
    size = (size / size.max()) * 800

    # =========================
    # GRAFICA
    # =========================
    fig, ax = plt.subplots(figsize=(8,5), dpi=100)

    colores = df_group['cuadrante'].map({
        "CORE": "green",
        "PREMIUM": "blue",
        "OPORTUNIDAD": "orange",
        "ELIMINAR": "red"
    })

    ax.scatter(
        df_group['x'] + 0.01,
        df_group['y'] + 0.01,
        s=size,
        c=colores,
        alpha=0.6
    )

    ax.axvline(corte_rotacion, linestyle='--')
    ax.axhline(corte_valor, linestyle='--')

    ax.set_xscale('log')
    ax.set_yscale('log')

    ax.set_xlim(df_group['x'].min()*0.8, df_group['x'].max()*1.2)
    ax.set_ylim(df_group['y'].min()*0.8, df_group['y'].max()*1.2)

    ax.set_xlabel("Unidades" if modo=="Valor absoluto (total)" else "Rotación")
    ax.set_ylabel("Ventas Valor")

    # =========================
    # ETIQUETAS
    # =========================
    df_group = df_group.sort_values(by='venta_total', ascending=False)
    top_n = st.sidebar.selectbox("Mostrar Top", ["Todos",20,30,50])

    if top_n == "Todos":
        df_labels = df_group
    else:
        df_labels = df_group.head(top_n)

    for _, row in df_labels.iterrows():

        if col_nombre and col_marca:
            label = f"{str(row[col_marca])[:10]} - {str(row[col_nombre])[:20]}"
        elif col_nombre:
            label = str(row[col_nombre])[:25]
        else:
            label = str(row['EAN'])

        ax.text(row['x'], row['y'], label, fontsize=7)

    st.pyplot(fig)
    plt.close(fig)

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