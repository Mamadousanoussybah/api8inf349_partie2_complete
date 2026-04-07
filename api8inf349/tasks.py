from .db import db
from .models import Order
from .order_logic import build_order_response
from .redis_client import save_cached_order, set_processing
from .services.payment import pay_remote


def process_payment(order_id: int, credit_card: dict):
    db.connect(reuse_if_open=True)
    try:
        order = Order.get_by_id(order_id)
        amount_charged = int(order.total_price) + int(order.shipping_price)
        remote_resp = pay_remote(credit_card, amount_charged)

        if 'errors' in remote_resp:
            err = remote_resp['errors'].get('credit_card', {})
            order.tx_success = False
            order.tx_error_code = err.get('code')
            order.tx_error_name = err.get('name')
            order.amount_charged = amount_charged
            order.status = 'failed'
            order.paid = False
            order.save()
            return

        cc_out = remote_resp.get('credit_card', {})
        tx = remote_resp.get('transaction', {})

        order.cc_name = cc_out.get('name')
        order.cc_first_digits = cc_out.get('first_digits')
        order.cc_last_digits = cc_out.get('last_digits')
        order.cc_exp_year = cc_out.get('expiration_year')
        order.cc_exp_month = cc_out.get('expiration_month')

        order.tx_id = tx.get('id')
        order.tx_success = bool(tx.get('success'))
        order.tx_error_code = None
        order.tx_error_name = None
        order.amount_charged = tx.get('amount_charged', amount_charged)
        order.paid = bool(tx.get('success'))
        order.status = 'paid' if order.paid else 'failed'
        order.save()

        if order.paid:
            save_cached_order(order.id, build_order_response(order))
    finally:
        set_processing(order_id, False)
        db.close()
