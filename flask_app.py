import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, template_folder="templates")


# Use the Railway DATABASE_URL
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Example model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

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
    import os, json
    p = os.path.join(app.root_path, 'static', 'data', 'products.json')
    return json.load(open(p)) if os.path.exists(p) else []

    
#Gemstone infomation apps products route
@app.route('/products')
def list_products():
    return render_template('business_Gem/products.html', products=load_products())




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
