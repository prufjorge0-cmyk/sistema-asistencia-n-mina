import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

import pandas as pd

import app


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        instant = datetime(2026, 1, 2, 2, 0, tzinfo=timezone.utc)
        return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)


class PeruTimezoneTests(unittest.TestCase):
    def test_airtable_utc_timestamp_is_coerced_to_peru_time(self):
        converted = app._coerce_datetime("2026-01-02T02:00:00.000Z")

        self.assertEqual(converted, datetime(2026, 1, 1, 21, 0))

    def test_clock_in_writes_peru_timestamp_independent_of_server_timezone(self):
        def create_record(method, payload):
            return {"id": "rec123", "fields": payload["fields"]}

        with (
            patch.object(app, "datetime", FixedDateTime),
            patch.object(
                app,
                "_find_employee",
                return_value={"name": "Test Worker", "rate_per_hour": 5.0},
            ),
            patch.object(app, "_find_open_record", return_value=None),
            patch.object(app, "st", None),
            patch.object(app, "_airtable_request", side_effect=create_record) as request,
        ):
            app.clock_in("123")

        fields = request.call_args.kwargs["payload"]["fields"]
        recorded_at = datetime.fromisoformat(fields["Hora de entrada"])
        self.assertEqual(fields["Fecha"], "2026-01-01")
        self.assertEqual(recorded_at.date(), date(2026, 1, 1))
        self.assertEqual(recorded_at.hour, 21)
        self.assertEqual(recorded_at.utcoffset().total_seconds(), -5 * 60 * 60)

    def test_open_record_search_uses_peru_calendar_date(self):
        records = pd.DataFrame(
            [
                {
                    "ID Empleado": "123",
                    "Fecha Registro": date(2026, 1, 1),
                    "Hora Entrada": datetime(2026, 1, 1, 20, 0),
                    "Hora Salida": pd.NaT,
                }
            ]
        )

        with (
            patch.object(app, "datetime", FixedDateTime),
            patch.object(app, "load_data_from_airtable", return_value=records),
        ):
            found = app._find_open_record("123")

        self.assertIsNotNone(found)


if __name__ == "__main__":
    unittest.main()
