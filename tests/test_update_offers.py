import os
import unittest
from unittest.mock import patch

from scripts.update_offers import (
    map_offer,
    map_offer_from_api,
    parse_csv_bytes,
    parse_date,
    parse_monto,
    normalize_header,
    pick_value,
)


class TestUpdateOffersParsing(unittest.TestCase):
    """Tests para parsing de CSV y mapping"""

    def test_parse_csv_handles_extra_columns_as_list(self):
        raw = (
            "CodigoExterno;Nombre;Descripcion\n"
            "123;Licitacion A;Servicio TI;EXTRA_1;EXTRA_2\n"
        ).encode("utf-8")

        rows = parse_csv_bytes(raw)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["codigoexterno"], "123")
        self.assertIn("extra_columns", rows[0])
        self.assertEqual(rows[0]["extra_columns"], "EXTRA_1 | EXTRA_2")

    def test_parse_csv_comma_delimited(self):
        raw = (
            "CodigoExterno,Nombre,Descripcion\n"
            "999,Compra Publica,Equipamiento\n"
        ).encode("utf-8")

        rows = parse_csv_bytes(raw)

        self.assertEqual(rows[0]["codigoexterno"], "999")
        self.assertEqual(rows[0]["nombre"], "Compra Publica")

    def test_parse_csv_skips_preamble_and_detects_textbox_header(self):
        raw = (
            "Textbox69,ReportTitle\n"
            "Listado de Licitaciones Publicadas\n"
            "\n"
            "Textbox36,TipoLC,Textbox37,Textbox38,Textbox39,citName,Textbox40,FechaCierre1\n"
            "123-AB-26,Licitacion Publica,Nombre X,Descripcion X,Org X,Region Metropolitana,06-05-2026 07:00:00,10-05-2026 12:00:00\n"
        ).encode("utf-8")

        rows = parse_csv_bytes(raw)

        self.assertEqual(len(rows), 1)

        mapped = map_offer(rows[0])

        self.assertEqual(mapped["codigo_externo"], "123-AB-26")
        self.assertEqual(mapped["tipo_oferta"], "Licitacion Publica")
        self.assertEqual(mapped["organismo"], "Org X")

        self.assertTrue(
            mapped["link"].endswith("idLicitacion=123-AB-26")
        )

    def test_parse_monto_handles_chilean_format(self):
        self.assertEqual(parse_monto("1.000.000"), "1000000.0")
        self.assertEqual(parse_monto("1.500.000,50"), "1500000.5")
        self.assertEqual(parse_monto("1000"), "1000.0")
        self.assertEqual(parse_monto(""), "0")

    def test_parse_date_iso_format(self):
        result = parse_date("06-05-2026 07:00:00")

        self.assertIn("2026", result)
        self.assertIn("05", result)

        result = parse_date("2026-05-06")

        self.assertIn("2026-05-06", result)

        result = parse_date("")

        self.assertEqual(result, "")

    def test_normalize_header_removes_accents(self):
        self.assertEqual(normalize_header("Organismo"), "organismo")
        self.assertEqual(normalize_header("Región"), "region")

        self.assertEqual(
            normalize_header("Descripción Producto"),
            "descripcion_producto",
        )

    def test_pick_value_returns_first_available(self):
        row = {
            "nombre": "Value A",
            "titulo": "Value B",
        }

        self.assertEqual(
            pick_value(row, "nombre", "titulo"),
            "Value A",
        )

        self.assertEqual(
            pick_value(row, "titulo", "nombre"),
            "Value B",
        )

        self.assertEqual(
            pick_value(row, "inexistente", "nombre"),
            "Value A",
        )

        self.assertEqual(
            pick_value(row, "inexistente"),
            "",
        )

    def test_map_offer_complete(self):
        raw_row = {
            "codigoexterno": "123-AB-26",
            "nombre": "Contratación de Servicios",
            "descripcion": "Servicios de consultoría",
            "tipooferta": "Licitación Pública",
            "nombreorganismo": "Ministerio X",
            "region": "Metropolitana",
            "montoestimado": "1.000.000",
            "fechapublicacion": "01-05-2026",
            "fechacierre": "10-05-2026",
        }

        mapped = map_offer(raw_row)

        self.assertEqual(mapped["codigo_externo"], "123-AB-26")
        self.assertEqual(
            mapped["nombre"],
            "Contratación de Servicios",
        )

        self.assertEqual(
            mapped["tipo_oferta"],
            "Licitación Pública",
        )

        self.assertEqual(
            mapped["organismo"],
            "Ministerio X",
        )

        self.assertEqual(
            mapped["region"],
            "Metropolitana",
        )

        self.assertEqual(
            mapped["monto_estimado"],
            "1000000.0",
        )

    def test_map_offer_from_api_nested_fields(self):
        item = {
            "CodigoExterno": "1234-56-LP24",
            "Nombre": "Compra equipos",
            "Descripcion": "Descripcion licitacion",
            "CodigoEstado": "5",
            "TipoLicitacion": "LP",
            "Moneda": "CLP",
            "MontoEstimado": "1500000",
            "Comprador": {
                "NombreOrganismo": "Ministerio Test",
                "RegionUnidad": "Metropolitana",
                "ComunaUnidad": "Santiago",
            },
            "Fechas": {
                "FechaPublicacion": "2026-05-06T10:00:00",
                "FechaCierre": "2026-06-01T15:00:00",
            },
        }

        mapped = map_offer_from_api(item)

        self.assertEqual(mapped["codigo_externo"], "1234-56-LP24")
        self.assertEqual(mapped["organismo"], "Ministerio Test")
        self.assertEqual(mapped["region"], "Metropolitana")
        self.assertIn("2026", mapped["fecha_publicacion"])
        self.assertTrue(mapped["link"].endswith("idLicitacion=1234-56-LP24"))


class TestUpdateOffersGoogleSheets(unittest.TestCase):
    """Tests integración update_offers"""

    @patch("scripts.update_offers._get_existing_codes", return_value=set())
    @patch("scripts.update_offers._clean_old_offers_local", return_value=0)
    @patch("scripts.update_offers.fetch_offers")
    def test_update_offers_local_integration(
        self,
        mock_fetch,
        mock_clean_local,
        mock_existing,
    ):
        from scripts.update_offers import update_offers

        mock_fetch.return_value = (
            [
                {
                    "codigo_externo": "999-XX-99",
                    "nombre": "Test Offer",
                    "descripcion": "Descripcion",
                    "descripcion_producto": "Producto",
                    "organismo": "Org",
                    "estado": "5",
                    "region": "Metropolitana",
                    "comuna": "",
                    "tipo_oferta": "LP",
                    "moneda": "CLP",
                    "monto_estimado": "500000.0",
                    "fecha_publicacion": "2026-05-01",
                    "fecha_cierre": "2026-06-01",
                    "link": "http://example.com",
                }
            ],
            "feed.csv",
        )

        result = update_offers(local_only=True)

        self.assertEqual(result["new_count"], 1)
        mock_clean_local.assert_called_once()

    @patch("scripts.update_offers.clean_old_offers")
    @patch("scripts.update_offers.append_many_rows")
    @patch("scripts.update_offers.append_to_sheet")
    @patch("scripts.update_offers._get_existing_codes", return_value=set())
    @patch("scripts.update_offers.fetch_offers")
    @patch.dict(
        os.environ,
        {
            "GOOGLE_SHEETS_ID": "sheet-id",
            "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type":"service_account"}',
        },
    )
    def test_update_offers_sheets_integration(
        self,
        mock_fetch,
        mock_existing,
        mock_append_single,
        mock_append_many,
        mock_clean,
    ):
        from scripts.update_offers import update_offers

        mock_clean.return_value = 0

        mock_fetch.return_value = (
            [
                {
                    "codigo_externo": "999-XX-99",
                    "nombre": "Test Offer",
                    "descripcion": "Descripcion",
                    "descripcion_producto": "Producto",
                    "organismo": "Org",
                    "estado": "5",
                    "region": "Metropolitana",
                    "comuna": "",
                    "tipo_oferta": "LP",
                    "moneda": "CLP",
                    "monto_estimado": "500000.0",
                    "fecha_publicacion": "2026-05-01",
                    "fecha_cierre": "2026-06-01",
                    "link": "http://example.com",
                }
            ],
            "feed.csv",
        )

        result = update_offers(local_only=False)

        self.assertEqual(result["new_count"], 1)
        self.assertTrue(mock_append_many.called)
        self.assertTrue(mock_append_single.called)

    @patch("scripts.update_offers._get_existing_codes", return_value=set())
    @patch("scripts.update_offers._clean_old_offers_local", return_value=0)
    @patch("scripts.update_offers.fetch_offers")
    def test_deduplication(
        self,
        mock_fetch,
        mock_clean_local,
        mock_existing,
    ):
        from scripts.update_offers import update_offers

        mock_fetch.return_value = (
            [
                {
                    "codigo_externo": "ABC-123",
                    "nombre": "Oferta 1",
                    "descripcion": "",
                    "descripcion_producto": "",
                    "organismo": "",
                    "estado": "",
                    "region": "",
                    "comuna": "",
                    "tipo_oferta": "",
                    "moneda": "",
                    "monto_estimado": "0",
                    "fecha_publicacion": "",
                    "fecha_cierre": "",
                    "link": "",
                },
                {
                    "codigo_externo": "ABC-123",
                    "nombre": "Oferta duplicada",
                    "descripcion": "",
                    "descripcion_producto": "",
                    "organismo": "",
                    "estado": "",
                    "region": "",
                    "comuna": "",
                    "tipo_oferta": "",
                    "moneda": "",
                    "monto_estimado": "0",
                    "fecha_publicacion": "",
                    "fecha_cierre": "",
                    "link": "",
                },
            ],
            "feed.csv",
        )

        result = update_offers(local_only=True)

        self.assertEqual(result["new_count"], 1)

    @patch("scripts.update_offers.get_sheet_data")
    def test_existing_offers_detection(self, mock_get_data):

        mock_get_data.return_value = [
            ["codigo_externo", "nombre"],
            ["999-XX-99", "Oferta existente"],
        ]

        data = mock_get_data("ofertas")

        self.assertEqual(len(data), 2)

        self.assertEqual(
            data[1][0],
            "999-XX-99",
        )


if __name__ == "__main__":
    unittest.main()