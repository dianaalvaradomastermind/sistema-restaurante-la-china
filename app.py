import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Restaurante Nube", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIONES DE BASE DE DATOS ---
def obtener_data(hoja):
    return conn.read(worksheet=hoja, ttl=0)

def actualizar_data(df, hoja):
    conn.update(worksheet=hoja, data=df)

def agregar_platillo(nombre, precio, categoria, imagen):
    try:
        df_actual = obtener_data("menu")
        nuevo_platillo = pd.DataFrame([{
            "nombre": nombre,
            "precio": precio,
            "categoria": categoria,
            "imagen": imagen
        }])
        df_actualizado = pd.concat([df_actual, nuevo_platillo], ignore_index=True)
        actualizar_data(df_actualizado, "menu")
        return True
    except Exception as e:
        st.error(f"Error al guardar platillo: {e}")
        return False

def guardar_pedido(mesa, tipo_pedido, items_str, total):
    try:
        df_actual = obtener_data("pedidos")
        
        # Lógica para número de pedido correlativo
        if df_actual.empty or 'no_pedido' not in df_actual.columns:
            nuevo_folio = 1
        else:
            max_val = pd.to_numeric(df_actual['no_pedido'], errors='coerce').max()
            nuevo_folio = 1 if pd.isna(max_val) else int(max_val) + 1
        
        # Nuevo registro con TIPO DE PEDIDO
        nuevo_pedido = pd.DataFrame([{
            "mesa": mesa,
            "no_pedido": nuevo_folio,
            "tipo_pedido": tipo_pedido, # <-- Nuevo campo
            "items": items_str,
            "total": total,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        
        df_actualizado = pd.concat([df_actual, nuevo_pedido], ignore_index=True)
        actualizar_data(df_actualizado, "pedidos")
        return nuevo_folio
    except Exception as e:
        st.error(f"Error al guardar pedido: {e}")
        return None

# --- INTERFAZ DE USUARIO ---
def main():
    st.title("🍽️ Gestión de Restaurante")

    opcion = st.sidebar.selectbox("Selecciona una opción", ["Tomar Pedido", "Administrar Menú", "Reportes"])

    # ---------------- MÓDULO 1: ADMINISTRAR MENÚ ----------------
    if opcion == "Administrar Menú":
        st.header("📝 Gestión del Menú")
        
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre del Platillo")
            precio = st.number_input("Precio ($)", min_value=0.0, step=0.5)
        with col2:
            categoria = st.selectbox("Categoría", ["Entrada", "Plato Fuerte", "Bebidas", "Postre"])
            imagen = st.text_input("URL de la imagen (Direct Link de Drive/Web)")

        if st.button("Guardar Platillo"):
            if nombre and precio:
                with st.spinner("Guardando en la nube..."):
                    if agregar_platillo(nombre, precio, categoria, imagen):
                        st.success(f"¡{nombre} agregado!")
                        st.cache_data.clear()
            else:
                st.error("Nombre y precio son obligatorios.")

        st.divider()
        st.subheader("Menú Actual")
        try:
            st.dataframe(obtener_data("menu"), use_container_width=True)
        except:
            st.info("Agrega tu primer platillo para ver el menú.")

    # ---------------- MÓDULO 2: TOMAR PEDIDOS ----------------
    elif opcion == "Tomar Pedido":
        st.header("🛒 Nuevo Pedido")
        
        try:
            df_menu = obtener_data("menu")
            if df_menu.empty:
                st.warning("El menú está vacío. Agrega platillos primero.")
            else:
                col_config, col_pedido = st.columns([1, 2])
                
                with col_config:
                    st.subheader("Configuración")
                    mesa = st.selectbox("Mesa / Referencia", [f"Mesa {i}" for i in range(1, 21)] + ["Barra", "Domicilio"])
                    
                    # --- NUEVO SELECTOR DE TIPO DE PEDIDO ---
                    tipo_p = st.radio("Tipo de Pedido:", ["Comer en sitio", "Para llevar"])
                    st.info(f"Seleccionado: {tipo_p}")

                with col_pedido:
                    st.subheader("Selección de Productos")
                    seleccion = []
                    total_t = 0
                    
                    for _, row in df_menu.iterrows():
                        c1, c2, c3 = st.columns([1, 3, 1])
                        with c1:
                            if pd.notna(row['imagen']) and str(row['imagen']).strip() != "":
                                st.image(row['imagen'], width=60)
                            else:
                                st.write("🍴")
                        with c2:
                            st.write(f"**{row['nombre']}**")
                            st.caption(row['categoria'])
                        with c3:
                            if st.checkbox(f"${row['precio']}", key=f"chk_{row['nombre']}"):
                                seleccion.append(row['nombre'])
                                total_t += row['precio']
                    
                    st.divider()
                    st.metric("Total de la Cuenta", f"${total_t:.2f}")

                    if st.button("🔥 ENVIAR PEDIDO"):
                        if total_t > 0:
                            with st.spinner("Registrando..."):
                                items_s = ", ".join(seleccion)
                                folio = guardar_pedido(mesa, tipo_p, items_s, total_t)
                                
                            if folio:
                                st.balloons()
                                st.success(f"¡Pedido #{folio} ({tipo_p}) guardado para {mesa}!")
                        else:
                            st.error("No has seleccionado ningún producto.")
        except Exception as e:
            st.error("Error al conectar con la base de datos.")

    # ---------------- MÓDULO 3: REPORTES ----------------
    elif opcion == "Reportes":
        st.header("📊 Resumen de Ventas")
        if st.button("🔄 Actualizar Reporte"):
            st.cache_data.clear()
            
        try:
            df_v = obtener_data("pedidos")
            if not df_v.empty:
                # Reordenamos columnas para que tipo_pedido sea visible
                cols = ['no_pedido', 'tipo_pedido', 'mesa', 'items', 'total', 'fecha']
                st.dataframe(df_v[[c for c in cols if c in df_v.columns]], hide_index=True, use_container_width=True)
                
                st.divider()
                st.subheader(f"Total Vendido: ${df_v['total'].sum():.2f}")
            else:
                st.info("No hay ventas registradas.")
        except:
            st.error("Asegúrate de que la hoja 'pedidos' tenga la columna 'tipo_pedido'.")

if __name__ == '__main__':
    main()