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


if not check_login():
    st.stop()


# =========================
# LIBRERÍAS
# =========================
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
    df.columns = df.columns.astype(str).str.strip()

    # eliminar duplicadas
    df = df.loc[:, ~df.columns.duplicated()]

    # =========================
    # 2. SEMANAS
    # =========================
    columnas_semanas = [
        col for col in df.columns
        if isinstance(col, str) and "Venta Semana" in col
    ]

    columnas_semanas = sorted(columnas_semanas, key=lambda x: int(x.split()[-1]))

    df[columnas_semanas] = df[columnas_semanas].fillna(0)

    df['Inventario actual en la tienda'] = df['Inventario actual en la tienda'].fillna(0)
    df['Pedido que ya va en transito'] = df['Pedido que ya va en transito'].fillna(0)

    ultimas_4 = columnas_semanas[-4:]

    df['venta_promedio'] = df[ultimas_4].mean(axis=1)

    # =========================
    # 2.1 HISTÓRICO 2025
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
    # DEMANDA HÍBRIDA
    # =========================
    df['venta_hibrida'] = (
        df['venta_promedio'] * 0.7 +
        df['venta_promedio_semanal_2025'] * 0.3
    )

    # =========================
    # DEMANDA
    # =========================
    df['demanda_lt'] = df['venta_hibrida'] * 2.6
    df['stock_seguridad'] = df['venta_hibrida']

    df['inventario_proyectado'] = (
        df['Inventario actual en la tienda'] +
        df['Pedido que ya va en transito']
    )

    # =========================
    # PEDIDO BASE
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
    # TENDENCIA
    # =========================
    def tendencia(row):
        semanas = [row[col] for col in ultimas_4]
        if semanas[0] == 0:
            return 0
        return (semanas[-1] - semanas[0]) / (semanas[0] + 1)

    df['tendencia'] = df.apply(tendencia, axis=1)

    # =========================
    # AJUSTE
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
    # PORTAFOLIO
    # =========================
    df['pedido_ajustado'] = np.where(
        df['Tipo de portafolio'] == "NO - FUERA DEL PORTAFOLIO IDEAL COLOMBIA",
        0,
        df['pedido_ajustado']
    )

    # =========================
    # CLASIFICACIÓN
    # =========================
    df['cobertura'] = df['inventario_proyectado'] / (df['venta_hibrida'] + 1)

    def clasificar(row):
        if row['venta_hibrida'] == 0:
            return "Producto muerto"
        elif row['cobertura'] < 1:
            return "Riesgo quiebre"
        elif row['cobertura'] > 6:
            return "Sobrestock"
        else:
            return "Saludable"

    df['estado_producto'] = df.apply(clasificar, axis=1)

    # =========================
    # PRIORIDAD
    # =========================
    df['prioridad'] = df['pedido_ajustado'] * df['venta_hibrida']
    df = df.sort_values(by='prioridad', ascending=False)

    # =========================
    # FILTROS
    # =========================
    st.sidebar.header("🔎 Filtros")

    df_f = df.copy()

    for col in ["Tienda","Tipo de portafolio","Segmento","Formato","estado_producto"]:
        if col in df_f.columns:
            val = st.sidebar.multiselect(col, sorted(df_f[col].dropna().unique()))
            if val:
                df_f = df_f[df_f[col].isin(val)]

    df = df_f

    # =========================
    # KPIs
    # =========================
    st.subheader("📊 KPIs")

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Venta", int(df['venta_hibrida'].sum()))
    c2.metric("Pedido", int(df['pedido_final'].sum()))

    riesgo = (df['estado_producto']=="Riesgo quiebre").mean()*100
    sobre = (df['estado_producto']=="Sobrestock").mean()*100

    c3.metric("% Quiebre", f"{riesgo:.1f}%")
    c4.metric("% Sobre", f"{sobre:.1f}%")

    # =========================
    # 🤖 IA
    # =========================
    st.subheader("🤖 IA - Recomendaciones")

    rec = []

    if riesgo > 20:
        rec.append("⚠️ Alto riesgo de quiebre")

    if sobre > 20:
        rec.append("📉 Reducir inventario")

    muertos = (df['estado_producto']=="Producto muerto").sum()
    if muertos>0:
        rec.append(f"💀 {muertos} productos sin rotación")

    crec = (df['tendencia']>0.3).sum()
    if crec>0:
        rec.append(f"📈 {crec} productos creciendo")

    for r in rec:
        st.write(r)

    # =========================
    # VISUAL
    # =========================
    st.bar_chart(df['estado_producto'].value_counts())

    # =========================
    # TABLA
    # =========================
    st.dataframe(df)

    # =========================
    # DESCARGA
    # =========================
    df.to_excel("pedido.xlsx", index=False)

    with open("pedido.xlsx","rb") as f:
        st.download_button("Descargar", f, "pedido.xlsx")