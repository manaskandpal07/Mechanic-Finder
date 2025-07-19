from flask import Flask, render_template, request, redirect, url_for, jsonify, session,flash
import mysql.connector
import requests
import os
from dotenv import load_dotenv
from geopy.distance import geodesic
import re
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_secret_key")  # Set this in .env too

@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}

# Database Configuration
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# ---------------- Home & Pages ----------------

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/map")
def map():
    return render_template("map.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/services")
def services():
    return render_template("services.html")

# ---------------- Admin Routes ----------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin_login.html", error="Invalid credentials")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM mechanics")
        mechanics = cur.fetchall()

        cur.execute("SELECT * FROM contact_messages ORDER BY id DESC")
        messages = cur.fetchall()

        cur.close()
        conn.close()
        return render_template("admin_dashboard.html", mechanics=mechanics, messages=messages)

    except Exception as e:
        return f"Error loading admin dashboard: {e}"

@app.route("/admin/delete/<int:mechanic_id>", methods=["POST"])
def delete_mechanic(mechanic_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM mechanics WHERE id = %s", (mechanic_id,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("admin_dashboard"))
    except Exception as e:
        return f"Error deleting mechanic: {e}"

@app.route("/admin/messages")
def admin_messages():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM contact_messages ORDER BY id DESC")
        messages = cur.fetchall()
        cur.close()
        conn.close()
        return render_template("admin_messages.html", messages=messages)
    except Exception as e:
        return f"Error loading messages: {e}"
    
@app.route("/find-mechanic")
def find_mechanic():
    return render_template("find_mechanic.html", api_key=GOOGLE_MAPS_API_KEY)

@app.route("/admin/mechanics")
def admin_mechanics():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM mechanics ORDER BY id DESC")
        mechanics = cur.fetchall()
        cur.close()
        conn.close()
        return render_template("admin_mechanics.html", mechanics=mechanics)
    except Exception as e:
        return f"Error loading mechanics: {e}"

# ---------------- Contact ----------------

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        # Server-side validation
        if not name or not email or not message:
            flash("All fields are required.", "danger")
            return redirect(url_for("contact"))
        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("contact"))
        if len(message) < 10:
            flash("Message must be at least 10 characters long.", "warning")
            return redirect(url_for("contact"))

        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO contact_messages (name, email, message)
                VALUES (%s, %s, %s)
            """, (name, email, message))
            conn.commit()
            cur.close()
            conn.close()

            flash("✅ Message sent successfully!", "success")
            return redirect(url_for("contact"))

        except Exception as e:
            import traceback
            print("Error saving contact message:", e)
            traceback.print_exc()
            flash("⚠️ Database error. Please try again later.", "danger")
            return redirect(url_for("contact"))

    return render_template("contact.html")


# ---------------- Mechanic Registration with Validation ----------------

@app.route("/register-mechanic", methods=["GET", "POST"])
def register_mechanic():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        location = request.form.get("location", "").strip()
        services = request.form.get("services", "").strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()

        errors = []

        # Validations
        if not name:
            errors.append("Name is required.")
        if not phone or not re.match(r'^\d{10}$', phone):
            errors.append("Enter a valid 10-digit phone number.")
        if not location:
            errors.append("Location is required.")
        if not services:
            errors.append("Please mention services offered.")
        try:
            lat_val = float(latitude)
            if not (-90 <= lat_val <= 90):
                errors.append("Latitude must be between -90 and 90.")
        except ValueError:
            errors.append("Latitude must be a number.")

        try:
            long_val = float(longitude)
            if not (-180 <= long_val <= 180):
                errors.append("Longitude must be between -180 and 180.")
        except ValueError:
            errors.append("Longitude must be a number.")

        if errors:
            return render_template("register_mechanic.html", errors=errors, api_key=GOOGLE_MAPS_API_KEY)

        try:
            conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO mechanics (name, phone, location, services, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, phone, location, services, lat_val, long_val))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for("home"))
        except Exception as e:
            return f"Error occurred: {str(e)}"

    return render_template("register_mechanic.html", api_key=GOOGLE_MAPS_API_KEY)

# ---------------- Mechanic Search APIs ----------------

@app.route("/search")
def search():
    query = request.args.get("q")
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM mechanics WHERE location LIKE %s", ('%' + query + '%',))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        print("Error:", e)
        return jsonify([])

@app.route('/api/mechanics')
def api_mechanics():
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)

    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM mechanics")
        results = cur.fetchall()
        cur.close()
        conn.close()

        if lat and lng:
            for mech in results:
                if mech.get("latitude") and mech.get("longitude"):
                    distance = geodesic((lat, lng), (mech["latitude"], mech["longitude"])).km
                    mech["distance_km"] = round(distance, 2)
            results.sort(key=lambda x: x.get("distance_km", 9999))

        return jsonify(results)
    except Exception as e:
        print("Error fetching mechanic data:", e)
        return jsonify([])
    
@app.route("/test-flash")
def test_flash():
    flash("This is a test flash message!", "success")
    return redirect(url_for("home"))


# ---------------- Main ----------------

if __name__ == "__main__":
    app.run(debug=True)
