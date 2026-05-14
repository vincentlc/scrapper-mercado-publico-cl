import sqlite3
import unittest

from app.query import build_offer_filters, normalize_option_values


class TestApiFilters(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE offers (
                codigo_externo TEXT,
                nombre TEXT,
                descripcion TEXT,
                descripcion_producto TEXT,
                organismo TEXT,
                estado TEXT,
                region TEXT,
                comuna TEXT,
                tipo_oferta TEXT,
                monto_estimado REAL,
                fecha_publicacion TEXT,
                fecha_cierre TEXT
            )
            """
        )
        self.conn.executemany(
            """
            INSERT INTO offers (
                codigo_externo, nombre, descripcion, descripcion_producto, organismo, estado, region, comuna,
                tipo_oferta, monto_estimado, fecha_publicacion, fecha_cierre
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("L1", "Compra de software ERP", "Servicio ERP municipal", "Licencia SaaS", "Municipalidad A", "Publicada", "Metropolitana", "Santiago", "Servicio", 1000000, "2026-05-01T10:00:00", "2026-06-01T10:00:00"),
                ("L2", "Adquisicion de computadores", "Compra hardware", "Notebook empresarial", "Municipalidad B", "Publicada", "Valparaiso", "Valparaiso", "Suministro", 2000000, "2026-05-02T10:00:00", "2026-05-15T10:00:00"),
                ("L3", "Servicio de mantencion", "Mantencion preventiva", "Kit mantenimiento", "Servicio Salud", "Cerrada", "Metropolitana", "Providencia", "Servicio", 3000000, "2026-04-15T10:00:00", "2026-04-30T10:00:00"),
                (
                    "L4",
                    "Compra publica menor",
                    "Texto ejemplo",
                    "Producto demo",
                    "Municipalidad C",
                    "Publicada",
                    "Biobio",
                    "Concepcion",
                    "Licitación pública inferior a 100 UTM",
                    0,
                    "2026-05-03T10:00:00",
                    "2026-07-01T10:00:00",
                ),
            ],
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def query_count(self, **kwargs):
        where_sql, args = build_offer_filters(**kwargs)
        row = self.conn.execute(f"SELECT COUNT(*) AS c FROM offers WHERE {where_sql}", args).fetchone()
        return row["c"]

    def test_filter_by_keyword(self):
        self.assertEqual(self.query_count(keyword="software"), 1)

    def test_filter_by_tipo_and_estado(self):
        self.assertEqual(self.query_count(tipo_oferta="Servicio", estado="Publicada"), 1)

    def test_filter_by_keyword_in_descripcion_producto(self):
        self.assertEqual(self.query_count(keyword="Notebook"), 1)

    def test_filter_by_monto_and_date(self):
        self.assertEqual(self.query_count(min_monto=1500000, start_date="2026-05-01"), 1)

    def test_filter_by_utm_range(self):
        self.assertEqual(self.query_count(utm_range="lt100"), 1)

    def test_filter_by_close_date_range(self):
        self.assertEqual(self.query_count(start_close_date="2026-05-01", end_close_date="2026-05-31"), 1)

    def test_normalize_option_values(self):
        values = normalize_option_values(
            [{"value": " Servicio "}, {"value": "Suministro"}, {"value": ""}, {"value": "Servicio"}]
        )
        self.assertEqual(values, ["Servicio", "Suministro"])


if __name__ == "__main__":
    unittest.main()
