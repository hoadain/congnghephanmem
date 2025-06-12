from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection as get_db

auth = Blueprint('auth', __name__)

def get_db():
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=MSI\SQLEXPRESS;"
            "DATABASE=QuanLyXeBuyt;"
            "Trusted_Connection=yes;"
        )
        return conn
    except Exception as e:
        print("Lỗi kết nối CSDL:", e)
        return None  # Tránh lỗi 'NoneType'
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ten = request.form['username']
        mk = request.form['password']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM NguoiDung WHERE TenDangNhap = ?", (ten,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user.MatKhau, mk):
            session['user_id'] = user.Id
            session['username'] = user.TenDangNhap
            session['role'] = user.VaiTro
            return redirect(url_for('index'))
        flash("Sai tên đăng nhập hoặc mật khẩu.")
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ten = request.form['username']
        mk = request.form['password']
        hashed = generate_password_hash(mk)
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO NguoiDung (TenDangNhap, MatKhau, VaiTro) VALUES (?, ?, 'user')",
                (ten, hashed)
            )
            conn.commit()
            flash("Đăng ký thành công. Vui lòng đăng nhập.")
            return redirect(url_for('auth.login'))
        except:
            flash("Tên đăng nhập đã tồn tại.")
        finally:
            conn.close()
    return render_template('register.html')

@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
