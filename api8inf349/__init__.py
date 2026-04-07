from flask import Flask
from flask.cli import with_appcontext

from .db import db
from .models import Product, Order, OrderItem
from .routes.api import api_bp
from .routes.web import web_bp
from .services.products import fetch_products


def clean_text(value):
    if value is None:
        return None
    return str(value).replace("\x00", "")


def create_app():
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    register_commands(app)

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    return app


def register_commands(app):
    @app.cli.command("init-db")
    @with_appcontext
    def init_db_command():
        """Crée les tables et recharge les produits distants."""
        db.connect(reuse_if_open=True)
        db.create_tables([Product, Order, OrderItem])

        OrderItem.delete().execute()
        Order.delete().execute()
        Product.delete().execute()
        data = fetch_products()

        for item in data.get("products", []):
            cleaned = {
                "id": int(item["id"]),
                "name": clean_text(item.get("name") or ""),
                "description": clean_text(item.get("description")),
                "price": int(item.get("price", 0)),
                "weight": int(item.get("weight", 0)),
                "in_stock": bool(item.get("in_stock", False)),
                "image": clean_text(item.get("image")),
            }
            print("Import produit:", cleaned["id"], cleaned["name"])
            Product.create(**cleaned)

        db.close()
        print("Base de données initialisée et produits importés.")

    @app.cli.command("worker")
    @with_appcontext
    def worker_command():
      """Worker compatible Windows sans fork."""
      from rq import SimpleWorker
      from .redis_client import get_queue_redis_connection, get_queue_name

      redis_conn = get_queue_redis_connection()
      worker = SimpleWorker([get_queue_name()], connection=redis_conn)

      print("Worker RQ démarré (mode Windows)...")
      worker.work(burst=False)


app = create_app()