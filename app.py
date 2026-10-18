import os
from datetime import date, datetime
from urllib.parse import quote

import pandas as pd
import requests

try:
    import streamlit as st
    from streamlit.errors import StreamlitSecretNotFoundError
except ModuleNotFoundError:  # pragma: no cover - Streamlit is optional for tests.
    st = None
    StreamlitSecretNotFoundError = None


DEFAULT_BASE_ID = "appMxgsfddYoBt47A"
DEFAULT_TABLE_NAME = "Asistencias"
DEFAULT_EMPLOYEE_TABLE_NAME = "Trabajador"
DEFAULT_HOURLY_RATE = 5.0
AIRTABLE_API_URL = "https://api.airtable.com/v0"
AIRTABLE_CONFIG = {
    "api_key": None,
    "base_id": DEFAULT_BASE_ID,
    "table_name": DEFAULT_TABLE_NAME,
    "employee_table_name": DEFAULT_EMPLOYEE_TABLE_NAME,
}
ATTENDANCE_COLUMNS = [
    "ID Empleado",
    "Nombre Completo",
    "Fecha Registro",
    "Hora Entrada",
    "Hora Salida",
    "Tarifa por Hora",
]


class AirtableAPIError(RuntimeError):
    """An Airtable configuration, network, or API error safe to show in the UI."""


def _get_secret(name):
    if st is None:
        return None
    try:
        return st.secrets.get(name)
    except (KeyError, StreamlitSecretNotFoundError):
        return None


def connect_to_airtable(
    api_key=None, base_id=None, table_name=None, employee_table_name=None
):
    """Load Airtable configuration from arguments, environment, or Streamlit secrets."""
    AIRTABLE_CONFIG["api_key"] = (
        api_key or os.getenv("AIRTABLE_API_KEY") or _get_secret("AIRTABLE_API_KEY")
    )
    AIRTABLE_CONFIG["base_id"] = (
        base_id
        or os.getenv("AIRTABLE_BASE_ID")
        or _get_secret("AIRTABLE_BASE_ID")
        or DEFAULT_BASE_ID
    )
    AIRTABLE_CONFIG["table_name"] = (
        table_name
        or os.getenv("AIRTABLE_TABLE_NAME")
        or _get_secret("AIRTABLE_TABLE_NAME")
        or DEFAULT_TABLE_NAME
    )
    AIRTABLE_CONFIG["employee_table_name"] = (
        employee_table_name
        or os.getenv("AIRTABLE_EMPLOYEE_TABLE_NAME")
        or _get_secret("AIRTABLE_EMPLOYEE_TABLE_NAME")
        or DEFAULT_EMPLOYEE_TABLE_NAME
    )

    if st is not None:
        st.sidebar.header("⚙️ Configuración")
        if AIRTABLE_CONFIG["api_key"]:
            st.sidebar.success("Conexión con Airtable configurada.")
        else:
            st.sidebar.info(
                "Configura AIRTABLE_API_KEY en las variables de entorno o en "
                ".streamlit/secrets.toml."
            )

    return {
        "configured": bool(AIRTABLE_CONFIG["api_key"]),
        "base_id": AIRTABLE_CONFIG["base_id"],
        "table_name": AIRTABLE_CONFIG["table_name"],
        "employee_table_name": AIRTABLE_CONFIG["employee_table_name"],
    }


def _airtable_url(record_id=None, table_name=None):
    api_key = AIRTABLE_CONFIG["api_key"]
    if not api_key:
        raise AirtableAPIError(
            "Falta configurar AIRTABLE_API_KEY en las variables de entorno o en "
            ".streamlit/secrets.toml."
        )

    base_id = AIRTABLE_CONFIG["base_id"]
    table_name = table_name or AIRTABLE_CONFIG["table_name"]
    if not base_id or not table_name:
        raise AirtableAPIError("Falta configurar el Base ID o la tabla de Airtable.")

    url = f"{AIRTABLE_API_URL}/{quote(base_id, safe='')}/{quote(table_name, safe='')}"
    if record_id:
        url = f"{url}/{quote(record_id, safe='')}"
    return url


def _airtable_request(
    method, record_id=None, *, params=None, payload=None, table_name=None
):
    headers = {
        "Authorization": f"Bearer {AIRTABLE_CONFIG['api_key']}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.request(
            method,
            _airtable_url(record_id, table_name=table_name),
            headers=headers,
            params=params,
            json=payload,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise AirtableAPIError(f"No se pudo conectar con Airtable: {exc}") from exc

    try:
        result = response.json()
    except ValueError as exc:
        raise AirtableAPIError("Airtable devolvió una respuesta JSON inválida.") from exc

    if not isinstance(result, dict):
        raise AirtableAPIError("Airtable devolvió una respuesta con formato inesperado.")

    if not response.ok:
        error = result.get("error", {})
        if isinstance(error, dict):
            detail = error.get("message") or error.get("type")
        else:
            detail = str(error)
        detail = detail or f"error HTTP {response.status_code}"
        raise AirtableAPIError(f"Airtable rechazó la solicitud: {detail}.")
    return result


def _build_empty_dataframe():
    return pd.DataFrame(columns=ATTENDANCE_COLUMNS + ["_airtable_record_id"])


def _coerce_datetime(value):
    if value is None or value == "":
        return pd.NaT
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return pd.NaT
    local_timezone = datetime.now().astimezone().tzinfo
    return parsed.tz_convert(local_timezone).tz_localize(None)


def _coerce_date(value):
    if value is None or value == "":
        return pd.NaT
    parsed = pd.to_datetime(value, errors="coerce")
    return parsed.date() if pd.notna(parsed) else pd.NaT


def _normalize_records(records):
    rows = []
    for record in records:
        fields = record.get("fields", {})
        row = {
            "ID Empleado": fields.get("Trabajador"),
            "Nombre Completo": "",
            "Fecha Registro": fields.get("Fecha"),
            "Hora Entrada": fields.get("Hora de entrada"),
            "Hora Salida": fields.get("Hora de salida"),
            "Tarifa por Hora": fields.get("Pago por hora"),
        }
        row["_airtable_record_id"] = record.get("id")
        rows.append(row)

    if not rows:
        return _build_empty_dataframe()

    df = pd.DataFrame(rows)
    df["Fecha Registro"] = df["Fecha Registro"].apply(_coerce_date)
    df["Hora Entrada"] = df["Hora Entrada"].apply(_coerce_datetime)
    df["Hora Salida"] = df["Hora Salida"].apply(_coerce_datetime)
    df["Tarifa por Hora"] = pd.to_numeric(
        df["Tarifa por Hora"], errors="coerce"
    ).fillna(0.0)
    return df[ATTENDANCE_COLUMNS + ["_airtable_record_id"]]


def load_data_from_airtable():
    """Load attendance records using the existing Airtable table schema."""
    records = []
    offset = None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        result = _airtable_request("GET", params=params)
        page = result.get("records")
        if not isinstance(page, list):
            raise AirtableAPIError("Airtable devolvió una lista de registros inválida.")
        records.extend(page)
        offset = result.get("offset")
        if not offset:
            break

    df = _normalize_records(records)
    if df.empty:
        return df

    employees = {}
    employee_ids_by_name = {}
    offset = None
    while True:
        params = {"pageSize": 100, "fields[]": ["ID Empleado", "Name"]}
        if offset:
            params["offset"] = offset
        result = _airtable_request(
            "GET",
            params=params,
            table_name=AIRTABLE_CONFIG["employee_table_name"],
        )
        page = result.get("records")
        if not isinstance(page, list):
            raise AirtableAPIError("Airtable devolvió una lista de empleados inválida.")
        for employee in page:
            fields = employee.get("fields", {})
            employee_id = fields.get("ID Empleado")
            if employee_id is not None:
                employee_name = fields.get("Name", "")
                employees[str(employee_id)] = employee_name
                if employee_name:
                    employee_ids_by_name[str(employee_name).strip().casefold()] = str(
                        employee_id
                    )
        offset = result.get("offset")
        if not offset:
            break

    attendance_ids = []
    employee_names = []
    for worker_value in df["ID Empleado"]:
        worker_value = str(worker_value).strip() if pd.notna(worker_value) else ""
        if worker_value in employees:
            attendance_ids.append(worker_value)
            employee_names.append(employees[worker_value])
        elif worker_value.strip().casefold() in employee_ids_by_name:
            employee_id = employee_ids_by_name[worker_value.strip().casefold()]
            attendance_ids.append(employee_id)
            employee_names.append(employees[employee_id])
        else:
            attendance_ids.append(pd.NA)
            employee_names.append(worker_value)
    df["ID Empleado"] = attendance_ids
    df["Nombre Completo"] = employee_names
    return df


def _find_employee(employee_id):
    escaped_id = str(employee_id).replace("\\", "\\\\").replace('"', '\\"')
    result = _airtable_request(
        "GET",
        params={
            "pageSize": 2,
            "filterByFormula": f'{{ID Empleado}} = "{escaped_id}"',
        },
        table_name=AIRTABLE_CONFIG["employee_table_name"],
    )
    employees = result.get("records")
    if not isinstance(employees, list):
        raise AirtableAPIError("Airtable devolvió una lista de empleados inválida.")
    if not employees:
        raise ValueError(f"No se encontró un trabajador con ID {employee_id}.")
    if len(employees) > 1:
        raise ValueError(f"El ID {employee_id} está duplicado en Trabajador.")

    fields = employees[0].get("fields", {})
    name = fields.get("Name")
    rate = pd.to_numeric(
        fields.get("Tarifa por Hora", DEFAULT_HOURLY_RATE), errors="coerce"
    )
    if pd.isna(rate):
        rate = DEFAULT_HOURLY_RATE
    if not name:
        raise ValueError(f"El trabajador {employee_id} no tiene un nombre en Name.")
    if pd.isna(rate) or rate < 0:
        raise ValueError(
            f"El trabajador {employee_id} no tiene una Tarifa por Hora válida."
        )
    return {"name": str(name), "rate_per_hour": float(rate)}


def _find_open_record(employee_id):
    df = load_data_from_airtable()
    matches = df[
        (df["ID Empleado"].astype(str) == str(employee_id))
        & (df["Fecha Registro"] == date.today())
        & df["Hora Entrada"].notna()
        & df["Hora Salida"].isna()
    ]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def _normalize_record(record):
    return _normalize_records([record]).iloc[0].to_dict()


def clock_in(employee_id, employee_name="", rate_per_hour=0.0):
    """Register an employee's clock-in event in Airtable."""
    if not employee_id:
        raise ValueError("Debe proporcionar un ID de empleado.")

    employee = _find_employee(employee_id)
    existing = _find_open_record(employee_id)
    if existing is not None:
        if st is not None:
            st.info(f"Ya existe una entrada abierta para {employee_id} hoy.")
        return existing

    now = datetime.now().astimezone()
    fields = {
        "Trabajador": str(employee_id),
        "Fecha": date.today().isoformat(),
        "Hora de entrada": now.isoformat(timespec="seconds"),
        "Pago por hora": employee["rate_per_hour"],
    }
    record = _airtable_request("POST", payload={"fields": fields})
    normalized = _normalize_record(record)

    if st is not None:
        st.success(
            f"🕒 ¡Entrada registrada para {employee_id} "
            f"a las {normalized['Hora Entrada'].strftime('%H:%M')}!"
        )
    return normalized


def clock_out(employee_id, employee_name="", rate_per_hour=0.0):
    """Register an employee's clock-out event and finalize the Airtable record."""
    if not employee_id:
        raise ValueError("Debe proporcionar un ID de empleado.")

    _find_employee(employee_id)
    record = _find_open_record(employee_id)
    if record is None:
        if st is not None:
            st.warning(f"No hay una entrada abierta para {employee_id} en este día.")
        return None

    fields = {
        "Hora de salida": datetime.now().astimezone().isoformat(timespec="seconds")
    }
    updated = _airtable_request(
        "PATCH",
        record_id=record["_airtable_record_id"],
        payload={"fields": fields},
    )
    normalized = _normalize_record(updated)

    if st is not None:
        st.success(
            f"🚀 ¡Salida registrada para {employee_id} "
            f"a las {normalized['Hora Salida'].strftime('%H:%M')}!"
        )
    return normalized


def generate_report():
    """Return a payroll report after validating completed attendance records."""
    if st is not None:
        st.subheader("📊 Reporte Diario / Mensual")

    df = load_data_from_airtable()
    if df.empty:
        if st is not None:
            st.warning("No hay registros de asistencia para mostrar.")
        return df.drop(columns=["_airtable_record_id"])

    df_calculable = df[
        pd.notnull(df["Hora Entrada"]) & pd.notnull(df["Hora Salida"])
    ].copy()

    if df_calculable.empty:
        if st is not None:
            st.info("Aún no hay registros de salida completados para calcular el pago.")
        return df_calculable.drop(columns=["_airtable_record_id"])

    def calculate_pay(row):
        entrada = pd.to_datetime(row["Hora Entrada"])
        salida = pd.to_datetime(row["Hora Salida"])
        tarifa = float(row.get("Tarifa por Hora", 0.0) or 0.0)

        if pd.isna(entrada) or pd.isna(salida):
            return pd.Series({"Horas Trabajadas": 0.0, "Pago Bruto": 0.0})

        horas_decimales = (salida - entrada).total_seconds() / 3600.0
        pago_bruto = round(horas_decimales * tarifa, 2)
        return pd.Series({"Horas Trabajadas": horas_decimales, "Pago Bruto": pago_bruto})

    df_calculable[["Horas Trabajadas", "Pago Bruto"]] = df_calculable.apply(
        calculate_pay, axis=1
    )
    columna_reporte = df_calculable[
        [
            "ID Empleado",
            "Nombre Completo",
            "Fecha Registro",
            "Hora Entrada",
            "Hora Salida",
            "Horas Trabajadas",
            "Pago Bruto",
        ]
    ]

    if st is not None:
        st.dataframe(columna_reporte, width="stretch")
    return columna_reporte


def _show_airtable_error(action):
    try:
        action()
    except (AirtableAPIError, ValueError) as exc:
        st.error(str(exc))


if __name__ == "__main__" and st is not None:
    connect_to_airtable()

    st.title("🕒 Sistema de Control de Asistencia y Nómina")

    with st.container():
        employee_id = st.text_input("🆔 Ingresar ID del Empleado:", key="id_input").strip()
        st.write("---")

        col_in, col_out = st.columns(2)

        with col_in:
            if st.button("✅ Registrar ENTRADA", key="btn_in"):
                if employee_id:
                    _show_airtable_error(lambda: clock_in(employee_id))
                else:
                    st.error("Por favor, ingresa un ID de empleado.")

        with col_out:
            if st.button("❌ Registrar SALIDA", key="btn_out"):
                if employee_id:
                    _show_airtable_error(lambda: clock_out(employee_id))
                else:
                    st.error("Por favor, ingresa un ID de empleado.")

    st.markdown("---")
    if st.button("📄 Generar Reporte Completo"):
        _show_airtable_error(generate_report)
