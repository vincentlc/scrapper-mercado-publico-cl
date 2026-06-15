"""
Test file to verify that map_offer_from_api handles multiple API response structures.
This tests the robustness of field extraction for region, comuna, and fecha_publicacion.
"""

import unittest
from scripts.update_offers import map_offer_from_api


class TestMapOfferFromApiRobustness(unittest.TestCase):
    """Pruebas para la robustez del mapeo de ofertas desde diferentes estructuras API"""

    def test_standard_api_structure(self):
        """Test con la estructura estándar de Mercado Público API"""
        item = {
            "CodigoExterno": "1002-59-LE26",
            "Nombre": "Convenio de Mantencion",
            "Descripcion": "Descripcion prueba",
            "Comprador": {
                "NombreOrganismo": "Ministerio Test",
                "RegionUnidad": "Región de los Lagos",
                "ComunaUnidad": "Puerto Montt",
            },
            "CodigoEstado": "5",
            "Fechas": {
                "FechaPublicacion": "2026-06-12T12:03:25",
                "FechaCierre": "2026-06-22T16:00:00",
            },
            "Moneda": "CLP",
            "MontoEstimado": "1000000",
        }
        
        result = map_offer_from_api(item)
        
        self.assertEqual(result["codigo_externo"], "1002-59-LE26")
        self.assertEqual(result["region"], "Región de los Lagos")
        self.assertEqual(result["comuna"], "Puerto Montt")
        self.assertIn("2026-06-12", result["fecha_publicacion"])

    def test_alternative_region_path_ubicacion(self):
        """Test cuando región está bajo Comprador.Ubicacion.Region"""
        item = {
            "CodigoExterno": "TEST-001",
            "Nombre": "Test Oferta",
            "Comprador": {
                "NombreOrganismo": "Org Test",
                "Ubicacion": {
                    "Region": "Región Metropolitana",
                    "Comuna": "Santiago",
                },
            },
            "CodigoEstado": "5",
            "Fechas": {
                "FechaPublicacion": "2026-06-12T00:00:00",
                "FechaCierre": "2026-06-22T16:00:00",
            },
        }
        
        result = map_offer_from_api(item)
        
        self.assertEqual(result["region"], "Región Metropolitana")
        self.assertEqual(result["comuna"], "Santiago")

    def test_alternative_fecha_at_root_level(self):
        """Test cuando fechas están al nivel raíz sin nesting Fechas"""
        item = {
            "CodigoExterno": "TEST-002",
            "Nombre": "Test Oferta 2",
            "Comprador": {
                "NombreOrganismo": "Org Test",
                "RegionUnidad": "Región del Biobío",
                "ComunaUnidad": "Concepción",
            },
            "CodigoEstado": "5",
            "FechaPublicacion": "2026-06-12T10:00:00",
            "FechaCierre": "2026-06-25T16:00:00",
            "Moneda": "CLP",
        }
        
        result = map_offer_from_api(item)
        
        self.assertEqual(result["region"], "Región del Biobío")
        self.assertEqual(result["comuna"], "Concepción")
        self.assertIn("2026-06-12", result["fecha_publicacion"])

    def test_region_at_root_level(self):
        """Test cuando región está directamente al nivel raíz"""
        item = {
            "CodigoExterno": "TEST-003",
            "Nombre": "Test Oferta 3",
            "Comprador": {
                "NombreOrganismo": "Org Test",
            },
            "Region": "Región de Valparaíso",
            "Comuna": "Valparaíso",
            "CodigoEstado": "5",
            "FechaPublicacion": "2026-06-15T08:00:00",
            "FechaCierre": "2026-06-30T17:00:00",
        }
        
        result = map_offer_from_api(item)
        
        self.assertEqual(result["region"], "Región de Valparaíso")
        self.assertEqual(result["comuna"], "Valparaíso")
        self.assertIn("2026-06-15", result["fecha_publicacion"])

    def test_mixed_standard_and_alternative_paths(self):
        """Test con mix de paths estándar y alternativos"""
        item = {
            "CodigoExterno": "TEST-004",
            "Nombre": "Test Oferta Mix",
            "Comprador": {
                "NombreOrganismo": "Org Test",
                "RegionUnidad": "Región de Aysén",
                "Ubicacion": {
                    "Comuna": "Coyhaique",  # Alternative path
                },
            },
            "CodigoEstado": "5",
            "Fechas": {
                "FechaPublicacion": "2026-06-10T14:30:00",
            },
            "FechaCierre": "2026-06-25T16:00:00",  # At root level
        }
        
        result = map_offer_from_api(item)
        
        self.assertEqual(result["region"], "Región de Aysén")
        self.assertEqual(result["comuna"], "Coyhaique")
        self.assertIn("2026-06-10", result["fecha_publicacion"])

    def test_fallback_to_lowercase_keys(self):
        """Test con fallback a claves en minúsculas"""
        item = {
            "codigoexterno": "TEST-005",  # lowercase
            "nombre": "Test Lowercase",
            "region": "Región de Magallanes",  # lowercase
            "comuna": "Punta Arenas",  # lowercase
            "fecha_publicacion": "2026-06-08T09:00:00",
            "CodigoEstado": "5",
        }
        
        result = map_offer_from_api(item)
        
        self.assertEqual(result["codigo_externo"], "TEST-005")
        self.assertEqual(result["region"], "Región de Magallanes")
        self.assertEqual(result["comuna"], "Punta Arenas")

    def test_missing_optional_fields(self):
        """Test cuando faltan algunos campos opcionales"""
        item = {
            "CodigoExterno": "TEST-006",
            "Nombre": "Test Sin Optional",
            "Comprador": {
                "NombreOrganismo": "Org Test",
            },
            "CodigoEstado": "5",
        }
        
        result = map_offer_from_api(item)
        
        self.assertEqual(result["codigo_externo"], "TEST-006")
        # Los campos vacíos deben ser strings vacíos, no None
        self.assertEqual(result["region"], "")
        self.assertEqual(result["comuna"], "")
        self.assertEqual(result["fecha_publicacion"], "")


if __name__ == "__main__":
    unittest.main()
