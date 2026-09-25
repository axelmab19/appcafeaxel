import streamlit as st
import pandas as pd
import os
import socket
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
# FUNCIONES DE IMPRESIÓN POR RED (ESC/POS)
# ==========================================
def enviar_a_impresora_red(ip_impresora, contenido_escpos, puerto=9100):
    """Envía comandos ESC/POS a impresoras térmicas conectadas por Wi-Fi / Ethernet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((ip_impresora, puerto))
        s.sendall(contenido_escpos)
        s.close()
        return True
    except Exception as e:
        return False

def generar_escpos_ticket(folio, fecha_hora, items, total, metodo_pago):
    """Genera el flujo de bytes ESC/POS para el ticket de cliente."""
    ESC = b'\x1b'
    GS = b'\x1d'
    
    # Inicializar, centrar, texto grande
    datos = ESC + b'@' + ESC + b'a\x01' + ESC + b'!\x18' + b"CYBER PUNK CAFE\n"
    datos += ESC + b'!\x00' + b"Tijuana, B.C.\n"
    datos += b"--------------------------------\n"
    datos += f"Folio: #{folio}\n".encode('utf-8')
    datos += f"Fecha: {fecha_hora}\n".encode('utf-8')
    datos += b"--------------------------------\n"
    
    # Alineación izquierda para los productos
    datos += ESC + b'a\x00'
    for item in items:
        prod = f"{item['Cantidad']}x {item['Producto']} ({item['Tamaño']})\n"
        detalles = f"   Leche: {item['Leche']}\n   Extras: {item['Extras']}\n"
        precio = f"   Total: ${item['Total']:.2f} MXN\n"
        datos += prod.encode('utf-8') + detalles.encode('utf-8') + precio.encode('utf-8')
    
    datos += b"--------------------------------\n"
    datos += ESC + b'a\x01' + ESC + b'!\x10' + f"TOTAL: ${total:.2f} MXN\n".encode('utf-8')
    datos += ESC + b'!\x00' + f"Pago: {metodo_pago}\n".encode('utf-8')
    datos += b"--------------------------------\n"
    datos += b"¡Gracias por tu compra!\n\n\n\n"
    
    # Comando de corte de papel (Corte total)
    datos += GS + b'V\x41\x00'
    return datos

def generar_escpos_comanda(folio, fecha_hora, items):
    """Genera el flujo de bytes ESC/POS para la comanda de la barra (Barista)."""
    ESC = b'\x1b'
    GS = b'\x1d'
    
    datos = ESC + b'@' + ESC + b'a\x01' + ESC + b'!\x30' + b"COMANDA BARRA\n"
    datos += ESC + b'!\x10' + f"ORDEN #{folio}\n".encode('utf-8')
    datos += ESC + b'!\x00' + f"Hora: {fecha_hora.split()[1]}\n".encode('utf-8')
    datos += b"================================\n"
    
    datos += ESC + b'a\x00' + ESC + b'!\x08'
    for item in items:
        linea_main = f"-> {item['Cantidad']}x {item['Producto'].upper()} ({item['Tamaño']})\n"
        linea_det = f"   * Leche: {item['Leche']}\n   * Extras: {item['Extras']}\n\n"
        datos += linea_main.encode('utf-8') + linea_det.encode('utf-8')
        
    datos += b"================================\n\n\n"
    datos += GS + b'V\x41\x00'
    return datos

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

if "folio_contador" not in st.session_state:
    st.session_state.folio_contador = 101

# ==========================================
# CONFIGURACIÓN EN BARRA LATERAL (IMPRESORAS)
# ==========================================
with st.sidebar:
    st.header("🖨️ Configuración de Impresoras")
    usar_impresion_red = st.checkbox("Habilitar Impresión por Red", value=False)
    ip_caja = st.text_input("IP Impresora Caja:", "192.168.1.100")
    ip_barra = st.text_input("IP Impresora Barra:", "192.168.1.101")

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
                folio = st.session_state.folio_contador
                
                # 1. Registrar venta en la sesión del turno
                for item in st.session_state.carrito:
                    item_guardar = item.copy()
                    item_guardar["Folio"] = folio
                    item_guardar["Fecha_Hora"] = fecha_hora
                    item_guardar["Metodo_Pago"] = metodo_pago
                    st.session_state.ventas_turno.append(item_guardar)
                
                # 2. Enviar a impresión por Red (si está habilitado)
                if usar_impresion_red:
                    bytes_ticket = generar_escpos_ticket(folio, fecha_hora, st.session_state.carrito, total_orden, metodo_pago)
                    bytes_comanda = generar_escpos_comanda(folio, fecha_hora, st.session_state.carrito)
                    
                    res_caja = enviar_a_impresora_red(ip_caja, bytes_ticket)
                    res_barra = enviar_a_impresora_red(ip_barra, bytes_comanda)
                    
                    if res_caja and res_barra:
                        st.toast("🖨️ Ticket y Comanda impresos con éxito.")
                    else:
                        st.warning("⚠️ No se pudo conectar a una o ambas impresoras de red.")

                st.session_state.folio_contador += 1
                st.session_state.carrito = []
                st.success(f"🎉 ¡Orden #{folio} Cobrada con Éxito!")
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
