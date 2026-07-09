import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from sqlalchemy import text
#import os, json
import time
import json

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


#Electronic information apps routes from here.

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
    app.logger.info("SQL.IN query=%s", q)

    if not q.strip().lower().startswith("select"):
        app.logger.warning("SQL.BLOCK non-select")
        return {"ok": False, "error": "SELECT only"}, 400

    try:
        t0=time.perf_counter()
        with db.engine.connect() as c:
            rows = c.execute(text(q)).mappings().all()
        rows = [dict(r) for r in rows]
        ms=int((time.perf_counter()-t0)*1000)
        return {"ok":True,"rowCount":len(rows),"duration_ms":ms,"rows":rows}
    except Exception as e:
        app.logger.exception("SQL.ERR"); return {"ok":False,"error":str(e)},500



@app.post("/api/cart/add")
def api_cart_add():
    pid = (request.get_json(silent=True) or {}).get("product_id")
    if not pid: return {"ok": False, "error": "product_id required"}, 400
    cart = session.get("cart", [])
    cart.append(str(pid)); session["cart"] = cart
    return {"ok": True, "count": len(cart)}



#data modeling page routes
@app.route('/dataModel')
def dataModel():
    return render_template('dataModel.html')

#AI & LLM integration - llm_ai routes
@app.route('/llm_ai')
def llm_ai():
    return render_template('llm_ai.html')


#robotics routes
@app.route('/robot')
def robot():
    return render_template('Robits.html')

#system_circuit routes
@app.route('/system_circuit')
def system_circuit():
    return render_template('system_circuit.html')

#health routes
@app.route('/health')
def health():
    return render_template('health.html')

@app.route('/three')
def three():
    return render_template('three.html')

@app.route('/git_github')
def git_github():
    return render_template('git_github.html')

@app.route('/Luc8k')
def Luc8k():
    return render_template('Luc8k.html')

#@app.route('/calendar')
#def calendar():
    #return render_template('calendar.html')


@app.route('/meshes')
def meshes():
    return render_template('meshes.html')

#use Three.js products visualization demo page
@app.route('/design')
def design():
    return render_template('design.html')

#use 360 panoramic image visualization demo page
@app.route('/panoramic')
def panoramic():
    return render_template('panoramic.html')

# use Valentine html 
@app.route('/Valentine')
def Valentine(): 
    return render_template('Valentine.html')

#gallery html route 
@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

#ArcGis instance 
@app.route('/arcGis')
def arcGis():
    return render_template('arcGis.html') 
    

#GSOC_2026 

#GA4GH html 
@app.route('/ga4gh')
def ga4gh():
    return render_template('ga4gh.html')

#Wagtail html 
@app.route('/wagtail')
def wagtail():
    return render_template('wagtail.html')

#DBpedia html 
@app.route('/dbpedia')
def dbpedia():
    return render_template('dbpedia.html')


#Adding here app.py full with all routs and def with all data for apticare apps 

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import os
import json
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APTICARE_DATA_FILE = os.path.join(BASE_DIR, "static", "aptiCareData.json")
APTICARE_RESPONSES_FILE = os.path.join(BASE_DIR, "static", "aptiCareResponses.json")


def load_json_file(file_path, fallback_data):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return fallback_data


def get_aptiCare_data():
    fallback_data = {
        "imgData": [
            {
                "id": "img1",
                "name": "For Patients",
                "title": "On-Demand Teleconsultation",
                "des": "On-demand teleconsultation provides an immediate, secure link between remote patients and specialized physicians.",
                "image": "https://anthem-blog-media.s3.us-west-1.amazonaws.com/wp-content/uploads/2020/11/10202642/BLG-ALL-0095-20-Blog-Article-Images-for-2020-Oct_Telehealth-2.gif"
            },
            {
                "id": "img2",
                "name": "For Doctors",
                "title": "Next-Gen Digital Chambers",
                "des": "The next-generation digital medical chamber is a compact, autonomous healthcare hub that uses AI and biometric sensors.",
                "image": "https://optimoz.com/wp-content/uploads/2024/12/Harnessing-Artificial-Intelligence-to-Revolutionize-Healthcare.gif"
            },
            {
                "id": "img3",
                "name": "For Researchers",
                "title": "Anonymized Clinical Cohorts",
                "des": "Anonymized clinical cohorts aggregate de-identified patient data to enable large-scale medical research without compromising privacy.",
                "image": "https://i.makeagif.com/media/6-30-2020/WxMaqz.gif"
            },
            {
                "id": "img4",
                "name": "For Institutions",
                "title": "Decentralized Hospital Networks",
                "des": "Decentralized hospital networks distribute authority and data across multiple independent nodes for faster local decisions.",
                "image": "https://i.giphy.com/l1J9CXWtcXqkfRN60.gif"
            },
            {
                "id": "img5",
                "name": "Ancient Care",
                "title": "Ancient Medical Techniques",
                "des": "Ancient medical techniques use time-tested, nature-based practices like herbalism and acupuncture to treat ailments.",
                "image": "https://cdn.egyptatours.com/wp-content/uploads/2024/12/Ancient-Egyptian-Medicine-Powerful-Secrets-of-Healing-and-Science-Featured-Image-EgyptaTours.webp"
            }
        ],
        "hostData": {
            "contributors": [
                {
                    "name": "AptiCare Core Team",
                    "role": "Contributor",
                    "study": "UI and portal development",
                    "updated": "07:30 PM, 09 July, 2026 CDT"
                }
            ],
            "doctors": [
                {
                    "name": "Dr. Sarah Mitchell",
                    "role": "Cardiologist",
                    "affiliation": "City General Hospital, Texas",
                    "updated": "07:30 PM, 09 July, 2026 CDT"
                }
            ],
            "research": [
                {
                    "name": "AptiCare Research Lab",
                    "role": "Research Center",
                    "affiliation": "Biomedical Innovation Group",
                    "updated": "07:30 PM, 09 July, 2026 CDT"
                }
            ]
        }
    }
    return load_json_file(APTICARE_DATA_FILE, fallback_data)


def get_aptiCare_responses():
    fallback_data = {
        "patient_intake": "Thanks. Your intake was received successfully.",
        "patient_followup": "Doctor reviewed your submission. We will contact you soon.",
        "groq": "Demo reply from local static file.",
        "gene_llm": "Gene panel demo reply from local static file."
    }
    return load_json_file(APTICARE_RESPONSES_FILE, fallback_data)


def top_five(items):
    return (items or [])[:5]


@app.route('/hosting/<section_id>')
def hosting(section_id):
    section_id = (section_id or '').strip().lower()

    @stream_with_context
    def event_stream():
        for _ in range(5):
            apticare_data = get_aptiCare_data()
            host_data = apticare_data.get("hostData", {})
            sent_at = datetime.now().strftime("%I:%M %p, %d %B, %Y CDT")

            payload = {
                "section": section_id,
                "sent_at": sent_at,
                "items": top_five(host_data.get(section_id, []))
            }

            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(300)

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/aptiCare')
def aptiCare():
    llm_text = request.args.get('llm_response')
    apticare_data = get_aptiCare_data()
    return render_template(
        'aptiCare.html',
        title_name='AptiCares Home',
        imageData=apticare_data.get("imgData", []),
        llm_response=llm_text
    )


@app.route('/imgData')
def imgData():
    apticare_data = get_aptiCare_data()
    return jsonify(apticare_data.get("imgData", []))


@app.route('/patient-intake', methods=['POST'])
def patient_intake():
    responses = get_aptiCare_responses()
    reply_text = responses.get("patient_intake", "Thanks. Your intake was received successfully.")
    return jsonify({'ai_reply': reply_text})


@app.route('/patient-followup', methods=['POST'])
def patient_followup():
    responses = get_aptiCare_responses()
    req = request.get_json(force=True) or {}
    contact = req.get('contact') or {}
    email = (contact.get('email') or '').strip()
    phone = (contact.get('phone') or '').strip()

    base_reply = responses.get("patient_followup", "Doctor reviewed your submission. We will contact you soon.")
    if email or phone:
        base_reply = f"{base_reply} Contact: {email or phone}"

    return jsonify({'doctor_reply': base_reply})


@app.route('/groq', methods=['POST'])
def groq():
    responses = get_aptiCare_responses()
    reply_text = responses.get("groq", "Demo reply from local static file.")
    return jsonify({'reply': reply_text})


@app.route('/gene-llm', methods=['POST'])
def gene_llm():
    responses = get_aptiCare_responses()
    reply_text = responses.get("gene_llm", "Gene panel demo reply from local static file.")
    return jsonify({'reply': reply_text})




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
