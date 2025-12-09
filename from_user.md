# CÔNG NGHỆ PHẦN MỀM - KHOA CNTT, TRƯỜNG ĐẠI HỌC MỞ TP.HCM

# ĐỀ TÀI 1: QUẢN LÝ PHÒNG TẬP GYM

## Yêu cầu 1: Lễ tân lập danh sách hội viên
- Người dùng có thể đăng ký trực tuyến hoặc tại quầy.
- Thông tin: Họ tên, giới tính, năm sinh, số điện thoại, gói tập, ngày đăng ký.
- Mỗi gói tập có thời hạn (1 tháng, 3 tháng, 6 tháng, 12 tháng).
- Khi đăng ký thành công, gửi thông báo xác nhận qua email (gợi ý dùng SMTP).

---

## Yêu cầu 2: Huấn luyện viên lập lịch tập cho hội viên
- Mỗi hội viên có thể được gán huấn luyện viên cá nhân.
- Huấn luyện viên tạo kế hoạch tập luyện gồm: bài tập, số hiệp, số lần, lịch tập trong tuần.

### Ví dụ bảng lịch tập:

| STT | Bài tập | Số hiệp | Số lần/hiệp | Ngày tập      |
|----|---------|---------|-------------|----------------|
| 1  | Squat   | 3       | 15          | Thứ 2, 4, 6    |

---

## Yêu cầu 3: Bộ phận thu ngân quản lý thanh toán
- Mỗi hội viên có hóa đơn đăng ký gói tập.
- Gói tập có giá:
  - 1 tháng = 500.000đ
  - 3 tháng = 1.200.000đ
  - 6 tháng = 2.000.000đ
  - 12 tháng = 3.500.000đ
- Lưu lịch sử thanh toán của từng hội viên.

---

## Yêu cầu 4: Báo cáo, thống kê
- Thống kê số hội viên đang ký tập.
- Thống kê doanh thu theo tháng.
- Thống kê số hội viên theo từng gói (còn hạn).
- Hiển thị biểu đồ bằng Chart.js.

---

## Yêu cầu 5: Thay đổi quy định
- Quản trị viên có thể thay đổi giá gói tập.
- Cập nhật danh mục bài tập (thêm/sửa/xóa).
- Thay đổi số ngày tập tối đa/tuần.
