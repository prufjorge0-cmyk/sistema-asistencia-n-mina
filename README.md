# Control de asistencia

Aplicación Streamlit para registrar entradas y salidas, y calcular el reporte de nómina con datos guardados en Airtable.

## Configuración

Instala las dependencias y configura el token de Airtable en una variable de entorno llamada `AIRTABLE_API_KEY`. También puedes guardarlo en `.streamlit/secrets.toml`:

```toml
AIRTABLE_API_KEY = "patPYLvPYEccoc576.8e9f498bc1a22eea07ddb2746e96bea4581a564b1dc9da69f07d00376915e4c6"
```

No subas ese archivo ni compartas el token. El Base ID predeterminado es `appMxgsfddYoBt47A` y la tabla predeterminada es `Asistencias`. Si necesitas otros valores, configúralos como `AIRTABLE_BASE_ID` y `AIRTABLE_TABLE_NAME` en el entorno o en `secrets.toml`.

La tabla debe tener estos campos: `ID Empleado`, `Nombre Completo`, `Fecha Registro`, `Hora Entrada`, `Hora Salida` y `Tarifa por Hora`. `Fecha Registro` se envía como fecha ISO y las horas como fecha/hora ISO con zona horaria.

Ejecuta la aplicación con:

```text
streamlit run app.py
```
