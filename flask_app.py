import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from sqlalchemy import text
#import os, json

from flask import request, redirect, url_for, flash , session

app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecret123"  # use a strong random key in production


# Use DATABASE_URL from Render/GitHub → force driver + SSL
url = os.environ.get("DATABASE_URL","")
if url.startswith("postgres://"):
    url = url.replace("postgres://","postgresql+psycopg2://",1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://","postgresql+psycopg2://",1)
if "sslmode=" not in url: url += ("&" if "?" in url else "?")+"sslmode=require"
app.config["SQLALCHEMY_DATABASE_URI"] = url


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Example model
#class User(db.Model):
    #id = db.Column(db.Integer, primary_key=True)
    #name = db.Column(db.String(100), nullable=False)

#@app.route("/")
@app.route("/", endpoint="index")
def home():
    return render_template("index.html")

#electroinc apps
@app.route("/electronic")
def electronic():
    return render_template("electronic.html")

#gemsone apps
@app.route('/gemstone')
def gemstone(): 
    return render_template('gemstone.html')

#nanize apps
@app.route('/nanize')
def nanize():
    return render_template('nanize.html')

#Gemstone informational apps
@app.route('/info_index')
def info_index():
    return render_template('business_Gem/index.html')

#Load products routes
def load_products():
    p = os.path.join(app.root_path, 'static', 'product.json')  # matches your repo
    return json.load(open(p)) if os.path.exists(p) else []

    
#Gemstone infomation apps products route
@app.route('/products')
def list_products():
    return render_template('business_Gem/products.html', products=load_products())

#product page products add to cart route
#@app.route('/cart/add/<product_id>', methods=['GET','POST'])
#def add_to_cart(product_id):
    # TODO: add to session/db cart
    #return redirect(url_for('list_products'))

#register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_type = request.form.get('userType')
        if user_type == 'seller':
            session['user'] = {
                'role': 'seller',
                'username': request.form.get('seller_username'),
                'shop_name': request.form.get('seller_fullname'),
                'location': request.form.get('location')
            }
        else:
            session['user'] = {
                'role': 'buyer',
                'username': request.form.get('buyer_username')
            }
        return redirect(url_for('dashboard'))
    return render_template('business_Gem/register.html')



@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username','').strip()
        p = request.form.get('password','').strip()
        if u == 'admin' and p == 'admin123':
            session['user'] = {'username': u}
            session['role']  = 'user'   # keep simple
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('business_Gem/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template('business_Gem/dashboard.html')
    
#suppliers route 
@app.route('/suppliers')
def supplier():
    return render_template('business_Gem/suppliers.html')
    

# total, cart , add & remove item routes 
def get_product_by_id(pid):
    for p in load_products():
        if str(p.get("id")) == str(pid):
            return p
    return None

@app.route('/cart')
def view_cart():
    ids = session.get('cart', [])
    cart_items = []
    for pid in ids:
        p = get_product_by_id(pid)
        if p:
            price = float(str(p.get('price', 0)).replace('$','').replace(',',''))
            cart_items.append((pid, p.get('name',''), p.get('description',''), price, p.get('image','')))

    total = sum(i[3] for i in cart_items)
    return render_template('business_Gem/cart.html', cart_items=cart_items, total=total)

@app.route('/add-to-cart/<product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', [])
    cart.append(product_id)
    session['cart'] = cart
    return redirect(url_for('view_cart'))

@app.route('/remove-from-cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    if product_id in cart:
        cart.remove(product_id)
    session['cart'] = cart
    return redirect(url_for('view_cart'))

#check out route
@app.route('/checkout', methods=['POST'])
def checkout():
    # Read shipping form
    name    = request.form.get('name', '')
    email   = request.form.get('email', '')
    phone   = request.form.get('phone', '')
    address = request.form.get('address', '')

    # Here you could save the order to DB / send email, etc.
    order = {
        "items": session.get('cart', []),
        "name": name, "email": email, "phone": phone, "address": address
    }

    # Clear cart after “purchase”
    session['cart'] = []
    flash("Checkout complete. Thank you!")
    return redirect(url_for('view_cart'))


#Electronic information apps
@app.route('/elec_index')
def elec_index():
    return render_template('business_Electro/index.html')


# --- Electronic products page (DB-driven) ---
def _fetch_dim_products(limit=6):
    sql = """
      SELECT product_id, product_name, category, price, image_url, details
      FROM public.dim_products
      ORDER BY product_id
      LIMIT %s
    """
    with db.engine.connect() as conn:
        rows = conn.exec_driver_sql(sql, (limit,)).fetchall()
    return [dict(r._mapping) for r in rows]

@app.route('/elec_products')
def elec_products():
    rows = _fetch_dim_products(6)
    return render_template('business_Electro/products.html', db_products=rows)


# Electronic products page 
@app.post("/api/sql/run")
def api_sql_run():
    data = request.get_json(silent=True) or {}
    q = data.get("query") or "SELECT product_id, product_name, category, price FROM public.dim_products LIMIT 5"
    if not q.strip().lower().startswith("select"):
        return {"ok": False, "error": "SELECT only"}, 400
    try:
        with db.engine.connect() as c:
            rows = c.execute(text(q)).mappings().all()
        return {"ok": True, "rowCount": len(rows), "rows": rows}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500








if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
