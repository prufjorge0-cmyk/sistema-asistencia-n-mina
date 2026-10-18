import unittest
from datetime import date, datetime

import pandas as pd

import app


class PayrollReportTests(unittest.TestCase):
    def setUp(self):
        self.records = pd.DataFrame(
            [
                {
                    "ID Empleado": "101",
                    "Nombre Completo": "Ana",
                    "Fecha Registro": date(2026, 5, 1),
                    "Hora Entrada": datetime(2026, 5, 1, 8, 0),
                    "Hora Salida": datetime(2026, 5, 1, 9, 1),
                    "Tarifa por Hora": 10.5,
                },
                {
                    "ID Empleado": "101",
                    "Nombre Completo": "Ana",
                    "Fecha Registro": date(2026, 5, 2),
                    "Hora Entrada": datetime(2026, 5, 2, 8, 0),
                    "Hora Salida": datetime(2026, 5, 2, 9, 0),
                    "Tarifa por Hora": 10.5,
                },
                {
                    "ID Empleado": "202",
                    "Nombre Completo": "Luis",
                    "Fecha Registro": date(2026, 5, 2),
                    "Hora Entrada": datetime(2026, 5, 2, 8, 0),
                    "Hora Salida": pd.NaT,
                    "Tarifa por Hora": 20.0,
                },
                {
                    "ID Empleado": "202",
                    "Nombre Completo": "Luis",
                    "Fecha Registro": date(2026, 5, 3),
                    "Hora Entrada": pd.NaT,
                    "Hora Salida": datetime(2026, 5, 3, 9, 0),
                    "Tarifa por Hora": 20.0,
                },
                {
                    "ID Empleado": "202",
                    "Nombre Completo": "Luis",
                    "Fecha Registro": date(2026, 5, 4),
                    "Hora Entrada": datetime(2026, 5, 4, 8, 0),
                    "Hora Salida": datetime(2026, 5, 4, 10, 0),
                    "Tarifa por Hora": 20.0,
                },
            ]
        )

    def test_summarizes_completed_shifts_per_employee(self):
        detail, summary = app._build_payroll_report(self.records)

        self.assertEqual(len(detail), 3)
        ana = summary.loc[summary["ID Empleado"] == "101"].iloc[0]
        luis = summary.loc[summary["ID Empleado"] == "202"].iloc[0]
        self.assertEqual(ana["Horas Totales"], 2.02)
        self.assertEqual(ana["Pago total (S/)"], 21.21)
        self.assertEqual(luis["Horas Totales"], 2.0)
        self.assertEqual(luis["Pago total (S/)"], 40.0)
        self.assertEqual(
            summary.columns.tolist(),
            ["ID Empleado", "Nombre Completo", "Horas Totales", "Pago total (S/)"],
        )

    def test_filters_inclusive_date_range_and_excludes_incomplete_shifts(self):
        detail, summary = app._build_payroll_report(
            self.records, date(2026, 5, 2), date(2026, 5, 2)
        )

        self.assertEqual(detail["ID Empleado"].tolist(), ["101"])
        self.assertEqual(summary["Nombre Completo"].tolist(), ["Ana"])
        self.assertEqual(summary.iloc[0]["Horas Totales"], 1.0)

    def test_rounds_hours_before_multiplying_rate_like_airtable(self):
        records = pd.DataFrame(
            [
                {
                    "ID Empleado": "303",
                    "Nombre Completo": "Rosa",
                    "Fecha Registro": date(2026, 5, 4),
                    "Hora Entrada": datetime(2026, 5, 4, 8, 0),
                    "Hora Salida": datetime(2026, 5, 4, 9, 7, 30),
                    "Tarifa por Hora": 10.0,
                }
            ]
        )

        detail, summary = app._build_payroll_report(records)

        self.assertEqual(detail.iloc[0]["Horas Trabajadas"], 1.13)
        self.assertEqual(detail.iloc[0]["Pago por turno (S/)"], 11.3)
        self.assertEqual(summary.iloc[0]["Pago total (S/)"], 11.3)

    def test_empty_date_range_returns_empty_report_frames(self):
        detail, summary = app._build_payroll_report(
            self.records, date(2026, 6, 1), date(2026, 6, 30)
        )

        self.assertTrue(detail.empty)
        self.assertTrue(summary.empty)
        self.assertIn("Horas Trabajadas", detail.columns)
        self.assertIn("Pago total (S/)", summary.columns)

    def test_range_with_only_incomplete_shifts_returns_empty_report(self):
        detail, summary = app._build_payroll_report(
            self.records, date(2026, 5, 3), date(2026, 5, 3)
        )

        self.assertTrue(detail.empty)
        self.assertTrue(summary.empty)

    def test_rejects_reversed_date_range(self):
        with self.assertRaisesRegex(ValueError, "fecha inicial"):
            app._build_payroll_report(
                self.records, date(2026, 5, 3), date(2026, 5, 1)
            )


if __name__ == "__main__":
    unittest.main()
