import random

def get_live_bus_positions(route_id):
    # 🚨 Nếu bạn muốn thật: Gọi API công cộng ở đây
    # Giả lập dữ liệu xe buýt
    return [
        {"plate": "51B-12345", "lat": 10.76 + random.uniform(-0.01, 0.01), "lng": 106.68 + random.uniform(-0.01, 0.01)},
        {"plate": "51B-67890", "lat": 10.77 + random.uniform(-0.01, 0.01), "lng": 106.69 + random.uniform(-0.01, 0.01)},
    ]
