from flask import Flask, render_template, request, redirect, session, flash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import secrets
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/send-email', methods=['POST'])
def send_email():
    try:
        name = request.form.get('name')
        recipient = request.form.get('recipient')
        
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        sender_email = 'madhan786819@gmail.com'
        app_password = os.getenv('APP_PASSWORD')
        
        otp = random.randint(100000, 999999)
        session['otp'] = str(otp)
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = "Radium Music - Your OTP"
        
        body = f"""
        Hi {name},
        
        Welcome to Radium Music!
        
        Your OTP is: {otp}
        
        Please use this OTP to complete your registration.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
        
        flash("Email sent successfully! Please check your inbox for the OTP.", "success")
        return redirect('/signup')
    
    except Exception as e:
        flash("Error sending email. Please try again.", "error")
        return redirect('/signup')

@app.route('/validateotp', methods=['POST'])
def validateotp():
    entered_otp = request.form.get('otp')
    stored_otp = session.get('otp')
    
    if not stored_otp:
        flash("Please request a new OTP.", "error")
        return redirect('/signup')
    
    if stored_otp == entered_otp:
        flash("OTP verified successfully!\nWe welcome you to our AI powered music world!!!!", "success")
        session.pop('otp', None)
        return redirect('/signup')
    else:
        flash("Invalid OTP. Please try again.", "error")
        return redirect('/signup')

@app.route('/signin')
def signin():
    return render_template('signin.html')

if __name__ == '__main__':
    app.run(debug=True)
