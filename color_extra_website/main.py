from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from datetime import date
from PIL import Image
import numpy as np
import os
from werkzeug.utils import secure_filename
import pyperclip
from email_info import SMTP_SERVER, SMTP_PORT, MY_EMAIL, MY_PASS
import smtplib


# Initialize the Flask application
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for flashing messages


# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Ensure the 'uploads' folder exists
uploads_folder = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(uploads_folder, exist_ok=True)


# Set the current year
year = date.today().year


def allowed_file(filename):
    """ Function to check allowed file extensions """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_top_colors(image_array, n):
    """ Function to extract top colors from an image """
    # Reshape image array into one-dimensional array
    flat_image = image_array.reshape(-1, image_array.shape[-1])

    # Count the occurrences of each color
    unique_colors, color_counts = np.unique(flat_image, axis=0, return_counts=True)

    # Sort by color occurrences
    sorted_colors = unique_colors[np.argsort(color_counts)][::-1]

    # Get the first n colors
    top_colors = sorted_colors[:n]

    # Create a list to store color details
    color_details = []

    # Iterate over top colors and get their RGB and HEX values
    for color in top_colors:
        # Get RGB values
        rgb_values = tuple(color)

        # Convert RGB to HEX
        hex_value = '#{:02x}{:02x}{:02x}'.format(*color)

        # Append color details to the list
        color_details.append({'color': color, 'rgb': rgb_values, 'hex': hex_value})

    return color_details


def copy_all_colors(top_colors):
    all_colors_text = ""
    for color in top_colors:
        all_colors_text += f"RGB: {color['rgb']}, HEX: {color['hex']}\n"

    pyperclip.copy(all_colors_text)

    flash("All color data has been copied to the clipboard!")


def send_email(firstname, lastname, email, message):
    try:
        email_message = (f"Subject: A message comes from Todo-list Website!\n\n"
                         f"You got a message:\n"
                         f"From {firstname} {lastname}, Email:{email} \n"
                         f"For details:\n"
                         f"{message}")

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as connection:
            connection.starttls()
            connection.login(user=MY_EMAIL, password=MY_PASS)
            connection.sendmail(from_addr=MY_EMAIL,
                                to_addrs=MY_EMAIL,
                                msg=email_message)
            print(f"The message was sent.")
    except smtplib.SMTPServerDisconnected:
        print("ERROR: Could not connect to the SMTP server. "
              "Make sure the SMTP_LOGIN and SMTP_PASS credentials have been set correctly.")


@app.route('/')
def home_page():
    return render_template("index.html", current_year=year)


@app.route('/upload', methods=['POST'])
def handle_upload():
    if 'image' not in request.files:
        flash('No file part')
        return redirect(request.url)

    user_image = request.files['image']

    if user_image.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if user_image and allowed_file(user_image.filename):
        try:
            # Secure the filename and save the file
            filename = secure_filename(user_image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            user_image.save(filepath)

            # Open the image file and convert it to a numpy array
            image = Image.open(filepath)
            user_image_array = np.array(image)

            # Extract the top colors from the image
            top_colors = extract_top_colors(user_image_array, n=10)

            # Render the template with the top colors and the uploaded image path
            return render_template("index.html", current_year=year, top_colors=top_colors,
                                   image_url=url_for('static', filename=f'uploads/{filename}'))

        except Exception as e:
            flash('Failed to process image: ' + str(e))
            return redirect(url_for('home_page'))

    flash('File not allowed')
    return redirect(request.url)


@app.route('/copy_colors', methods=['POST'])
def copy_colors_info():
    try:
        colors_data = request.json.get('colors')
        if not colors_data:
            return jsonify({'success': False, 'message': 'No colors data provided'}), 400
        copy_all_colors(colors_data)
        return jsonify({'success': True, 'message': 'Color data has been copied to clipboard'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/contact")
def contact():
    if request.method == "POST":
        firstname = request.form['firstname'],
        lastname = request.form['lastname'],
        email = request.form['email'],
        message = request.form['message']
        send_email(firstname, lastname, email, message)
        if send_email:
            flash('Successfully sent your message!')
            return redirect(url_for('contact'))
        else:
            flash('Unable to send email, please try again later')

    return render_template("contact.html", current_year=year)


if __name__ == '__main__':
    app.run(debug=True)