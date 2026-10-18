import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
# Importa la librería que usarás para conectar con Airtable 
# (Ej: 'airtable-sdk' o simplemente 'requests' si usas API directa)


def connect_to_airtable(api_key, base_id):
    """Función placeholder: Inicializa la conexión a Airtable."""
    # Aquí iría tu lógica de autenticación con las credenciales.
    st.sidebar.header("⚙️ Configuración")
    st.sidebar.info("Asegúrate de que tus claves API y Base ID estén correctamente cargadas.")


def clock_in(employee_id):
    """Registra la entrada del empleado en Airtable."""
    timestamp = datetime.now()
    # 1. Lógica para consultar si hay un registro abierto HOY para este ID.
    # 2. Si lo encuentra, actualizarlo: Solo llenar 'Hora Entrada' con timestamp.
    # Ejemplo: write_to_airtable(data={'ID Empleado': employee_id, 'Fecha Registro': hoy, 'Hora Entrada': timestamp})
    st.success(f"🕒 ¡Entrada registrada para {employee_id} a las {timestamp.strftime('%H:%M')}!")


def clock_out(employee_id):
    """Registra la salida del empleado en Airtable y desencadena el cálculo."""
    timestamp = datetime.now()
    # 1. Lógica: Buscar el registro INCOMPLETO de HOY para este ID.
    # 2. Actualizar ese registro, llenando 'Hora Salida' con timestamp.
    st.success(f"🚀 ¡Salida registrada para {employee_id} a las {timestamp.strftime('%H:%M')}!")


def generate_report():
    """Lee los datos finales de Airtable y realiza los cálculos complejos en Python."""
    st.subheader("📊 Reporte Diario / Mensual")

    # 1. Consulta todos los registros de la base (filtrando por fecha).
    df = load_data_from_airtable() # Esta función trae los datos a un DataFrame
    
    if df.empty:
        st.warning("No hay registros de asistencia para mostrar.")
        return

    # 2. Filtro crucial: Solo calcula si ambas fechas (Entrada y Salida) están llenas.
    df_calculable = df[pd.notnull(df['Hora Entrada']) & pd.notnull(df['Hora Salida'])]
    
    if df_calculable.empty:
         st.info("Aún no hay registros de salida completados para calcular el pago.")
         return

    # --- CÁLCULOS DE PYTHON (EL MOTOR DEL PAGO) ---
    
    def calculate_pay(row):
        entrada = row['Hora Entrada'] # Debe ser un objeto datetime
        salida = row['Hora Salida'] # Debe ser un objeto datetime
        tarifa = row['Tarifa por Hora']

        # 1. Calcular la diferencia de tiempo (timedelta)
        tiempo_trabajado = salida - entrada
        
        # 2. Convertir a horas decimales: Total segundos / 3600
        horas_decimales = timedelta(seconds=int(tiempo_trabajado.total_seconds())) / 3600
        
        # 3. Calcular el pago bruto
        pago_bruto = round(horas_decimales * tarifa, 2)
        
        return pd.Series([horas_decimales, pago_bruto])

    # Aplicamos la función de cálculo a las columnas 'Hora Entrada' y 'Hora Salida'
    df_calculable[['Horas Trabajadas', 'Pago Bruto']] = df_calculable.apply(calculate_pay, axis=1)
    
    # 3. Mostrar el resultado limpio
    columna_reporte = df_calculable[['ID Empleado', 'Nombre Completo', 'Fecha Registro', 'Hora Entrada', 'Hora Salida', 'Horas Trabajadas', 'Pago Bruto']]
    st.dataframe(columna_reporte, use_container_width=True)

# --- Flujo de la aplicación Streamlit ---

connect_to_airtable(API_KEY, BASE_ID)

st.title("🕒 Sistema de Control de Asistencia y Nómina")

# 1. Sección de Asistencia (La caja de herramientas)
with st.container():
    employee_id = st.text_input("🆔 Ingresar ID del Empleado:", key="id_input").strip()
    st.write("---")

    col_in, col_out = st.columns(2)
    
    # Botón de Entrada (Clock In)
    with col_in:
        if st.button("✅ Registrar ENTRADA", key="btn_in"):
            if employee_id:
                clock_in(employee_id) # Llama a la función del paso 1
            else:
                st.error("Por favor, ingresa un ID de empleado.")

    # Botón de Salida (Clock Out)
    with col_out:
        if st.button("❌ Registrar SALIDA", key="btn_out"):
             if employee_id:
                clock_out(employee_id) # Llama a la función del paso 2
            else:
                st.error("Por favor, ingresa un ID de empleado.")

# 2. Sección de Reportes (El dashboard para el administrador)
st.markdown("---")
if st.button("📄 Generar Reporte Completo"):
    generate_report() # Llama a la función del paso 3

