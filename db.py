
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def connect():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database="banking_analysis",
        ssl_disabled=False
    )
