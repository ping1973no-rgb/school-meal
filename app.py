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

# --- 구글 시트 연결 설정 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # 구글 시트의 'orders' 탭에서 데이터를 읽어옵니다.
    return conn.read(worksheet="orders", ttl="0")

# --- 스타일링 (체크박스 강조 및 디자인) ---
st.markdown("""
    <style>
    div[data-testid="stCheckbox"] { transform: scale(1.2); margin-left: 5px; }
    .header-style { font-weight: bold; color: #495057; background-color: #e9ecef; padding: 5px; border-radius: 5px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 기초 데이터 로드 (직원 및 메뉴는 CSV에서 읽음)
@st.cache_data
def load_base_data():
    staff_df = pd.read_csv('staff.csv')
    menu_df = pd.read_csv('menu.csv')
    return staff_df, menu_df

staff_df, menu_df = load_base_data()
today_str = datetime.date.today().strftime('%Y-%m-%d')

# 메뉴 리셋 함수
def reset_on_change():
    if "menu_selection" in st.session_state:
        st.session_state.menu_selection = []

# 메인 타이틀
st.title('🍱 인천생활과학고 "밥먹고 초근하자"')

tab1, tab2, tab3 = st.tabs(["🍴 맛있는 주문", "📋 관리자 데스크", "📜 지난 기록"])

# --- [Tab 1: 주문하기] ---
with tab1:
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 20px;">
        💡 <b>성함과 메뉴를 확인 후 [주문 확정]을 눌러주세요.</b> 수정/삭제는 교무기획부로 문의 바랍니다.
    </div>
    """, unsafe_allow_html=True)

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

            st.warning(f"⚠️ **{user_name}** 선생님, 선택하신 메뉴가 맞나요? 아래 버튼을 눌러야 주문이 완료됩니다.")
            
            if st.button("🚀 주문 확정하기 (클릭!)", type="primary", use_container_width=True):
                # 기존 데이터 가져오기
                existing_data = get_data()
                new_id = len(existing_data) + 1
                
                # 새 주문 데이터 행 생성
                new_row = pd.DataFrame([{
                    "id": new_id, "order_date": today_str, "department": dept, "user_name": user_name,
                    "restaurant": selected_res, "items": ", ".join(pure_items), "total_price": total_price,
                    "delivery_fee": 0, "over_price": 0, "status": "주문대기", "batch_id": ""
                }])
                
                # 시트 업데이트
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                conn.update(worksheet="orders", data=updated_df)
                
                st.success(f"🎉 접수 완료! 내역: {', '.join(pure_items)} ({total_price:,}원)")
                st.info("💡 수정/삭제는 교무기획부에 말씀해 주세요.")
                st.balloons()
                st.button("🔄 확인 (새 주문 화면으로)", on_click=lambda: st.session_state.clear())

# --- [Tab 2: 관리자 데스크] ---
with tab2:
    st.header("👨‍💻 관리자 주문 취합")
    all_data = get_data()
    today_data = all_data[all_data['order_date'] == today_str]
    
    if today_data.empty:
        st.info("오늘 접수된 주문이 없습니다.")
    else:
        pending = today_data[today_data['status'] == '주문대기']
        if not pending.empty:
            for res in pending['restaurant'].unique():
                res_orders = pending[pending['restaurant'] == res]
                with st.expander(f"📍 {res} (대기 {len(res_orders)}건)", expanded=True):
                    # 배달비 계산 (선생님 기존 로직 동일)
                    food_sum = res_orders['total_price'].sum()
                    d_fee = 4000 if res != '장강' else 0
                    if res == '오르드브' and food_sum >= 50000: d_fee = 0
                    
                    st.write(f"음식 합계: {food_sum:,}원 | 배달비: {d_fee:,}원")
                    
                    to_confirm = []
                    for idx, row in res_orders.iterrows():
                        col = st.columns([0.1, 0.2, 0.2, 0.4, 0.1])
                        if col[0].checkbox("", key=f"chk_{row['id']}"):
                            to_confirm.append(row['id'])
                        col[1].write(row['department'])
                        col[2].write(row['user_name'])
                        col[3].write(row['items'])
                        col[4].write(f"{row['total_price']:,}")
                    
                    if st.button(f"✅ {res} 선택 주문 확정", key=f"btn_{res}"):
                        if to_confirm:
                            all_data.loc[all_data['id'].isin(to_confirm), 'status'] = '주문완료'
                            all_data.loc[all_data['id'].isin(to_confirm), 'batch_id'] = f"{res}_확정"
                            conn.update(worksheet="orders", data=all_data)
                            st.rerun()

        # 확정 내역 표시
        done = today_data[today_data['status'] == '주문완료']
        if not done.empty:
            st.subheader("✅ 확정 완료 명단")
            st.dataframe(done[['batch_id', 'user_name', 'items', 'total_price']], hide_index=True)

# --- [Tab 3: 지난 기록] ---
with tab3:
    st.subheader("📜 누적 주문 기록")
    st.dataframe(all_data, hide_index=True)
