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
    # SELECTOR ESCALA
    # =========================
    escala = st.sidebar.radio("Tipo de visualización", ["Logarítmica", "Lineal"])

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

        # escala cada 100 unidades
        max_y = df_group['y'].max()
        step = 100

        yticks = np.arange(0, max_y + step, step)
        ax.set_yticks(yticks)
    

    ax.set_xlim(df_group['x'].min()*0.8, df_group['x'].max()*1.2)
    ax.set_ylim(df_group['y'].min()*0.8, df_group['y'].max()*1.2)

    ax.set_xlabel("Ventas Valor ($)")
    ax.set_ylabel("Ventas Unidades")

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
    # MIX DINÁMICO
    # =========================
    if df_mix is not None:

        col_desc = [c for c in df_mix.columns if "desc" in c.lower()]
        col_marca = [c for c in df_mix.columns if "marca" in c.lower()]
        col_mix = [c for c in df_mix.columns if "mix" in c.lower()]

        columnas = ['EAN']
        if col_mix: columnas.append(col_mix[0])
        if col_desc: columnas.append(col_desc[0])
        if col_marca: columnas.append(col_marca[0])

        df_mix_simple = df_mix[columnas].drop_duplicates()

        df_mix_simple = df_mix_simple.rename(columns={
            col_mix[0]: 'MIX ACTUAL',
            col_desc[0]: 'Descripción producto',
            col_marca[0]: 'MARCA'
        })

        df_group = df_group.merge(df_mix_simple, on='EAN', how='left')

    # =========================
    # OPTIMIZACIÓN REAL
    # =========================
    bdcf_tiendas = df_bdcf.groupby('Sigla BDCF')['Cod. Tienda'].nunique().to_dict()

    df_group['eficiencia'] = df_group['venta_valor_12'] / (df_group['tiendas_activas'] + 1)

    nuevo_mix = {}

    for _, row in df_group.iterrows():

        ean = row['EAN']
        decision = row['decision']

        if ean not in nuevo_mix:
            nuevo_mix[ean] = set()

        if decision in ["CORE","OPORTUNIDAD"]:
            for bdcf in bdcf_tiendas.keys():
                if row['eficiencia'] > df_group['eficiencia'].median():
                    nuevo_mix[ean].add(bdcf)

        elif decision == "ELIMINAR":
            nuevo_mix[ean] = set()

        else:
            actual = str(row.get('MIX ACTUAL',"")).split("-")
            nuevo_mix[ean] = set(actual)

    def join_mix(ean):
        return "-".join(sorted(nuevo_mix.get(ean, [])))

    df_group['MIX PROPUESTO'] = df_group['EAN'].apply(join_mix)

    # =========================
    # IMPACTO
    # =========================
    def contar_tiendas_mix(mix):
        if pd.isna(mix):
            return 0
        return sum([bdcf_tiendas.get(s,0) for s in str(mix).split("-")])

    df_group['tiendas_mix_actual'] = df_group['MIX ACTUAL'].apply(contar_tiendas_mix)
    df_group['tiendas_mix_nuevo'] = df_group['MIX PROPUESTO'].apply(contar_tiendas_mix)

    df_group['delta_tiendas'] = df_group['tiendas_mix_nuevo'] - df_group['tiendas_mix_actual']

    df_group['impacto_valor_mix'] = df_group['delta_tiendas'] * df_group['eficiencia']
    df_group['impacto_unidades_mix'] = df_group['delta_tiendas'] * (
        df_group['venta_unidades_12'] / (df_group['tiendas_activas'] + 1)
    )

    # =========================
    # TABLA FINAL
    # =========================
    st.subheader("📋 Resultado final")

    columnas = [
        'EAN','Descripción producto','MARCA',
        'venta_valor_12','venta_unidades_12',
        'tiendas_activas','cuadrante','decision',
        'MIX ACTUAL','MIX PROPUESTO',
        'delta_tiendas','impacto_valor_mix','impacto_unidades_mix'
    ]

    columnas = [c for c in columnas if c in df_group.columns]

    df_final = df_group[columnas]

    st.dataframe(df_final)

    # =========================
    # DESCARGA
    # =========================
    archivo_salida = "OPTIMIZACION_PORTAFOLIO_PRO.xlsx"
    df_final.to_excel(archivo_salida, index=False)

    with open(archivo_salida, "rb") as f:
        st.download_button("📥 Descargar análisis PRO", f, file_name=archivo_salida)