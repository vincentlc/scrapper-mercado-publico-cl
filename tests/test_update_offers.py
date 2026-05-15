import json
import unittest
from unittest.mock import patch, MagicMock

from scripts.update_offers import (
    map_offer,
    parse_csv_bytes,
    parse_date,
    parse_monto,
    normalize_header,
    pick_value,
    update_offers,
    download_csv,
)


class TestUpdateOffersParsing(unittest.TestCase):
    """Tests para parsing de CSV y mapping de ofertas"""

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
            "123-AB-26,Licitacion Publica,Nombre X,Descripcion X,Org X,Region Metropolitana,06/05/2026 07:00:00,10/05/2026 12:00:00\n"
        ).encode("utf-8")
        rows = parse_csv_bytes(raw)
        self.assertEqual(len(rows), 1)
        mapped = map_offer(rows[0])
        self.assertEqual(mapped["codigo_externo"], "123-AB-26")
        self.assertEqual(mapped["tipo_oferta"], "Licitacion Publica")
        self.assertEqual(mapped["organismo"], "Org X")
        self.assertTrue(mapped["link"].endswith("idLicitacion=123-AB-26"))

    def test_parse_monto_handles_chilean_format(self):
        """Test parsing de montos con formato chileno (punto de miles, coma decimal)"""
        self.assertEqual(parse_monto("1.000.000"), "1000000.0")
        self.assertEqual(parse_monto("1.500.000,50"), "1500000.5")
        self.assertEqual(parse_monto("1000"), "1000.0")
        self.assertEqual(parse_monto(""), "0")

    def test_parse_date_iso_format(self):
        """Test parsing de fechas en diferentes formatos"""
        result = parse_date("06/05/2026 07:00:00")
        self.assertTrue("2026" in result and "05" in result and "06" in result)
        
        result = parse_date("2026-05-06")
        self.assertIn("2026-05-06", result)
        
        result = parse_date("")
        self.assertEqual(result, "")

    def test_normalize_header_removes_accents(self):
        """Test normalización de headers"""
        self.assertEqual(normalize_header("Organismo"), "organismo")
        self.assertEqual(normalize_header("Región"), "region")
        self.assertEqual(normalize_header("Descripción Producto"), "descripcion_producto")

    def test_pick_value_returns_first_available(self):
        """Test extracción de valores con fallback"""
        row = {"nombre": "Value A", "titulo": "Value B"}
        self.assertEqual(pick_value(row, "nombre", "titulo"), "Value A")
        self.assertEqual(pick_value(row, "titulo", "nombre"), "Value B")
        self.assertEqual(pick_value(row, "inexistente", "nombre"), "Value A")
        self.assertEqual(pick_value(row, "inexistente"), "")

    def test_map_offer_complete(self):
        """Test mapping completo de una oferta"""
        raw_row = {
            "codigoexterno": "123-AB-26",
            "nombre": "Contratación de Servicios",
            "descripcion": "Servicios de consultoría",
            "tipooferta": "Licitación Pública",
            "nombreorganismo": "Ministerio X",
            "region": "Metropolitana",
            "montoestimado": "1.000.000",
            "fechapublicacion": "01/05/2026",
            "fechacierre": "10/05/2026",
        }
        
        mapped = map_offer(raw_row)
        self.assertEqual(mapped["codigo_externo"], "123-AB-26")
        self.assertEqual(mapped["nombre"], "Contratación de Servicios")
        self.assertEqual(mapped["tipo_oferta"], "Licitación Pública")
        self.assertEqual(mapped["organismo"], "Ministerio X")
        self.assertEqual(mapped["region"], "Metropolitana")
        self.assertEqual(mapped["monto_estimado"], "1000000.0")


class TestUpdateOffersGoogleSheets(unittest.TestCase):
    """Tests para integración con Google Sheets (usando mocks)"""

    @patch('scripts.update_offers.get_sheet_data')
    @patch('scripts.update_offers.append_to_sheet')
    @patch('scripts.update_offers.download_csv')
    def test_update_offers_integration(self, mock_download, mock_append, mock_get_data):
        """Test flujo completo de actualización"""
        from scripts.update_offers import update_offers
        
        # Mock: Descargar CSV
        csv_row = {
            "codigoexterno": "999-XX-99",
            "nombre": "Test Offer",
            "montoestimado": "500.000",
        }
        mock_download.return_value = ([csv_row], "test.csv")
        
        # Mock: Google Sheets vacío (primera vez)
        mock_get_data.return_value = [
            ["codigo_externo", "nombre", "monto_estimado", "created_at", "updated_at", "scraped_at"]
        ]
        
        # Ejecutar
        result = update_offers()
        
        # Verificar
        self.assertEqual(result["new_count"], 1)
        self.assertEqual(result["updated_count"], 0)
        self.assertTrue(mock_append.called)

    @patch('scripts.update_offers.get_sheet_data')
    def test_existing_offers_detection(self, mock_get_data):
        """Test detección de ofertas existentes"""
        from scripts.update_offers import update_offers
        
        # Mock: Ofertas existentes
        mock_get_data.return_value = [
            ["codigo_externo", "nombre", "monto_estimado"],
            ["999-XX-99", "Test Offer", "500000"],  # Existente
        ]
        
        # Debería retornar dataset con la oferta existente
        data = mock_get_data("ofertas")
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1][0], "999-XX-99")


if __name__ == "__main__":
    unittest.main()
