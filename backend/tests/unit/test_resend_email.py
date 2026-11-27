from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from src.services import email_service
from src.services.email_service import SesEmailService, EmailContent, InlineImage


def service(**extra):
    values = dict(aws_region=None, aws_access_key_id=None, aws_secret_access_key=None,
        ses_from_email='unused@example.com', email_provider='resend',
        resend_api_key='synthetic-key', resend_from_email='App <mail@example.com>')
    values.update(extra)
    return SesEmailService(SimpleNamespace(**values))


def test_resend_works_without_aws_credentials_and_preserves_content(monkeypatch):
    response = MagicMock(status_code=200)
    response.json.return_value = {'id': 'test-message'}
    post = MagicMock(return_value=response)
    monkeypatch.setattr(email_service.requests, 'post', post)
    sender = service()
    assert sender.is_configured
    content = EmailContent('Verify', '<p>secret-link</p>', 'secret-link',
        headers=(('List-Unsubscribe-Post', 'List-Unsubscribe=One-Click'),),
        reply_to=('support@example.com',),
        inline_images=(InlineImage('preview@example.com', b'abc'),))
    assert sender._send('user@example.com', content) == {'MessageId': 'test-message'}
    payload = post.call_args.kwargs['json']
    assert payload['to'] == ['user@example.com']
    assert payload['html'] == content.html and payload['text'] == content.text
    assert payload['reply_to'] == ['support@example.com']
    assert payload['attachments'][0]['content_id'] == 'preview@example.com'
    assert payload['attachments'][0]['content'] == 'YWJj'
    assert payload['headers']['List-Unsubscribe-Post'] == 'List-Unsubscribe=One-Click'
    assert post.call_args.kwargs['allow_redirects'] is False


def test_resend_rejection_does_not_expose_secret_response(monkeypatch):
    response = MagicMock(status_code=403, text='secret-link synthetic-key')
    monkeypatch.setattr(email_service.requests, 'post', lambda *a, **k: response)
    with pytest.raises(ValueError, match='HTTP 403') as error:
        service()._send('user@example.com', EmailContent('Verify', 'html', 'text'))
    assert 'secret' not in str(error.value)


def test_resend_missing_key_and_unknown_provider_fail_closed():
    assert not service(resend_api_key='').is_configured
    assert not service(email_provider='unknown').is_configured


def test_resend_missing_message_id_is_not_success(monkeypatch):
    response = MagicMock(status_code=200)
    response.json.return_value = {}
    monkeypatch.setattr(email_service.requests, 'post', lambda *a, **k: response)
    with pytest.raises(ValueError, match='message ID'):
        service()._send('user@example.com', EmailContent('Verify', 'html', 'text'))
