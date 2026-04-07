from peewee import (
    Model,
    AutoField,
    IntegerField,
    CharField,
    TextField,
    BooleanField,
    ForeignKeyField,
)

from .db import db


class BaseModel(Model):
    class Meta:
        database = db


class Product(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    description = TextField(null=True)
    price = IntegerField()  # cents
    weight = IntegerField()  # grammes
    in_stock = BooleanField(default=False)
    image = CharField(null=True)


class Order(BaseModel):
    id = AutoField()

    email = CharField(null=True)
    shipping_country = CharField(null=True)
    shipping_address = CharField(null=True)
    shipping_postal_code = CharField(null=True)
    shipping_city = CharField(null=True)
    shipping_province = CharField(null=True)

    shipping_price = IntegerField(default=0)
    total_price = IntegerField(default=0)

    paid = BooleanField(default=False)
    status = CharField(default='pending')  # pending / processing / paid / failed

    cc_name = CharField(null=True)
    cc_first_digits = CharField(null=True)
    cc_last_digits = CharField(null=True)
    cc_exp_year = IntegerField(null=True)
    cc_exp_month = IntegerField(null=True)

    tx_id = CharField(null=True)
    tx_success = BooleanField(null=True)
    tx_error_code = CharField(null=True)
    tx_error_name = CharField(null=True)
    amount_charged = IntegerField(null=True)


class OrderItem(BaseModel):
    id = AutoField()
    order = ForeignKeyField(Order, backref='items', on_delete='CASCADE')
    product_id = IntegerField()
    quantity = IntegerField()
