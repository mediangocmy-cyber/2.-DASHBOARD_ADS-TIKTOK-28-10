import io, re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

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
tabs=st.tabs(['🏠 Tổng quan','📅 Theo ngày','📦 Đơn hàng','🎯 Chiến dịch','🧴 Sản phẩm','🎬 Creative','🔍 Đối soát','📈 Phân tích chuyên sâu'])

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



with tabs[7]:
    # ─────────────────────────────────────────────────────────────────────────────
    # 09 / PHÂN TÍCH CHUYÊN SÂU CREATIVE: thẻ sản phẩm, video, nguyên nhân và giải pháp
    # ─────────────────────────────────────────────────────────────────────────────
    st.divider()
    st.header('09 / Phân tích chuyên sâu hiệu quả nội dung GMV Max')
    st.caption('Tự tính lại khi tải báo cáo mới • So sánh trong cùng phạm vi Creative • Nhận định nguyên nhân là giả thuyết cần kiểm chứng')
    if creative is None:
        st.info('Tải Creative data để kích hoạt phân tích chuyên sâu thẻ sản phẩm và video. Thêm CSV đơn hàng để đối chiếu hủy đơn.')
    else:
        deep=creative.copy()
        impressions='Số lượt hiển thị quảng cáo sản phẩm'
        clicks='Số lượt nhấp vào quảng cáo sản phẩm'
        for c in ['Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU',impressions,clicks]:
            if c not in deep.columns:deep[c]=0.0
            else:deep[c]=num(deep[c])
        deep['Nhóm nội dung']=deep.get('Loại nội dung sáng tạo',pd.Series('Không xác định',index=deep.index)).fillna('Không xác định').astype(str)
        deep['ROAS tính lại']=np.where(deep['Chi phí']>0,deep['Doanh thu gộp']/deep['Chi phí'],np.nan)
        deep['CTR tính lại (%)']=np.where(deep[impressions]>0,100*deep[clicks]/deep[impressions],np.nan)
        total_spend=deep['Chi phí'].sum();total_revenue=deep['Doanh thu gộp'].sum()
        total_imp=deep[impressions].sum();total_click=deep[clicks].sum();total_sku=deep['Số lượng đơn hàng SKU'].sum()
        a,b,c,d=st.columns(4)
        a.metric('Hiển thị quảng cáo SP',f'{total_imp:,.0f}')
        b.metric('Nhấp quảng cáo SP',f'{total_click:,.0f}',help=f'CTR tổng hợp: {100*ratio(total_click,total_imp):.2f}%' if total_imp else 'Chưa có hiển thị')
        c.metric('Doanh thu Creative',vnd(total_revenue))
        d.metric('ROAS Creative',show_roas(ratio(total_revenue,total_spend)))
        e,f,g=st.columns(3)
        e.metric('CTR Creative',f'{100*ratio(total_click,total_imp):.2f}%' if total_imp else '—')
        f.metric('CVR nhấp → SKU',f'{100*ratio(total_sku,total_click):.2f}%' if total_click else '—')
        g.metric('Chi phí / SKU',vnd(total_spend/total_sku) if total_sku else '—')
        st.caption('CVR = số SKU đặt hàng được Creative ghi nhận / lượt nhấp quảng cáo sản phẩm. Đây là tỷ lệ quy đổi theo SKU, không phải tỷ lệ đơn hàng duy nhất hay tỷ lệ đơn hoàn tất.')
        if orders is not None:
            a,b,c=st.columns(3)
            a.metric('Đơn không hủy (CSV)',int((~order_level['Đã hủy']).sum()))
            b.metric('Đơn đã giao (CSV)',int((~order_level['Đã hủy'] & order_level['Đã giao']).sum()))
            c.metric('Đơn hủy (CSV)',int(order_level['Đã hủy'].sum()))
            st.caption('Số đơn CSV không được cộng vào số SKU Creative; chưa có liên kết attribution theo Order ID.')
        if ov is not None:
            diff=total_spend-ov['Chi phí'].sum()
            st.info(f'Chi phí Creative {vnd(total_spend)}; Campaign Overview {vnd(ov["Chi phí"].sum())}; chênh lệch Creative − Overview: {vnd(diff)}. Không cộng hai báo cáo. Phạm vi phân bổ và thời điểm ghi nhận có thể khác nhau.')

        st.subheader('9.1 / Thẻ sản phẩm so với video')
        grp=deep.groupby('Nhóm nội dung',dropna=False).agg(Chi_phi=('Chi phí','sum'),Doanh_thu=('Doanh thu gộp','sum'),SKU=('Số lượng đơn hàng SKU','sum'),Hien_thi=(impressions,'sum'),Nhap=(clicks,'sum'),So_creative=('Nhóm nội dung','size')).reset_index()
        grp['Tỷ trọng chi phí (%)']=np.where(total_spend>0,grp['Chi_phi']/total_spend*100,0)
        grp['ROAS']=np.where(grp['Chi_phi']>0,grp['Doanh_thu']/grp['Chi_phi'],np.nan)
        grp['CTR (%)']=np.where(grp['Hien_thi']>0,grp['Nhap']/grp['Hien_thi']*100,np.nan)
        grp['CVR nhấp→SKU (%)']=np.where(grp['Nhap']>0,100*grp['SKU']/grp['Nhap'],np.nan)
        grp['Chi phí/SKU']=np.where(grp['SKU']>0,grp['Chi_phi']/grp['SKU'],np.nan)
        st.dataframe(grp.rename(columns={'Nhóm nội dung':'Hình thức','Chi_phi':'Chi phí','Doanh_thu':'Doanh thu','SKU':'Đơn SKU','Hien_thi':'Hiển thị','Nhap':'Nhấp'}).style.format({'Chi phí':vnd,'Doanh thu':vnd,'Chi phí/SKU':vnd,'ROAS':show_roas,'CTR (%)':'{:.2f}','Tỷ trọng chi phí (%)':'{:.1f}','CVR nhấp→SKU (%)':'{:.2f}'}),hide_index=True,use_container_width=True)
        left,right=st.columns(2)
        with left:
            st.plotly_chart(px.bar(grp,x='Nhóm nội dung',y='CTR (%)',text_auto='.2f',title='CTR theo hình thức (%)',color='Nhóm nội dung'),use_container_width=True)
        with right:
            st.plotly_chart(px.bar(grp,x='Nhóm nội dung',y=['Chi_phi','Doanh_thu'],barmode='group',title='Chi phí và doanh thu Creative'),use_container_width=True)
        vids=grp[grp['Nhóm nội dung'].str.contains('video',case=False)]
        cards=grp[grp['Nhóm nội dung'].str.contains('thẻ',case=False)]
        if len(vids) and len(cards):
            v=vids.iloc[0];t=cards.iloc[0]
            if pd.notna(v['CTR (%)']) and pd.notna(t['CTR (%)']) and t['CTR (%)']>0:
                st.write(f'**Nhận xét:** CTR video bằng {v["CTR (%)"]/t["CTR (%)"]:.2f} lần thẻ sản phẩm; ROAS video {show_roas(v["ROAS"])} so với thẻ {show_roas(t["ROAS"])}. CTR cao không chứng minh doanh thu hoặc lợi nhuận tốt hơn.')

        st.subheader('9.2 / Phân tích thẻ sản phẩm: phân phối, nhấp và mua')
        card_rows=deep[deep['Nhóm nội dung'].str.contains('thẻ',case=False)].copy()
        if len(card_rows):
            card_rows['Sản phẩm']=card_rows.get('Tên sản phẩm',pd.Series('Không rõ',index=card_rows.index)).fillna('Không rõ')
            ct=card_rows.groupby('Sản phẩm',as_index=False).agg(Chi_phi=('Chi phí','sum'),Doanh_thu=('Doanh thu gộp','sum'),SKU=('Số lượng đơn hàng SKU','sum'),Hien_thi=(impressions,'sum'),Nhap=(clicks,'sum'))
            ct['CTR (%)']=np.where(ct['Hien_thi']>0,100*ct['Nhap']/ct['Hien_thi'],np.nan)
            ct['ROAS']=np.where(ct['Chi_phi']>0,ct['Doanh_thu']/ct['Chi_phi'],np.nan)
            ct['CVR nhấp→SKU (%)']=np.where(ct['Nhap']>0,100*ct['SKU']/ct['Nhap'],np.nan)
            ct['Nhận định']=np.select([(ct['Chi_phi']>0)&(ct['SKU']==0),(ct['Chi_phi']>0)&(ct['ROAS']<1)],['Có chi phí, chưa ghi nhận SKU','Doanh thu thấp hơn chi phí Ads'],default='Có tín hiệu chuyển đổi; cần theo dõi đơn hủy')
            st.dataframe(ct.sort_values('Chi_phi',ascending=False).rename(columns={'Chi_phi':'Chi phí','Doanh_thu':'Doanh thu','SKU':'Đơn SKU','Hien_thi':'Hiển thị','Nhap':'Nhấp'}).style.format({'Chi phí':vnd,'Doanh thu':vnd,'ROAS':show_roas,'CTR (%)':'{:.2f}','CVR nhấp→SKU (%)':'{:.2f}'}),hide_index=True,use_container_width=True)
            bad=ct[(ct['Chi_phi']>0)&((ct['SKU']==0)|(ct['ROAS']<1))].sort_values('Chi_phi',ascending=False).head(4)
            if len(bad):st.warning('**Nhóm cần kiểm tra trước:** '+', '.join(f'{r["Sản phẩm"]} ({vnd(r["Chi_phi"])}; ROAS {show_roas(r["ROAS"])})' for _,r in bad.iterrows()))
            st.markdown('**Giả thuyết cần kiểm chứng:** ảnh đại diện chưa truyền đạt lợi ích; tên sản phẩm khó đọc; giá/ưu đãi/phí vận chuyển chưa cạnh tranh; thiếu đánh giá hoặc thông tin trên trang đích. CTR thấp không tự chứng minh nguyên nhân nào trong số này.')
        else:st.caption('Không tìm thấy dòng thẻ sản phẩm trong báo cáo.')

        st.subheader('9.3 / Video: giữ chân, CTR, chuyển đổi và nội dung')
        video_rows=deep[deep['Nhóm nội dung'].str.contains('video',case=False)].copy()
        def parse_pct(s):
            ss=s.astype(str).str.strip()
            has_pct=ss.str.contains('%',regex=False)
            vals=pd.to_numeric(ss.str.replace('%','',regex=False).str.replace(',','.',regex=False),errors='coerce')
            # Values with % are already percentage points; decimals <=1 without % are fractions.
            return np.where(has_pct,vals,np.where(vals.abs()<=1,vals*100,vals))
        if len(video_rows):
            for raw,out in [('Tỷ lệ xem video quảng cáo trong 2 giây','Xem 2s (%)'),('Tỷ lệ xem video quảng cáo trong 6 giây','Xem 6s (%)')]:
                video_rows[out]=parse_pct(video_rows[raw]) if raw in video_rows else np.nan
            video_rows['Mẫu quảng cáo']=video_rows.get('Mẫu quảng cáo',pd.Series('',index=video_rows.index)).fillna('').astype(str)
            video_rows['Tên sản phẩm']=video_rows.get('Tên sản phẩm',pd.Series('',index=video_rows.index)).fillna('').astype(str)
            video_rows['CVR nhấp→SKU (%)']=np.where(video_rows[clicks]>0,100*video_rows['Số lượng đơn hàng SKU']/video_rows[clicks],np.nan)
            video_rows['Cảnh báo giữ chân']=np.where((video_rows['Xem 6s (%)']<8)&(video_rows['Chi phí']>0),'Xem 6 giây dưới 8%','Theo dõi')
            max_rows=st.slider('Số video hiển thị',5,100,20,5,key='deep_video_rows')
            vv=video_rows.sort_values('Chi phí',ascending=False).head(max_rows)
            st.dataframe(vv[['Mẫu quảng cáo','Tên sản phẩm','Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','CTR tính lại (%)','CVR nhấp→SKU (%)','Xem 2s (%)','Xem 6s (%)','ROAS tính lại','Cảnh báo giữ chân']].style.format({'Chi phí':vnd,'Doanh thu gộp':vnd,'CTR tính lại (%)':'{:.2f}','CVR nhấp→SKU (%)':'{:.2f}','Xem 2s (%)':'{:.2f}','Xem 6s (%)':'{:.2f}','ROAS tính lại':show_roas}),hide_index=True,use_container_width=True)
            st.plotly_chart(px.scatter(video_rows,x='Xem 6s (%)',y='CTR tính lại (%)',size='Chi phí',color='Số lượng đơn hàng SKU',hover_name='Mẫu quảng cáo',title='Giữ chân 6 giây và CTR (kích thước = chi phí)'),use_container_width=True)
            low=video_rows[(video_rows['Chi phí']>0)&(video_rows['Xem 6s (%)']<8)].sort_values('Chi phí',ascending=False)
            if len(low):st.warning(f'{len(low)} dòng video có tỷ lệ xem 6 giây dưới 8% và đã tiêu {vnd(low["Chi phí"].sum())}. Đây là ngưỡng cảnh báo phân tích, không phải chuẩn chính thức của TikTok.')
            st.markdown('**Giả thuyết nội dung:** hook chưa đủ cụ thể; video nói về công dụng nhưng thiếu cách dùng, đối tượng phù hợp, điểm khác biệt và CTA; người xem nhấp nhưng không đủ lý do mua. Cần xem video gốc để kết luận về hình ảnh, lời thoại và nhịp dựng.')

        st.subheader('9.4 / Kết luận và ưu tiên hành động')
        st.markdown('**Đạt được:** có dữ liệu về mức tiếp cận, nhấp, doanh thu quy thuộc và SKU; xác định được nội dung có tín hiệu mua. **Chưa đạt:** ROAS chưa phản ánh lợi nhuận; một số nội dung tiêu ngân sách nhưng không có SKU; hủy đơn có thể làm giảm doanh thu giữ lại.')
        recommendations=[]
        if len(card_rows):
            for _,r in ct.sort_values('Chi_phi',ascending=False).iterrows():
                if r['Chi_phi']<=0:continue
                if r['SKU']==0:action='Tạm dừng/giảm phân phối; thay ảnh, tên, giá/ưu đãi rồi thử lại'
                elif pd.notna(r['ROAS']) and r['ROAS']<1:action='Không mở rộng; kiểm tra trang đích, giá, đánh giá và chi phí chuyển đổi'
                else:action='Giữ thử nghiệm có kiểm soát; theo dõi chi phí chuyển đổi và đơn hủy'
                recommendations.append({'Đối tượng':r['Sản phẩm'],'Loại':'Thẻ sản phẩm','Chi phí':r['Chi_phi'],'ROAS':r['ROAS'],'Đề xuất':action})
        if len(video_rows):
            for _,r in video_rows.sort_values('Chi phí',ascending=False).head(8).iterrows():
                action='Thử lại hook 3 giây, kiểm tra giỏ hàng và CTA' if r['Số lượng đơn hàng SKU']==0 else 'Đối chiếu đơn hủy và tỷ lệ chuyển đổi trước khi tăng ngân sách'
                if pd.notna(r['Xem 6s (%)']) and r['Xem 6s (%)']<8:action='Ưu tiên làm lại hook 3 giây và cấu trúc mở đầu; '+action.lower()
                recommendations.append({'Đối tượng':r['Mẫu quảng cáo'],'Loại':'Video','Chi phí':r['Chi phí'],'ROAS':r['ROAS tính lại'],'Đề xuất':action})
        if recommendations:
            rec=pd.DataFrame(recommendations).sort_values('Chi phí',ascending=False)
            st.dataframe(rec.style.format({'Chi phí':vnd,'ROAS':show_roas}),hide_index=True,use_container_width=True)
            st.download_button('Tải danh sách hành động tối ưu (.csv)',rec.to_csv(index=False).encode('utf-8-sig'),file_name='de_xuat_toi_uu_creative.csv',mime='text/csv')
        st.caption('Quy tắc gợi ý là heuristic, không phải bằng chứng quan hệ nhân quả. Cần thêm ảnh thẻ, video gốc, giá đối thủ, lịch sử ưu đãi và mã đơn quy thuộc Ads để xác minh.')

