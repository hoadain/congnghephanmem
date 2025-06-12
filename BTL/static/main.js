// Khởi tạo bản đồ
const map = L.map('map').setView([21.5942, 105.8482], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Global state
let stopMarkers = [];
let routeLine = null;
let busMarkers = [];
let currentRouteId = null;
let allRoutes = [];

// Icon xe buýt
const busIcon = L.icon({
  iconUrl: 'https://cdn-icons-png.flaticon.com/512/61/61231.png',
  iconSize: [32, 32],
  iconAnchor: [16, 16]
});

// Load danh sách tuyến
fetch('/api/routes')
  .then(res => res.json())
  .then(routes => {
    allRoutes = routes;
    const selector = document.getElementById('route-selector');
    routes.forEach(route => {
      const opt = document.createElement('option');
      opt.value = route.route_id;
      opt.textContent = route.name;
      selector.appendChild(opt);
    });
  });

// Khi chọn tuyến
document.getElementById('route-selector').addEventListener('change', e => {
  const routeId = e.target.value;
  if (!routeId) return;

  currentRouteId = routeId;
  loadRouteData(routeId);
});

// Load dữ liệu tuyến
function loadRouteData(routeId) {
  fetch(`/api/route/${routeId}`)
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        alert("Không tìm thấy tuyến!");
        return;
      }

      document.getElementById('route-name').textContent = data.name || `Tuyến ${data.route_id}`;
      document.getElementById('route-direction').textContent = data.direction || 'Chưa có thông tin';
      document.getElementById('route-hours').textContent = data.hours || '---';
      document.getElementById('route-fare').textContent = data.fare || '---';

      if (routeLine) map.removeLayer(routeLine);
      stopMarkers.forEach(m => map.removeLayer(m));
      stopMarkers = [];

      const latlngs = data.stops.map(s => [s.lat, s.lng]);
      routeLine = L.polyline(latlngs, { color: 'blue' }).addTo(map);
      map.fitBounds(routeLine.getBounds());

      const ul = document.getElementById('stops-list');
      ul.innerHTML = '';
      data.stops.forEach((s, i) => {
        const marker = L.marker([s.lat, s.lng]).addTo(map)
          .bindPopup(`<b>Trạm ${i + 1}:</b> ${s.name}`);
        stopMarkers.push(marker);

        const li = document.createElement('li');
        li.innerText = `${i + 1}. ${s.name}`;
        li.onclick = () => map.setView([s.lat, s.lng], 16);
        ul.appendChild(li);
      });

      loadRatings(routeId);
    });

  fetchBusPositions();
}

function fetchBusPositions() {
  if (!currentRouteId) return;

  fetch(`/api/route/${currentRouteId}/buses`)
    .then(res => res.json())
    .then(data => {
      busMarkers.forEach(m => map.removeLayer(m));
      busMarkers = [];

      if (data.error) return;

      data.forEach(bus => {
        const marker = L.marker([bus.lat, bus.lng], { icon: busIcon }).addTo(map)
          .bindPopup(`🚌 Xe ${bus.plate}`);
        busMarkers.push(marker);
      });
    });
}
setInterval(fetchBusPositions, 10000);

// Tìm tuyến
document.getElementById("search-form").addEventListener("submit", function (e) {
  e.preventDefault();

  const start = document.getElementById("start-point").value.trim();
  const end = document.getElementById("end-point").value.trim();
  const resultList = document.getElementById("search-results");
  resultList.innerHTML = "";

  if (!start || !end) return;

  fetch(`/api/search_route?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`)
    .then(res => res.json())
    .then(routes => {
      if (!routes || routes.length === 0) {
        const li = document.createElement("li");
        li.textContent = "Không tìm thấy tuyến phù hợp.";
        resultList.appendChild(li);
      } else {
        routes.forEach(route => {
          const li = document.createElement("li");
          li.textContent = `${route.name} (${route.direction})`;
          li.style.cursor = "pointer";
          li.onclick = () => {
            document.getElementById("route-selector").value = route.route_id;
            currentRouteId = route.route_id;
            loadRouteData(route.route_id);
          };
          resultList.appendChild(li);
        });
      }

      fetch("/ghi_thong_ke", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tukhoa: `${start} -> ${end}` })
      });
    })
    .catch(err => {
      console.error("Lỗi tìm tuyến:", err);
      const li = document.createElement("li");
      li.textContent = "Đã xảy ra lỗi khi tìm tuyến.";
      resultList.appendChild(li);
    });
});

// =============================
// 📌 ĐÁNH GIÁ TUYẾN XE BUÝT
// =============================
function loadRatings(routeId) {
  const ul = document.getElementById("ratings-list");
  ul.innerHTML = "<li>Đang tải đánh giá...</li>";

  fetch(`/api/route/${routeId}/ratings`)
    .then(res => res.json())
    .then(data => {
      ul.innerHTML = "";

      if (!data || data.length === 0) {
        ul.innerHTML = "<li>Chưa có đánh giá nào.</li>";
        return;
      }

      data.forEach(r => {
        const li = document.createElement("li");
        li.innerHTML = `
          ⭐ ${r.diem}/5 - <strong>${r.username}</strong><br>
          <em>${r.nhanxet || "Không có nhận xét"}</em>
        `;

        // Thêm nút sửa/xóa nếu là admin
        if (r.is_admin) {
          const btnEdit = document.createElement("button");
          btnEdit.textContent = "Sửa";
          btnEdit.style.marginLeft = "8px";
          btnEdit.onclick = () => editRating(r);

          const btnDelete = document.createElement("button");
          btnDelete.textContent = "Xóa";
          btnDelete.style.marginLeft = "4px";
          btnDelete.onclick = () => deleteRating(r.id);

          li.appendChild(document.createElement("br"));
          li.appendChild(btnEdit);
          li.appendChild(btnDelete);
        }

        ul.appendChild(li);
      });
    })
    .catch(err => {
      console.error("Lỗi tải đánh giá:", err);
      ul.innerHTML = "<li>Lỗi tải đánh giá.</li>";
    });
}

// Gửi đánh giá mới
const ratingForm = document.getElementById("rating-form");
if (ratingForm) {
  ratingForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const diem = parseInt(document.getElementById("diem").value);
    const nhanxet = document.getElementById("nhanxet").value.trim();

    if (!currentRouteId || diem < 1 || diem > 5) return;

    fetch(`/api/route/${currentRouteId}/ratings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ diem, nhanxet })
    })
      .then(res => res.json())
      .then(resp => {
        if (resp.success) {
          alert("Đánh giá đã được gửi!");
          document.getElementById("rating-form").reset();
          loadRatings(currentRouteId);
        } else {
          alert("Không thể gửi đánh giá.");
        }
      })
      .catch(err => {
        console.error("Lỗi gửi đánh giá:", err);
        alert("Đã xảy ra lỗi khi gửi đánh giá.");
      });
  });
}

// Sửa đánh giá
function editRating(rating) {
  const newScore = prompt("Nhập điểm mới (1-5):", rating.diem);
  const newComment = prompt("Nhận xét mới:", rating.nhanxet || "");

  const diem = parseInt(newScore);
  if (!diem || diem < 1 || diem > 5) {
    alert("Điểm không hợp lệ.");
    return;
  }

  fetch(`/api/ratings/${rating.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ diem, nhanxet: newComment })
  })
    .then(res => res.json())
    .then(resp => {
      if (resp.success) {
        alert("Đã cập nhật đánh giá.");
        loadRatings(currentRouteId);
      } else {
        alert("Không thể cập nhật.");
      }
    });
}

// Xóa đánh giá
function deleteRating(id) {
  if (!confirm("Bạn có chắc muốn xóa đánh giá này?")) return;

  fetch(`/api/ratings/${id}`, { method: "DELETE" })
    .then(res => res.json())
    .then(resp => {
      if (resp.success) {
        alert("Đã xóa đánh giá.");
        loadRatings(currentRouteId);
      } else {
        alert("Không thể xóa.");
      }
    });
}
