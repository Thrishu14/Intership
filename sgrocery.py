import streamlit as st
import requests
from datetime import date
from PIL import Image
import os

API_URL = "http://localhost:8001"

# --- Set Page Config ---
st.set_page_config(page_title="\U0001F6D2 Grocery Store", layout="wide")
st.markdown("""
    <style>
        body {
            background: linear-gradient(to right, #fceabb, #f8b500);
        }
        .stApp {
            background: linear-gradient(to right, #fceabb, #f8b500);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>\U0001F6D2 Grocery Purchase & Checkout System</h1>", unsafe_allow_html=True)

# --- Helper Functions ---

def list_products():
    st.subheader("\U0001F9FE Product List")

    col1, col2, col3 = st.columns(3)
    category_filter = col1.text_input("Filter by Category")
    brand_filter = col2.text_input("Filter by Brand")
    sort_option = col3.selectbox("Sort by Price", ["None", "Low to High", "High to Low"])

    response = requests.get(f"{API_URL}/products")
    if response.ok:
        products = response.json()

        if category_filter:
            products = [p for p in products if category_filter.lower() in p[2].lower()]
        if brand_filter:
            products = [p for p in products if brand_filter.lower() in p[3].lower()]

        if sort_option == "Low to High":
            products.sort(key=lambda x: x[4])
        elif sort_option == "High to Low":
            products.sort(key=lambda x: x[4], reverse=True)

        st.markdown(f"### Total Products: {len(products)}")

        for p in products:
            stock = p[7] if len(p) > 7 else None
            image_path = p[8] if len(p) > 8 and p[8] else ""
            if os.path.exists(image_path):
                try:
                    img = Image.open(image_path)
                    image_url = img
                except:
                    image_url = "https://via.placeholder.com/120"
            else:
                image_url = "https://via.placeholder.com/120"

            if stock is not None:
                if stock <= 5:
                    stock_status = f"<span style='color:red;'>Only {stock} left!</span>"
                elif stock <= 15:
                    stock_status = f"<span style='color:orange;'>Limited stock ({stock})</span>"
                else:
                    stock_status = f"<span style='color:green;'>In stock ({stock})</span>"
            else:
                stock_status = ""

            with st.container():
                cols = st.columns([1, 3])
                with cols[0]:
                    if isinstance(image_url, str):
                        st.image(image_url, width=120)
                    else:
                        st.image(image_url, width=120)
                with cols[1]:
                    st.markdown(f"""
                        <b style='font-size: 18px;'>{p[1]}</b><br>
                        Category: {p[2]} | Brand: {p[3]}<br>
                        <span style='color: green;'>₹{p[4]}</span> per {p[5]}<br>
                        <i>Description: {p[6]}</i><br>
                        {stock_status}
                    """, unsafe_allow_html=True)
    else:
        st.error("❌ Could not fetch products.")

def search_product():
    st.subheader("🔍 Search Product")
    name = st.text_input("Enter product name")
    if st.button("Search"):
        res = requests.get(f"{API_URL}/product/search", params={"name": name})
        if res.ok:
            for p in res.json():
                st.success(f"{p[1]} | Brand: {p[3]} | ₹{p[4]} | Stock: {p[6]}")
        else:
            st.error("Search failed.")

def check_stock():
    st.subheader("📦 Check Stock")
    p_id = st.number_input("Enter Product ID", step=1)
    if st.button("Check"):
        res = requests.get(f"{API_URL}/stock/{p_id}")
        if res.ok:
            st.success(f"✅ Available Quantity: {res.json()['stock_qty']}")
        else:
            st.error(res.json().get("detail", "Error"))

def add_product():
    st.subheader("➕ Add New Product")
    col1, col2 = st.columns(2)

    name = col1.text_input("Product Name")
    brand = col2.text_input("Brand")

    category_id = col1.number_input("Category ID", step=1)
    price = col2.number_input("Price", format="%.2f")

    unit = col1.text_input("Unit (e.g., kg, L, pcs)")
    stock_qty = col2.number_input("Initial Stock", step=1)

    description = st.text_area("Description")
    image_url = st.text_input("Image URL")

    if st.button("Add Product"):
        data = {
            "name": name, "category_id": category_id, "brand": brand,
            "price": price, "unit": unit, "stock_qty": stock_qty,
            "description": description, "image_url": image_url
        }
        res = requests.post(f"{API_URL}/product", json=data)
        if res.ok:
            st.balloons()
            st.success("🎉 Product added successfully!")
        else:
            st.error("Failed to add product")

def update_inventory():
    st.subheader("🧮 Update Inventory")
    p_id = st.number_input("Product ID", step=1)
    quantity = st.number_input("Quantity Change (+/-)", step=1)
    note = st.text_input("Note (e.g., 'Manual update')")
    if st.button("Update Inventory"):
        res = requests.post(f"{API_URL}/inventory/update", json={
            "p_id": p_id, "quantity_change": quantity, "note": note
        })
        if res.ok:
            st.success("✅ Inventory updated")
        else:
            st.error("Update failed")

def restock_order():
    st.subheader("📦 Create Restock Order")
    supplier_id = st.number_input("Supplier ID", step=1)
    with st.form("restock_form"):
        item_count = st.number_input("Number of items", min_value=1, step=1)
        items = []
        for i in range(item_count):
            st.markdown(f"**📦 Item {i+1}**")
            cols = st.columns(3)
            p_id = cols[0].number_input(f"Product ID #{i+1}", step=1, key=f"rp{i}")
            qty = cols[1].number_input(f"Quantity #{i+1}", step=1, key=f"rq{i}")
            unit_cost = cols[2].number_input(f"Unit Cost ₹#{i+1}", format="%.2f", key=f"rc{i}")
            items.append({"p_id": p_id, "quantity": qty, "unit_cost": unit_cost})

        submitted = st.form_submit_button("✅ Create Restock Order")
        if submitted:
            res = requests.post(f"{API_URL}/restock", json={
                "supplier_id": supplier_id,
                "items": items
            })
            if res.ok:
                st.success(res.json()["message"])
            else:
                st.error("Failed to create restock order")

def inventory_log():
    st.subheader("📜 Inventory Log")
    with st.expander("🔎 Filter Options"):
        p_id = st.text_input("Filter by Product ID")
        start_date = st.date_input("Start Date", value=date(2024, 1, 1))
        end_date = st.date_input("End Date", value=date.today())

    params = {"p_id": p_id} if p_id else {}
    res = requests.get(f"{API_URL}/inventory/log", params=params)
    if res.ok:
        logs = res.json()
        for log in logs:
            st.info(f"🕒 {log[4]} | Product ID: {log[1]} | Qty: {log[2]} | Note: {log[3]}")
    else:
        st.error("❌ Could not retrieve logs")

# --- Main Tabs ---
tabs = st.tabs([
    "📋 View Products", "🔍 Search Product", "📦 Check Stock",
    "🛍️ Place Order", "➕ Add Product", "🧮 Update Inventory",
    "📦 Restock Order", "📜 Inventory Log"
])

with tabs[0]:
    list_products()
with tabs[1]:
    search_product()
with tabs[2]:
    check_stock()
with tabs[3]:
    st.subheader("🛍️ Place Order")

    products_resp = requests.get(f"{API_URL}/products")
    if products_resp.ok:
        products = products_resp.json()
        product_options = {f"{p[1]} (ID: {p[0]})": p[0] for p in products}

        item_count = st.number_input("Number of items", min_value=1, step=1)

        selected_products = []
        for i in range(item_count):
            st.markdown(f"**Item {i + 1}**")
            selected_product = st.selectbox(
                f"Select Product #{i+1}", list(product_options.keys()), key=f"prod_{i}"
            )
            quantity = st.number_input(f"Quantity #{i+1}", min_value=1, step=1, key=f"qty_{i}")
            selected_products.append({
                "product_id": product_options[selected_product],
                "quantity": quantity
            })

        if st.button("Place Orders"):
            order_payload = {
                "user_id": 1,
                "items": [
                    {
                        "p_id": int(item["product_id"]),
                        "quantity": int(item["quantity"])
                    }
                    for item in selected_products
                ]
            }

            try:
                res = requests.post(f"{API_URL}/order", json=order_payload)
                if res.ok:
                    data = res.json()
                    st.success(f"✅ {data['message']} | Total: ₹{data['total']}")
                else:
                    st.error(f"❌ Failed to place order: {res.json().get('detail')}")
            except Exception as e:
                st.error(f"❌ Request failed: {e}")
    else:
        st.error("❌ Failed to fetch product list.")

with tabs[4]:
    add_product()
with tabs[5]:
    update_inventory()
with tabs[6]:
    restock_order()
with tabs[7]:
    inventory_log()