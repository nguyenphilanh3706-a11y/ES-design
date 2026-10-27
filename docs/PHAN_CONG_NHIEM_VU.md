# BẢNG PHÂN CÔNG NHIỆM VỤ CHI TIẾT (4 TUẦN)

## Nhân sự thực hiện
- **Nguyễn Phi Lanh**: Chuyên trách **Hardware, Firmware và AI**.
- **Lê Công Quốc Anh**: Chuyên trách **Backend, Frontend và Web Deployment**.

---

## Kế hoạch triển khai trong 4 tuần

### TUẦN 1: Phân tích yêu cầu, Thiết kế kiến trúc & Khởi tạo nền tảng
| Thành viên | Mảng phụ trách | Công việc cụ thể | Sản phẩm bàn giao (Deliverables) |
| :--- | :--- | :--- | :--- |
| **Nguyễn Phi Lanh** | **Hardware & Firmware & AI** | - Lựa chọn linh kiện, thiết kế sơ đồ nguyên lý (Schematic) trên KiCad.<br>- Khởi tạo project Firmware ESP32 (PlatformIO), viết hàm đọc cảm biến cơ bản.<br>- Thu thập bộ dữ liệu (Dataset) cho bài toán AI. | - File Schematic (`.kicad_sch`) & BOM.<br>- Source code đọc cảm biến qua Serial.<br>- Dataset đã làm sạch. |
| **Lê Công Quốc Anh** | **Backend, Frontend & Web** | - Thiết kế cơ sở dữ liệu (ERD) và tài liệu đặc tả API / MQTT Topics.<br>- Khởi tạo khung dự án Backend (Node.js/Express) và cấu hình MQTT Broker.<br>- Thiết kế UI/UX Wireframe và dựng khung ứng dụng React.js. | - Tài liệu `API_SPECIFICATION.md`.<br>- Khung project Backend + Frontend trên Git.<br>- Giao diện Layout tĩnh. |

---

### TUẦN 2: Phát triển lõi (Core Development)
| Thành viên | Mảng phụ trách | Công việc cụ thể | Sản phẩm bàn giao (Deliverables) |
| :--- | :--- | :--- | :--- |
| **Nguyễn Phi Lanh** | **Hardware & Firmware & AI** | - Vẽ PCB Layout trên KiCad và xuất file Gerber/lắp mạch thử nghiệm.<br>- Lập trình Firmware kết nối Wi-Fi, giao tiếp MQTT (Publish/Subscribe).<br>- Huấn luyện (Train) mô hình AI và đánh giá độ chính xác (Accuracy/F1). | - File PCB (`.kicad_pcb`).<br>- Firmware gửi/nhận JSON qua MQTT.<br>- File trọng số mô hình AI (`.onnx` / `.pt` / `.pkl`). |
| **Lê Công Quốc Anh** | **Backend, Frontend & Web** | - Xây dựng RESTful API (Auth, Device, Sensor History, Alert Logs).<br>- Viết dịch vụ lắng nghe MQTT tại Backend để lưu DB và đẩy qua Socket.IO.<br>- Xây dựng các trang Dashboard, Biểu đồ thời gian thực và nút điều khiển. | - Backend API hoàn chỉnh.<br>- Web Dashboard hiển thị biểu đồ động. |

---

### TUẦN 3: Tích hợp hệ thống (System Integration) & Tối ưu hóa
| Thành viên | Mảng phụ trách | Công việc cụ thể | Sản phẩm bàn giao (Deliverables) |
| :--- | :--- | :--- | :--- |
| **Nguyễn Phi Lanh** | **Hardware & Firmware & AI** | - Hàn mạch hoàn chỉnh, đo kiểm nguồn và tín hiệu thực tế.<br>- Đóng gói AI Engine thành dịch vụ chạy thời gian thực, kết nối vào luồng MQTT/API.<br>- Tối ưu Firmware: xử lý chống nhiễu cảm biến, Non-blocking code, Auto-reconnect. | - Mạch phần cứng hoạt động ổn định.<br>- Dịch vụ AI tự động đẩy cảnh báo về Server.<br>- Firmware v1.0 ổn định. |
| **Lê Công Quốc Anh** | **Backend, Frontend & Web** | - Kết nối toàn diện Frontend <-> Backend <-> Thiết bị & AI Engine.<br>- Xây dựng giao diện hiển thị cảnh báo AI thời gian thực (Popup, âm báo, lịch sử).<br>- Tối ưu hiệu năng truy vấn Database và bảo mật API (JWT, CORS). | - Hệ thống Web chạy thông suốt End-to-End.<br>- Module quản lý cảnh báo AI trên Web. |

---

### TUẦN 4: Kiểm thử (Testing), Đóng gói & Triển khai thực tế
| Thành viên | Mảng phụ trách | Công việc cụ thể | Sản phẩm bàn giao (Deliverables) |
| :--- | :--- | :--- | :--- |
| **Nguyễn Phi Lanh** | **Hardware & Firmware & AI** | - Kiểm thử độ bền phần cứng và Firmware liên tục 24/7 (Stress Test).<br>- Tinh chỉnh ngưỡng (Threshold) của mô hình AI để giảm cảnh báo giả (False Positive).<br>- Hoàn thiện tài liệu kỹ thuật phần cứng và AI. | - Báo cáo kiểm thử phần cứng & AI.<br>- Bộ mã nguồn Firmware/AI/KiCad hoàn chỉnh. |
| **Lê Công Quốc Anh** | **Backend, Frontend & Web** | - Đóng gói Docker (`Dockerfile`, `docker-compose.yml`) cho Backend & Web.<br>- Triển khai hệ thống Web lên Cloud/VPS và kiểm thử tải (Load testing).<br>- Hoàn thiện tài liệu hướng dẫn sử dụng và tổng hợp toàn bộ Repository. | - Hệ thống Web hoạt động trực tuyến.<br>- Tài liệu hướng dẫn triển khai & Báo cáo tổng kết. |
