from flask import Blueprint, jsonify, request, url_for
from peewee import OperationalError

from ..db import db
from ..models import Product, Order
from ..order_logic import (
    normalize_products_payload,
    create_order_with_items,
    set_customer_information,
    build_order_response,
    get_order_payload,
    start_processing,
)
from ..redis_client import get_queue, is_processing
from ..tasks import process_payment

api_bp = Blueprint('api', __name__)


@api_bp.get('/api')
def index():
    return {"name": "api8inf349", "status": "ok"}


@api_bp.get('/products')
def get_products():
    products = [
        {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'weight': product.weight,
            'in_stock': product.in_stock,
            'image': product.image,
        }
        for product in Product.select().order_by(Product.id)
    ]
    return jsonify({'products': products}), 200


@api_bp.route('/order', methods=['POST'])
def create_order():
    data = request.get_json(silent=True) or {}
    products_payload = normalize_products_payload(data)
    if products_payload is None:
        return jsonify({
            'errors': {
                'product': {
                    'code': 'missing-fields',
                    'name': "La creation d'une commande necessite au moins un produit",
                }
            }
        }), 422

    order, error = create_order_with_items(products_payload)
    if error:
        return jsonify(error), 422

    location = url_for('api.get_order', order_id=order.id)
    return ('', 302, {'Location': location})


@api_bp.route('/order/<int:order_id>', methods=['GET'])
def get_order(order_id: int):
    try:
        state, payload = get_order_payload(order_id)
    except OperationalError:
        # Si Postgres est down mais la commande n'était pas dans Redis.
        return jsonify({'error': 'database-unavailable'}), 503

    if state == 'cached':
        return jsonify(payload), 200
    if state == 'processing':
        return ('', 202)
    if state == 'missing':
        return jsonify({'error': 'not-found'}), 404
    return jsonify(payload), 200


@api_bp.route('/order/<int:order_id>', methods=['PUT'])
def update_order(order_id: int):
    order = Order.get_or_none(Order.id == order_id)
    if order is None:
        return jsonify({'error': 'not-found'}), 404

    data = request.get_json(silent=True) or {}

    if 'order' in data and 'credit_card' in data:
        return jsonify({
            'errors': {
                'order': {
                    'code': 'missing-fields',
                    'name': 'Il manque un ou plusieurs champs qui sont obligatoires',
                }
            }
        }), 422

    if order.status == 'processing' or is_processing(order.id):
        return ('', 409)

    if 'order' in data:
        if order.paid:
            return jsonify({
                'errors': {
                    'order': {
                        'code': 'already-paid',
                        'name': 'La commande a deja ete payee.',
                    }
                }
            }), 422

        error = set_customer_information(order, data)
        if error:
            return jsonify(error), 422
        return jsonify(build_order_response(order)), 200

    if 'credit_card' in data:
        if order.paid:
            return jsonify({
                'errors': {
                    'order': {
                        'code': 'already-paid',
                        'name': 'La commande a deja ete payee.',
                    }
                }
            }), 422

        if not order.email or not order.shipping_country:
            return jsonify({
                'errors': {
                    'order': {
                        'code': 'missing-fields',
                        'name': "Les informations du client sont nécessaire avant d'appliquer une carte de credit",
                    }
                }
            }), 422

        credit_card = data.get('credit_card')
        if not isinstance(credit_card, dict):
            return jsonify({
                'errors': {
                    'credit_card': {
                        'code': 'missing-fields',
                        'name': 'La carte de credit est obligatoire',
                    }
                }
            }), 422

        start_processing(order)
        get_queue().enqueue(process_payment, order.id, credit_card)
        return ('', 202)

    return jsonify({
        'errors': {
            'order': {
                'code': 'missing-fields',
                'name': 'Il manque un ou plusieurs champs qui sont obligatoires',
            }
        }
    }), 422
