from typing import List, Dict, Tuple

from peewee import DoesNotExist

from .db import db
from .models import Product, Order, OrderItem
from .redis_client import load_cached_order, save_cached_order, is_processing, set_processing


TAX_RATES = {'QC': 0.15, 'ON': 0.13, 'AB': 0.05, 'BC': 0.12, 'NS': 0.14}


def shipping_price_for_weight(total_weight: int) -> int:
    if total_weight <= 500:
        return 500
    if total_weight < 2000:
        return 1000
    return 2500


def normalize_products_payload(data: dict):
    if isinstance(data.get('products'), list) and data['products']:
        return data['products']
    if isinstance(data.get('product'), dict):
        return [data['product']]
    return None


def validate_products(products_payload) -> Tuple[list, dict]:
    normalized = []
    if not isinstance(products_payload, list) or not products_payload:
        return [], {
            'errors': {
                'product': {
                    'code': 'missing-fields',
                    'name': "La creation d'une commande necessite au moins un produit",
                }
            }
        }

    for entry in products_payload:
        if not isinstance(entry, dict):
            return [], {
                'errors': {
                    'product': {
                        'code': 'missing-fields',
                        'name': "La creation d'une commande necessite au moins un produit",
                    }
                }
            }

        product_id = entry.get('id')
        quantity = entry.get('quantity')
        if product_id is None or quantity is None:
            return [], {
                'errors': {
                    'product': {
                        'code': 'missing-fields',
                        'name': "La creation d'une commande necessite au moins un produit",
                    }
                }
            }

        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            return [], {
                'errors': {
                    'product': {
                        'code': 'missing-fields',
                        'name': "La creation d'une commande necessite au moins un produit",
                    }
                }
            }

        if quantity < 1:
            return [], {
                'errors': {
                    'product': {
                        'code': 'missing-fields',
                        'name': "La creation d'une commande necessite au moins un produit",
                    }
                }
            }

        product = Product.get_or_none(Product.id == product_id)
        if product is None:
            return [], {
                'errors': {
                    'product': {
                        'code': 'missing-fields',
                        'name': "La creation d'une commande necessite au moins un produit",
                    }
                }
            }

        if not product.in_stock:
            return [], {
                'errors': {
                    'product': {
                        'code': 'out-of-inventory',
                        'name': "Le produit demande n'est pas en inventaire",
                    }
                }
            }

        normalized.append({'product': product, 'quantity': quantity})

    return normalized, None


def create_order_with_items(products_payload):
    products, error = validate_products(products_payload)
    if error:
        return None, error

    total_weight = sum(entry['product'].weight * entry['quantity'] for entry in products)
    total_price = sum(entry['product'].price * entry['quantity'] for entry in products)
    shipping_price = shipping_price_for_weight(total_weight)

    with db.atomic():
        order = Order.create(total_price=total_price, shipping_price=shipping_price, status='pending')
        for entry in products:
            OrderItem.create(order=order, product_id=entry['product'].id, quantity=entry['quantity'])
    return order, None


def set_customer_information(order: Order, payload: dict):
    order_obj = payload.get('order')
    if not isinstance(order_obj, dict):
        return {
            'errors': {
                'order': {
                    'code': 'missing-fields',
                    'name': 'Il manque un ou plusieurs champs qui sont obligatoires',
                }
            }
        }

    shipping = order_obj.get('shipping_information')
    email = order_obj.get('email')
    required_fields = ['country', 'address', 'postal_code', 'city', 'province']

    if not email or not isinstance(shipping, dict):
        return {
            'errors': {
                'order': {
                    'code': 'missing-fields',
                    'name': 'Il manque un ou plusieurs champs qui sont obligatoires',
                }
            }
        }

    for field in required_fields:
        if not shipping.get(field):
            return {
                'errors': {
                    'order': {
                        'code': 'missing-fields',
                        'name': 'Il manque un ou plusieurs champs qui sont obligatoires',
                    }
                }
            }

    province = shipping['province'].upper()
    order.email = email
    order.shipping_country = shipping['country']
    order.shipping_address = shipping['address']
    order.shipping_postal_code = shipping['postal_code']
    order.shipping_city = shipping['city']
    order.shipping_province = province
    order.save()
    return None


def build_order_response(order: Order) -> dict:
    shipping_information = {}
    if order.shipping_country:
        shipping_information = {
            'country': order.shipping_country,
            'address': order.shipping_address,
            'postal_code': order.shipping_postal_code,
            'city': order.shipping_city,
            'province': order.shipping_province,
        }

    credit_card = {}
    if order.cc_first_digits and order.cc_last_digits:
        credit_card = {
            'name': order.cc_name,
            'first_digits': order.cc_first_digits,
            'last_digits': order.cc_last_digits,
            'expiration_year': order.cc_exp_year,
            'expiration_month': order.cc_exp_month,
        }

    transaction = {}
    if order.tx_id or order.tx_success is not None or order.tx_error_code:
        transaction = {
            'id': order.tx_id,
            'success': bool(order.tx_success) if order.tx_success is not None else False,
            'error': {},
            'amount_charged': order.amount_charged,
        }
        if order.tx_error_code or order.tx_error_name:
            transaction['error'] = {
                'code': order.tx_error_code,
                'name': order.tx_error_name,
            }

    products = [
        {'id': item.product_id, 'quantity': item.quantity}
        for item in order.items.order_by(OrderItem.id)
    ]

    return {
        'order': {
            'id': order.id,
            'total_price': order.total_price,
            'email': order.email,
            'credit_card': credit_card,
            'shipping_information': shipping_information,
            'paid': order.paid,
            'transaction': transaction,
            'products': products,
            'shipping_price': order.shipping_price,
        }
    }


def get_order_payload(order_id: int):
    cached = load_cached_order(order_id)
    if cached is not None:
        return 'cached', cached

    if is_processing(order_id):
        return 'processing', None

    order = Order.get_or_none(Order.id == order_id)
    if order is None:
        return 'missing', None

    if order.status == 'processing':
        return 'processing', None

    payload = build_order_response(order)
    return 'ok', payload


def cache_paid_order_if_needed(order: Order):
    if order.paid:
        save_cached_order(order.id, build_order_response(order))


def start_processing(order: Order):
    order.status = 'processing'
    order.save()
    set_processing(order.id, True)


def finish_processing(order: Order):
    if order.status == 'processing':
        order.status = 'pending'
        order.save()
    set_processing(order.id, False)
