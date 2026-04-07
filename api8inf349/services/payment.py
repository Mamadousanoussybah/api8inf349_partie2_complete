import requests

PAY_URLS = [
    'https://dimensweb.uqac.ca/~jgnault/shops/pay/',
    'http://dimensweb.uqac.ca/~jgnault/shops/pay/',
]


def pay_remote(credit_card: dict, amount_charged: int) -> dict:
    payload = {
        'credit_card': credit_card,
        'amount_charged': amount_charged,
    }

    last_error = None
    for url in PAY_URLS:
        try:
            response = requests.post(url, json=payload, timeout=20, allow_redirects=False)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get('Location')
                if location:
                    response = requests.post(location, json=payload, timeout=20, allow_redirects=False)

            try:
                data = response.json()
            except Exception:
                return {
                    'errors': {
                        'credit_card': {
                            'code': 'invalid-response',
                            'name': f'Reponse non-JSON du service de paiement (HTTP {response.status_code}).',
                        }
                    }
                }

            return data
        except requests.RequestException as exc:
            last_error = str(exc)

    return {
        'errors': {
            'credit_card': {
                'code': 'payment-unreachable',
                'name': f'Impossible de joindre le service de paiement: {last_error or "erreur inconnue"}',
            }
        }
    }
