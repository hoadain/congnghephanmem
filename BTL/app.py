from flask import Flask, render_template, jsonify, session, redirect, url_for, request
import json
import os
from utils.bus_api import get_live_bus_positions
from auth import auth  # Từ file auth.py (chứa xử lý đăng nhập)
from db import get_db_connection

app = Flask(__name__)
app.secret_key = "matkhau-bi-mat"

# Đăng ký Blueprint
app.register_blueprint(auth)

# Trang chính
@app.route("/")
def index():
    if 'username' not in session:
        return redirect(url_for("auth.login"))
    return render_template("index.html", username=session['username'], role=session['role'], is_admin=(session['role'] == 'admin'))

# API: Lấy thông tin tuyến
@app.route("/api/route/<route_id>")
def route_data(route_id):
    try:
        with open(f"data/route_{route_id}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Không tìm thấy tuyến"}), 404

# API: Lấy xe đang chạy trên tuyến
@app.route("/api/route/<route_id>/buses")
def buses_on_route(route_id):
    try:
        buses = get_live_bus_positions(route_id)
        return jsonify(buses)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API: Lấy danh sách tuyến xe
@app.route("/api/routes")
def list_routes():
    try:
        route_files = [f for f in os.listdir("data") if f.startswith("route_") and f.endswith(".json")]
        routes = []
        for file in route_files:
            with open(os.path.join("data", file), encoding="utf-8") as f:
                data = json.load(f)
                routes.append({
                    "route_id": data.get("route_id"),
                    "name": data.get("name"),
                    "direction": data.get("direction", ""),
                    "stops": data.get("stops", [])
                })
        return jsonify(routes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API: Tìm tuyến xe buýt theo điểm đi / đến
@app.route("/api/search_route")
def search_route():
    start = request.args.get("start", "").strip().lower()
    end = request.args.get("end", "").strip().lower()

    result = []
    for filename in os.listdir("data"):
        if filename.startswith("route_") and filename.endswith(".json"):
            with open(os.path.join("data", filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                stop_names = [s["name"].lower() for s in data["stops"]]

                start_index = next((i for i, name in enumerate(stop_names) if start in name), -1)
                end_index = next((i for i, name in enumerate(stop_names) if end in name), -1)

                if start_index != -1 and end_index != -1 and start_index < end_index:
                    result.append({
                        "route_id": data["route_id"],
                        "name": data["name"],
                        "direction": data.get("direction", "")
                    })

    return jsonify(result)

# Ghi thống kê tìm kiếm
@app.route('/ghi_thong_ke', methods=['POST'])
def ghi_thong_ke():
    if 'user_id' not in session:
        return '', 401

    tukhoa = request.json.get('tukhoa')
    if not tukhoa:
        return '', 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ThongKeTimKiem (TuKhoa, NguoiDungId) VALUES (?, ?)",
            (tukhoa, session['user_id'])
        )
        conn.commit()
        conn.close()
        return '', 204
    except Exception as e:
        return f"Lỗi ghi thống kê: {e}", 500

# Trang thống kê tìm kiếm (admin)
@app.route("/thongke")
def thong_ke_tim_kiem():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for("index"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TuKhoa, COUNT(*) AS SoLan
            FROM ThongKeTimKiem
            GROUP BY TuKhoa
            ORDER BY SoLan DESC
        """)
        rows = cursor.fetchall()
        data = [{"tukhoa": row[0], "solan": row[1]} for row in rows]
        conn.close()
        return render_template("thongke.html", data=data)
    except Exception as e:
        return f"Lỗi thống kê: {e}", 500

# API: Lấy đánh giá tuyến
@app.route("/api/route/<int:route_id>/ratings", methods=['GET'])
def get_ratings(route_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, Username, Diem, NhanXet, ThoiGian FROM DanhGia WHERE RouteId = ?", (route_id,))
    data = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "id": row.Id,
            "username": row.Username,
            "diem": row.Diem,
            "nhanxet": row.NhanXet,
            "thoigian": row.ThoiGian.strftime("%d-%m-%Y %H:%M")
        }
        for row in data
    ])

# API: Gửi đánh giá (chỉ user)
@app.route("/api/route/<int:route_id>/ratings", methods=['POST'])
def submit_rating(route_id):
    if 'user_id' not in session or 'username' not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401

    data = request.get_json()
    diem_raw = data.get("diem")
    nhanxet = data.get("nhanxet", "").strip()

    try:
        diem = int(diem_raw)
        if diem < 1 or diem > 5:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Điểm đánh giá không hợp lệ"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO DanhGia (RouteId, Username, Diem, NhanXet, ThoiGian) "
            "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (route_id, session['username'], diem, nhanxet)
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print("❌ Lỗi ghi đánh giá:", e)
        return jsonify({"error": str(e)}), 500

# API: Sửa đánh giá (admin)
@app.route("/api/ratings/<int:rating_id>", methods=['PUT'])
def sua_danh_gia(rating_id):
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({"error": "Không có quyền"}), 403

    data = request.get_json()
    diem = int(data.get('diem', 0))
    nhanxet = data.get('nhanxet', '')

    if diem < 1 or diem > 5:
        return jsonify({"error": "Điểm không hợp lệ"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE DanhGia SET Diem = ?, NhanXet = ? WHERE Id = ?", (diem, nhanxet, rating_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# API: Xóa đánh giá (admin)
@app.route("/api/ratings/<int:rating_id>", methods=['DELETE'])
def xoa_danh_gia(rating_id):
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({"error": "Không có quyền"}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM DanhGia WHERE Id = ?", (rating_id,))
    conn.commit()
    conn.close()

    return '', 204

# Đăng xuất
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

# Admin: Danh sách người dùng
@app.route("/admin/users")
def danh_sach_nguoi_dung():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, TenDangNhap, MatKhau, VaiTro FROM NguoiDung")
    users = cursor.fetchall()
    conn.close()

    return render_template("admin_users.html", users=users)

# Admin: Sửa người dùng
@app.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
def sua_nguoi_dung(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        ten_dang_nhap = request.form['TenDangNhap']
        mat_khau = request.form['MatKhau']
        vai_tro = request.form['VaiTro']
        cursor.execute(
            "UPDATE NguoiDung SET TenDangNhap = ?, MatKhau = ?, VaiTro = ? WHERE Id = ?",
            (ten_dang_nhap, mat_khau, vai_tro, user_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("danh_sach_nguoi_dung"))

    cursor.execute("SELECT * FROM NguoiDung WHERE Id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template("edit_user.html", user=user)

# Admin: Xoá người dùng
@app.route("/admin/users/delete/<int:user_id>")
def xoa_nguoi_dung(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM NguoiDung WHERE Id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("danh_sach_nguoi_dung"))
@app.route("/quan_ly_danh_gia")
def quan_ly_danh_gia():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, RouteId, Username, Diem, NhanXet, ThoiGian FROM DanhGia ORDER BY ThoiGian DESC")
    danh_gia = cursor.fetchall()
    conn.close()

    return render_template("manage_ratings.html", danh_gia=danh_gia)


@app.route("/quan_ly_tuyen_xe")
def quan_ly_tuyen_xe():
    if session.get("role") != "admin":
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TuyenXe")
    tuyen_list = cursor.fetchall()
    conn.close()

    return render_template("admin_routes.html", danh_sach_tuyen=tuyen_list)


@app.route("/them_tuyen", methods=["POST"])
def them_tuyen():
    ten = request.form["TenTuyen"]
    chieu = request.form["ChieuDi"]
    gio = request.form["GioHoatDong"]
    gia = request.form["GiaVe"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Lấy RouteId mới
    cursor.execute("SELECT TOP 1 RouteId FROM TuyenXe ORDER BY RouteId DESC")
    last_id = cursor.fetchone()
    if last_id:
        last_number = int(last_id[0][1:])
        new_number = last_number + 1
    else:
        new_number = 1
    new_route_id = f"T{new_number:03}"

    # Thêm vào CSDL
    cursor.execute(
        "INSERT INTO TuyenXe (RouteId, TenTuyen, ChieuDi, GioHoatDong, GiaVe) VALUES (?, ?, ?, ?, ?)",
        (new_route_id, ten, chieu, gio, gia)
    )
    conn.commit()
    conn.close()

    # Ghi file JSON tương ứng
    new_route_data = {
        "route_id": new_route_id,
        "name": ten,
        "direction": chieu,
        "hours": gio,
        "fare": gia,
        "stops": []  # mặc định là chưa có điểm dừng
    }

    data_path = os.path.join("data", f"route_{new_route_id}.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(new_route_data, f, ensure_ascii=False, indent=4)

    return redirect(url_for("quan_ly_tuyen_xe"))

@app.route("/xoa_tuyen/<route_id>")
def xoa_tuyen(route_id):
    if session.get("role") != "admin":
        return redirect(url_for("index"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM TuyenXe WHERE RouteId = ?", (route_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("quan_ly_tuyen_xe"))

@app.route("/sua_tuyen/<route_id>", methods=["GET", "POST"])
def sua_tuyen(route_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        ten_tuyen = request.form["TenTuyen"]
        chieu_di = request.form["ChieuDi"]
        gio_hoat_dong = request.form["GioHoatDong"]
        gia_ve = request.form["GiaVe"]

        cursor.execute(
            "UPDATE TuyenXe SET TenTuyen=?, ChieuDi=?, GioHoatDong=?, GiaVe=? WHERE RouteId=?",
            (ten_tuyen, chieu_di, gio_hoat_dong, gia_ve, route_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("quan_ly_tuyen_xe"))
    else:
        cursor.execute("SELECT * FROM TuyenXe WHERE RouteId = ?", (route_id,))
        tuyen = cursor.fetchone()
        conn.close()
        if tuyen:
            return render_template("sua_tuyen.html", tuyen=tuyen)
        else:
            return "Không tìm thấy tuyến", 404

if __name__ == "__main__":
    app.run(debug=True)
