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

# --- 구글 시트 연결 (Secrets 설정을 기반으로 함) ---
# 이 부분에서 에러가 난다면 Secrets의 URL 설정을 확인해야 합니다.
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # 'orders'는 구글 시트 하단 탭 이름과 일치해야 합니다.
    return conn.read(worksheet="orders", ttl="0")

# --- 스타일링 ---
st.markdown("""
    <style>
    div[data-testid="stCheckbox"] { transform: scale(1.3); }
    .header-style { font-weight: bold; color: #495057; background-color: #e9ecef; padding: 5px; border-radius: 5px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 기초 데이터 로드 (기존 CSV 파일 활용)
@st.cache_data
def load_base_data():
    staff_df = pd.read_csv('staff.csv')
    menu_df = pd.read_csv('menu.csv')
    return staff_df, menu_df

staff_df, menu_df = load_base_data()
today_str = datetime.date.today().strftime('%Y-%m-%d')

# 메뉴 초기화 로직
if "menu_selection" not in st.session_state:
    st.session_state.menu_selection = []

def reset_on_change():
    st.session_state.menu_selection = []

# 메인 타이틀
st.title('🍱 인천생활과학고 "밥먹고 초근하자"')

tab1, tab2, tab3 = st.tabs(["🍴 맛있는 주문", "📋 관리자 데스크", "📜 지난 기록"])

# --- [Tab 1: 주문하기] ---
with tab1:
    st.info("💡 부서 -> 이름 -> 식당 순서로 선택해 주세요.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        depts = ["--- 부서 선택 ---"] + sorted(staff_df['department'].unique().tolist())
        dept = st.selectbox("🏢 부서 선택", depts, on_change=reset_on_change)
    with col2:
        if dept != "--- 부서 선택 ---":
            names = ["--- 이름 선택 ---"] + sorted(staff_df[staff_df['department']==dept]['name'].tolist())
            user_name = st.selectbox("👤 이름 선택", names, on_change=reset_on_change)
        else:
            st.selectbox("👤 이름 선택", ["부서 먼저 선택"], disabled=True)
            user_name = "--- 이름 선택 ---"
    with col3:
        if user_name != "--- 이름 선택 ---":
            restaurants = ["--- 식당 선택 ---"] + sorted(menu_df['restaurant'].unique().tolist())
            selected_res = st.selectbox("🏪 식당 선택", restaurants, on_change=reset_on_change)
        else:
            st.selectbox("🏪 식당 선택", ["이름 먼저 선택"], disabled=True)
            selected_res = "--- 식당 선택 ---"

    if selected_res != "--- 식당 선택 ---":
        res_menu = menu_df[menu_df['restaurant'] == selected_res]
        menu_options = [f"{row['item_name']} ({row['price']:,}원)" for _, row in res_menu.iterrows()]
        
        selected_display = st.multiselect("📝 메뉴보기", menu_options, key="menu_selection")
        
        if selected_display:
            total_price = sum([int(s.split('(')[1].replace('원)', '').replace(',', '')) for s in selected_display])
            pure_items = [s.split(' (')[0] for s in selected_display]

            st.warning(f"⚠️ **{user_name}** 선생님, 아래 버튼을 눌러야 주문이 확정됩니다!")
            
            if st.button("🚀 주문 확정하기", type="primary", use_container_width=True):
                # 구글 시트에서 기존 데이터 읽기
                df = get_data()
                
                # 새 행 데이터 생성
                new_row = {
                    "id": len(df) + 1,
                    "order_date": today_str,
                    "department": dept,
                    "user_name": user_name,
                    "restaurant": selected_res,
                    "items": ", ".join(pure_items),
                    "total_price": total_price,
                    "delivery_fee": 0,
                    "over_price": 0,
                    "status": "주문대기",
                    "batch_id": ""
                }
                
                # 데이터 추가 및 시트 업데이트
                updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                conn.update(worksheet="orders", data=updated_df)
                
                st.success(f"🎉 접수 완료! ({total_price:,}원)")
                st.balloons()
                st.button("🔄 다음 사람 주문하기", on_click=lambda: st.rerun())

# --- [Tab 2: 관리자 데스크] ---
with tab2:
    st.header("👨‍💻 관리자 취합")
    all_data = get_data()
    today_data = all_data[all_data['order_date'] == today_str]
    
    if today_data.empty:
        st.info("오늘 접수된 주문이 없습니다.")
    else:
        pending = today_data[today_data['status'] == '주문대기']
        if not pending.empty:
            for res in pending['restaurant'].unique():
                res_orders = pending[pending['restaurant'] == res]
                with st.expander(f"📍 {res} 대기 현황", expanded=True):
                    to_confirm = []
                    for idx, row in res_orders.iterrows():
                        if st.checkbox(f"{row['user_name']} - {row['items']} ({row['total_price']:,}원)", key=f"c_{row['id']}"):
                            to_confirm.append(row['id'])
                    
                    if st.button(f"✅ {res} 확정", key=f"b_{res}"):
                        all_data.loc[all_data['id'].isin(to_confirm), 'status'] = '주문완료'
                        all_data.loc[all_data['id'].isin(to_confirm), 'batch_id'] = f"{res}_완료"
                        conn.update(worksheet="orders", data=all_data)
                        st.rerun()

# --- [Tab 3: 지난 기록] ---
with tab3:
    st.subheader("📜 전체 주문 데이터")
    st.dataframe(get_data(), use_container_width=True, hide_index=True)
