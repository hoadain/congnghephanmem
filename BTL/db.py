# db.py
import pyodbc

def get_db_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=LAPTOP-SGL9NSVP\\SQLEXPRESS;"
        "DATABASE=QuanLyXeBuyt;"
        "Trusted_Connection=yes;"
    )
