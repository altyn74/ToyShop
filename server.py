from flask import Flask, jsonify, send_from_directory, request
import json
import os
import time
import uuid

app = Flask(__name__)

DATA_FILE = "/var/data/products.json"
PENDING_FILE = "/var/data/pending.json"
SELLERS_FILE = "/var/data/sellers.json"
SECTIONS_FILE = "/var/data/sections.json"
PHOTOS_DIR = "/var/data/photos"
BASE_URL = "https://toyshop-c632.onrender.com"
MAX_PRODUCTS = 100

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


@app.route("/register_seller", methods=["POST"])
def register_seller():
    seller_token = str(uuid.uuid4())

    sellers = load_json_file(SELLERS_FILE)

    seller = {
        "seller_token": seller_token,
        "section_id": "",
        "section_name": "",
        "status": "unassigned"
    }

    sellers.append(seller)
    save_json_file(SELLERS_FILE, sellers)

    return jsonify({
        "status": "ok",
        "seller_token": seller_token,
        "section_id": "",
        "section_name": "",
        "seller_status": "unassigned"
    })
    
@app.route("/admin/unassigned_sellers")
def admin_unassigned_sellers():
    sellers = load_json_file(SELLERS_FILE)

    result = []

    for seller in sellers:
        if seller.get("status") == "unassigned":
            result.append(seller)

    return jsonify({
        "status": "ok",
        "count": len(result),
        "sellers": result
    })

@app.route("/admin/pending_all")
def admin_pending_all():
    pending = load_json_file(PENDING_FILE)

    return jsonify({
        "status": "ok",
        "count": len(pending),
        "items": pending
    })

@app.route("/admin/assign_section", methods=["POST"])
def admin_assign_section():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "status": "error",
            "message": "Нет данных"
        }), 400

    seller_token = str(data.get("seller_token", "")).strip()
    section_id = str(data.get("section_id", "")).strip()
    section_name = str(data.get("section_name", "")).strip()

    if not seller_token or not section_id or not section_name:
        return jsonify({
            "status": "error",
            "message": "Не хватает данных"
        }), 400

    sellers = load_json_file(SELLERS_FILE)

    found = False

    for seller in sellers:
        if seller.get("seller_token") == seller_token:
            seller["section_id"] = section_id
            seller["section_name"] = section_name
            seller["status"] = "assigned"
            found = True
            break

    if not found:
        return jsonify({
            "status": "error",
            "message": "Продавец не найден"
        }), 404

    save_json_file(SELLERS_FILE, sellers)

    return jsonify({
        "status": "ok",
        "message": "Раздел назначен",
        "seller_token": seller_token,
        "section_id": section_id,
        "section_name": section_name
    })

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
            "product_status": "",
            "seller_token": "",
            "section_id": "",
            "section_name": ""
        }

    photo_name = product.get("photo", "").replace("\\", "/").split("/")[-1] if product.get("photo") else ""
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
        "product_status": product.get("status", ""),
        "seller_token": product.get("seller_token", ""),
        "section_id": product.get("section_id", ""),
        "section_name": product.get("section_name", "")
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

    product = pending.pop(0)
    product["status"] = "Продаётся"

    # Новый товар всегда первым
    products.insert(0, product)

    # Оставляем только 100 самых новых
    products = products[:MAX_PRODUCTS]

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
    print("SUBMIT DATA:", data)
    if not data:
        return jsonify({
            "status": "error",
            "message": "Нет данных"
        }), 400

    seller_token = str(data.get("seller_token", "")).strip()

    section_id = ""
    section_name = ""

    if seller_token:
        sellers = load_json_file(SELLERS_FILE)

        for seller in sellers:
            if seller.get("seller_token") == seller_token:
                section_id = str(seller.get("section_id", "")).strip()
                section_name = str(seller.get("section_name", "")).strip()
                break

    product = {
        "name": str(data.get("name", "")).strip(),
        "price": str(data.get("price", "")).strip(),
        "description": str(data.get("description", "")).strip(),
        "seller": str(data.get("seller", "")).strip(),
        "photo": str(data.get("photo", "")).strip(),

        "seller_token": seller_token,
        "section_id": section_id,
        "section_name": section_name,

        "status": "На модерации"
    }

    if not product["name"] or not product["price"]:
        return jsonify({
            "status": "error",
            "message": "Нужно название и цена"
        }), 400

    pending = load_json_file(PENDING_FILE)
    pending.append(product)
    save_json_file(PENDING_FILE, pending)

    return jsonify({
        "status": "ok",
        "message": "Товар отправлен на модерацию",
        "section_id": section_id,
        "section_name": section_name
    })

@app.route("/admin/section/<section_id>")
def admin_section(section_id):
    products = load_json_file(DATA_FILE)
    pending = load_json_file(PENDING_FILE)

    approved_items = []
    pending_items = []

    for product in products:
        if str(product.get("section_id", "")) == str(section_id):
            approved_items.append(product)

    for product in pending:
        if str(product.get("section_id", "")) == str(section_id):
            pending_items.append(product)

    return jsonify({
        "status": "ok",
        "section_id": str(section_id),
        "approved_count": len(approved_items),
        "pending_count": len(pending_items),
        "approved": approved_items,
        "pending": pending_items
    })

@app.route("/photos/<path:filename>")
def photos(filename):
    return send_from_directory(PHOTOS_DIR, filename)


if __name__ == "__main__":
    app.json.ensure_ascii = False
    app.run(host="0.0.0.0", port=5000)
