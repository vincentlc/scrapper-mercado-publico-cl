"""
Pruebas unitarias para el módulo delivery (versión simple).
"""

import pytest
import asyncio
from datetime import datetime
import sys
import os

# Configurar PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.alerts.models import EmailQueueItem
from scripts.alerts.delivery import MockEmailClient, EmailDelivery, DeliveryResult


@pytest.fixture
def mock_client():
    return MockEmailClient()


@pytest.fixture
def delivery(mock_client):
    return EmailDelivery(client=mock_client)


@pytest.fixture
def sample_queue_item():
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


class TestMockEmailClient:
    @pytest.mark.asyncio
    async def test_send_email_success(self, mock_client):
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
    async def test_send_email_multiple(self, mock_client):
        for i in range(3):
            await mock_client.send_email(
                to=f"test{i}@example.com",
                subject=f"Test {i}",
            )
        
        assert len(mock_client.sent_emails) == 3
        assert mock_client.send_count == 3
    
    def test_reset(self, mock_client):
        asyncio.run(mock_client.send_email(
            to="test@example.com",
            subject="Test",
        ))
        
        mock_client.reset()
        
        assert mock_client.send_count == 0
        assert len(mock_client.sent_emails) == 0


class TestEmailDelivery:
    @pytest.mark.asyncio
    async def test_send_email_directly(self, delivery, sample_queue_item):
        result = await delivery.send_email(
            to=sample_queue_item.email,
            subject=sample_queue_item.subject,
            html=sample_queue_item.body_html,
            text=sample_queue_item.body_text,
            queue_id=sample_queue_item.queue_id,
        )
        
        assert result.success is True
        assert result.queue_id == sample_queue_item.queue_id
    
    @pytest.mark.asyncio
    async def test_process_queue_item(self, delivery, sample_queue_item):
        result = await delivery.process_queue_item(sample_queue_item)
        
        assert result.success is True
        assert result.queue_id == sample_queue_item.queue_id
    
    @pytest.mark.asyncio
    async def test_process_queue_item_max_attempts(self, delivery):
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
        
        result = await delivery.process_queue_item(item)
        
        assert result.success is False
        assert "Max attempts" in result.error
    
    @pytest.mark.asyncio
    async def test_process_pending_queue(self, delivery):
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
            for i in range(3)
        ]
        
        stats = await delivery.process_pending_queue(items)
        
        assert stats['pending'] == 3
        assert stats['sent'] == 3
        assert stats['failed'] == 0


class TestDeliveryResult:
    def test_to_dict(self):
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
