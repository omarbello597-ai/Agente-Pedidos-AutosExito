import streamlit as st
import pandas as pd
import numpy as np

st.title("📦 Agente Inteligente de Pedidos")

archivo = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

if archivo:

    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip()

    # =========================
    # LIMPIEZA
    # =========================
    cols_numericas = [
        'Venta Semana 1','Venta Semana 2','Venta Semana 3','Venta Semana 4',
        'Venta Semana 5','Venta Semana 6','Venta Semana 7','Venta Semana 8',
        'Venta Semana 9','Venta Semana 10',
        'Inventario actual en la tienda',
        'Pedido que ya va en transito'
    ]

    df[cols_numericas] = df[cols_numericas].fillna(0)

    # =========================
    # BOTÓN
    # =========================
    if st.button("🚀 Generar Pedido"):

        # Promedio
        semanas = ['Venta Semana 7','Venta Semana 8','Venta Semana 9','Venta Semana 10']
        df['venta_promedio'] = df[semanas].mean(axis=1)

        # Demanda
        df['demanda_lt'] = df['venta_promedio'] * 2.6
        df['stock_seguridad'] = df['venta_promedio'] * 1

        # Inventario
        df['inventario_proyectado'] = (
            df['Inventario actual en la tienda'] +
            df['Pedido que ya va en transito']
        )

        # Pedido base
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

        # Tendencia
        def tendencia(row):
            ult = [row['Venta Semana 7'], row['Venta Semana 8'], row['Venta Semana 9'], row['Venta Semana 10']]
            if ult[0] == 0:
                return 0
            return (ult[-1] - ult[0]) / (ult[0] + 1)

        df['tendencia'] = df.apply(tendencia, axis=1)

        # Ajuste
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

        # 🚫 REGLA PORTAFOLIO
        df['pedido_ajustado'] = np.where(
            df['Tipo de portafolio'] == "NO - FUERA DEL PORTAFOLIO IDEAL COLOMBIA",
            0,
            df['pedido_ajustado']
        )

        # Prioridad
        df['prioridad'] = df['pedido_ajustado'] * df['venta_promedio']
        df = df.sort_values(by='prioridad', ascending=False)

        st.success("✅ Pedido generado")

        st.dataframe(df.head(20))

        # Descargar
        output = "pedido_sugerido.xlsx"
        df.to_excel(output, index=False)

        with open(output, "rb") as f:
            st.download_button("📥 Descargar pedido", f, file_name=output)