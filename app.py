import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE PANTALLA TÁCTIL PARA iPAD
# ==========================================
st.set_page_config(
    page_title="POS Cafetería Táctil",
    page_icon="☕",
    layout="wide"
)

# Estilos CSS para botones coloridos, grandes y modernos
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 65px;
        font-size: 18px !important;
        font-weight: bold;
        border-radius: 12px;
        color: white !important;
        border: none;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.15);
        transition: transform 0.1s ease;
    }
    .stButton>button:active {
        transform: scale(0.96);
    }
    
    div[data-testid="column"]:nth-child(1) .stButton>button {
        background-color: #D97706 !important;
    }
    div[data-testid="column"]:nth-child(2) .stButton>button {
        background-color: #9333EA !important;
    }
    div[data-testid="column"]:nth-child(3) .stButton>button {
        background-color: #0D9488 !important;
    }
    
    .ticket-box {
        background-color: #1E293B;
        padding: 18px;
        border-radius: 12px;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# BASE DE DATOS DE MENÚ Y MODIFICADORES
# ==========================================
BEBIDAS_BASE = {
    "Espresso": 40.0,
    "Americano": 45.0,
    "Latte": 55.0,
    "Cappuccino": 55.0,
    "Mocha": 65.0,
    "Flat White": 60.0,
    "Caramel Macchiato": 70.0,
    "Chai Latte": 65.0,
    "Matcha Latte": 70.0
}

TAMAÑOS = {
    "12 oz (Chico)": 0.0,
    "16 oz (Mediano)": 10.0,
    "20 oz (Grande)": 20.0
}

LECHES = {
    "Entera": 0.0,
    "Deslactosada": 0.0,
    "Almendra": 12.0,
    "Avena": 15.0,
    "Coco": 12.0
}

EXTRAS = {
    "Shot Extra Espresso": 15.0,
    "Canela en Polvo": 0.0,
    "Jarabe de Vainilla": 10.0,
    "Jarabe de Avellana": 10.0,
    "Crema Batida": 10.0,
    "Caramelo Drizzle": 8.0
}

if "carrito" not in st.session_state:
    st.session_state.carrito = []

if "ventas_turno" not in st.session_state:
    st.session_state.ventas_turno = []

# ==========================================
# ESTRUCTURA DE LA INTERFAZ TÁCTIL
# ==========================================
col_armador, col_ticket = st.columns([65, 35])

with col_armador:
    st.title("☕ Personalizar Bebida")
    
    st.subheader("1️⃣ Selecciona la Bebida Base")
    bebida_seleccionada = st.radio(
        "Bebida Base:",
        options=list(BEBIDAS_BASE.keys()),
        horizontal=True,
        label_visibility="collapsed"
    )

    st.subheader("2️⃣ Tamaño y Tipo de Leche")
    col_tam, col_lec = st.columns(2)
    with col_tam:
        tamano_sel = st.selectbox("📏 Tamaño del Vaso:", list(TAMAÑOS.keys()))
    with col_lec:
        leche_sel = st.selectbox("🥛 Tipo de Leche:", list(LECHES.keys()))

    st.subheader("3️⃣ Extras y Toppings")
    extras_sel = st.multiselect("✨ Selecciona los extras que desea el cliente:", list(EXTRAS.keys()))

    precio_base = BEBIDAS_BASE[bebida_seleccionada]
    precio_tamano = TAMAÑOS[tamano_sel]
    precio_leche = LECHES[leche_sel]
    precio_extras = sum([EXTRAS[e] for e in extras_sel])
    
    precio_item_total = precio_base + precio_tamano + precio_leche + precio_extras

    st.markdown("---")
    
    col_p, col_btn = st.columns([4, 6])
    with col_p:
        st.metric("Precio de esta bebida:", f"${precio_item_total:.2f} MXN")
    with col_btn:
        if st.button("➕ AGREGAR A LA ORDEN", type="primary"):
            desc_extras = ", ".join(extras_sel) if extras_sel else "Ninguno"
            st.session_state.carrito.append({
                "Producto": bebida_seleccionada,
                "Tamaño": tamano_sel,
                "Leche": leche_sel,
                "Extras": desc_extras,
                "Precio_Unitario": precio_item_total,
                "Cantidad": 1,
                "Total": precio_item_total
            })
            st.toast(f"✅ Agregado: {bebida_seleccionada} ({tamano_sel})")
            st.rerun()

with col_ticket:
    st.title("🛒 Orden Actual")
    
    if not st.session_state.carrito:
        st.info("La orden está vacía. Selecciona los ingredientes a la izquierda.")
    else:
        df_ticket = pd.DataFrame(st.session_state.carrito)
        
        for idx, item in df_ticket.iterrows():
            st.markdown(f"**{item['Producto']}** ({item['Tamaño']}) - **${item['Total']:.2f} MXN**")
            st.caption(f"Leche: {item['Leche']} | Extras: {item['Extras']}")
            st.markdown("---")
            
        total_orden = df_ticket["Total"].sum()
        st.metric(label="TOTAL A COBRAR", value=f"${total_orden:.2f} MXN")

        st.subheader("Método de Pago")
        metodo_pago = st.radio(
            "Forma de pago:",
            ["Efectivo", "Tarjeta", "Transferencia"],
            horizontal=True
        )

        col_cobrar, col_limpiar = st.columns(2)

        with col_cobrar:
            if st.button("💳 TERMINAR Y COBRAR"):
                fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in st.session_state.carrito:
                    item["Fecha_Hora"] = fecha_hora
                    item["Metodo_Pago"] = metodo_pago
                    st.session_state.ventas_turno.append(item)
                
                st.session_state.carrito = []
                st.success("🎉 ¡Orden Cobrada con Éxito!")
                st.rerun()

        with col_limpiar:
            if st.button("❌ Cancelar Orden"):
                st.session_state.carrito = []
                st.rerun()

    st.markdown("---")
    st.subheader("📂 Guardado en Excel")
    if st.session_state.ventas_turno:
        if st.button("🔒 GUARDAR Y CIERRE EN DRIVE"):
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            nombre_archivo = f"Ventas_Cafeteria_{fecha_hoy}.xlsx"

            df_turno = pd.DataFrame(st.session_state.ventas_turno)

            if os.path.exists(nombre_archivo):
                df_existente = pd.read_excel(nombre_archivo)
                df_final = pd.concat([df_existente, df_turno], ignore_index=True)
            else:
                df_final = df_turno

            df_final.to_excel(nombre_archivo, index=False)
            st.session_state.ventas_turno = []
            st.success(f" Archivo '{nombre_archivo}' guardado exitosamente.")
            st.rerun()
