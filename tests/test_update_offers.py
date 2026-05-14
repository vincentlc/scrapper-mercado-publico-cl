import unittest

from scripts.update_offers import map_offer, parse_csv_bytes


class TestUpdateOffersParsing(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
