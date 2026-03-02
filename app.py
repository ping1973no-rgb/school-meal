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
# Secrets에 등록한 설정을 기반으로 연결합니다.
conn_gs = st.connection("gsheets", type=GSheetsConnection)

def get_db_data():
    """구글 시트에서 전체 데이터를 읽어옵니다."""
    try:
        df = conn_gs.read(worksheet="orders", ttl="0")
        if df.empty:
            return pd.DataFrame(columns=['id', 'order_date', 'department', 'user_name', 'restaurant', 'items', 'total_price', 'delivery_fee', 'over_price', 'status', 'batch_id'])
        return df
    except Exception as e:
        st.error(f"구글 시트를 읽지 못했습니다. (탭 이름 'orders' 확인): {e}")
        return pd.DataFrame()

# --- 스타일링 (선생님 PC 버전의 CSS 그대로 유지) ---
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

# 기초 데이터 로드 (CSV 파일)
@st.cache_data
def load_data():
    staff_df = pd.read_csv('staff.csv')
    menu_df = pd.read_csv('menu.csv')
    return staff_df, menu_df

staff_df, menu_df = load_data()
today = datetime.date.today()
today_str = today.strftime('%Y-%m-%d')

# 메뉴 초기화 로직
def reset_menu():
    if "menu_selection" in st.session_state:
        st.session_state.menu_selection = []

st.title('🍱 인천생활과학고 "밥먹고 초근하자"')

tab1, tab2, tab3 = st.tabs(["🍴 맛있는 주문", "📋 관리자 데스크", "📜 지난 기록"])

# --- [Tab 1: 주문하기] ---
with tab1:
    st.info("💡 부서 -> 이름 -> 식당 순서로 선택 후 메뉴를 확정해 주세요.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        depts = ["--- 부서 선택 ---"] + sorted(staff_df['department'].unique().tolist())
        dept = st.selectbox("🏢 부서 선택", depts, on_change=reset_menu)
    with col2:
        if dept != "--- 부서 선택 ---":
            names = ["--- 이름 선택 ---"] + sorted(staff_df[staff_df['department']==dept]['name'].tolist())
            user_name = st.selectbox("👤 이름 선택", names, on_change=reset_menu)
        else:
            user_name = st.selectbox("👤 이름 선택", ["부서 먼저 선택"], disabled=True)
    with col3:
        if user_name not in ["--- 이름 선택 ---", "부서 먼저 선택"]:
            restaurants = ["--- 식당 선택 ---"] + sorted(menu_df['restaurant'].unique().tolist())
            selected_res = st.selectbox("🏪 식당 선택", restaurants, on_change=reset_menu)
        else:
            selected_res = st.selectbox("🏪 식당 선택", ["이름 먼저 선택"], disabled=True)

    if selected_res not in ["--- 식당 선택 ---", "이름 먼저 선택"]:
        res_menu = menu_df[menu_df['restaurant'] == selected_res]
        menu_options = [f"{row['item_name']} ({row['price']:,}원)" for _, row in res_menu.iterrows()]
        selected_display = st.multiselect("📝 메뉴 선택", menu_options, key="menu_selection")
        
        if selected_display:
            total_food_price = sum([int(s.split('(')[1].replace('원)', '').replace(',', '')) for s in selected_display])
            pure_items = [s.split(' (')[0] for s in selected_display]

            if st.button("🚀 주문 확정하기", type="primary", use_container_width=True):
                df = get_db_data()
                # 중복 주문 확인
                is_dup = not df[(df['order_date'] == today_str) & (df['user_name'] == user_name)].empty
                if is_dup:
                    st.error("❌ 이미 주문한 기록이 있습니다. 수정은 교무기획부에 문의해 주세요.")
                else:
                    new_row = pd.DataFrame([{
                        "id": len(df) + 1, "order_date": today_str, "department": dept, "user_name": user_name,
                        "restaurant": selected_res, "items": ", ".join(pure_items), "total_price": total_food_price,
                        "delivery_fee": 0, "over_price": 0, "status": "주문대기", "batch_id": ""
                    }])
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    # 시트 업데이트
                    conn_gs.update(worksheet="orders", data=updated_df)
                    st.success(f"🎉 주문 완료! 구글 시트에 기록되었습니다.")
                    st.balloons()
                    st.button("🔄 다음 사람 주문하기", on_click=lambda: st.session_state.clear())

# --- [Tab 2: 관리자 데스크] ---
with tab2:
    st.header("👨‍💻 관리자 취합")
    all_data = get_db_data()
    today_data = all_data[all_data['order_date'] == today_str]
    
    if today_data.empty:
        st.info("오늘 접수된 주문이 없습니다.")
    else:
        # 대기 내역
        pending = today_data[today_data['status'] == '주문대기']
        if not pending.empty:
            for res in pending['restaurant'].unique():
                res_orders = pending[pending['restaurant'] == res]
                with st.expander(f"📍 {res} (대기 {len(res_orders)}건)", expanded=True):
                    food_sum = res_orders['total_price'].sum()
                    d_fee = 4000 if res != '장강' else 0
                    if res == '오르드브' and food_sum >= 50000: d_fee = 0
                    per_fee = d_fee // len(res_orders) if len(res_orders) > 0 else 0
                    
                    st.write(f"음식: {food_sum:,}원 | 배달비: {d_fee:,}원 (1인당 {per_fee:,}원)")
                    
                    to_confirm = []
                    # 테이블 헤더
                    h_col = st.columns([0.1, 0.15, 0.15, 0.4, 0.2])
                    headers = ["선택", "부서", "성함", "메뉴", "음식값"]
                    for col, text in zip(h_col, headers): col.markdown(f'<p class="header-style">{text}</p>', unsafe_allow_html=True)

                    for _, row in res_orders.iterrows():
                        c = st.columns([0.1, 0.15, 0.15, 0.4, 0.2])
                        if c[0].checkbox("", key=f"sel_{row['id']}"): to_confirm.append(row['id'])
                        c[1].write(row['department'])
                        c[2].write(row['user_name'])
                        c[3].write(row['items'])
                        c[4].write(f"{row['total_price']:,}")

                    if st.button(f"✅ {res} 주문 확정 및 차수 부여", key=f"btn_{res}"):
                        if to_confirm:
                            # 차수 이름 결정
                            done_batches = all_data[(all_data['order_date'] == today_str) & (all_data['status'] == '주문완료')]['batch_id'].unique()
                            batch_name = f"{len(done_batches)+1}차({res})"
                            
                            # 데이터 업데이트 로직
                            all_data.loc[all_data['id'].isin(to_confirm), 'status'] = '주문완료'
                            all_data.loc[all_data['id'].isin(to_confirm), 'batch_id'] = batch_name
                            all_data.loc[all_data['id'].isin(to_confirm), 'delivery_fee'] = per_fee
                            for tid in to_confirm:
                                row_idx = all_data.index[all_data['id'] == tid][0]
                                all_data.at[row_idx, 'over_price'] = max(0, (all_data.at[row_idx, 'total_price'] + per_fee) - 9000)
                            
                            conn_gs.update(worksheet="orders", data=all_data)
                            st.rerun()

        # 확정 완료 현황
        done = today_data[today_data['status'] == '주문완료']
        if not done.empty:
            st.markdown("---")
            st.subheader("✅ 확정 내역 요약")
            for b_id in sorted(done['batch_id'].unique()):
                b_df = done[done['batch_id'] == b_id]
                b_food = b_df['total_price'].sum()
                b_del = b_df['delivery_fee'].sum()
                with st.expander(f"📋 {b_id} 현황 ({len(b_df)}명)", expanded=True):
                    st.markdown(f"""<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #28a745;">
                        결제액: <b>{b_food+b_del:,}원</b> (음식 {b_food:,} + 배달비 {b_del:,})</div>""", unsafe_allow_html=True)
                    st.dataframe(b_df[['department', 'user_name', 'items', 'total_price', 'delivery_fee', 'over_price']], hide_index=True)

# --- [Tab 3: 지난 기록] ---
with tab3:
    st.header("📅 지난 주문 기록 조회")
    search_date = st.date_input("조회할 날짜를 선택하세요", today)
    all_data_hist = get_db_data()
    
    if not all_data_hist.empty:
        history = all_data_hist[(all_data_hist['order_date'] == search_date.strftime('%Y-%m-%d')) & (all_data_hist['status'] == '주문완료')]
        if not history.empty:
            df_hist = history[['batch_id', 'department', 'user_name', 'restaurant', 'items', 'total_price', 'delivery_fee', 'over_price']].copy()
            df_hist.columns = ['차수', '부서', '성함', '식당', '메뉴', '음식값', '배달비', '초과금']
            st.table(df_hist)
            st.metric("총 결제 금액 (배달비 포함)", f"{history['total_price'].sum() + history['delivery_fee'].sum():,}원")
        else:
            st.warning("조회된 기록이 없습니다.")
