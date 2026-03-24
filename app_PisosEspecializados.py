import streamlit as st
import pandas as pd
import numpy as np

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

    # =========================
    # DISTRIBUCIÓN
    # =========================
    total_tiendas = df_bdcf['Cod. Tienda'].nunique()
    df_group['distribucion_actual'] = df_group['tiendas_activas'] / total_tiendas

    # =========================
    # BOSTON
    # =========================
    df_group['x'] = df_group['venta_unidades_12']
    df_group['y'] = df_group['venta_valor_12']

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
    # MIX DINÁMICO (FIX ERROR)
    # =========================
    if df_mix is not None:

        col_desc, col_marca, col_mix = None, None, None

        for col in df_mix.columns:
            c = col.lower()

            if "descripcion" in c or "producto" in c:
                col_desc = col
            elif "marca" in c:
                col_marca = col
            elif "mix" in c:
                col_mix = col

        columnas = ['EAN']
        if col_mix: columnas.append(col_mix)
        if col_desc: columnas.append(col_desc)
        if col_marca: columnas.append(col_marca)

        df_mix_simple = df_mix[columnas].drop_duplicates()

        df_mix_simple = df_mix_simple.rename(columns={
            col_mix: 'MIX ACTUAL',
            col_desc: 'Descripción producto',
            col_marca: 'MARCA'
        })

        df_group = df_group.merge(df_mix_simple, on='EAN', how='left')

    # =========================
    # NUEVO MIX
    # =========================
    df_group['MIX NUEVO'] = df_group['decision']

    # =========================
    # IMPACTO
    # =========================
    df_group['impacto_valor'] = np.where(
        df_group['decision']=="Expandir",
        df_group['venta_valor_12']*0.2,
        -df_group['venta_valor_12']*0.1
    )

    df_group['impacto_unidades'] = np.where(
        df_group['decision']=="Expandir",
        df_group['venta_unidades_12']*0.2,
        -df_group['venta_unidades_12']*0.1
    )

    # =========================
    # TABLA FINAL
    # =========================
    st.subheader("📋 Resultado final")

    columnas = [
        'EAN',
        'Descripción producto',
        'MARCA',
        'venta_valor_12',
        'venta_unidades_12',
        'cuadrante',
        'decision',
        'distribucion_actual',
        'MIX ACTUAL',
        'MIX NUEVO',
        'impacto_valor',
        'impacto_unidades'
    ]

    columnas = [c for c in columnas if c in df_group.columns]

    df_final = df_group[columnas]

    st.dataframe(df_final)

    # =========================
    # DESCARGA
    # =========================
    archivo_salida = "OPTIMIZACION_PORTAFOLIO.xlsx"
    df_final.to_excel(archivo_salida, index=False)

    with open(archivo_salida, "rb") as f:
        st.download_button("📥 Descargar análisis", f, file_name=archivo_salida)