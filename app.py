import streamlit as st
import pandas as pd
import sqlite3
import datetime
import os

# --- 1. 데이터베이스 설정 ---
DB_FILE = "delivery.db"

def get_db_connection():
    # 데이터베이스 파일 연결 (없으면 자동 생성)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

def init_db():
    """앱 실행 시 테이블이 없으면 생성"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            order_date TEXT,
            department TEXT,
            user_name TEXT,
            restaurant TEXT,
            items TEXT,
            total_price INTEGER,
            delivery_fee INTEGER DEFAULT 0,
            over_price INTEGER DEFAULT 0,
            status TEXT DEFAULT '주문대기',
            batch_id TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

# 앱 시작 시 DB 초기화
init_db()

# --- 2. 외부 CSV 파일 로드 ---
@st.cache_data
def load_external_data():
    try:
        staff = pd.read_csv('staff.csv')
        menu = pd.read_csv('menu.csv')
        return staff, menu
    except FileNotFoundError:
        st.error("🚨 staff.csv 또는 menu.csv 파일이 없습니다. 파일을 업로드해 주세요.")
        return pd.DataFrame(columns=['name', 'department']), pd.DataFrame(columns=['restaurant', 'item_name', 'price'])

staff_df, menu_df = load_external_data()

# --- 3. 앱 설정 및 스타일 ---
st.set_page_config(page_title='인천생활과학고 "밥먹고 초근하자"', page_icon="🍱", layout="wide")
today_str = datetime.date.today().strftime('%Y-%m-%d')

st.title('🍱 인천생활과학고 "밥먹고 초근하자"')
st.markdown(f"### 📅 오늘은 **{today_str}** 입니다.")

tab1, tab2, tab3 = st.tabs(["🍴 맛있는 주문", "📋 관리자 데스크", "📜 지난 기록"])

# --- [Tab 1: 주문하기] ---
with tab1:
    st.info("💡 부서 → 이름 → 식당 순으로 선택 후 주문하세요. (SQLite DB 적용 중)")
    
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
            conn = get_db_connection()
            # 중복 체크
            existing = pd.read_sql("SELECT * FROM orders WHERE order_date=? AND user_name=?", conn, params=(today_str, user_name))
            
            if not existing.empty:
                st.error("❌ 이미 오늘 주문하셨습니다!")
            else:
                total_food = sum([int(s.split('(')[1].replace('원)', '').replace(',', '')) for s in selected_display])
                items_str = ", ".join([s.split(' (')[0] for s in selected_display])
                order_id = str(datetime.datetime.now().timestamp())
                
                cur = conn.cursor()
                cur.execute("INSERT INTO orders (id, order_date, department, user_name, restaurant, items, total_price) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (order_id, today_str, dept, user_name, selected_res, items_str, total_food))
                conn.commit()
                st.success("🎉 주문 완료! 메뉴가 초기화됩니다.")
                st.balloons()
                st.rerun()
            conn.close()

# --- [Tab 2: 관리자 데스크] ---
with tab2:
    conn = get_db_connection()
    today_data = pd.read_sql(f"SELECT * FROM orders WHERE order_date='{today_str}'", conn)
    
    if today_data.empty:
        st.info("오늘 접수된 주문이 없습니다.")
    else:
        pending = today_data[today_data['status'] == '주문대기']
        if not pending.empty:
            st.markdown("#### ⏳ 확정 대기 목록 (체크 후 확정하거나 삭제하세요)")
            for res in pending['restaurant'].unique():
                res_orders = pending[pending['restaurant'] == res]
                with st.expander(f"📍 {res} (대기 {len(res_orders)}건)", expanded=True):
                    # 배달비 로직
                    order_count = len(res_orders)
                    food_sum = res_orders['total_price'].sum()
                    if res == '아말피': d_fee = 3000 if order_count == 1 else 4000
                    elif res == '오르드브': d_fee = 2000 if order_count == 1 else 4000
                    elif res == '장강': d_fee = 0
                    else: d_fee = 4000
                    if res == '오르드브' and food_sum >= 50000: d_fee = 0
                    per_fee = d_fee // order_count
                    
                    st.write(f"💰 예상 배달비: 총 {d_fee:,}원 (1인당 {per_fee:,}원)")
                    
                    to_action = []
                    for _, row in res_orders.iterrows():
                        if st.checkbox(f"{row['user_name']} | {row['items']} ({row['total_price']:,}원)", key=f"chk_{row['id']}"):
                            to_action.append(row['id'])
                    
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if st.button(f"✅ {res} 선택 확정", key=f"conf_{res}"):
                            if to_action:
                                cur = conn.cursor()
                                # 차수(batch_id) 계산
                                done_batches = today_data[today_data['status']=='주문완료']['batch_id'].unique()
                                b_id = f"{len(done_batches)+1}차({res})"
                                for tid in to_action:
                                    # 초과금 계산 (음식값+배달비 - 9000)
                                    row_data = res_orders[res_orders['id'] == tid].iloc[0]
                                    over = max(0, (row_data['total_price'] + per_fee) - 9000)
                                    cur.execute("UPDATE orders SET status='주문완료', batch_id=?, delivery_fee=?, over_price=? WHERE id=?", (b_id, per_fee, over, tid))
                                conn.commit()
                                st.rerun()
                    with b_col2:
                        if st.button(f"🗑️ {res} 선택 삭제", key=f"del_{res}"):
                            if to_action:
                                cur = conn.cursor()
                                for tid in to_action:
                                    cur.execute("DELETE FROM orders WHERE id=?", (tid,))
                                conn.commit()
                                st.rerun()

        # 완료 내역 출력
        done = today_data[today_data['status'] == '주문완료']
        if not done.empty:
            st.divider()
            st.subheader("✅ 오늘 주문 확정 내역")
            
            # 차수(batch_id)별로 그룹을 지어 각각 표를 그려줍니다.
            for batch in sorted(done['batch_id'].unique()):
                with st.container():
                    st.markdown(f"#### 🏷️ {batch}") # 예: 1차(아말피), 2차(오르드브)
                    batch_df = done[done['batch_id'] == batch]
                    
                    # 보기 좋게 열 순서와 이름 조정
                    display_df = batch_df[['department', 'user_name', 'items', 'total_price', 'delivery_fee', 'over_price']]
                    display_df.columns = ['부서', '성함', '메뉴', '음식값', '배달비', '개인부담금']
                    
                    st.table(display_df)
                    
                    # 차수별 합계 요약 (선택 사항)
                    total_sum = batch_df['total_price'].sum() + batch_df['delivery_fee'].sum()
                    st.caption(f"💰 {batch} 총결제액: {total_sum:,}원")
                    st.write("") # 간격 띄우기

    conn.close()

# --- [Tab 3: 지난 기록] ---
with tab3:
    search_date = st.date_input("날짜 선택", datetime.date.today())
    conn = get_db_connection()
    history = pd.read_sql("SELECT * FROM orders WHERE order_date=? AND status='주문완료'", conn, params=(search_date.strftime('%Y-%m-%d'),))
    if not history.empty:
        st.table(history)
    else:
        st.write("해당 날짜의 기록이 없습니다.")
    conn.close()
