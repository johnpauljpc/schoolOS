"""
finance/paystack.py

Paystack payment gateway integration for SchoolOS.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PaystackAPIError(Exception):
    """Raised when Paystack returns an error response."""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class PaystackAPI:
    """
    Thin wrapper around the Paystack REST API.

    Usage::

        api = PaystackAPI()
        result = api.initialize_transaction(
            email='student@school.edu',
            amount_kobo=50000,
            reference='INV-2024-0001',
            callback_url='https://school.edu/finance/paystack/callback/',
        )
        authorization_url = result['data']['authorization_url']
    """

    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = settings.PAYSTACK_BASE_URL.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }
        self.timeout = 30  # seconds

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Perform a GET request against the Paystack API."""
        url = f'{self.base_url}/{endpoint.lstrip("/")}'
        try:
            response = requests.get(url, headers=self.headers, params=params or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            body = {}
            try:
                body = exc.response.json()
            except Exception:
                pass
            logger.error('Paystack GET %s → HTTP %s: %s', url, exc.response.status_code, body)
            raise PaystackAPIError(
                body.get('message', str(exc)),
                status_code=exc.response.status_code,
                response=body,
            ) from exc
        except requests.exceptions.RequestException as exc:
            logger.error('Paystack GET %s → network error: %s', url, exc)
            raise PaystackAPIError(f'Network error: {exc}') from exc

    def _post(self, endpoint: str, payload: dict = None) -> dict:
        """Perform a POST request against the Paystack API."""
        url = f'{self.base_url}/{endpoint.lstrip("/")}'
        try:
            response = requests.post(url, headers=self.headers, json=payload or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            body = {}
            try:
                body = exc.response.json()
            except Exception:
                pass
            logger.error('Paystack POST %s → HTTP %s: %s', url, exc.response.status_code, body)
            raise PaystackAPIError(
                body.get('message', str(exc)),
                status_code=exc.response.status_code,
                response=body,
            ) from exc
        except requests.exceptions.RequestException as exc:
            logger.error('Paystack POST %s → network error: %s', url, exc)
            raise PaystackAPIError(f'Network error: {exc}') from exc

    # ──────────────────────────────────────────────────────────────────────────
    # Public methods
    # ──────────────────────────────────────────────────────────────────────────

    def initialize_transaction(
        self,
        email: str,
        amount_kobo: int,
        reference: str,
        callback_url: str,
        metadata: dict = None,
    ) -> dict:
        """
        Initialize a Paystack transaction.

        POST /transaction/initialize

        :param email: Customer email address.
        :param amount_kobo: Amount in kobo (Naira x 100).
        :param reference: Unique transaction reference.
        :param callback_url: URL Paystack redirects to after payment.
        :param metadata: Optional dict of extra data stored on the transaction.
        :returns: Dict with keys ``status``, ``message``, ``data`` where
                  ``data`` contains ``authorization_url``, ``access_code``,
                  and ``reference``.
        """
        payload = {
            'email': email,
            'amount': int(amount_kobo),
            'reference': reference,
            'callback_url': callback_url,
            'currency': 'NGN',
        }
        if metadata:
            payload['metadata'] = metadata

        result = self._post('/transaction/initialize', payload)
        logger.info('Paystack initialize_transaction: ref=%s status=%s', reference, result.get('status'))
        return result

    def verify_transaction(self, reference: str) -> dict:
        """
        Verify a Paystack transaction.

        GET /transaction/verify/{reference}

        :param reference: The transaction reference to verify.
        :returns: Full transaction response dict from Paystack.
        """
        result = self._get(f'/transaction/verify/{reference}')
        logger.info('Paystack verify_transaction: ref=%s gateway_status=%s',
                    reference, result.get('data', {}).get('status'))
        return result

    def list_transactions(self, **params) -> dict:
        """
        List Paystack transactions.

        GET /transaction

        Accepted kwargs: ``perPage``, ``page``, ``from``, ``to``, ``status``,
        ``customer``, ``currency``, ``amount``, ``settled``, ``settlement``,
        ``payment_page``.

        :returns: Paystack list response with ``data`` list and ``meta`` dict.
        """
        result = self._get('/transaction', params=params)
        logger.debug('Paystack list_transactions: retrieved %d records', len(result.get('data', [])))
        return result
