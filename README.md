# Xây dựng và phát triển website bán laptop N19.VN

### Mô tả dự án:
## Giới thiệu
LapTopShop là hệ thống thương mại điện tử chuyên bán laptop, được xây dựng theo kiến trúc MERN Stack (MongoDB, Express, React, Node.js). Dự án bao gồm một cổng mua sắm dành cho người dùng cuối và một trang quản trị nội bộ, cùng với chatbot AI được fine-tune riêng trên dữ liệu sản phẩm để tư vấn khách hàng theo thời gian thực.

Tính năng nổi bật
🛒 Phía người dùng (Customer)

        Đăng ký / Đăng nhập (Email + Google OAuth2)
        Xác thực tài khoản qua email, đặt lại mật khẩu
        Trang chủ với banner slider, danh sách sản phẩm nổi bật
        Tìm kiếm & lọc nâng cao (theo hãng, giá, cấu hình, ...)
        Trang chi tiết sản phẩm, so sánh sản phẩm
        Giỏ hàng, nhập địa chỉ giao hàng
        Thanh toán: COD, PayPal, VNPay, Số dư tài khoản
        Quản lý đơn hàng cá nhân
        Đánh giá & bình luận sản phẩm
        AI Chatbot tư vấn sản phẩm

🛠️ Phía quản trị (Admin)

        Dashboard thống kê doanh thu, đơn hàng, sản phẩm
        Quản lý sản phẩm (thêm / sửa / xoá, upload ảnh Cloudinary)
        Quản lý danh mục & thương hiệu
        Quản lý phiếu nhập kho
        Quản lý đơn hàng & xử lý trạng thái
        Quản lý người dùng
        Xem & phản hồi đánh giá
        Trang quản lý địa điểm giao hàng

## Cấu trúc thư mục
Ecommerce-Fe-master/
├── public/                    # Static assets (ảnh, banner, logo)
│   └── images/
│       └── laptops/           # Ảnh sản phẩm mẫu
├── src/
│   ├── api/                   # Cấu hình Axios + các hàm gọi API
│   │   ├── axiosClient.js     # Axios instance + interceptors
│   │   ├── userApi.js
│   │   ├── productApi.js
│   │   ├── orderApi.js
│   │   ├── reviewApi.js
│   │   ├── commentApi.js
│   │   └── chatApi.js
│   ├── components/            # Các component dùng chung
│   │   ├── header/
│   │   ├── footer/
│   │   ├── navbar/
│   │   └── Chatbot/
│   ├── module/                # Các module theo chức năng
│   │   ├── cart/              # Giỏ hàng
│   │   ├── dashboard/         # Layout trang tài khoản (sidebar)
│   │   ├── feedback/          # Đánh giá & nhận xét
│   │   ├── filter/            # Lọc sản phẩm
│   │   ├── payment/           # Thanh toán
│   │   ├── product/           # Hiển thị sản phẩm
│   │   └── UserProfile/       # Quản lý tài khoản
│   ├── page/                  # Các trang chính (route level)
│   │   ├── HomePage.jsx
│   │   ├── ProductFilterPage.jsx
│   │   ├── ProductDetail.jsx
│   │   ├── SignInPage.jsx
│   │   ├── SignUpPage.jsx
│   │   ├── VerifyPage.jsx
│   │   ├── ForgotPasswordPage.jsx
│   │   ├── ResetPasswordPage.jsx
│   │   └── NotFoundPage.jsx
│   ├── redux/                 # Redux store & slices
│   │   ├── auth/              # userSlice, addressSlice
│   │   ├── cart/              # cartSlice
│   │   ├── feedback/          # feedbackSlice, commentSlice
│   │   ├── order/             # orderSlice
│   │   ├── product/           # productSlice
│   │   └── store.js
│   ├── styles/                # File SCSS/CSS toàn cục
│   ├── utils/                 # Hàm tiện ích & hằng số
│   │   ├── constants/         # key.js, status.js, storage-keys.js
│   │   ├── formatPrice.js
│   │   └── calculateScore.js
│   └── App.jsx                # Route chính của ứng dụng
├── index.html
├── vite.config.js
├── tailwind.config.cjs
└── package.json
## Hướng dẫn cài đặt
1. Clone repository
- git clone <https://github.com/vandat-snk/N19-TTCS-LapTopShop.git>
- `cd Ecommerce-Fe-master`
2. Cài đặt dependencies
`npm install`
3. Tạo file môi trường
Tạo file .env ở thư mục gốc (xem phần Biến môi trường).
4. Chạy ở chế độ development
`npm run dev`
Ứng dụng sẽ chạy tại http://localhost:5173
## Biến môi trường
Tạo file .env tại thư mục gốc với nội dung sau:

        VITE_API_URL=http://127.0.0.1:5000
        VITE_PAYPAL_CLIENT_ID=your_paypal_client_id

        VITE_FIREBASE_API_KEY=your_firebase_api_key
        VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
        VITE_FIREBASE_PROJECT_ID=your_project_id

        VITE_STREAM_API_KEY=your_stream_api_key

## Các trang chính
/                              # Trang chủ
├── sign-in                    # Đăng nhập
├── sign-up                    # Đăng ký
├── verify                     # Xác thực email
├── forgot-password            # Quên mật khẩu
├── reset-password/:token      # Đặt lại mật khẩu
├── product                    # Danh sách & lọc sản phẩm
├── :slug/:id                  # Chi tiết sản phẩm
├── cart                       # Giỏ hàng
├── checkout                   # Trang thanh toán
└── account                    # Thông tin tài khoản
    ├── orders                 # Lịch sử đơn hàng
    │   └── :id                # Chi tiết đơn hàng
    ├── address                # Quản lý địa chỉ
    └── reset-password         # Cập nhật mật khẩu
### Kết quả đạt được
#### Trang chủ
![Trang chủ](https://res.cloudinary.com/davolb88z/image/upload/v1779631898/TrangChu_h8fh5l.jpg)
#### Trang đăng nhập
![Trang đăng nhập](https://res.cloudinary.com/davolb88z/image/upload/v1779631642/TrangDangNhap_ihnlbd.jpg)
#### Trang quên mật khẩu
![Trang quên mật khẩu](https://res.cloudinary.com/davolb88z/image/upload/v1779632086/DoiMatKhau_cuhydj.jpg)
#### Trang thông tin tài khoản
![Trang thông tin tài khoản](https://res.cloudinary.com/davolb88z/image/upload/v1779632124/ThongTinTaiKhoan_aekgfc.jpg)
#### Trang đăng nhập cho Admin
![Trang đăng nhập](https://res.cloudinary.com/davolb88z/image/upload/v1779632243/TrangDangNhap_dfehzy.jpg)
#### Trang chủ cho Admin
![Trang chủ](https://res.cloudinary.com/davolb88z/image/upload/v1779632300/TrangChu_eqli2y.jpg)
#### Trang quản lý danh mục cho Admin
![danh mục](https://res.cloudinary.com/davolb88z/image/upload/v1779632981/ThuongHieu_l87u0n.jpg)
#### Trang quản lý phiếu nhập cho Admin
![Phiếu nhập](https://res.cloudinary.com/davolb88z/image/upload/v1779633134/PhieuNhap_sx439k.jpg)
#### Trang quản lý chi tiêu phiếu nhập cho Admin
![Chi tiet phiếu nhập](https://res.cloudinary.com/davolb88z/image/upload/v1779639262/ChiTietPhieuNhap_q2gpct.jpg)
#### Trang quản lý đơn hàng
![Trang quản lý đơn hàng](https://res.cloudinary.com/davolb88z/image/upload/v1779632347/QuanLyDonHang_pkd5aq.jpg)
#### Trang chi tiết đơn hàng
![Trang chi tiết đơn hàng](https://res.cloudinary.com/davolb88z/image/upload/v1779632391/ChiTietDonHang_yi1rj6.jpg)
#### Trang quản lý thông tin giao nhận hàng
![Trang quản lý thông tin giao nhận hàng](https://res.cloudinary.com/davolb88z/image/upload/v1779632497/NhapDiaChi_fczzqt.jpg)
#### Trang lọc sản phẩm nâng cao
![Trang lọc sản phẩm nâng cao](https://res.cloudinary.com/davolb88z/image/upload/v1779632564/TimKiemNangCao_xm0ldp.jpg)
#### Trang giỏ hàng
![Trang giỏ hàng](https://res.cloudinary.com/davolb88z/image/upload/v1779632664/GioHang_dlt3ze.jpg)
#### Chức năng đánh giá sao và nhận xét
![Đánh giá sao và nhận xét](https://res.cloudinary.com/davolb88z/image/upload/v1779632697/DanhGia_sfdc78.jpg)
#### Chức năng thanh toán
![thanh toán](https://res.cloudinary.com/davolb88z/image/upload/v1779632773/ThanhToan_rs5u5x.jpg)
#### Chức năng so sánh thông số giữa 2 sản phẩm
![so sánh](https://res.cloudinary.com/davolb88z/image/upload/v1779632853/SoSanh_rdlpf1.jpg)
#### Chức năng tìm kiếm
![so sánh](https://res.cloudinary.com/davolb88z/image/upload/v1779632893/TimKiem_r5krwi.jpg)


