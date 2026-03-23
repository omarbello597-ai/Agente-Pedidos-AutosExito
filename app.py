import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

st.title("📦 Agente Inteligente de Abastecimiento")

archivo = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

if archivo:

    # =========================
    # 1. CARGAR DATA
    # =========================
    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip()

    # =========================
    # 2. DETECTAR SEMANAS
    # =========================
    columnas_semanas = [col for col in df.columns if "Venta Semana" in col]
    columnas_semanas = sorted(columnas_semanas, key=lambda x: int(x.split()[-1]))

    df[columnas_semanas] = df[columnas_semanas].fillna(0)

    df['Inventario actual en la tienda'] = df['Inventario actual en la tienda'].fillna(0)
    df['Pedido que ya va en transito'] = df['Pedido que ya va en transito'].fillna(0)

    ultimas_4_semanas = columnas_semanas[-4:]

    df['venta_promedio'] = df[ultimas_4_semanas].mean(axis=1)

    # =========================
    # 3. DEMANDA
    # =========================
    df['demanda_lt'] = df['venta_promedio'] * 2.6
    df['stock_seguridad'] = df['venta_promedio']

    df['inventario_proyectado'] = (
        df['Inventario actual en la tienda'] +
        df['Pedido que ya va en transito']
    )

    # =========================
    # 4. PEDIDO BASE
    # =========================
    df['pedido_sugerido'] = (
        df['demanda_lt'] +
        df['stock_seguridad'] -
        df['inventario_proyectado']
    )

    df['pedido_sugerido'] = np.where(df['pedido_sugerido'] < 0, 0, df['pedido_sugerido'])

    df['pedido_final'] = np.where(
        df['pedido_sugerido'] < df['Pedido Minimo a realizar'],
        df['Pedido Minimo a realizar'],
        df['pedido_sugerido']
    )

    # =========================
    # 5. TENDENCIA
    # =========================
    def tendencia(row):
        semanas = [row[col] for col in ultimas_4_semanas]
        if semanas[0] == 0:
            return 0
        return (semanas[-1] - semanas[0]) / (semanas[0] + 1)

    df['tendencia'] = df.apply(tendencia, axis=1)

    # =========================
    # 6. AJUSTE INTELIGENTE
    # =========================
    def ajustar(row):
        pedido = row['pedido_final']
        cobertura = row['inventario_proyectado'] / (row['venta_promedio'] + 1)

        if row['tendencia'] > 0.3:
            pedido *= 1.3
        elif row['tendencia'] < -0.3:
            pedido *= 0.7

        if cobertura > 6:
            pedido *= 0.5
        elif cobertura < 1:
            pedido *= 1.5

        return max(pedido, 0)

    df['pedido_ajustado'] = df.apply(ajustar, axis=1)

    # =========================
    # 7. PORTAFOLIO
    # =========================
    df['pedido_ajustado'] = np.where(
        df['Tipo de portafolio'] == "NO - FUERA DEL PORTAFOLIO IDEAL COLOMBIA",
        0,
        df['pedido_ajustado']
    )

    # =========================
    # 8. CLASIFICACIÓN
    # =========================
    df['cobertura_semanas'] = df['inventario_proyectado'] / (df['venta_promedio'] + 1)

    def clasificar(row):
        if row['venta_promedio'] == 0:
            return "Producto muerto"
        elif row['cobertura_semanas'] < 1:
            return "Riesgo quiebre"
        elif row['cobertura_semanas'] > 6:
            return "Sobrestock"
        else:
            return "Saludable"

    df['estado_producto'] = df.apply(clasificar, axis=1)

    # =========================
    # 9. PRIORIDAD
    # =========================
    df['prioridad'] = df['pedido_ajustado'] * df['venta_promedio']
    df = df.sort_values(by='prioridad', ascending=False)

    # =========================
    # 10. FILTROS
    # =========================
    st.sidebar.header("🔎 Filtros")

    df_filtrado = df.copy()

    # Tienda
    if 'Tienda' in df_filtrado.columns:
        tiendas = st.sidebar.multiselect("Tienda", sorted(df_filtrado['Tienda'].dropna().unique()))
        if tiendas:
            df_filtrado = df_filtrado[df_filtrado['Tienda'].isin(tiendas)]

    # Portafolio
    if 'Tipo de portafolio' in df_filtrado.columns:
        portafolio = st.sidebar.multiselect("Portafolio", sorted(df_filtrado['Tipo de portafolio'].dropna().unique()))
        if portafolio:
            df_filtrado = df_filtrado[df_filtrado['Tipo de portafolio'].isin(portafolio)]

    # Segmento
    if 'Segmento' in df_filtrado.columns:
        segmentos = st.sidebar.multiselect("Segmento", sorted(df_filtrado['Segmento'].dropna().unique()))
        if segmentos:
            df_filtrado = df_filtrado[df_filtrado['Segmento'].isin(segmentos)]

    # Formato
    if 'Formato' in df_filtrado.columns:
        formatos = st.sidebar.multiselect("Formato", sorted(df_filtrado['Formato'].dropna().unique()))
        if formatos:
            df_filtrado = df_filtrado[df_filtrado['Formato'].isin(formatos)]

    df = df_filtrado

    # =========================
    # 11. KPIs
    # =========================
    st.subheader("📊 KPIs del negocio")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Venta total", int(df['venta_promedio'].sum()))
    col2.metric("Pedido total", int(df['pedido_final'].sum()))

    riesgo = (df['estado_producto'] == "Riesgo quiebre").mean() * 100
    sobrestock = (df['estado_producto'] == "Sobrestock").mean() * 100

    col3.metric("% Quiebre", f"{riesgo:.1f}%")
    col4.metric("% Sobrestock", f"{sobrestock:.1f}%")

    # =========================
    # 12. INSIGHTS
    # =========================
    st.subheader("🧠 Insights automáticos")

    colA, colB, colC = st.columns(3)

    top = df.head(5)
    riesgo_df = df[df['estado_producto'] == "Riesgo quiebre"].head(5)
    muertos = df[df['estado_producto'] == "Producto muerto"].head(5)

    with colA:
        st.write("🔥 Top prioridad")
        st.dataframe(top[['pedido_ajustado', 'venta_promedio']])

    with colB:
        st.write("⚠️ Riesgo quiebre")
        st.dataframe(riesgo_df[['venta_promedio', 'inventario_proyectado']])

    with colC:
        st.write("💀 Productos muertos")
        st.dataframe(muertos[['venta_promedio']])

    # =========================
    # 13. VISUAL
    # =========================
    st.subheader("📊 Distribución del estado")
    st.bar_chart(df['estado_producto'].value_counts())

    # =========================
    # 14. TABLA FINAL
    # =========================
    st.subheader("📋 Resultado detallado")
    st.dataframe(df)

    # =========================
    # 15. DESCARGA
    # =========================
    output = "pedido_sugerido.xlsx"
    df.to_excel(output, index=False)

    with open(output, "rb") as f:
        st.download_button("📥 Descargar pedido", f, file_name=output)