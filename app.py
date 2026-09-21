from flask import Flask, render_template, request
import os
import boto3
import pymysql
from werkzeug.utils import secure_filename
from datetime import datetime


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)


# ============================================================
# AWS CONFIGURATION
# ============================================================

S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

AWS_REGION = os.environ.get(
    "AWS_REGION",
    "ap-south-1"
)


# ============================================================
# RDS MYSQL CONFIGURATION
# ============================================================

DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get(
    "DB_NAME",
    "campus_maintenance"
)


# ============================================================
# S3 CLIENT
# ============================================================

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

    return connection


# ============================================================
# CREATE DATABASE TABLE
# ============================================================

def create_table():

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_requests (

            id INT AUTO_INCREMENT PRIMARY KEY,

            name VARCHAR(100) NOT NULL,

            email VARCHAR(150) NOT NULL,

            location VARCHAR(200) NOT NULL,

            category VARCHAR(100) NOT NULL,

            description TEXT NOT NULL,

            photo_key VARCHAR(500),

            status VARCHAR(50) DEFAULT 'Pending',

            created_at DATETIME NOT NULL

        )
    """)

    connection.commit()

    cursor.close()

    connection.close()


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    return render_template("index.html")


# ============================================================
# SUBMIT MAINTENANCE REQUEST
# ============================================================

@app.route("/submit", methods=["POST"])
def submit_request():

    try:

        # ----------------------------------------------------
        # GET FORM DATA
        # ----------------------------------------------------

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()


        # ----------------------------------------------------
        # VALIDATE FORM
        # ----------------------------------------------------

        if not name or not email or not location or not category or not description:

            return render_template(
                "index.html",
                error="Please fill in all required fields."
            )


        # ----------------------------------------------------
        # UPLOAD PHOTO TO S3
        # ----------------------------------------------------

        photo = request.files.get("photo")

        photo_key = ""


        if photo and photo.filename:

            safe_filename = secure_filename(
                photo.filename
            )

            timestamp = datetime.now().strftime(
                "%Y%m%d%H%M%S"
            )

            photo_key = (
                "maintenance/"
                + timestamp
                + "_"
                + safe_filename
            )


            s3_client.upload_fileobj(

                photo,

                S3_BUCKET_NAME,

                photo_key,

                ExtraArgs={
                    "ContentType": photo.content_type
                }

            )


        # ----------------------------------------------------
        # SAVE DATA TO RDS MYSQL
        # ----------------------------------------------------

        connection = get_db_connection()

        cursor = connection.cursor()


        cursor.execute("""
            INSERT INTO maintenance_requests
            (
                name,
                email,
                location,
                category,
                description,
                photo_key,
                status,
                created_at
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (

            name,

            email,

            location,

            category,

            description,

            photo_key,

            "Pending",

            datetime.now()

        ))


        connection.commit()

        cursor.close()

        connection.close()


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return render_template(
            "index.html",
            message="Maintenance request submitted successfully!"
        )


    except Exception as error:

        print(
            "ERROR:",
            error
        )


        return render_template(
            "index.html",
            error="Something went wrong. Please try again."
        )


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )