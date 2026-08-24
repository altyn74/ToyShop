from flask import Flask, jsonify, send_from_directory, request
import json
import os
import time

app = Flask(__name__)

DATA_FILE = "products.json"
PENDING_FILE = "pending.json"
PHOTOS_DIR = "photos"
BASE_URL = "https://toyshop-c632.onrender.com"
MAX_PRODUCTS = 10

os.makedirs(PHOTOS_DIR, exist_ok=True)


def load_json_file(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def product_payload(product=None, index=0, count=0, status="ok", message=""):
    if not product:
        return {
            "status": status,
            "message": message,
            "index": 0,
            "count": count,
            "name": "",
            "price": "",
            "seller": "",
            "description": "",
            "photo": "",
            "photo_url": "",
            "product_status": ""
        }

    photo_name = os.path.basename(product.get("photo", "")) if product.get("photo") else ""
    photo_url = f"{BASE_URL}/photos/{photo_name}" if photo_name else ""
    return {
        "status": status,
        "message": message,
        "index": index,
        "count": count,
        "name": product.get("name", ""),
        "price": product.get("price", ""),
        "seller": product.get("seller", ""),
        "description": product.get("description", ""),
        "photo": photo_name,
        "photo_url": photo_url,
        "product_status": product.get("status", "")
    }


def pending_payload(message=""):
    pending = load_json_file(PENDING_FILE)
    if not pending:
        return product_payload(None, count=0, status="empty", message=message or "Нет товаров на модерации")
    return product_payload(pending[0], index=0, count=len(pending), status="ok", message=message)


@app.route("/")
def home():
    return "ToyShop server works!"


@app.route("/catalog")
def catalog_first():
    return catalog_item(0)


@app.route("/catalog/<int:index>")
def catalog_item(index):
    products = load_json_file(DATA_FILE)
    if not products:
        return jsonify(product_payload(None, count=0, status="empty", message="Каталог пуст"))
    if index < 0 or index >= len(products):
        return jsonify(product_payload(None, count=len(products), status="error", message="Товар не найден")), 404
    return jsonify(product_payload(products[index], index=index, count=len(products)))


@app.route("/pending/0")
def pending_first():
    return jsonify(pending_payload())


@app.route("/approve/0", methods=["POST"])
def approve_first():
    pending = load_json_file(PENDING_FILE)
    products = load_json_file(DATA_FILE)
    if not pending:
        return jsonify(pending_payload("Нет товаров для одобрения"))
    if len(products) >= MAX_PRODUCTS:
        return jsonify(product_payload(pending[0], count=len(pending), status="error", message="Каталог заполнен: максимум 10 товаров")), 409

    product = pending.pop(0)
    product["status"] = "Продаётся"
    products.append(product)
    save_json_file(DATA_FILE, products)
    save_json_file(PENDING_FILE, pending)
    return jsonify(pending_payload("Товар одобрен"))


@app.route("/reject/0", methods=["POST"])
def reject_first():
    pending = load_json_file(PENDING_FILE)
    if not pending:
        return jsonify(pending_payload("Нет товаров для отклонения"))
    pending.pop(0)
    save_json_file(PENDING_FILE, pending)
    return jsonify(pending_payload("Товар отклонён"))


@app.route("/upload_photo", methods=["POST"])
def upload_photo():
    data = request.get_data()
    if not data:
        return jsonify({"status": "error", "message": "Файл не получен"}), 400

    content_type = request.headers.get("Content-Type", "").lower()
    if "png" in content_type:
        extension = ".png"
    elif "webp" in content_type:
        extension = ".webp"
    elif "jpeg" in content_type or "jpg" in content_type:
        extension = ".jpg"
    else:
        extension = ".jpg"

    filename = f"phone_{int(time.time() * 1000)}{extension}"
    path = os.path.join(PHOTOS_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)

    return jsonify({
        "status": "ok",
        "photo": filename,
        "photo_url": f"{BASE_URL}/photos/{filename}"
    })


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Нет данных"}), 400

    product = {
        "name": str(data.get("name", "")).strip(),
        "price": str(data.get("price", "")).strip(),
        "description": str(data.get("description", "")).strip(),
        "seller": str(data.get("seller", "")).strip(),
        "photo": str(data.get("photo", "")).strip(),
        "status": "На модерации"
    }

    if not product["name"] or not product["price"]:
        return jsonify({"status": "error", "message": "Нужно название и цена"}), 400

    pending = load_json_file(PENDING_FILE)
    pending.append(product)
    save_json_file(PENDING_FILE, pending)
    return jsonify({"status": "ok", "message": "Товар отправлен на модерацию"})


@app.route("/photos/<path:filename>")
def photos(filename):
    return send_from_directory(PHOTOS_DIR, filename)


if __name__ == "__main__":
    app.json.ensure_ascii = False
    app.run(host="0.0.0.0", port=5000)
