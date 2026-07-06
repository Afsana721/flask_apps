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
from flask import Flask, render_template, request, redirect, jsonify, json, Response, stream_with_context
import time
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq
# removed huggingface dependency

from datetime import datetime


load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

app = Flask(__name__)

# global store for Chroma
chroma_db = None

# helper: ingest once if not exists
# ingest data once and create vector index (with logs)
# def ingest_url_if_needed(url):
#     global chroma_db
#     try:
#         print("[INGEST] Fetching data...")
#         headers = {'User-Agent': 'Mozilla/5.0'}
#         response = requests.get(url, headers=headers, timeout=10)
#         soup = BeautifulSoup(response.text, 'html.parser')
#         text = soup.get_text(separator=' ', strip=True)

#         splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
#         docs = [Document(page_content=chunk) for chunk in splitter.split_text(text)]

#         embeddings = FakeEmbeddings(size=384)
#         chroma_db = Chroma.from_documents(docs, embeddings)
#         print("Saved vectors:", len(chroma_db._collection.get()['ids']))

#         print("[INGEST] Chroma vector ready")
#     except Exception as e:
#         print(f"[INGEST ERROR]: {str(e)}")
#         chroma_db = []  # fallback store

data = {
    "imgData": [
        {"id": "img1", "name": "For Patients", "title": "On-Demand Teleconsultation", "des": "On-demand teleconsultation provides an immediate, secure link between remote patients and specialized physicians through high-definition video interfaces.", "image": "https://anthem-blog-media.s3.us-west-1.amazonaws.com/wp-content/uploads/2020/11/10202642/BLG-ALL-0095-20-Blog-Article-Images-for-2020-Oct_Telehealth-2.gif"},
        {"id": "img2", "name": "For Doctors", "title": "Next-Gen Digital Chambers", "des": "The next-generation digital medical chamber is a compact, autonomous healthcare hub that uses AI and biometric sensors.", "image": "https://optimoz.com/wp-content/uploads/2024/12/Harnessing-Artificial-Intelligence-to-Revolutionize-Healthcare.gif"},
        {"id": "img3", "name": "For Researchers", "title": "Anonymized Clinical Cohorts", "des": "Anonymized clinical cohorts aggregate de-identified patient data to enable large-scale medical research without compromising individual privacy.", "image": "https://i.makeagif.com/media/6-30-2020/WxMaqz.gif"},
        {"id": "img4", "name": "For Institutions", "title": "Decentralized Hospital Networks", "des": "Decentralized hospital networks distribute authority and data across multiple independent nodes, enabling faster local decision-making.", "image": "https://i.giphy.com/l1J9CXWtcXqkfRN60.gif"},
        {"id": "img5", "name": "Ancient Care", "title": "Ancient Medical Techniques", "des": "Ancient medical techniques use time-tested, nature-based practices like herbalism and acupuncture to treat ailments.", "image": "https://cdn.egyptatours.com/wp-content/uploads/2024/12/Ancient-Egyptian-Medicine-Powerful-Secrets-of-Healing-and-Science-Featured-Image-EgyptaTours.webp"}
    ]
}


@app.route('/hosting/<section_id>')
def hosting(section_id):
    # route path sends clicked section id into hosting function
    section_id = (section_id or '').strip().lower()

    def unique_top_five(items):
        seen = set()
        result = []

        for item in items:
            name = (item.get("name") or "").strip()
            if not name:
                continue

            key = name.lower()
            if key in seen:
                continue

            seen.add(key)
            result.append(item)

            if len(result) == 5:
                break

        return result

    def get_host_data():
        api_url = "https://clinicaltrials.gov/api/v2/studies"

        params = {
            "query.locn": "United States",
            "pageSize": 100,
            "format": "json",
        }

        response = requests.get(api_url, params=params, timeout=20)
        response.raise_for_status()

        payload_json = response.json()
        studies = payload_json.get("studies", [])

        contributors = []
        doctors = []
        research = []

        for study in studies:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            contacts_module = protocol.get("contactsLocationsModule", {})

            title = (
                identification.get("briefTitle")
                or identification.get("officialTitle")
                or "Untitled Study"
            )

            updated = (
                status_module.get("lastUpdatePostDateStruct", {})
                or {}
            ).get("date", "")

            if updated and not str(updated).startswith("2026"):
                continue

            lead_sponsor = sponsor_module.get("leadSponsor", {}) or {}
            lead_name = (lead_sponsor.get("name") or "").strip()

            if lead_name:
                contributors.append({
                    "name": lead_name,
                    "role": "Lead Sponsor",
                    "study": title,
                    "updated": updated,
                })

                lead_low = lead_name.lower()
                if any(word in lead_low for word in ["research", "center", "centre", "institute", "university", "lab"]):
                    research.append({
                        "name": lead_name,
                        "role": "Research Organization",
                        "study": title,
                        "updated": updated,
                    })

            for collaborator in sponsor_module.get("collaborators", []) or []:
                collab_name = (collaborator.get("name") or "").strip()

                if not collab_name:
                    continue

                contributors.append({
                    "name": collab_name,
                    "role": "Collaborator",
                    "study": title,
                    "updated": updated,
                })

            for official in contacts_module.get("overallOfficials", []) or []:
                official_name = (official.get("name") or "").strip()
                official_role = (official.get("role") or "").strip()
                official_affiliation = (official.get("affiliation") or "").strip()

                if not official_name:
                    continue

                role_low = official_role.lower()

                if "investigator" in role_low or "physician" in role_low or "doctor" in role_low:
                    doctors.append({
                        "name": official_name,
                        "role": official_role or "Doctor",
                        "affiliation": official_affiliation,
                        "study": title,
                        "updated": updated,
                    })
                else:
                    research.append({
                        "name": official_name,
                        "role": official_role or "Researcher",
                        "affiliation": official_affiliation,
                        "study": title,
                        "updated": updated,
                    })

        return {
            "contributors": unique_top_five(contributors),
            "doctors": unique_top_five(doctors),
            "research": unique_top_five(research),
        }

    @stream_with_context
    def event_stream():
        for _ in range(5):
            host_data = get_host_data()
            # server timestamp for this SSE response
            sent_at = datetime.now().strftime("%I:%M %p, %d %B, %Y CDT")
            if section_id == 'contributors':
                payload = {
                    "section": "contributors",
                    # send current server time with contributors data
                    "sent_at": sent_at,
                    "items": host_data["contributors"],
                }
            elif section_id == 'doctors':
                payload = {
                    "section": "doctors",
                    # send current server time with doctors data
                    "sent_at": sent_at,
                    "items": host_data["doctors"],
                }
            elif section_id == 'research':
                payload = {
                    "section": "research",
                    # send current server time with research data
                    "sent_at": sent_at,
                    "items": host_data["research"],
                }
            else:
                payload = {
                    "section": section_id,
                    # send current server time even if no items found
                    "sent_at": sent_at,
                    "items": [],
                }

            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(300)

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@app.route('/aptiCare')
def aptiCare():
    llm_text = request.args.get('llm_response')
    return render_template(
        'aptiCare.html',
        title_name='AptiCares Home',
        imageData=data["imgData"],
        llm_response=llm_text
    )

@app.route('/imgData')
def imgData():
    return render_template("index.html", title_name="AptiCares Home", imageData=data["imgData"])

@app.route('/patient-intake', methods=['POST'])
def patient_intake():
    client = Groq(api_key=groq_api_key)
    req = request.get_json(force=True)
    msg = (req.get('message') or '').strip()
    completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": "You are a medical assistant."}, {"role": "user", "content": msg}])
    return jsonify({'ai_reply': completion.choices[0].message.content})

@app.route('/patient-followup', methods=['POST'])
def patient_followup():
    req = request.get_json(force=True) or {}
    contact = req.get('contact') or {}
    email = (contact.get('email') or '').strip()
    phone = (contact.get('phone') or '').strip()
    note = f"Thanks. We will contact you at {email or phone}." if (email or phone) else "Please share your email or phone."
    return jsonify({'doctor_reply': f"Doctor reviewed your submission. {note}"})

@app.route('/groq', methods=['POST'])
def groq():
    try:
        client = Groq(api_key=groq_api_key)
        data = request.get_json(force=True) or {}
        msg = (data.get('message') or '').strip()

        if not msg:
            return jsonify({'reply': 'Empty message'})

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Reply in max 5 lines only. Keep answer short and direct."},
                {"role": "user", "content": msg}
            ]
        )

        return jsonify({'reply': completion.choices[0].message.content})

    except Exception as e:
        return jsonify({'reply': f'Error: {str(e)}'})


@app.route('/gene-llm', methods=['POST'])
def gene_llm():
    try:
        client = Groq(api_key=groq_api_key)
        data = request.get_json(force=True) or {}
        msg = (data.get('message') or '').strip()

        if not msg:
            return jsonify({'reply': 'Empty message'})

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Reply in max 5 lines only. Keep answer short and direct."},
                {"role": "user", "content": msg}
            ]
        )

        return jsonify({'reply': completion.choices[0].message.content})

    except Exception as e:
        return jsonify({'reply': f'Error: {str(e)}'})
   



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
