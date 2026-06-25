"""
Pruebas unitarias para el módulo delivery.

Estas pruebas verifican el envío de emails usando el MockEmailClient,
sin depender de servicios externos como Mailgun.
"""

import pytest
import asyncio
from datetime import datetime
import sys
import os

# Agregar el directorio scripts al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from alerts.models import User, UserFilter, Offer, EmailQueueItem, EmailEvent
from alerts.delivery import (
    MockEmailClient,
    EmailDelivery,
    DeliveryResult,
)


# Fixtures para datos de prueba

@pytest.fixture
def mock_client():
    """Cliente de email mock."""
    return MockEmailClient()


@pytest.fixture
def failing_mock_client():
    """Cliente mock que siempre falla."""
    return MockEmailClient(fail_every_n=1)


@pytest.fixture
def selective_failing_mock_client():
    """Cliente mock que falla para emails específicos."""
    return MockEmailClient(fail_pattern="fail@example.com")


@pytest.fixture
def delivery(mock_client):
    """Servicio de delivery con cliente mock."""
    return EmailDelivery(client=mock_client)


@pytest.fixture
def sample_queue_item():
    """Item de cola de ejemplo."""
    return EmailQueueItem(
        queue_id="q_001",
        user_id="usr_001",
        filter_id="fil_001",
        email="test@example.com",
        subject="Test Subject",
        body_html="<p>Test body</p>",
        body_text="Test body",
        status="pending",
        attempt_count=0,
        created_at=datetime.now().isoformat(),
    )


# Pruebas

class TestMockEmailClient:
    """Pruebas del cliente mock."""
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, mock_client):
        """Prueba: envío exitoso."""
        result = await mock_client.send_email(
            to="test@example.com",
            subject="Test",
            html="<p>Test</p>",
            text="Test",
        )
        
        assert result['success'] is True
        assert 'message_id' in result
        assert len(mock_client.sent_emails) == 1
    
    @pytest.mark.asyncio
    async def test_send_email_multiple_success(self, mock_client):
        """Prueba: múltiples envíos exitosos."""
        for i in range(5):
            result = await mock_client.send_email(
                to=f"test{i}@example.com",
                subject=f"Test {i}",
                html=f"<p>Test {i}</p>",
            )
            assert result['success'] is True
        
        assert len(mock_client.sent_emails) == 5
        assert mock_client.send_count == 5
    
    @pytest.mark.asyncio
    async def test_send_email_fail_every_n(self, failing_mock_client):
        """Prueba: fallo cada N envíos."""
        result1 = await failing_mock_client.send_email(
            to="test@example.com",
            subject="Test 1",
        )
        assert result1['success'] is False
        
        result2 = await failing_mock_client.send_email(
            to="test2@example.com",
            subject="Test 2",
        )
        assert result2['success'] is False
        
        assert len(failing_mock_client.failed_emails) == 2
    
    @pytest.mark.asyncio
    async def test_send_email_fail_pattern(self, selective_failing_mock_client):
        """Prueba: fallo para emails específicos."""
        # Este debería fallar
        result1 = await selective_failing_mock_client.send_email(
            to="fail@example.com",
            subject="Test",
        )
        assert result1['success'] is False
        
        # Este debería tener éxito
        result2 = await selective_failing_mock_client.send_email(
            to="success@example.com",
            subject="Test",
        )
        assert result2['success'] is True
    
    def test_reset(self, mock_client):
        """Prueba: resetear estado del mock."""
        # Enviar algunos emails
        asyncio.run(mock_client.send_email(
            to="test@example.com",
            subject="Test",
            html="<p>Test</p>",
        ))
        
        assert mock_client.send_count == 1
        
        # Resetear
        mock_client.reset()
        
        assert mock_client.send_count == 0
        assert len(mock_client.sent_emails) == 0
        assert len(mock_client.failed_emails) == 0


class TestEmailDelivery:
    """Pruebas del servicio de delivery."""
    
    @pytest.mark.asyncio
    async def test_send_email_directly(self, delivery, sample_queue_item):
        """Prueba: enviar email directamente."""
        result = await delivery.send_email(
            to=sample_queue_item.email,
            subject=sample_queue_item.subject,
            html=sample_queue_item.body_html,
            text=sample_queue_item.body_text,
            queue_id=sample_queue_item.queue_id,
            user_id=sample_queue_item.user_id,
            filter_id=sample_queue_item.filter_id,
        )
        
        assert result.success is True
        assert result.queue_id == sample_queue_item.queue_id
        assert result.email == sample_queue_item.email
    
    @pytest.mark.asyncio
    async def test_process_queue_item_success(self, delivery, sample_queue_item):
        """Prueba: procesar item de cola con éxito."""
        result = await delivery.process_queue_item(sample_queue_item)
        
        assert result.success is True
        assert result.queue_id == sample_queue_item.queue_id
    
    @pytest.mark.asyncio
    async def test_process_queue_item_max_attempts(self, delivery):
        """Prueba: procesar item con máximo de intentos."""
        # Crear item con muchos intentos
        item = EmailQueueItem(
            queue_id="q_002",
            user_id="usr_001",
            filter_id="fil_001",
            email="test@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            status="pending",
            attempt_count=3,  # Ya excedió el máximo
        )
        
        result = await delivery.process_queue_item(item)
        
        assert result.success is False
        assert "Max attempts" in result.error
    
    @pytest.mark.asyncio
    async def test_process_pending_queue(self, delivery):
        """Prueba: procesar cola pendiente."""
        items = [
            EmailQueueItem(
                queue_id=f"q_{i}",
                user_id="usr_001",
                filter_id="fil_001",
                email="test@example.com",
                subject=f"Test {i}",
                body_html=f"<p>Test {i}</p>",
                status="pending",
                attempt_count=0,
            )
            for i in range(5)
        ]
        
        stats = await delivery.process_pending_queue(items, max_concurrent=5)
        
        assert stats['pending'] == 5
        assert stats['sent'] == 5
        assert stats['failed'] == 0
    
    @pytest.mark.asyncio
    async def test_event_callbacks(self, delivery):
        """Prueba: callbacks de eventos."""
        events = []
        
        def event_callback(event):
            events.append(event)
        
        delivery.add_event_callback(event_callback)
        
        # Enviar email
        await delivery.send_email(
            to="test@example.com",
            subject="Test",
            html="<p>Test</p>",
            queue_id="q_003",
            user_id="usr_001",
            filter_id="fil_001",
        )
        
        # Debería haber registrado un evento
        assert len(events) == 1
        assert events[0].event_type == 'sent'
        assert events[0].queue_id == "q_003"


class TestDeliveryWithFailingClient:
    """Pruebas de delivery con cliente que falla."""
    
    @pytest.fixture
    def failing_delivery(self):
        """Delivery con cliente que falla."""
        client = MockEmailClient(fail_every_n=1)
        return EmailDelivery(client=client)
    
    @pytest.mark.asyncio
    async def test_send_email_failure(self, failing_delivery):
        """Prueba: envío fallido."""
        result = await failing_delivery.send_email(
            to="test@example.com",
            subject="Test",
            html="<p>Test</p>",
            queue_id="q_004",
        )
        
        assert result.success is False
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_process_queue_with_failures(self, failing_delivery):
        """Prueba: procesar cola con fallos."""
        items = [
            EmailQueueItem(
                queue_id="q_005",
                user_id="usr_001",
                filter_id="fil_001",
                email="test@example.com",
                subject="Test",
                body_html="<p>Test</p>",
                status="pending",
                attempt_count=0,
            ),
            EmailQueueItem(
                queue_id="q_006",
                user_id="usr_001",
                filter_id="fil_001",
                email="test2@example.com",
                subject="Test 2",
                body_html="<p>Test 2</p>",
                status="pending",
                attempt_count=0,
            ),
        ]
        
        stats = await failing_delivery.process_pending_queue(items)
        
        assert stats['pending'] == 2
        assert stats['failed'] == 2
    
    @pytest.mark.asyncio
    async def test_retry_after(self, failing_delivery):
        """Prueba: tiempo de reintento."""
        item = EmailQueueItem(
            queue_id="q_007",
            user_id="usr_001",
            filter_id="fil_001",
            email="test@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            status="pending",
            attempt_count=0,
        )
        
        result = await failing_delivery.process_queue_item(item)
        
        assert result.success is False
        assert result.retry_after is not None
        assert result.retry_after > 0


class TestDeliveryResult:
    """Pruebas de DeliveryResult."""
    
    def test_to_dict(self):
        """Prueba: conversión a diccionario."""
        result = DeliveryResult(
            success=True,
            queue_id="q_001",
            email="test@example.com",
            message_id="msg_001",
            error=None,
            retry_after=None,
        )
        
        data = result.to_dict()
        
        assert data['success'] is True
        assert data['queue_id'] == "q_001"
        assert data['email'] == "test@example.com"
        assert data['message_id'] == "msg_001"
        assert data['error'] is None
        assert data['retry_after'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
