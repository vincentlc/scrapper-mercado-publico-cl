"""
Pruebas unitarias para el módulo delivery (versión síncrona).
"""

import sys
import os
from datetime import datetime

# Configurar PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.alerts.models import EmailQueueItem
from scripts.alerts.delivery import MockEmailClient, EmailDelivery, DeliveryResult


def test_mock_client_send_email():
    """Prueba: envío exitoso con mock."""
    client = MockEmailClient()
    
    # Enviar email (usar versión síncrona)
    result = client.send_email_sync(
        to="test@example.com",
        subject="Test",
        html="<p>Test</p>",
        text="Test",
    )
    
    assert result['success'] is True
    assert 'message_id' in result
    assert len(client.sent_emails) == 1


def test_mock_client_multiple():
    """Prueba: múltiples envíos."""
    client = MockEmailClient()
    
    for i in range(3):
        client.send_email_sync(
            to=f"test{i}@example.com",
            subject=f"Test {i}",
            html=f"<p>Test {i}</p>",
            text=f"Test {i}",
        )
    
    assert len(client.sent_emails) == 3
    assert client.send_count == 3


def test_mock_client_reset():
    """Prueba: resetear estado."""
    client = MockEmailClient()
    
    client.send_email_sync(
        to="test@example.com",
        subject="Test",
        html="<p>Test</p>",
        text="Test",
    )
    
    assert client.send_count == 1
    
    client.reset()
    
    assert client.send_count == 0
    assert len(client.sent_emails) == 0


def test_delivery_result_to_dict():
    """Prueba: conversión a diccionario."""
    result = DeliveryResult(
        success=True,
        queue_id="q_001",
        email="test@example.com",
        message_id="msg_001",
    )
    
    data = result.to_dict()
    
    assert data['success'] is True
    assert data['queue_id'] == "q_001"
    assert data['email'] == "test@example.com"


def test_delivery_process_queue_item_max_attempts():
    """Prueba: procesar item con máximo de intentos."""
    client = MockEmailClient()
    delivery = EmailDelivery(client=client)
    
    item = EmailQueueItem(
        queue_id="q_002",
        user_id="usr_001",
        filter_id="fil_001",
        email="test@example.com",
        subject="Test",
        body_html="<p>Test</p>",
        status="pending",
        attempt_count=5,  # Más que MAX_ATTEMPTS
    )
    
    # Procesar item (síncrono)
    import asyncio
    result = asyncio.run(delivery.process_queue_item(item))
    
    assert result.success is False
    assert "Max attempts" in result.error


if __name__ == '__main__':
    # Ejecutar pruebas manualmente
    print("Running delivery tests...")
    
    test_mock_client_send_email()
    print("✓ test_mock_client_send_email")
    
    test_mock_client_multiple()
    print("✓ test_mock_client_multiple")
    
    test_mock_client_reset()
    print("✓ test_mock_client_reset")
    
    test_delivery_result_to_dict()
    print("✓ test_delivery_result_to_dict")
    
    test_delivery_process_queue_item_max_attempts()
    print("✓ test_delivery_process_queue_item_max_attempts")
    
    print("\nAll tests passed!")
