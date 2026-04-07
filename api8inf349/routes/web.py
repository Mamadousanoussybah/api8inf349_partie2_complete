from flask import Blueprint, render_template

from ..models import Product

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def home():
    products = Product.select().order_by(Product.id)
    return render_template("index.html", products=products)


@web_bp.get("/ui")
def ui_index():
    products = Product.select().order_by(Product.id)
    return render_template("index.html", products=products)