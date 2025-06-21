from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import mysql.connector

app = FastAPI()

# Database Connection
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="grocery",
        charset="utf8"
    )

# --- Pydantic Models ---

class Product(BaseModel):
    name: str
    category_id: int
    brand: str
    price: float
    unit: str
    stock_qty: int
    description: str
    image_url: Optional[str] = None

class CartItem(BaseModel):
    p_id: int
    quantity: int

class OrderRequest(BaseModel):
    user_id: int
    items: List[CartItem]

class InventoryUpdate(BaseModel):
    p_id: int
    quantity_change: int
    note: str

class RestockItem(BaseModel):
    p_id: int
    quantity: int
    unit_cost: float

class RestockOrder(BaseModel):
    supplier_id: int
    items: List[RestockItem]

# --- API Endpoints ---

@app.get("/products")
def view_products_by_category():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.p_id, p.name, c.name, p.brand, p.price, p.unit, p.description, p.stock_qty, p.image_url
        FROM Product p
        JOIN Categories c ON p.category_id = c.category_id
    ''')
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

@app.get("/product/search")
def search_product(name: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Product WHERE name LIKE %s", (f"%{name}%",))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

@app.get("/stock/{p_id}")
def check_stock(p_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT stock_qty FROM Inventory WHERE p_id = %s", (p_id,))
    stock = cursor.fetchone()
    cursor.close()
    conn.close()
    if stock:
        return {"stock_qty": stock[0]}
    raise HTTPException(status_code=404, detail="Product not found")

@app.post("/order")
def place_order(order: OrderRequest):
    conn = get_db()
    cursor = conn.cursor()
    total = 0

    for item in order.items:
        cursor.execute("SELECT stock_qty FROM inventory WHERE p_id = %s", (item.p_id,))
        stock = cursor.fetchone()
        if not stock or stock[0] < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for product {item.p_id}")

    for item in order.items:
        cursor.execute("UPDATE inventory SET stock_qty = stock_qty - %s WHERE p_id = %s", (item.quantity, item.p_id))
        cursor.execute("SELECT price FROM product WHERE p_id = %s", (item.p_id,))
        price = cursor.fetchone()[0]
        total += price * item.quantity

        cursor.execute('''
            INSERT INTO inventory_log (p_id, quantity, description, datetime)
            VALUES (%s, %s, %s, %s)
        ''', (item.p_id, -item.quantity, 'Customer purchase', datetime.now()))

    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Order placed", "total": total}

@app.post("/product")
def add_product(product: Product):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Product (name, category_id, brand, price, unit, stock_qty, description, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (product.name, product.category_id, product.brand, product.price,
          product.unit, product.stock_qty, product.description, product.image_url))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Product added"}

@app.post("/inventory/update")
def update_inventory(update: InventoryUpdate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Inventory SET stock_qty = stock_qty + %s WHERE p_id = %s", (update.quantity_change, update.p_id))
    cursor.execute('''
        INSERT INTO Inventory_Log (p_id, quantity, description, datetime)
        VALUES (%s, %s, %s, %s)
    ''', (update.p_id, update.quantity_change, update.note, datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "Inventory updated"}

@app.post("/restock")
def create_restock_order(order: RestockOrder):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Restock_Orders (supplier_id, order_date, status)
        VALUES (%s, %s, 'Pending')
    ''', (order.supplier_id, datetime.now().date()))
    restock_id = cursor.lastrowid

    for item in order.items:
        cursor.execute('''
            INSERT INTO Restock_Items (restock_id, p_id, quantity, unit_cost)
            VALUES (%s, %s, %s, %s)
        ''', (restock_id, item.p_id, item.quantity, item.unit_cost))

    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Restock order #{restock_id} created"}

@app.get("/inventory/log")
def view_inventory_log(p_id: Optional[int] = None):
    conn = get_db()
    cursor = conn.cursor()
    if p_id is not None:
        cursor.execute("SELECT * FROM Inventory_Log WHERE p_id = %s ORDER BY datetime DESC", (p_id,))
    else:
        cursor.execute("SELECT * FROM Inventory_Log ORDER BY datetime DESC")
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return logs
