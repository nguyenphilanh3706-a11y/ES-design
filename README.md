# Hệ Thống IoT & AI Thông Minh (Smart IoT & AI System)

Dự án tích hợp Phần cứng (ESP32), Firmware, Trí tuệ nhân tạo (Edge/Server AI), Backend (Node.js/FastAPI) và Frontend Web (React.js) theo kiến trúc thời gian thực.

## Cấu trúc thư mục
```
Smart_IoT_AI_System/
├── docs/
│   ├── DAC_TA_HE_THONG.md        # Tài liệu đặc tả kỹ thuật và kiến trúc hệ thống
│   ├── PHAN_CONG_NHIEM_VU.md     # Kế hoạch phân công công việc trong 4 tuần
│   └── API_SPECIFICATION.md      # Tài liệu đặc tả giao thức API & MQTT
├── hardware/
│   └── kicad/                    # Sơ đồ nguyên lý (Schematic), PCB Layout và BOM
├── firmware/                     # Source code cho vi điều khiển ESP32 (PlatformIO)
├── ai_engine/                    # Source code xử lý AI / Computer Vision / ML
├── backend/                      # RESTful API, WebSocket & MQTT Broker Handler
├── frontend/                     # Giao diện Web Dashboard theo dõi & điều khiển
├── docker-compose.yml            # Cấu hình triển khai nhanh toàn hệ thống
└── .gitignore
```

## Đội ngũ phát triển
1. **Nguyễn Phi Lanh**: Phụ trách Hardware (KiCad), Firmware (ESP32/C++) và AI Engine (Python/Inference).
2. **Lê Công Quốc Anh**: Phụ trách Backend (Server/Database/MQTT), Frontend (Web Dashboard) và Triển khai Web.
