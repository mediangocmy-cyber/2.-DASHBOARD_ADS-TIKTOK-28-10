import io, re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title='Ngọc Mỹ | TikTok Ads',page_icon='📊',layout='wide')
st.markdown('''<style>.block-container{padding-top:1.5rem;max-width:1500px}div[data-testid="stMetric"]{background:#f5f7fb;border:1px solid #e6eaf0;padding:14px;border-radius:14px}h1,h2,h3{letter-spacing:-.025em} .stAlert{border-radius:12px}</style>''',unsafe_allow_html=True)

def read_xlsx(file):
    return pd.read_excel(file,dtype={'ID chiến dịch':str,'ID sản phẩm':str,'ID bài đăng':str})

def read_orders(file):
    b=file.getvalue()
    for enc in ('utf-8-sig','utf-16','cp1258'):
        try:return pd.read_csv(io.BytesIO(b),encoding=enc,dtype=str,sep=None,engine='python')
        except (UnicodeError,ValueError):pass
    raise ValueError('Không đọc được file CSV')

def num(s):
    return pd.to_numeric(s.astype(str).str.replace(',','',regex=False).str.replace('₫','',regex=False).str.strip().replace({'-':None,'':None,'nan':None}),errors='coerce').fillna(0)

def clean_id(s):return s.astype(str).str.replace(r'\D','',regex=True)
def vnd(v):return f'{v:,.0f}đ'.replace(',','.')
def ratio(n,d):return n/d if d>0 else np.nan
def show_roas(v):return f'{v:.2f}' if pd.notna(v) else '—'

def find_col(df,options):
    for c in options:
        if c in df.columns:return c
    return None

st.title('📊 TikTok Shop | Hiệu quả Ads & đối soát đơn hủy')
st.caption('GMV Max • ROAS = Doanh thu / Chi phí Ads • Không cộng doanh thu từ nhiều cấp báo cáo')
with st.sidebar:
    st.header('1. Tải dữ liệu')
    overview_file=st.file_uploader('Campaign overview (.xlsx)',type=['xlsx'],key='overview')
    campaign_file=st.file_uploader('Product campaign (.xlsx)',type=['xlsx'],key='campaign')
    product_file=st.file_uploader('Product data (.xlsx)',type=['xlsx'],key='product')
    creative_file=st.file_uploader('Creative data (.xlsx)',type=['xlsx'],key='creative')
    order_file=st.file_uploader('Tất cả đơn hàng (.csv)',type=['csv'],key='orders')
    st.divider()
    st.header('2. Thiết lập')
    include_pending=st.toggle('Tính đơn chưa hủy nhưng chưa giao',value=True,help='Nếu tắt, chỉ tính đơn đã giao. Cả hai cách đều không phải doanh thu Ads được TikTok xác nhận.')
    st.caption('Tải từng tệp độc lập. Dashboard sẽ hiển thị những phần đủ dữ liệu.')

frames={}
for key,file,reader in [('overview',overview_file,read_xlsx),('campaign',campaign_file,read_xlsx),('product',product_file,read_xlsx),('creative',creative_file,read_xlsx),('orders',order_file,read_orders)]:
    if file is not None:
        try:frames[key]=reader(file)
        except Exception as e:st.error(f'Lỗi đọc {key}: {e}')
if not frames:
    st.info('Hãy tải các tệp xuất từ TikTok Ads và tệp đơn hàng ở thanh bên trái. Có thể tải 1–5 tệp, nhưng cần Campaign overview + CSV đơn hàng để tính ROAS điều chỉnh tham khảo.')
    st.stop()

ov=frames.get('overview');camp=frames.get('campaign');prod=frames.get('product');creative=frames.get('creative');orders=frames.get('orders')
if ov is not None:
    ov=ov.copy();ov['Chi phí']=num(ov['Chi phí']);ov['Doanh thu gộp (Cửa hàng hiện tại)']=num(ov['Doanh thu gộp (Cửa hàng hiện tại)']);ov['Theo ngày']=pd.to_datetime(ov['Theo ngày'],errors='coerce');ov=ov[ov['Theo ngày'].notna()]
if camp is not None:
    camp=camp.copy();camp['Chi phí']=num(camp['Chi phí']);camp['Doanh thu gộp']=num(camp['Doanh thu gộp']);camp['Số lượng đơn hàng SKU']=num(camp['Số lượng đơn hàng SKU']);camp['ID chiến dịch']=clean_id(camp['ID chiến dịch']);camp['ROAS tính lại']=camp.apply(lambda r:ratio(r['Doanh thu gộp'],r['Chi phí']),axis=1)
if prod is not None:
    prod=prod.copy();prod['Chi phí']=num(prod['Chi phí']);prod['Doanh thu gộp']=num(prod['Doanh thu gộp']);prod['Số lượng đơn hàng SKU']=num(prod['Số lượng đơn hàng SKU']);prod['ID sản phẩm']=clean_id(prod['ID sản phẩm']);prod['ID chiến dịch']=clean_id(prod['ID chiến dịch']);prod['ROAS tính lại']=prod.apply(lambda r:ratio(r['Doanh thu gộp'],r['Chi phí']),axis=1)
if creative is not None:
    creative=creative.copy()
    for c in ['Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','Số lượt hiển thị quảng cáo sản phẩm','Số lượt nhấp vào quảng cáo sản phẩm']:
        if c in creative:creative[c]=num(creative[c])
if orders is not None:
    orders=orders.copy()
    needed=['Order ID','Order Status','SKU ID','Order Amount','Product Name']
    missing=[c for c in needed if c not in orders]
    if missing:
        st.error('CSV thiếu cột: '+', '.join(missing));orders=None
    else:
        orders['Order ID']=clean_id(orders['Order ID']);orders['SKU ID']=clean_id(orders['SKU ID'])
        orders['Order Amount']=num(orders['Order Amount']);orders['Quantity']=num(orders['Quantity']) if 'Quantity' in orders else 1
        orders['Đã hủy']=orders['Order Status'].astype(str).str.contains('hủy|cancel',case=False,regex=True,na=False)
        orders['Đã giao']=orders['Order Status'].astype(str).str.contains('đã giao|delivered|completed|hoàn thành',case=False,regex=True,na=False)
        orders['Hợp lệ theo lựa chọn']=(~orders['Đã hủy']) & (True if include_pending else orders['Đã giao'])
        orders['Ngày tạo']=pd.to_datetime(orders['Created Time'].astype(str).str.strip() if 'Created Time' in orders else pd.Series(dtype=str),dayfirst=True,errors='coerce')
        # Order Amount is repeated on multi-line orders; count it only once per Order ID.
        order_level=orders.groupby('Order ID',as_index=False).agg({'Order Amount':'max','Đã hủy':'max','Đã giao':'max','Hợp lệ theo lựa chọn':'max','Ngày tạo':'min'})
        # If a multi-line order contains mixed statuses, avoid treating it as fully retained.
        order_level['Hợp lệ theo lựa chọn']=(~order_level['Đã hủy']) & (True if include_pending else order_level['Đã giao'])
        order_level['Doanh thu giữ lại']=np.where(order_level['Hợp lệ theo lựa chọn'],order_level['Order Amount'],0)

st.markdown('### Điều hướng báo cáo')
tabs=st.tabs(['🏠 Tổng quan','📅 Theo ngày','📦 Đơn hàng','🎯 Chiến dịch','🧴 Sản phẩm','🎬 Creative','🔍 Đối soát','🎥 Phân tích Video','🛍️ Phân tích Thẻ sản phẩm'])

with tabs[0]:
    st.subheader('01 / Tổng quan')
    spend=float(ov['Chi phí'].sum()) if ov is not None else float(camp['Chi phí'].sum()) if camp is not None else float(prod['Chi phí'].sum()) if prod is not None else np.nan
    ads_revenue=float(ov['Doanh thu gộp (Cửa hàng hiện tại)'].sum()) if ov is not None else float(camp['Doanh thu gộp'].sum()) if camp is not None else float(prod['Doanh thu gộp'].sum()) if prod is not None else np.nan
    retained=float(order_level['Doanh thu giữ lại'].sum()) if orders is not None else np.nan
    cancel_value=float(order_level.loc[order_level['Đã hủy'],'Order Amount'].sum()) if orders is not None else np.nan
    cols=st.columns(4)
    cols[0].metric('Chi phí Ads',vnd(spend) if pd.notna(spend) else '—')
    cols[1].metric('Doanh thu Ads báo cáo',vnd(ads_revenue) if pd.notna(ads_revenue) else '—')
    cols[2].metric('ROAS Ads báo cáo',show_roas(ratio(ads_revenue,spend)))
    cols[3].metric('ROAS điều chỉnh tham khảo',show_roas(ratio(retained,spend)))
    if orders is not None:
        c=st.columns(4)
        c[0].metric('Số đơn (không trùng)',len(order_level))
        c[1].metric('Đơn hủy',int(order_level['Đã hủy'].sum()))
        c[2].metric('Tỷ lệ hủy',f"{order_level['Đã hủy'].mean():.1%}")
        c[3].metric('Giá trị đơn hủy',vnd(cancel_value))
        st.caption(f"Doanh thu đơn hàng theo trạng thái đã chọn: {vnd(retained)}. Tổng giá trị đơn hàng CSV: {vnd(order_level['Order Amount'].sum())}.")
        if pd.notna(ads_revenue):
            delta=ads_revenue-order_level['Order Amount'].sum()
            if abs(delta)>0.01:st.warning(f'Chênh lệch giữa doanh thu Ads và tổng giá trị đơn CSV: {vnd(delta)}. Hai nguồn có thể khác phạm vi, giá trị khuyến mãi hoặc thời điểm ghi nhận. ROAS điều chỉnh là chỉ số THAM KHẢO, không phải ROAS Ads được đối soát theo từng đơn.')
        st.info('Đơn không hủy chưa chắc đã giao/thanh toán thành công. Doanh thu CSV không đồng nghĩa toàn bộ là doanh thu được quy cho Ads. Nếu chưa có mã đơn liên kết với quảng cáo, không thể xác định ROAS Ads sau hủy chính xác.')



with tabs[1]:
    if ov is not None:
        st.subheader('02 / Hiệu quả theo ngày')
        day=ov.groupby('Theo ngày',as_index=False)[['Chi phí','Doanh thu gộp (Cửa hàng hiện tại)']].sum().sort_values('Theo ngày')
        day['ROAS']=day.apply(lambda r:ratio(r['Doanh thu gộp (Cửa hàng hiện tại)'],r['Chi phí']),axis=1)
        fig=px.bar(day.melt('Theo ngày',value_vars=['Chi phí','Doanh thu gộp (Cửa hàng hiện tại)'],var_name='Chỉ tiêu',value_name='VND'),x='Theo ngày',y='VND',color='Chỉ tiêu',barmode='group',color_discrete_sequence=['#64748b','#2563eb'])
        fig.update_layout(margin=dict(l=0,r=0,t=10,b=0),legend_title_text='')
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(day.rename(columns={'Theo ngày':'Ngày','Doanh thu gộp (Cửa hàng hiện tại)':'Doanh thu Ads'}).style.format({'Chi phí':vnd,'Doanh thu Ads':vnd,'ROAS':show_roas}),use_container_width=True,hide_index=True)



with tabs[2]:
    if orders is not None:
        st.subheader('03 / Đơn hàng và hủy đơn')
        a,b=st.columns([1,2])
        with a:
            fig=px.pie(names=['Hủy','Không hủy'],values=[int(order_level['Đã hủy'].sum()),int((~order_level['Đã hủy']).sum())],hole=.62,color_discrete_sequence=['#ef4444','#22c55e']);fig.update_layout(margin=dict(l=0,r=0,t=10,b=0));st.plotly_chart(fig,use_container_width=True)
        with b:
            view_cols=[c for c in ['Order ID','Created Time','Product Name','SKU ID','Order Status','Order Substatus','Order Amount','Cancel Reason','Cancellation Reason','Cancelled Time'] if c in orders.columns]
            st.dataframe(orders[view_cols],use_container_width=True,hide_index=True)
        st.download_button('Tải CSV đơn hàng đã chuẩn hóa',orders.to_csv(index=False,encoding='utf-8-sig').encode('utf-8-sig'),file_name='don_hang_chuan_hoa.csv',mime='text/csv')



with tabs[3]:
    if camp is not None:
        st.subheader('04 / Chiến dịch GMV Max')
        cv=camp[['ID chiến dịch','Tên chiến dịch','Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','ROAS tính lại']].copy()
        st.dataframe(cv.style.format({'Chi phí':vnd,'Doanh thu gộp':vnd,'ROAS tính lại':show_roas}),hide_index=True,use_container_width=True)
        fig=px.bar(camp.sort_values('Chi phí',ascending=True),x='Chi phí',y='Tên chiến dịch',orientation='h',color='Doanh thu gộp',color_continuous_scale='Blues');fig.update_layout(height=max(350,len(camp)*48),margin=dict(l=0,r=0,t=15,b=0));st.plotly_chart(fig,use_container_width=True)



with tabs[4]:
    if prod is not None:
        st.subheader('05 / Sản phẩm & đối chiếu đơn hủy theo SKU')
        p=prod.copy()
        if orders is not None:
            # SKU-level monetary allocation only safe for single-SKU orders.
            sk=orders.groupby('SKU ID',as_index=False).agg(so_dong=('Order ID','size'),so_don=('Order ID','nunique'),so_don_huy=('Đã hủy','sum'),so_dong_khong_huy=('Hợp lệ theo lựa chọn','sum'))
            p=p.merge(sk,how='left',left_on='ID sản phẩm',right_on='SKU ID')
            p['so_don_huy']=p['so_don_huy'].fillna(0).astype(int)
            p['so_don']=p['so_don'].fillna(0).astype(int)
            p['Đánh giá']=np.select([p['so_don_huy']>0,p['Số lượng đơn hàng SKU']<=0],['Có đơn hủy — cần kiểm tra','Chưa ghi nhận chuyển đổi'],default='Có đơn — kiểm tra lợi nhuận')
        else:p['Đánh giá']=np.where(p['Số lượng đơn hàng SKU']>0,'Có chuyển đổi (chưa đối chiếu hủy)','Chưa ghi nhận chuyển đổi')
        st.dataframe(p[[c for c in ['Tên sản phẩm','ID sản phẩm','Tên chiến dịch','Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','ROAS tính lại','so_don','so_don_huy','Đánh giá'] if c in p]].style.format({'Chi phí':vnd,'Doanh thu gộp':vnd,'ROAS tính lại':show_roas}),hide_index=True,use_container_width=True)
        if orders is not None:
            missing_sku=set(orders['SKU ID'])-set(prod['ID sản phẩm'])
            if missing_sku:st.warning(f'{len(missing_sku)} SKU trong đơn hàng không khớp ID sản phẩm của báo cáo Ads. Không tự gán theo tên vì có thể sai.')
        st.download_button('Tải bảng đối chiếu sản phẩm',p.to_csv(index=False).encode('utf-8-sig'),file_name='doi_chieu_san_pham.csv',mime='text/csv')



with tabs[5]:
    if creative is not None:
        st.subheader('06 / Nội dung quảng cáo')
        types=creative['Loại nội dung sáng tạo'].dropna().unique().tolist() if 'Loại nội dung sáng tạo' in creative else []
        selected=st.multiselect('Loại nội dung',types,default=types)
        cr=creative[creative['Loại nội dung sáng tạo'].isin(selected)].copy() if types else creative.copy()
        if 'Chi phí' in cr:
            cr=cr.sort_values('Chi phí',ascending=False)
            st.metric('Chi phí trong báo cáo Creative (không cộng vào tổng Ads)',vnd(cr['Chi phí'].sum()))
        st.dataframe(cr[[c for c in ['ID bài đăng','Mẫu quảng cáo','Loại nội dung sáng tạo','Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','Số lượt hiển thị quảng cáo sản phẩm','Số lượt nhấp vào quảng cáo sản phẩm'] if c in cr]].head(100),hide_index=True,use_container_width=True)
        st.caption('Creative có thể ghi nhận doanh thu với chi phí 0đ do phân bổ/ghi nhận của nền tảng. Không xem ROAS cấp Creative là ROAS chiến dịch.')



with tabs[6]:
    st.subheader('07 / Kiểm tra chất lượng dữ liệu')
    checks=[]
    for name,df,sp,rev in [('Campaign overview',ov,'Chi phí','Doanh thu gộp (Cửa hàng hiện tại)'),('Product campaign',camp,'Chi phí','Doanh thu gộp'),('Product data',prod,'Chi phí','Doanh thu gộp'),('Creative data',creative,'Chi phí','Doanh thu gộp')]:
        if df is not None:checks.append({'Nguồn':name,'Số dòng':len(df),'Chi phí':df[sp].sum() if sp in df else np.nan,'Doanh thu':df[rev].sum() if rev in df else np.nan})
    if checks:st.dataframe(pd.DataFrame(checks).style.format({'Chi phí':vnd,'Doanh thu':vnd}),use_container_width=True,hide_index=True)
    st.caption('Nguồn chuẩn chi phí và doanh thu tổng quan: Campaign overview (nếu có). Các bảng chiến dịch, sản phẩm và Creative dùng để phân tích chi tiết, không cộng dồn. Dữ liệu đơn hàng chỉ tính một lần theo Order ID.')



# Phân tích theo phạm vi Creative; không cộng trùng dữ liệu Campaign/Order.
def prep_deep(df):
    if df is None:return None
    d=df.copy()
    for c in ['Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','Số lượt hiển thị quảng cáo sản phẩm','Số lượt nhấp vào quảng cáo sản phẩm']:
        d[c]=num(d[c]) if c in d else 0.0
    d['Nhóm nội dung']=d.get('Loại nội dung sáng tạo',pd.Series('',index=d.index)).fillna('').astype(str)
    d['CTR (%)']=np.where(d['Số lượt hiển thị quảng cáo sản phẩm']>0,100*d['Số lượt nhấp vào quảng cáo sản phẩm']/d['Số lượt hiển thị quảng cáo sản phẩm'],np.nan)
    d['ROAS']=np.where(d['Chi phí']>0,d['Doanh thu gộp']/d['Chi phí'],np.nan)
    d['SKU/Click (%)']=np.where(d['Số lượt nhấp vào quảng cáo sản phẩm']>0,100*d['Số lượng đơn hàng SKU']/d['Số lượt nhấp vào quảng cáo sản phẩm'],np.nan)
    return d

def pct_col(df,raw):
    if raw not in df:return pd.Series(np.nan,index=df.index)
    ss=df[raw].astype(str).str.strip(); marked=ss.str.contains('%',regex=False)
    val=pd.to_numeric(ss.str.replace('%','',regex=False).str.replace(',','.',regex=False),errors='coerce')
    return pd.Series(np.where(marked,val,np.where(val.abs()<=1,val*100,val)),index=df.index)

def comment_video(r,ctr_cut,ret_cut):
    ctr=r['CTR (%)']; ret=r['Xem 6s (%)']; sku=r['Số lượng đơn hàng SKU']; cost=r['Chi phí']; roas=r['ROAS']
    good=[]; weak=[]; hypotheses=[]
    if pd.notna(ret):
        (good if ret>=ret_cut else weak).append(f'Giữ chân 6 giây {ret:.2f}% '+('từ mức tham chiếu trở lên' if ret>=ret_cut else 'dưới mức tham chiếu'))
        if ret<ret_cut:hypotheses.append('Thử mở đầu bằng tình huống/vấn đề cụ thể; kiểm tra nhịp dựng và thông điệp 3–6 giây đầu')
    if pd.notna(ctr):
        (good if ctr>=ctr_cut else weak).append(f'CTR {ctr:.2f}% '+('từ mức tham chiếu trở lên' if ctr>=ctr_cut else 'dưới mức tham chiếu'))
        if ctr<ctr_cut:hypotheses.append('Kiểm tra lợi ích mua hàng, cách thể hiện sản phẩm và CTA dẫn đến trang mua')
    if sku>0:good.append(f'Có {sku:g} SKU quy thuộc trong báo cáo Creative')
    elif cost>0:
        weak.append(f'Đã tiêu {vnd(cost)} nhưng chưa ghi nhận SKU')
        hypotheses.append('Kiểm tra tính thuyết phục sau nhấp, giá/ưu đãi và thông tin trang sản phẩm')
    if pd.notna(roas) and roas<1:weak.append(f'Doanh thu quy thuộc thấp hơn chi phí (ROAS {roas:.2f})')
    if pd.isna(ctr) or pd.isna(ret):hypotheses.append('Thiếu CTR hoặc tỷ lệ xem 6 giây: chưa thể phân loại đủ hai chiều')
    if not hypotheses:hypotheses.append('Giữ hướng nội dung hiện tại để thử nghiệm thêm; kiểm tra đơn hủy và chất lượng chuyển đổi trước khi mở rộng')
    return ' • '.join(good) or 'Chưa có tín hiệu tích cực đủ rõ', ' • '.join(weak) or 'Chưa phát hiện điểm yếu rõ từ các chỉ số có sẵn', ' • '.join(dict.fromkeys(hypotheses))

def comment_card(r,ctr_cut):
    good=[];weak=[];hyp=[]
    if pd.notna(r['CTR (%)']):
        (good if r['CTR (%)']>=ctr_cut else weak).append(f'CTR {r["CTR (%)"]:.2f}% '+('từ mức tham chiếu trở lên' if r['CTR (%)']>=ctr_cut else 'dưới mức tham chiếu'))
        if r['CTR (%)']<ctr_cut:hyp.append('Thử ảnh đại diện thể hiện rõ sản phẩm/lợi ích, rút gọn tên và làm rõ ưu đãi')
    if r['SKU']>0:good.append(f'Ghi nhận {r["SKU"]:g} SKU bán được')
    elif r['Chi phí']>0:
        weak.append(f'Tiêu {vnd(r["Chi phí"])} nhưng chưa ghi nhận SKU')
        hyp.append('Kiểm tra trang chi tiết, giá, đánh giá, phí vận chuyển và ưu đãi sau nhấp')
    if pd.notna(r['ROAS']):
        if r['ROAS']>=1:good.append(f'Doanh thu quy thuộc lớn hơn/ bằng chi phí Ads (ROAS {r["ROAS"]:.2f})')
        else:weak.append(f'Doanh thu thấp hơn chi phí Ads (ROAS {r["ROAS"]:.2f})')
    if r['Nhấp']>0 and r['SKU']==0:hyp.append('Có nhấp nhưng chưa mua: cần kiểm tra trải nghiệm trang sản phẩm thay vì chỉ sửa ảnh thẻ')
    if not hyp:hyp.append('Duy trì thử nghiệm có kiểm soát; đối soát đơn hủy và chi phí chuyển đổi trước khi tăng ngân sách')
    return ' • '.join(good) or 'Chưa có tín hiệu tích cực đủ rõ',' • '.join(weak) or 'Chưa phát hiện điểm yếu rõ từ các chỉ số có sẵn',' • '.join(dict.fromkeys(hyp))

deep=prep_deep(creative)
with tabs[7]:
    st.header('08 / Phân tích chuyên sâu VIDEO')
    st.caption('Phân tích riêng từng dòng video trong Creative • Giữ chân 6 giây và CTR có mẫu số khác nhau • Giả thuyết không phải kết luận về chất lượng hình ảnh/lời thoại')
    if deep is None:st.info('Hãy tải Creative data để xem phân tích video.')
    else:
        videos=deep[deep['Nhóm nội dung'].str.contains('video',case=False,na=False)].copy()
        if videos.empty:st.info('Không có video trong dữ liệu Creative.')
        else:
            videos['Xem 2s (%)']=pct_col(videos,'Tỷ lệ xem video quảng cáo trong 2 giây')
            videos['Xem 6s (%)']=pct_col(videos,'Tỷ lệ xem video quảng cáo trong 6 giây')
            videos['Mẫu quảng cáo']=videos.get('Mẫu quảng cáo',pd.Series('',index=videos.index)).fillna('').astype(str)
            videos['Tên sản phẩm']=videos.get('Tên sản phẩm',pd.Series('',index=videos.index)).fillna('').astype(str)
            c1,c2,c3,c4=st.columns(4)
            c1.metric('Chi phí video',vnd(videos['Chi phí'].sum()))
            c2.metric('CTR tổng hợp',f"{100*ratio(videos['Số lượt nhấp vào quảng cáo sản phẩm'].sum(),videos['Số lượt hiển thị quảng cáo sản phẩm'].sum()):.2f}%" if videos['Số lượt hiển thị quảng cáo sản phẩm'].sum() else '—')
            c3.metric('SKU quy thuộc',f"{videos['Số lượng đơn hàng SKU'].sum():g}")
            c4.metric('ROAS video',show_roas(ratio(videos['Doanh thu gộp'].sum(),videos['Chi phí'].sum())))
            valid=videos[(videos['Xem 6s (%)'].notna())&(videos['CTR (%)'].notna())].copy()
            st.subheader('Ma trận 4 vùng: giữ chân 6 giây × CTR')
            if valid.empty:st.warning('Không đủ dữ liệu giữ chân 6 giây và CTR để tạo ma trận.')
            else:
                base_ret=float(valid['Xem 6s (%)'].median());base_ctr=float(valid['CTR (%)'].median())
                l,r=st.columns(2)
                with l:ret_cut=st.number_input('Mốc giữ chân 6s (%)',min_value=0.0,max_value=100.0,value=round(base_ret,2),step=0.1,help='Mặc định là trung vị các video có dữ liệu; không phải tiêu chuẩn TikTok')
                with r:ctr_cut=st.number_input('Mốc CTR (%)',min_value=0.0,max_value=100.0,value=round(base_ctr,2),step=0.1,help='Mặc định là trung vị các video có dữ liệu; không phải tiêu chuẩn TikTok')
                def region(row):
                    return ('Giữ chân cao' if row['Xem 6s (%)']>=ret_cut else 'Giữ chân thấp')+' – '+('CTR cao' if row['CTR (%)']>=ctr_cut else 'CTR thấp')
                valid['Vùng']=valid.apply(region,axis=1)
                maxx=max(10.0,float(valid['Xem 6s (%)'].max())*1.13,ret_cut*1.15)
                maxy=max(2.0,float(valid['CTR (%)'].max())*1.13,ctr_cut*1.15)
                fig=go.Figure()
                blocks=[(0,ret_cut,0,ctr_cut,'#fee2e2','Giữ chân thấp / CTR thấp'),(ret_cut,maxx,0,ctr_cut,'#dbeafe','Giữ chân cao / CTR thấp'),(0,ret_cut,ctr_cut,maxy,'#fef3c7','Giữ chân thấp / CTR cao'),(ret_cut,maxx,ctr_cut,maxy,'#dcfce7','Giữ chân cao / CTR cao')]
                for x0,x1,y0,y1,color,name in blocks:
                    fig.add_shape(type='rect',x0=x0,x1=x1,y0=y0,y1=y1,fillcolor=color,opacity=.55,line_width=0,layer='below')
                    if x1>x0 and y1>y0:fig.add_annotation(x=(x0+x1)/2,y=(y0+y1)/2,text=name.replace(' / ','<br>'),showarrow=False,font=dict(size=12,color='#475569'),opacity=.8)
                fig.add_vline(x=ret_cut,line_dash='dash',line_color='#64748b')
                fig.add_hline(y=ctr_cut,line_dash='dash',line_color='#64748b')
                fig.add_trace(go.Scatter(x=valid['Xem 6s (%)'],y=valid['CTR (%)'],mode='markers',text=valid['Mẫu quảng cáo'],customdata=np.stack([valid['Chi phí'],valid['Số lượng đơn hàng SKU'],valid['ROAS'].fillna(-1)],axis=-1),marker=dict(size=np.clip(9+np.sqrt(valid['Chi phí'].clip(lower=0))/35,9,34),color=valid['Số lượng đơn hàng SKU'],colorscale='Blues',showscale=True,colorbar=dict(title='SKU'),line=dict(color='white',width=1)),hovertemplate='<b>%{text}</b><br>Xem 6s: %{x:.2f}%<br>CTR: %{y:.2f}%<br>Chi phí: %{customdata[0]:,.0f}đ<br>SKU: %{customdata[1]:.0f}<extra></extra>'))
                fig.update_layout(height=520,margin=dict(l=10,r=10,t=25,b=20),xaxis=dict(title='Giữ chân 6 giây (%)',range=[0,maxx]),yaxis=dict(title='CTR sản phẩm (%)',range=[0,maxy]),showlegend=False)
                st.plotly_chart(fig,use_container_width=True)
                st.caption('Đường chia dùng trung vị của tập video hiện tại hoặc mốc tự điều chỉnh. Kích thước chấm thể hiện chi phí; màu thể hiện SKU. Vùng cao/thấp chỉ mang tính tương đối, không phải chuẩn ngành.')
                count=valid['Vùng'].value_counts()
                for name,meaning in [('Giữ chân cao – CTR cao','Nội dung có tín hiệu giữ người xem và thúc đẩy nhấp; kiểm tra thêm SKU, chi phí và đơn hủy.'),('Giữ chân cao – CTR thấp','Nội dung giữ người xem nhưng chưa thúc đẩy nhấp; thử làm rõ giá trị mua và CTA.'),('Giữ chân thấp – CTR cao','Người xem có thể nhấp sớm; không kết luận video kém chỉ vì thời gian xem thấp.'),('Giữ chân thấp – CTR thấp','Ưu tiên kiểm tra hook, cấu trúc nội dung và lời mời nhấp.')]:
                    st.markdown(f'**{name} ({count.get(name,0)} video):** {meaning}')
            st.subheader('Đánh giá từng video: làm tốt – chưa tốt – giả thuyết')
            cut_ret=ret_cut if not valid.empty else 8.0
            cut_ctr=ctr_cut if not valid.empty else 1.0
            videos['Vùng']=videos.apply(lambda x:('Thiếu dữ liệu phân loại' if pd.isna(x['Xem 6s (%)']) or pd.isna(x['CTR (%)']) else ('Giữ chân cao' if x['Xem 6s (%)']>=cut_ret else 'Giữ chân thấp')+' – '+('CTR cao' if x['CTR (%)']>=cut_ctr else 'CTR thấp')),axis=1)
            notes=videos.apply(lambda x:comment_video(x,cut_ctr,cut_ret),axis=1)
            videos['Làm tốt']=[n[0] for n in notes];videos['Chưa tốt']=[n[1] for n in notes];videos['Giả thuyết / hướng kiểm chứng']=[n[2] for n in notes]
            show=videos.sort_values('Chi phí',ascending=False)
            show=show[['Mẫu quảng cáo','Tên sản phẩm','Vùng','Chi phí','Xem 2s (%)','Xem 6s (%)','CTR (%)','SKU/Click (%)','Số lượng đơn hàng SKU','ROAS','Làm tốt','Chưa tốt','Giả thuyết / hướng kiểm chứng']]
            st.dataframe(show,hide_index=True,use_container_width=True,column_config={'Chi phí':st.column_config.NumberColumn(format='%,.0f đ'),'CTR (%)':st.column_config.NumberColumn(format='%.2f'),'Xem 6s (%)':st.column_config.NumberColumn(format='%.2f'),'Xem 2s (%)':st.column_config.NumberColumn(format='%.2f'),'ROAS':st.column_config.NumberColumn(format='%.2f')})
            options=list(show.index)
            selected=st.selectbox('Xem nhận xét chi tiết một video',options,format_func=lambda idx:f'{str(videos.loc[idx,"Mẫu quảng cáo"])[:95]} · {vnd(videos.loc[idx,"Chi phí"])}')
            row=videos.loc[selected]
            st.markdown(f'**Video:** {row["Mẫu quảng cáo"]}  |  **Vùng:** {row["Vùng"]}')
            a,b=st.columns(2)
            with a:st.success('**Làm tốt:** '+row['Làm tốt'])
            with b:st.warning('**Chưa tốt:** '+row['Chưa tốt'])
            st.info('**Giả thuyết cần kiểm chứng:** '+row['Giả thuyết / hướng kiểm chứng'])
            st.download_button('Tải nhận xét từng video (.csv)',show.to_csv(index=False).encode('utf-8-sig'),file_name='phan_tich_tung_video.csv',mime='text/csv')

with tabs[8]:
    st.header('09 / Phân tích chuyên sâu THẺ SẢN PHẨM')
    st.caption('Mỗi sản phẩm có nhận xét riêng theo chi phí, CTR, nhấp, SKU và ROAS • Giả thuyết ảnh/giá/trang sản phẩm cần được xác minh bằng dữ liệu bổ sung')
    if deep is None:st.info('Hãy tải Creative data để xem phân tích thẻ sản phẩm.')
    else:
        cards=deep[deep['Nhóm nội dung'].str.contains('thẻ',case=False,na=False)].copy()
        if cards.empty:st.info('Không tìm thấy thẻ sản phẩm trong Creative data.')
        else:
            cards['Sản phẩm']=cards.get('Tên sản phẩm',pd.Series('Không rõ',index=cards.index)).fillna('Không rõ').astype(str)
            imp='Số lượt hiển thị quảng cáo sản phẩm';click='Số lượt nhấp vào quảng cáo sản phẩm'
            ct=cards.groupby('Sản phẩm',as_index=False).agg(**{'Chi phí':('Chi phí','sum'),'Doanh thu':('Doanh thu gộp','sum'),'SKU':('Số lượng đơn hàng SKU','sum'),'Hiển thị':(imp,'sum'),'Nhấp':(click,'sum')})
            ct['CTR (%)']=np.where(ct['Hiển thị']>0,100*ct['Nhấp']/ct['Hiển thị'],np.nan)
            ct['SKU/Click (%)']=np.where(ct['Nhấp']>0,100*ct['SKU']/ct['Nhấp'],np.nan)
            ct['ROAS']=np.where(ct['Chi phí']>0,ct['Doanh thu']/ct['Chi phí'],np.nan)
            a,b,c,d=st.columns(4)
            a.metric('Chi phí thẻ',vnd(ct['Chi phí'].sum()))
            b.metric('CTR thẻ tổng hợp',f"{100*ratio(ct['Nhấp'].sum(),ct['Hiển thị'].sum()):.2f}%" if ct['Hiển thị'].sum() else '—')
            c.metric('SKU quy thuộc',f"{ct['SKU'].sum():g}")
            d.metric('ROAS thẻ',show_roas(ratio(ct['Doanh thu'].sum(),ct['Chi phí'].sum())))
            default=float(ct.loc[ct['CTR (%)'].notna(),'CTR (%)'].median()) if ct['CTR (%)'].notna().any() else 1.0
            threshold=st.number_input('Mốc CTR tham chiếu cho từng thẻ (%)',0.0,100.0,round(default,2),0.1,help='Mặc định là trung vị CTR các thẻ trong dữ liệu; không phải tiêu chuẩn TikTok')
            notes=ct.apply(lambda r:comment_card(r,threshold),axis=1)
            ct['Làm tốt']=[x[0] for x in notes];ct['Chưa tốt']=[x[1] for x in notes];ct['Giả thuyết / hướng kiểm chứng']=[x[2] for x in notes]
            ct=ct.sort_values('Chi phí',ascending=False)
            st.subheader('Hiệu quả và nhận xét cho từng sản phẩm')
            st.dataframe(ct,hide_index=True,use_container_width=True)
            st.plotly_chart(px.bar(ct,x='Sản phẩm',y=['Chi phí','Doanh thu'],barmode='group',title='Chi phí và doanh thu quy thuộc theo thẻ sản phẩm'),use_container_width=True)
            selected=st.selectbox('Xem nhận xét chi tiết một thẻ sản phẩm',ct['Sản phẩm'].tolist())
            row=ct[ct['Sản phẩm']==selected].iloc[0]
            st.markdown(f'**{selected}** · Chi phí {vnd(row["Chi phí"])} · {row["Nhấp"]:g} nhấp · {row["SKU"]:g} SKU · ROAS {show_roas(row["ROAS"])}')
            a,b=st.columns(2)
            with a:st.success('**Làm tốt:** '+row['Làm tốt'])
            with b:st.warning('**Chưa tốt:** '+row['Chưa tốt'])
            st.info('**Giả thuyết cần kiểm chứng:** '+row['Giả thuyết / hướng kiểm chứng'])
            st.download_button('Tải nhận xét từng thẻ (.csv)',ct.to_csv(index=False).encode('utf-8-sig'),file_name='phan_tich_tung_the_san_pham.csv',mime='text/csv')
            st.caption('Không suy luận trực tiếp chất lượng ảnh, giá bán hay đánh giá người mua từ CTR/ROAS. Cần kiểm tra ảnh, trang chi tiết, giá và lịch sử ưu đãi để xác nhận.')
