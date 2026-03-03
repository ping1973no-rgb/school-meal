import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# 1. 페이지 설정
st.set_page_config(
    page_title='인천생활과학고 "밥먹고 초근하자"',
    page_icon="🍱",
    layout="wide"
)

# --- [중요] 구글 시트 연결 ---
conn_gs = st.connection("gsheets", type=GSheetsConnection)

def get_db_data():
    try:
        df = conn_gs.read(worksheet="orders", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', 'order_date', 'department', 'user_name', 'restaurant', 'items', 'total_price', 'delivery_fee', 'over_price', 'status', 'batch_id'])
        df = df.astype(str).apply(lambda x: x.str.strip())
        df['order_date'] = pd.to_datetime(df['order_date']).dt.strftime('%Y-%m-%d')
        num_cols = ['total_price', 'delivery_fee', 'over_price']
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame(columns=['id', 'order_date', 'department', 'user_name', 'restaurant', 'items', 'total_price', 'delivery_fee', 'over_price', 'status', 'batch_id'])

# --- 스타일링 수정 (체크박스 정렬 보정) ---
st.markdown("""
    <style>
    .stAlert { padding: 15px; border-radius: 10px; }
    .stButton>button { border-radius: 10px; font-weight: bold; }
    .stExpander { border: none; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-radius: 10px; margin-bottom: 20px; }
    
    /* 체크박스와 텍스트 수직 정렬 보정 */
    div[data-testid="stHorizontalBlock"] {
        align-items: center;
        background-color: #ffffff;
        padding: 5px 10px;
        border-bottom: 1px solid #eee;
    }
    .header-style { font-weight: bold; color: #495057; background-color: #f1f3f5; padding: 8px; border-radius: 5px; text-align: center; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

staff_df = pd.read_csv('staff.csv')
menu_df = pd.read_csv('menu.csv')

today = datetime.date.today()
today_str = today.strftime('%Y-%m-%d')

st.title('🍱 인천생활과학고 "밥먹고 초근하자"')
st.markdown(f"### 📅 오늘은 **{today_str}** 입니다.")

tab1, tab2, tab3 = st.tabs(["🍴 맛있는 주문", "📋 관리자 데스크", "📜 지난 기록"])

# --- [Tab 1: 주문하기] ---
with tab1:
    st.info("💡 부서 → 이름 → 식당 순서로 선택 후 메뉴를 확정해 주세요. 16:40분에 일괄주문합니다.\n\n 메뉴확정 및 일괄 주문 후 수정이나 삭제는 식당에 문의해주세요.")
    col1, col2, col3 = st.columns(3)
    with col1:
        dept = st.selectbox("🏢 부서 선택", ["--- 부서 선택 ---"] + sorted(staff_df['department'].unique().tolist()))
    with col2:
        names = ["--- 이름 선택 ---"] + sorted(staff_df[staff_df['department']==dept]['name'].tolist()) if dept != "--- 부서 선택 ---" else ["부서 먼저 선택"]
        user_name = st.selectbox("👤 이름 선택", names)
    with col3:
        res_list = ["--- 식당 선택 ---"] + sorted(menu_df['restaurant'].unique().tolist()) if user_name not in ["--- 이름 선택 ---", "부서 먼저 선택"] else ["이름 먼저 선택"]
        selected_res = st.selectbox("🏪 식당 선택", res_list)

    if selected_res not in ["--- 식당 선택 ---", "이름 먼저 선택"]:
        res_menu = menu_df[menu_df['restaurant'] == selected_res]
        menu_options = [f"{row['item_name']} ({row['price']:,}원)" for _, row in res_menu.iterrows()]
        selected_display = st.multiselect("📝 메뉴 선택", menu_options)
        
        if selected_display and st.button("🚀 주문 확정하기", type="primary", use_container_width=True):
            df = get_db_data()
            if not df[(df['order_date'] == today_str) & (df['user_name'] == user_name)].empty:
                st.error("❌ 이미 오늘 주문하셨습니다!")
            else:
                total_food = sum([int(s.split('(')[1].replace('원)', '').replace(',', '')) for s in selected_display])
                new_row = pd.DataFrame([{
                    "id": len(df) + 1, "order_date": today_str, "department": dept, "user_name": user_name,
                    "restaurant": selected_res, "items": ", ".join([s.split(' (')[0] for s in selected_display]),
                    "total_price": total_food, "delivery_fee": 0, "over_price": 0, "status": "주문대기", "batch_id": ""
                }])
                conn_gs.update(worksheet="orders", data=pd.concat([df, new_row], ignore_index=True))
                st.success(f"🎉 {today_str} 주문 완료!")
                st.balloons()

# --- [Tab 2: 관리자 데스크] ---
with tab2:
    st.subheader(f"📊 {today_str} 주문 관리")
    all_data = get_db_data()
    today_data = all_data[all_data['order_date'] == today_str]
    
    if today_data.empty:
        st.info("오늘 접수된 주문이 없습니다.")
    else:
        # 1. 미확정 대기 내역
        pending = today_data[today_data['status'] == '주문대기']
        if not pending.empty:
            st.markdown("#### ⏳ 확정 대기 목록")
            for res in pending['restaurant'].unique():
                res_orders = pending[pending['restaurant'] == res]
                with st.expander(f"📍 {res} (대기 {len(res_orders)}건)", expanded=True):
                    food_sum = res_orders['total_price'].sum()
                    d_fee = 4000 if res != '장강' else 0
                    if res == '오르드브' and food_sum >= 50000: d_fee = 0
                    per_fee = d_fee // len(res_orders)
                    
                    st.write(f"배달비 총 {d_fee:,}원 (1인당 {per_fee:,}원)")
                    
                    # 체크박스를 포함한 주문 리스트 표 형태 구현
                    h_col = st.columns([0.1, 0.2, 0.2, 0.3, 0.2])
                    headers = ["선택", "부서", "성함", "메뉴", "음식값"]
                    for col, text in zip(h_col, headers): col.markdown(f'<p class="header-style">{text}</p>', unsafe_allow_html=True)

                    to_confirm = []
                    for _, row in res_orders.iterrows():
                        c = st.columns([0.1, 0.2, 0.2, 0.3, 0.2])
                        if c[0].checkbox("", key=f"chk_{row['id']}"): to_confirm.append(row['id'])
                        c[1].write(row['department'])
                        c[2].write(row['user_name'])
                        c[3].write(row['items'])
                        c[4].write(f"{row['total_price']:,}원")
                    
                    if st.button(f"✅ {res} 주문 확정 및 차수 부여", key=f"btn_{res}"):
                        if to_confirm:
                            done_batches = all_data[(all_data['order_date'] == today_str) & (all_data['status'] == '주문완료')]['batch_id'].unique()
                            batch_name = f"{len(done_batches)+1}차({res})"
                            
                            all_data.loc[all_data['id'].isin(to_confirm), ['status', 'batch_id', 'delivery_fee']] = ['주문완료', batch_name, per_fee]
                            for tid in to_confirm:
                                idx = all_data.index[all_data['id'] == tid][0]
                                all_data.at[idx, 'over_price'] = max(0, (all_data.at[idx, 'total_price'] + per_fee) - 9000)
                            
                            conn_gs.update(worksheet="orders", data=all_data)
                            st.rerun()

        # 2. [수정 요청사항] 오늘 확정 내역을 차수별로 표 분리
        done = today_data[today_data['status'] == '주문완료']
        if not done.empty:
            st.markdown("---")
            st.subheader("✅ 오늘 확정 완료 내역 (차수별)")
            
            # 차수(batch_id)별로 정렬하여 표를 따로 생성
            for b_id in sorted(done['batch_id'].unique()):
                b_df = done[done['batch_id'] == b_id]
                b_food = b_df['total_price'].sum()
                b_del = b_df['delivery_fee'].sum()
                
                # 차수별 박스 구성
                with st.container():
                    st.markdown(f"**📋 {b_id}** (합계: {b_food+b_del:,}원)")
                    # 가독성을 위해 불필요한 컬럼은 제외하고 보여줌
                    display_df = b_df[['department', 'user_name', 'items', 'total_price', 'delivery_fee', 'over_price']].copy()
                    display_df.columns = ['부서', '이름', '메뉴', '음식값', '배달비', '초과금']
                    st.table(display_df) # dataframe 대신 table을 써서 스크롤 없이 다 보이게 함
                    st.write("") # 간격 띄우기

# --- [Tab 3: 지난 기록] ---
with tab3:
    st.header("📅 전체 기록 조회")
    search_date = st.date_input("날짜 선택", today)
    all_data_hist = get_db_data()
    history = all_data_hist[(all_data_hist['order_date'] == search_date.strftime('%Y-%m-%d')) & (all_data_hist['status'] == '주문완료')]
    
    if not history.empty:
        st.table(history[['batch_id', 'department', 'user_name', 'restaurant', 'items', 'total_price', 'delivery_fee', 'over_price']])
        st.metric("총 결제 금액", f"{history['total_price'].sum() + history['delivery_fee'].sum():,}원")
    else:
        st.warning("기록이 없습니다.")
