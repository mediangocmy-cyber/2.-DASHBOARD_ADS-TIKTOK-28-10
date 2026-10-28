# Dashboard TikTok Shop Ngọc Mỹ

## Chạy trên máy tính
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Streamlit Cloud
Đưa `streamlit_app.py` và `requirements.txt` lên repository GitHub, chọn `streamlit_app.py` làm main file trong Streamlit Cloud.

## Dữ liệu tải lên
- Campaign overview data `.xlsx`: theo ngày, là nguồn chuẩn cho tổng chi phí/doanh thu Ads.
- Product campaign data `.xlsx`: chiến dịch.
- Product data `.xlsx`: sản phẩm và SKU ID.
- Creative data `.xlsx`: video và thẻ sản phẩm.
- Tất cả đơn hàng `.csv`: xuất từ TikTok Shop, có Order ID, SKU ID, trạng thái và giá trị đơn.

**Chú ý:** ROAS sau điều chỉnh = tổng giá trị đơn hàng chưa hủy (hoặc đã giao, theo lựa chọn) / tổng chi phí Ads, chỉ là chỉ số tham khảo nếu chưa có liên kết Order ID → quảng cáo. Đơn hàng CSV có thể bao gồm đơn tự nhiên. Không cộng tổng doanh thu các file Ads với nhau. Đối với đơn nhiều SKU, Order Amount chỉ được cộng một lần theo Order ID.
