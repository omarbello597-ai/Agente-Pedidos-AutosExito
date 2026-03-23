import streamlit as st
import pandas as pd
import numpy as np

st.title("📦 Agente Inteligente de Pedidos")

archivo = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

if archivo:

    # =========================
    # 1. CARGAR DATA
    # =========================
    df = pd.read_excel(archivo)

    # =========================
    # 2. LIMPIEZA
    # =========================
    df.columns = df.columns.str.strip()

    # Detectar columnas de semanas dinámicamente
    columnas_semanas = [col for col in df.columns if "Venta Semana" in col]

    columnas_semanas = sorted(
        columnas_semanas,
        key=lambda x: int(x.split()[-1])
    )

    df[columnas_semanas] = df[columnas_semanas].fillna(0)

    df['Inventario actual en la tienda'] = df['Inventario actual en la tienda'].fillna(0)
    df['Pedido que ya va en transito'] = df['Pedido que ya va en transito'].fillna(0)

    # =========================
    # 3. ÚLTIMAS 4 SEMANAS
    # =========================
    ultimas_4_semanas = columnas_semanas[-4:]

    df['venta_promedio'] = df[ultimas_4_semanas].mean(axis=1)

    # =========================
    # 4. DEMANDA Y STOCK
    # =========================
    df['demanda_lt'] = df['venta_promedio'] * 2.6
    df['stock_seguridad'] = df['venta_promedio'] * 1

    df['inventario_proyectado'] = (
        df['Inventario actual en la tienda'] +
        df['Pedido que ya va en transito']
    )

    # =========================
    # 5. PEDIDO BASE
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
    # 6. TENDENCIA DINÁMICA
    # =========================
    def calcular_tendencia(row):
        semanas = [row[col] for col in ultimas_4_semanas]

        if semanas[0] == 0:
            return 0

        return (semanas[-1] - semanas[0]) / (semanas[0] + 1)

    df['tendencia'] = df.apply(calcular_tendencia, axis=1)

    # =========================
    # 7. AJUSTE INTELIGENTE
    # =========================
    def ajustar_pedido(row):

        pedido = row['pedido_final']
        tendencia = row['tendencia']
        cobertura = row['inventario_proyectado'] / (row['venta_promedio'] + 1)

        # Tendencia
        if tendencia > 0.3:
            pedido *= 1.3
        elif tendencia < -0.3:
            pedido *= 0.7

        # Cobertura
        if cobertura > 6:
            pedido *= 0.5
        elif cobertura < 1:
            pedido *= 1.5

        return max(pedido, 0)

    df['pedido_ajustado'] = df.apply(ajustar_pedido, axis=1)

    # =========================
    # 8. REGLA DE PORTAFOLIO
    # =========================
    df['pedido_ajustado'] = np.where(
        df['Tipo de portafolio'] == "NO - FUERA DEL PORTAFOLIO IDEAL COLOMBIA",
        0,
        df['pedido_ajustado']
    )

    # =========================
    # 9. CLASIFICACIÓN
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
    # 10. PRIORIDAD
    # =========================
    df['prioridad'] = df['pedido_ajustado'] * df['venta_promedio']
    df = df.sort_values(by='prioridad', ascending=False)

    # =========================
    # 11. RESULTADOS
    # =========================
    st.success("✅ Pedido generado correctamente")

    st.subheader("📊 Top 20 productos priorizados")
    st.dataframe(df.head(20))

    # =========================
    # 12. DESCARGA
    # =========================
    output = "pedido_sugerido.xlsx"
    df.to_excel(output, index=False)

    with open(output, "rb") as f:
        st.download_button(
            label="📥 Descargar pedido",
            data=f,
            file_name=output
        )