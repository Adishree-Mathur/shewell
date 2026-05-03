from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from twilio.rest import Client
from dotenv import load_dotenv
from google import genai
from google.genai import types
from deep_translator import GoogleTranslator
from supabase import create_client
import random
from pathlib import Path
from postgrest.exceptions import APIError


load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

gemini_api_key = os.getenv('GEMINI_API_KEY')
requested_gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
genai_client = None
supabase_client = None


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'development-key'

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
if supabase_url and supabase_key:
    supabase_client = create_client(supabase_url, supabase_key)
else:
    app.logger.warning('SUPABASE_URL or SUPABASE_KEY is not set; Supabase client is disabled.')


def require_supabase_client():
    if not supabase_client:
        raise RuntimeError('Supabase client is not configured.')
    return supabase_client


def supabase_select_one(table_name, **filters):
    try:
        query = require_supabase_client().table(table_name).select('*')
        for column, value in filters.items():
            query = query.eq(column, value)
        response = query.limit(1).execute()
        rows = getattr(response, 'data', None) or []
        return rows[0] if rows else None
    except APIError as exc:
        app.logger.error('Supabase select failed for %s: %s', table_name, exc)
        raise


def supabase_select_many(table_name, **filters):
    try:
        query = require_supabase_client().table(table_name).select('*')
        for column, value in filters.items():
            query = query.eq(column, value)
        response = query.execute()
        return getattr(response, 'data', None) or []
    except APIError as exc:
        app.logger.error('Supabase select failed for %s: %s', table_name, exc)
        raise


def supabase_insert(table_name, payload):
    try:
        response = require_supabase_client().table(table_name).insert(payload).execute()
        rows = getattr(response, 'data', None) or []
        return rows[0] if rows else None
    except APIError as exc:
        app.logger.error('Supabase insert failed for %s: %s', table_name, exc)
        raise


def supabase_update(table_name, payload, **filters):
    try:
        query = require_supabase_client().table(table_name).update(payload)
        for column, value in filters.items():
            query = query.eq(column, value)
        response = query.execute()
        return getattr(response, 'data', None) or []
    except APIError as exc:
        app.logger.error('Supabase update failed for %s: %s', table_name, exc)
        raise


@app.errorhandler(APIError)
def handle_supabase_api_error(exc):
    message = getattr(exc, 'message', None) or str(exc)
    flash(f'Database error: {message}', 'error')
    return redirect(request.referrer or url_for('home'))

if os.getenv('TWILIO_ACCOUNT_SID') and os.getenv('TWILIO_AUTH_TOKEN'):
    twilio_client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
    twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
else:
    twilio_client = None
    twilio_phone_number = None

system_instruction = """
    You are a supportive AI assistant for pregnant women on the SheWell platform. Provide helpful, accurate information about pregnancy, but always recommend consulting with their doctor.

-Don't respond to irrelevant question
-Don't give inaccurate answers, you may skip if you are unsure
"""

generation_config: types.GenerateContentConfigDict = {
    "system_instruction": system_instruction,
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 65536,
    "response_mime_type": "text/plain",
}

if gemini_api_key:
    genai_client = genai.Client(api_key=gemini_api_key)
else:
    app.logger.warning('GEMINI_API_KEY is not set; chatbot API will be disabled.')

gemini_model_name = requested_gemini_model
if gemini_model_name.endswith('-live'):
    app.logger.warning(
        'GEMINI_MODEL=%s is a Live model, but /api/chat uses generateContent; falling back to gemini-2.5-flash.',
        gemini_model_name,
    )
    gemini_model_name = os.getenv('GEMINI_CHAT_MODEL', 'gemini-2.5-flash')

def login_required(user_type=None):
    if 'user_id' not in session:
        flash('Please log in to access this page', 'error')
        return redirect(url_for('login'))
    if user_type and session.get('user_type') != user_type:
        flash(f'You must be logged in as a {user_type} to access this page', 'error')
        return redirect(url_for('dashboard'))
    return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        table_name = 'user' if user_type == 'patient' else 'doctor'
        user = supabase_select_one(table_name, email=email)

        if user and check_password_hash(user.get('password_hash', ''), password):
            session['user_id'] = user['id']
            session['user_type'] = user_type
            session['name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/periods')
def periods():
    return render_template('periods.html')

@app.route("/mental-health")
def mental_health():
    quotes = [
        "This too shall pass.", "You are stronger than you think.",
        "Breathe in courage, breathe out fear.", "One day at a time.",
        "You are enough just as you are.", "The sun will rise, and so will you."
    ]
    return render_template("mental_health.html", quote=random.choice(quotes))

@app.route('/reels')
def reels():
    return render_template("reels.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route('/register_patient', methods=['POST'])
def register_patient():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')

    if supabase_select_one('user', email=email):
        flash('Email is already registered', 'error')
        return redirect(url_for('register'))

    supabase_insert('user', {
        'name': name,
        'email': email,
        'phone': phone,
        'password_hash': generate_password_hash(password),
        'due_date': None,
    })

    flash('Patient registered successfully! Please log in.', 'success')
    return redirect(url_for('login'))

@app.route('/register_doctor', methods=['POST'])
def register_doctor():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    specialization = request.form.get('specialization')
    password = request.form.get('password')
    per_minute_price = request.form.get('per_minute_price', type=float)

    if supabase_select_one('doctor', email=email):
        flash('Email is already registered', 'error')
        return redirect(url_for('register'))

    supabase_insert('doctor', {
        'name': name,
        'email': email,
        'phone': phone,
        'specialization': specialization,
        'experience': request.form.get('experience', 0, type=int),
        'available_days': request.form.get('available_days', 'Mon-Fri'),
        'per_minute_price': per_minute_price,
        'password_hash': generate_password_hash(password),
    })

    flash('Doctor registered successfully! Please log in.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or 'user_type' not in session:
        flash('Please log in to access this page', 'error')
        return redirect(url_for('login'))
    
    if session['user_type'] == 'patient':
        return redirect(url_for('patient_dashboard'))
    elif session['user_type'] == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    else:
        flash('Invalid user type', 'error')
        return redirect(url_for('login'))

@app.route('/patient_dashboard')
def patient_dashboard():
    redirect_result = login_required('patient')
    if redirect_result:
        return redirect_result

    user = supabase_select_one('user', id=session['user_id'])
    if not user:
        flash('Patient profile not found', 'error')
        return redirect(url_for('login'))

    appointments = supabase_select_many('appointment', user_id=user['id'])
    return render_template('patient_dashboard.html', user=user, appointments=appointments)

@app.route('/doctor_dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    try:
        # Verify user is logged in as doctor
        if 'user_id' not in session or session.get('user_type') != 'doctor':
            flash('Please login as a doctor first', 'error')
            return redirect(url_for('login'))

        # Get doctor from database
        doctor = supabase_select_one('doctor', id=session['user_id'])
        if not doctor:
            flash('Doctor profile not found', 'error')
            return redirect(url_for('login'))

        # Handle price update
        if request.method == 'POST':
            new_price = request.form.get('per_minute_price', type=float)
            if new_price is not None:
                supabase_update('doctor', {'per_minute_price': new_price}, id=doctor['id'])
                doctor['per_minute_price'] = new_price
                flash('Price updated successfully!', 'success')

        # Get appointments
        appointments = supabase_select_many('appointment', doctor_id=doctor['id'])
        
        # Render template with all required variables
        return render_template('doctor_dashboard.html',
                            doctor=doctor,
                            appointments=appointments,
                            current_time=datetime.now())  # Pass current time

    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        flash('Failed to load dashboard', 'error')
        return redirect(url_for('home'))
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/doctors')
def doctors():
    redirect_result = login_required('patient')
    if redirect_result:
        return redirect_result
    doctors_list = supabase_select_many('doctor')
    return render_template('doctors.html', doctors=doctors_list)

@app.route('/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
def book_appointment(doctor_id):
    redirect_result = login_required('patient')
    if redirect_result:
        return redirect_result

    doctor = supabase_select_one('doctor', id=doctor_id)
    if not doctor:
        flash('Doctor profile not found', 'error')
        return redirect(url_for('doctors'))

    if request.method == 'POST':
        date = request.form.get('date')
        time = request.form.get('time')

        if not date or not time:
            flash('Please provide both date and time', 'error')
            return redirect(url_for('book_appointment', doctor_id=doctor_id))

        supabase_insert('appointment', {
            'user_id': session['user_id'],
            'doctor_id': doctor_id,
            'date': date,
            'time': time,
            'status': 'scheduled',
        })

        if twilio_client and twilio_phone_number:
            user = supabase_select_one('user', id=session['user_id'])
            if user:
                try:
                    twilio_client.messages.create(
                        body=f"Hello {user['name']}, your appointment with Dr. {doctor['name']} is confirmed for {date} at {time}.",
                        from_=twilio_phone_number,
                        to=user['phone']
                    )
                except Exception as e:
                    app.logger.error(f"Failed to send SMS: {e}")

        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('book_appointment.html', doctor=doctor)

@app.route('/chatbot')
def chatbot():
    redirect_result = login_required('patient')
    if redirect_result:
        return redirect_result
    if not genai_client:
        flash('Chatbot is unavailable until GEMINI_API_KEY is configured.', 'error')
        return redirect(url_for('home'))
    return render_template('chatbot.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    redirect_result = login_required('patient')
    if redirect_result:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400

    user_message = data.get('message')
    selected_language = data.get('language', 'en')

    def translate_text(text, target_language="en"):
        try:
            return GoogleTranslator(source='auto', target=target_language).translate(text)
        except Exception as e:
            app.logger.error(f"Translation error: {e}")
            return text

    try:
        if not genai_client:
            return jsonify({'response': 'Chatbot is unavailable until GEMINI_API_KEY is configured.'}), 503

        response = genai_client.models.generate_content(
            model=gemini_model_name,
            contents=translate_text(user_message, 'en'),
            config=generation_config,
        )
        response_text = getattr(response, 'text', None)
        ai_response = response_text.strip() if isinstance(response_text, str) and response_text else "I'm sorry, I couldn't process your request."
        return jsonify({'response': translate_text(ai_response, selected_language)})
    except Exception as e:
        error_message = str(e)
        if 'quota' in error_message.lower() or '429' in error_message:
            app.logger.error(f"Gemini quota exceeded: {e}")
            return jsonify({'response': 'The chatbot is temporarily unavailable because the Gemini quota has been exceeded.'}), 503
        app.logger.error(f"Failed to generate AI response: {e}")
        return jsonify({'response': 'Sorry, I was unable to process your request. Please try again later.'}), 500

@app.route('/admin/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        specialization = request.form.get('specialization')
        experience = request.form.get('experience')
        phone = request.form.get('phone')
        available_days = request.form.get('available_days')
        per_minute_price = request.form.get('per_minute_price', type=float)

        if supabase_select_one('doctor', email=email):
            flash('Email already registered', 'error')
            return render_template('admin_add_doctor.html')

        supabase_insert('doctor', {
            'name': name,
            'email': email,
            'specialization': specialization,
            'experience': experience,
            'phone': phone,
            'available_days': available_days,
            'per_minute_price': per_minute_price,
            'password_hash': generate_password_hash(password),
        })
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('admin_add_doctor.html')

if __name__ == '__main__':
    app.run(debug=True)