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
    """구글 시트에서 데이터를 실시간으로 읽어오고 형식을 정리합니다."""
    try:
        # ttl=0으로 설정하여 캐시 없이 실시간 데이터를 가져옵니다.
        df = conn_gs.read(worksheet="orders", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', 'order_date', 'department', 'user_name', 'restaurant', 'items', 'total_price', 'delivery_fee', 'over_price', 'status', 'batch_id'])
        
        # 데이터 정리 (공백 제거 및 날짜 형식 통일)
        df = df.astype(str).apply(lambda x: x.str.strip())
        # 날짜 형식을 YYYY-MM-DD로 강제 변환 (직접 입력 대비)
        df['order_date'] = pd.to_datetime(df['order_date']).dt.strftime('%Y-%m-%d')
        
        # 숫자 컬럼 변환
        num_cols = ['total_price', 'delivery_fee', 'over_price']
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
        return df
    except:
        return pd.DataFrame(columns=['id', 'order_date', 'department', 'user_name', 'restaurant', 'items', 'total_price', 'delivery_fee', 'over_price', 'status', 'batch_id'])

# --- 스타일링 (선생님 디자인 유지) ---
st.markdown("""
    <style>
    .stAlert { padding: 15px; border-radius: 10px; }
    .stButton>button { border-radius: 10px; font-weight: bold; }
    .stExpander { border: none; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-radius: 10px; }
    div[data-testid="stCheckbox"] { transform: scale(1.3); margin-left: 5px; }
    div[data-testid="stCheckbox"] > label > div[aria-checked="true"] { background-color: #007bff !important; border-color: #007bff !important; }
    .header-style { font-weight: bold; color: #495057; background-color: #e9ecef; padding: 5px; border-radius: 5px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 기초 데이터 로드 (CSV)
@st.cache_data
def load_data():
    staff_df = pd.read_csv('staff.csv')
    menu_df = pd.read_csv('menu.csv')
    return staff_df, menu_df

staff_df, menu_df = load_data()

# --- [날짜 설정] ---
today = datetime.date.today()
today_str = today.strftime('%Y-%m-%d')

st.title('🍱 인천생활과학고 "밥먹고 초근하자"')
# 메인 화면에 오늘 날짜 표시
st.markdown(f"### 📅 오늘은 **{today_str}** 입니다.")

tab1, tab2, tab3 = st.tabs(["🍴 맛있는 주문", "📋 관리자 데스크", "📜 지난 기록"])

# --- [Tab 1: 주문하기] ---
with tab1:
    st.info(f"💡 오늘은 {today_str} 주문을 접수합니다.")
    st.info("💡 부서 → 이름 → 식당 순서로 선택 후 메뉴를 확정해 주세요. 16:30분에 일괄 주문합니다.")
    # (주문 로직은 동일하게 유지됩니다)
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
            # 오늘 날짜 중복 체크
            is_dup = not df[(df['order_date'] == today_str) & (df['user_name'] == user_name)].empty
            if is_dup:
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
    st.subheader(f"📊 {today_str} 주문 현황")
    all_data = get_db_data()
    # [핵심] 오늘 날짜인 것만 필터링
    today_data = all_data[all_data['order_date'] == today_str]
    
    if today_data.empty:
        st.info("오늘( {today_str} )은 아직 주문이 없습니다.")
    else:
        # 주문 대기 내역 처리 (기존 로직 동일)
        pending = today_data[today_data['status'] == '주문대기']
        if not pending.empty:
            for res in pending['restaurant'].unique():
                res_orders = pending[pending['restaurant'] == res]
                with st.expander(f"📍 {res} (대기 {len(res_orders)}건)", expanded=True):
                    food_sum = res_orders['total_price'].sum()
                    d_fee = 4000 if res != '장강' else 0
                    if res == '오르드브' and food_sum >= 50000: d_fee = 0
                    per_fee = d_fee // len(res_orders)
                    
                    st.write(f"배달비 총 {d_fee:,}원 (1인당 {per_fee:,}원)")
                    
                    to_confirm = []
                    for _, row in res_orders.iterrows():
                        if st.checkbox(f"{row['user_name']} | {row['items']} ({row['total_price']:,}원)", key=f"chk_{row['id']}"):
                            to_confirm.append(row['id'])
                    
                    if st.button(f"✅ {res} 주문 확정", key=f"btn_{res}"):
                        if to_confirm:
                            # 차수 계산 및 시트 업데이트 로직...
                            done_count = len(all_data[(all_data['order_date'] == today_str) & (all_data['status'] == '주문완료')]['batch_id'].unique())
                            all_data.loc[all_data['id'].isin(to_confirm), ['status', 'batch_id', 'delivery_fee']] = ['주문완료', f"{done_count+1}차({res})", per_fee]
                            for tid in to_confirm:
                                idx = all_data.index[all_data['id'] == tid][0]
                                all_data.at[idx, 'over_price'] = max(0, (all_data.at[idx, 'total_price'] + per_fee) - 9000)
                            conn_gs.update(worksheet="orders", data=all_data)
                            st.rerun()

        # 오늘 확정 내역 요약
        done = today_data[today_data['status'] == '주문완료']
        if not done.empty:
            st.markdown("---")
            st.subheader("✅ 오늘 확정 내역")
            st.dataframe(done[['batch_id', 'user_name', 'items', 'total_price', 'delivery_fee', 'over_price']], hide_index=True)

# --- [Tab 3: 지난 기록] ---
with tab3:
    st.header("📅 전체 기록 조회")
    # 날짜 선택기의 기본값을 오늘로 설정
    search_date = st.date_input("날짜를 선택하세요", today)
    all_data_hist = get_db_data()
    
    # 선택한 날짜에 해당하는 데이터 필터링
    history = all_data_hist[(all_data_hist['order_date'] == search_date.strftime('%Y-%m-%d')) & (all_data_hist['status'] == '주문완료')]
    
    if not history.empty:
        st.success(f"✅ {search_date} 기록을 불러왔습니다.")
        st.table(history[['batch_id', 'department', 'user_name', 'restaurant', 'items', 'total_price', 'delivery_fee', 'over_price']])
    else:
        st.warning(f"{search_date}에는 주문 기록이 없습니다.")
