# Cấu trúc dự án AquaPass

```text
aquapass/
├── frontend/                       # Phú phụ trách
│   ├── public/                     # Hình ảnh và tài nguyên tĩnh
│   ├── src/
│   │   ├── app/
│   │   │   ├── incidents/         # Trang sự cố và quyết định đang chờ
│   │   │   └── requests/          # Trang yêu cầu thu thập bằng chứng
│   │   ├── components/
│   │   │   ├── decision/          # Thẻ quyết định và màn hình trước/sau
│   │   │   ├── evidence/          # Evidence Graph và trạng thái bằng chứng
│   │   │   ├── requests/          # Form tạo, duyệt và theo dõi yêu cầu
│   │   │   ├── timeline/          # Dòng thời gian yêu cầu và quyết định
│   │   │   └── ui/                # Nút, hộp thoại và component dùng chung
│   │   ├── hooks/                 # Logic React dùng lại nhiều nơi
│   │   ├── lib/                   # Hàm hỗ trợ frontend
│   │   ├── services/              # Nơi gọi API backend
│   │   ├── styles/                # CSS và thiết kế chung
│   │   └── types/                 # Kiểu dữ liệu dùng ở frontend
│   └── tests/                     # Kiểm thử frontend
│
├── backend/                        # Quân và Sang cùng làm
│   ├── app/
│   │   ├── api/routes/            # Các đường dẫn API
│   │   ├── core/                  # Cấu hình chung và biến môi trường
│   │   ├── db/                    # Kết nối và khởi tạo database
│   │   ├── models/                # Các bảng trong database
│   │   ├── schemas/               # Mẫu dữ liệu gửi vào và trả ra
│   │   ├── services/              # Nối các module với nhau
│   │   └── modules/
│   │       ├── incident/          # Quân: quản lý sự cố
│   │       ├── decision/          # Quân: quyết định và các phiên bản
│   │       ├── orchestration/     # Quân: vòng đời yêu cầu
│   │       ├── fhir/              # Quân: ServiceRequest, Task, Observation
│   │       ├── audit/             # Quân: lưu lịch sử hoạt động
│   │       ├── actors/            # Quân: đội hiện trường và hệ thống nhận việc
│   │       ├── evidence/          # Sang: bằng chứng và Evidence Graph
│   │       ├── ranking/           # Sang: tính điểm và xếp hạng
│   │       ├── constraints/       # Sang: chi phí, thời gian và nguồn lực
│   │       └── ai/                # Sang: tìm khoảng trống và giải thích
│   └── tests/                     # Kiểm thử API và luồng đầy đủ
│
├── data/                           # Sang phụ trách chính
│   ├── demo/                      # Dữ liệu cá chết dùng trong video demo
│   ├── fixtures/                  # Dữ liệu cố định dùng để kiểm thử
│   └── evaluation/                # Gold set và kết quả đánh giá ranking
│
├── docs/
│   ├── architecture/              # Sơ đồ kiến trúc và database
│   ├── api/                       # Tài liệu API
│   ├── fhir/                      # Tài liệu ánh xạ FHIR
│   └── demo/                      # Kịch bản demo và video
│
├── infra/
│   └── docker/                    # Docker cho frontend, backend và database
├── scripts/                        # Lệnh tạo dữ liệu, reset và chạy demo
├── .github/workflows/              # Kiểm tra code tự động
├── .env.example                    # Danh sách biến môi trường mẫu
├── .gitignore                      # Những file không đưa lên GitHub
└── README.md                       # Giới thiệu dự án
```

## Quy tắc để không giẫm code nhau

- Phú chỉ làm trong `frontend/` và chỉ đọc cấu trúc API từ `docs/api/`.
- Quân quản lý database, API, FHIR và các module điều phối ở backend.
- Sang quản lý `data/` và các module `evidence`, `ranking`, `constraints`, `ai`.
- Khi cần đổi cấu trúc dữ liệu chung, cả nhóm phải chốt trước rồi mới sửa `models/` và `schemas/`.

