# =========================
# LOGIN SIMPLE
# =========================
import streamlit as st

def check_login():

    usuarios = {
        "CatMan": "ESCatMan2026*",
        "CatMan2": "ESCatMan2026*2"
    }

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:

        st.title("🔐 Login")

        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")

        if st.button("Ingresar"):
            if usuario in usuarios and usuarios[usuario] == password:
                st.session_state.logged_in = True
                st.success("✅ Acceso concedido")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

        return False

    return True


# Ejecutar login
if not check_login():
    st.stop()


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
    # 2. DETECTAR SEMANAS (ROBUSTO)
    # =========================
    columnas_semanas = [
        col for col in df.columns 
        if isinstance(col, str) and "Venta Semana" in col
    ]

    columnas_semanas = sorted(
        columnas_semanas, 
        key=lambda x: int(x.split()[-1])
    )

    df[columnas_semanas] = df[columnas_semanas].fillna(0)

    df['Inventario actual en la tienda'] = df['Inventario actual en la tienda'].fillna(0)
    df['Pedido que ya va en transito'] = df['Pedido que ya va en transito'].fillna(0)

    ultimas_4_semanas = columnas_semanas[-4:]

    df['venta_promedio'] = df[ultimas_4_semanas].mean(axis=1)

    # =========================
    # 2.1 HISTÓRICO 2025 (ROBUSTO)
    # =========================
    columnas_meses = [
        col for col in df.columns 
        if isinstance(col, str) and "2025" in col
    ]

    if columnas_meses:
        df[columnas_meses] = df[columnas_meses].fillna(0)

        df['venta_promedio_mensual_2025'] = df[columnas_meses].mean(axis=1)
        df['venta_promedio_semanal_2025'] = df['venta_promedio_mensual_2025'] / 4
    else:
        df['venta_promedio_semanal_2025'] = df['venta_promedio']

    # =========================
    # 2.2 DEMANDA HÍBRIDA
    # =========================
    df['venta_hibrida'] = (
        df['venta_promedio'] * 0.7 +
        df['venta_promedio_semanal_2025'] * 0.3
    )

    # =========================
    # 3. DEMANDA
    # =========================
    df['demanda_lt'] = df['venta_hibrida'] * 2.6
    df['stock_seguridad'] = df['venta_hibrida']

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
        cobertura = row['inventario_proyectado'] / (row['venta_hibrida'] + 1)

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
    df['cobertura_semanas'] = df['inventario_proyectado'] / (df['venta_hibrida'] + 1)

    def clasificar(row):
        if row['venta_hibrida'] == 0:
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
    df['prioridad'] = df['pedido_ajustado'] * df['venta_hibrida']
    df = df.sort_values(by='prioridad', ascending=False)

    # =========================
    # 10. FILTROS
    # =========================
    st.sidebar.header("🔎 Filtros")

    df_filtrado = df.copy()

    if 'Tienda' in df_filtrado.columns:
        tiendas = st.sidebar.multiselect("Tienda", sorted(df_filtrado['Tienda'].dropna().unique()))
        if tiendas:
            df_filtrado = df_filtrado[df_filtrado['Tienda'].isin(tiendas)]

    if 'Tipo de portafolio' in df_filtrado.columns:
        portafolio = st.sidebar.multiselect("Portafolio", sorted(df_filtrado['Tipo de portafolio'].dropna().unique()))
        if portafolio:
            df_filtrado = df_filtrado[df_filtrado['Tipo de portafolio'].isin(portafolio)]

    if 'Segmento' in df_filtrado.columns:
        segmentos = st.sidebar.multiselect("Segmento", sorted(df_filtrado['Segmento'].dropna().unique()))
        if segmentos:
            df_filtrado = df_filtrado[df_filtrado['Segmento'].isin(segmentos)]

    if 'estado_producto' in df_filtrado.columns:
        estados = st.sidebar.multiselect("Estado producto", sorted(df_filtrado['estado_producto'].dropna().unique()))
        if estados:
            df_filtrado = df_filtrado[df_filtrado['estado_producto'].isin(estados)]

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

    col1.metric("Venta total", int(df['venta_hibrida'].sum()))
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
        st.dataframe(top[['pedido_ajustado', 'venta_hibrida']])

    with colB:
        st.write("⚠️ Riesgo quiebre")
        st.dataframe(riesgo_df[['venta_hibrida', 'inventario_proyectado']])

    with colC:
        st.write("💀 Productos muertos")
        st.dataframe(muertos[['venta_hibrida']])

# =========================
# 🤖 IA - RECOMENDACIONES
# =========================
st.subheader("🤖 Recomendaciones Inteligentes")

recomendaciones = []

# 1. Riesgo de quiebre
riesgo_pct = (df['estado_producto'] == "Riesgo quiebre").mean()

if riesgo_pct > 0.2:
    recomendaciones.append("⚠️ Alto riesgo de quiebre: aumentar cobertura o revisar inventarios")

# 2. Sobrestock
sobrestock_pct = (df['estado_producto'] == "Sobrestock").mean()

if sobrestock_pct > 0.2:
    recomendaciones.append("📉 Exceso de inventario: reducir pedidos en productos con baja rotación")

# 3. Productos muertos
muertos = (df['estado_producto'] == "Producto muerto").sum()

if muertos > 0:
    recomendaciones.append(f"💀 Hay {muertos} productos sin rotación: evaluar salida o liquidación")

# 4. Tendencia positiva
if 'tendencia' in df.columns:
    crecimiento = (df['tendencia'] > 0.3).sum()

    if crecimiento > 0:
        recomendaciones.append(f"📈 {crecimiento} productos con crecimiento: oportunidad de inversión")

# 5. Portafolio
fuera_portafolio = (df['Tipo de portafolio'] == "NO - FUERA DEL PORTAFOLIO IDEAL COLOMBIA").sum()

if fuera_portafolio > 0:
    recomendaciones.append("🚫 Productos fuera de portafolio detectados: revisar estrategia comercial")

# Mostrar recomendaciones
if recomendaciones:
    for r in recomendaciones:
        st.write(r)
else:
    st.write("✅ Portafolio en buen estado general")

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