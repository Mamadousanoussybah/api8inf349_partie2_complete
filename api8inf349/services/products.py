import requests

PRODUCTS_URL = 'http://dimensweb.uqac.ca/~jgnault/shops/products/'


def fetch_products() -> dict:
    response = requests.get(PRODUCTS_URL, timeout=20)
    response.raise_for_status()
    return response.json()
