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

    df_ventas = None
    df_bdcf = None
    df_btcf = None
    df_mix = None

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
        st.error("⚠️ Debes subir mínimo Ventas y BDCF")
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

    # Clima
    if 'Clima' in df_base.columns:
        clima = st.sidebar.multiselect("Clima", sorted(df_base['Clima'].dropna().unique()))
        if clima:
            df = df[df['Clima'].isin(clima)]

    # BDCF
    if 'Sigla BDCF' in df_base.columns:
        cluster = st.sidebar.multiselect("Cluster BDCF", sorted(df_base['Sigla BDCF'].dropna().unique()))
        if cluster:
            df = df[df['Sigla BDCF'].isin(cluster)]

    # 🔥 NUEVO BTCF
    if 'Sigla BTCF' in df_base.columns:
        cluster_btcf = st.sidebar.multiselect("Cluster BTCF", sorted(df_base['Sigla BTCF'].dropna().unique()))
        if cluster_btcf:
            df = df[df['Sigla BTCF'].isin(cluster_btcf)]

    # Segmento
    if 'SEGMENTO' in df_base.columns:
        segmento = st.sidebar.multiselect("Segmento", sorted(df_base['SEGMENTO'].dropna().unique()))
        if segmento:
            df = df[df['SEGMENTO'].isin(segmento)]

    # Formato
    if 'Formato' in df_base.columns:
        formato = st.sidebar.multiselect("Formato", sorted(df_base['Formato'].dropna().unique()))
        if formato:
            df = df[df['Formato'].isin(formato)]

    # =========================
    # COLUMNAS VENTAS
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
    # NOMBRE PRODUCTO
    # =========================
    col_nombre = None
    for col in df.columns:
        if "descripcion" in col.lower() or "producto" in col.lower():
            col_nombre = col
            break

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

    df_group = df.groupby('EAN').agg(agg_dict).reset_index()
    df_group.rename(columns={'Cod. Tienda': 'tiendas'}, inplace=True)

    if df_group.empty:
        st.warning("No hay datos con los filtros seleccionados")
        st.stop()

    # =========================
    # MÉTRICAS
    # =========================
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

    def cuadrante(row):
        if row['valor'] >= corte_valor and row['rotacion'] >= corte_rotacion:
            return "CORE"
        elif row['valor'] >= corte_valor:
            return "PREMIUM"
        elif row['rotacion'] >= corte_rotacion:
            return "OPORTUNIDAD"
        else:
            return "ELIMINAR"

    df_group['cuadrante'] = df_group.apply(cuadrante, axis=1)

    # =========================
    # BURBUJAS
    # =========================
    size = np.sqrt(df_group['venta_total'])
    if size.max() > 0:
        size = (size / size.max()) * 800
    size = np.clip(size, 20, 800)

    # =========================
    # ETIQUETAS (ARREGLADO)
    # =========================
    st.sidebar.subheader("🏷️ Etiquetas")

    opciones_top = ["Todos", 20, 30, 50, 60]
    top_n = st.sidebar.selectbox("Mostrar Top", opciones_top)

    df_group = df_group.sort_values(by='venta_total', ascending=False)
    df_group['rank'] = range(1, len(df_group)+1)

    if top_n == "Todos":
        df_labels = df_group
    else:
        df_labels = df_group[df_group['rank'] <= top_n]

    # =========================
    # GRAFICA
    # =========================
    fig, ax = plt.subplots(figsize=(10,6))

    colores = df_group['cuadrante'].map({
        "CORE": "green",
        "PREMIUM": "blue",
        "OPORTUNIDAD": "orange",
        "ELIMINAR": "red"
    })

    ax.scatter(
        df_group['rotacion'] + 0.01,
        df_group['valor'] + 0.01,
        s=size,
        c=colores,
        alpha=0.6
    )

    ax.axvline(corte_rotacion, linestyle='--')
    ax.axhline(corte_valor, linestyle='--')

    if len(df_group) > 5:
        ax.set_xscale('log')
        ax.set_yscale('log')

    ax.set_xlim(max(df_group['rotacion'].quantile(0.02), 0.01),
                df_group['rotacion'].quantile(0.98))

    ax.set_ylim(max(df_group['valor'].quantile(0.02), 1),
                df_group['valor'].quantile(0.98))

    for _, row in df_labels.iterrows():
        label = str(row['EAN'])
        if col_nombre:
            label = str(row[col_nombre])[:25]
        ax.text(row['rotacion'], row['valor'], label, fontsize=8)

    st.pyplot(fig)

    # =========================
    # RESUMEN
    # =========================
    st.subheader("📊 Resumen por cuadrante")

    resumen = df_group.groupby('cuadrante').agg({
        'EAN': 'count',
        'venta_valor_12': 'sum',
        'venta_unidades_12': 'sum'
    })

    st.dataframe(resumen)