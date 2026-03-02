import streamlit as st
import sqlite3
import datetime
import pandas as pd

# 1. 페이지 설정
st.set_page_config(
    page_title='인천생활과학고 "밥먹고 초근하자"',
    page_icon="🍱",
    layout="wide"
)

# --- 스타일링 (CSS 인젝션 - 관리자 체크박스 강조 추가) ---
st.markdown("""
    <style>
    /* 기존 스타일 유지 */
    .stAlert { padding: 15px; border-radius: 10px; }
    .stButton>button { border-radius: 10px; font-weight: bold; }
    .stExpander { border: none; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-radius: 10px; }
    
    /* 🔥 [추가] 관리자 체크박스 특수 강조 스타일 🔥 */
    div[data-testid="stCheckbox"] {
        transform: scale(1.3); /* 크기 30% 확대 */
        margin-left: 5px;
    }
    
    div[data-testid="stCheckbox"] > label > div[aria-checked="true"] {
        background-color: #007bff !important; /* 체크 시 파란색 배경 */
        border-color: #007bff !important;
    }
    
    div[data-testid="stCheckbox"] > label > div[aria-checked="false"] {
        border: 2px solid #6c757d !important; /* 미체크 시 진한 회색 테두리 */
        background-color: white !important;
    }
    
    /* 표 헤더 강조 */
    .header-style {
        font-weight: bold;
        color: #495057;
        background-color: #e9ecef;
        padding: 5px;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# DB 연결 함수
def get_db_connection():
    conn = sqlite3.connect('meal_data.db')
    conn.row_factory = sqlite3.Row
    return conn

today = datetime.date.today()
today_str = today.strftime('%Y-%m-%d')

# --- 세션 초기화 및 메뉴 리셋 로직 ---
if "menu_selection" not in st.session_state:
    st.session_state.menu_selection = []

def reset_on_change():
    # 상위 선택지가 바뀌면 하위 선택지들을 초기화
    if "menu_selection" in st.session_state:
        st.session_state.menu_selection = []

# 메인 헤더
st.title('🍱 인천생활과학고 "밥먹고 초근하자"')
st.caption(f"📅 오늘은 {today.strftime('%Y년 %m월 %d일')}입니다. 오늘도 힘내세요, 선생님!")

tab1, tab2, tab3 = st.tabs(["🍴 맛있는 주문", "📋 관리자 데스크", "📜 지난 기록"])

# --- [Tab 1: 주문하기] ---
with tab1:
    # 1. 안내 문구 (항상 노출)
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 20px;">
        <h4 style="margin-top:0;">ℹ️ 식당 및 배송비 안내</h4>
        💡 <b>성함과 메뉴를 정확히 확인하신 후 [주문 확정]을 눌러주세요.</b> 여럿이 한꺼번에 주문하면 배송료를 아낍니다. ^ ^ <br><br>
        <ul>
            <li>🥗 <b>오르드브</b>: 샌드위치, 샐러드 전문 / 1인 주문 시 2,000원, 단체 4,000원 (5만원 이상 무료)</li>
            <li>🥪 <b>아말피</b>: 식사부터 샌드위치까지 다양 / 개인 및 단체 모두 4,000원</li>
            <li>🍜 <b>장강</b>: 기본 중국집 / 배송료 없음</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    conn = get_db_connection()
    try:
        # 데이터 로드 및 '선택하세요' 추가
        depts_raw = [row['department'] for row in conn.execute('SELECT DISTINCT department FROM staff ORDER BY department').fetchall()]
        depts = ["--- 부서 선택 ---"] + depts_raw
        
        res_raw = [row['restaurant'] for row in conn.execute('SELECT DISTINCT restaurant FROM menu ORDER BY restaurant').fetchall()]
        restaurants = ["--- 식당 선택 ---"] + res_raw
        
        col1, col2, col3 = st.columns(3)
        
        # [단계 1] 부서 선택
        with col1:
            dept = st.selectbox("🏢 부서 선택", depts, key="dept_select", on_change=reset_on_change)
        
        # [단계 2] 이름 선택
        with col2:
            if dept != "--- 부서 선택 ---":
                staff_raw = [row['name'] for row in conn.execute('SELECT name FROM staff WHERE department = ? ORDER BY name', (dept,)).fetchall()]
                staff_list = ["--- 이름 선택 ---"] + staff_raw
                user_name = st.selectbox("👤 이름 선택", staff_list, key="name_select", on_change=reset_on_change)
            else:
                st.selectbox("👤 이름 선택", ["부서를 먼저 선택하세요"], disabled=True)
                user_name = "--- 이름 선택 ---"

        # [단계 3] 식당 선택
        with col3:
            if user_name != "--- 이름 선택 ---" and user_name != "부서를 먼저 선택하세요":
                selected_res = st.selectbox("🏪 식당 선택", restaurants, key="res_select", on_change=reset_on_change)
            else:
                st.selectbox("🏪 식당 선택", ["이름을 먼저 선택하세요"], disabled=True)
                selected_res = "--- 식당 선택 ---"

        st.divider()
        
        # [단계 4] 메뉴 선택 및 주문 버튼
        if selected_res != "--- 식당 선택 ---":
            menus = conn.execute('SELECT item_name, price FROM menu WHERE restaurant = ?', (selected_res,)).fetchall()
            menu_options = [f"{m['item_name']} ({m['price']:,}원)" for m in menus]
            
            selected_display = st.multiselect(
                "📝 메뉴보기", 
                menu_options, 
                key="menu_selection",
                placeholder="클릭하면 메뉴가 나옵니다."
            )
            
            if selected_display:
                total_food_price = 0
                pure_items = []
                for s in selected_display:
                    parts = s.split(" (")
                    item_name = parts[0]
                    price_val = int(parts[1].replace("원)", "").replace(",", ""))
                    total_food_price += price_val
                    pure_items.append(item_name)

                # 🔥 [추가된 강조 안내창] 🔥
                st.markdown(f"""
                    <div style="background-color: #fff3cd; padding: 20px; border-radius: 10px; border: 2px solid #ffecb5; margin-top: 10px; margin-bottom: 10px; text-align: center;">
                        <h3 style="margin: 0; color: #856404;">⚠️ 마지막 단계입니다!</h3>
                        <p style="margin: 10px 0; font-size: 1.1em;">선택하신 메뉴가 맞다면 아래 <b>[🚀 주문 확정하기]</b> 버튼을 꼭 눌러주세요.</p>
                        <hr style="border: 0.5px solid #ffecb5;">
                        <p style="font-size: 1.3em; color: #d63384; margin: 0;"><b>총 주문 금액: {total_food_price:,}원</b></p>
                    </div>
                """, unsafe_allow_html=True)

                # --- [수정 구간 시작] ---
                if st.button("🚀 주문 확정하기 (이 버튼을 클릭하세요!)", type="primary", use_container_width=True):
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO orders (order_date, department, user_name, restaurant, items, total_price, status)
                        VALUES (?, ?, ?, ?, ?, ?, '주문대기')
                    ''', (today_str, dept, user_name, selected_res, ", ".join(pure_items), total_food_price))
                    conn.commit()
                    
                    # 1. 시각적 피드백
                    st.balloons() 
                    
                    # 2. 주문 완료 및 안내 메시지 출력
                    st.success(f"### 🎉 주문이 정상적으로 접수되었습니다!")
                    st.markdown(f"""
                        <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #28a745; margin-bottom: 20px;">
                            <h4 style="color: #28a745; margin-top: 0;">📋 {user_name} 선생님의 주문 내역</h4>
                            <p style="font-size: 1.1em; margin: 5px 0;"><b>식당:</b> {selected_res}</p>
                            <p style="font-size: 1.1em; margin: 5px 0;"><b>메뉴:</b> {', '.join(pure_items)}</p>
                            <p style="font-size: 1.1em; margin: 5px 0;"><b>음식 합계:</b> {total_food_price:,}원</p>
                            <hr>
                            <p style="color: #d63384; font-weight: bold; font-size: 1.05em; text-align: center; margin: 0;">
                                ⚠️ 주문 수정 및 삭제는 <b>교무기획부</b> 또는 <b>해당 식당</b>에 문의해 주세요.
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 3. 메뉴 선택창 비우기 (세션 삭제)
                    if "menu_selection" in st.session_state:
                        del st.session_state["menu_selection"]
                    
                    # 4. 새로고침 버튼 (안내문을 다 읽으신 후 누르도록 유도)
                    if st.button("🔄 확인 (새 주문 화면으로)"):
                        st.rerun()
                # --- [수정 구간 끝] ---

        else:
            st.info("💡 위에서 **부서 → 이름 → 식당**을 순서대로 선택하시면 메뉴판이 나타납니다.")

    except Exception as e:
        st.error(f"알림: {e}")
    finally:
        conn.close() # <--- 이 부분은 건드리지 마세요!


# --- [Tab 2: 관리자 데스크] ---
with tab2:
    st.header("👨‍💻 관리자 주문 취합 현황")
    conn = get_db_connection()
    # 오늘 날짜의 모든 데이터를 다시 불러옴
    all_today = conn.execute("SELECT * FROM orders WHERE order_date = ?", (today_str,)).fetchall()
    
    # 중복 체크용 이름 카운트
    name_counts = {}
    for row in all_today:
        name_counts[row['user_name']] = name_counts.get(row['user_name'], 0) + 1

    if not all_today:
        st.info("아직 접수된 주문이 없습니다. ☕")
    else:
        # 1. 미확정 주문 (주문대기) 영역
        pending = [row for row in all_today if row['status'] == '주문대기']
        if pending:
            st.subheader("🆕 접수된 신규 주문 (미확정)")
            res_groups = {}
            for p in pending: 
                res_groups.setdefault(p['restaurant'], []).append(p)

            for res, orders in res_groups.items():
                to_process_res = [] 
                with st.expander(f"📍 {res} (대기 {len(orders)}건)", expanded=True):
                    food_sum = sum([o['total_price'] for o in orders])
                    order_count = len(orders)
                    
                    # 배달비 계산 로직
                    d_fee = 0
                    if res == '장강': d_fee = 0
                    elif res == '아말피': d_fee = 4000
                    elif res == '오르드브':
                        d_fee = 0 if food_sum >= 50000 else (2000 if order_count == 1 else 4000)
                    
                    per_fee = d_fee // order_count if order_count > 0 else 0
                    
                    # 상단 지표 (Metric)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("음식 합계", f"{food_sum:,}원")
                    m2.metric("총 배달비", f"{d_fee:,}원")
                    m3.metric("1인당 배달비", f"{per_fee:,}원")

                    st.markdown("---")
                    
                    # 표 헤더 (스타일 적용)
                    h_col = st.columns([0.1, 0.15, 0.15, 0.1, 0.25, 0.1, 0.15])
                    cols = ["선택", "부서", "성함", "비고", "메뉴", "음식값", "개인부담"]
                    for col, text in zip(h_col, cols): 
                        col.markdown(f'<p style="font-weight:bold; color:#495057; background-color:#e9ecef; padding:5px; border-radius:5px; text-align:center;">{text}</p>', unsafe_allow_html=True)
                    
                    # 주문 목록 한 줄씩 출력
                    for o in orders:
                        final_over = max(0, (o['total_price'] + per_fee) - 9000)
                        dup = "⚠️중복" if name_counts[o['user_name']] > 1 else ""
                        c = st.columns([0.1, 0.15, 0.15, 0.1, 0.25, 0.1, 0.15])
                        with c[0]:
                            # 스타일 시트에서 scale(1.3) 적용된 체크박스
                            if st.checkbox("", key=f"sel_{o['id']}"):
                                to_process_res.append({"id": o['id'], "fee": per_fee, "over": final_over})
                        c[1].write(o['department'])
                        c[2].write(o['user_name'])
                        c[3].markdown(f"<p style='color:red; text-align:center;'>{dup}</p>", unsafe_allow_html=True)
                        c[4].write(o['items'])
                        c[5].write(f"{o['total_price']:,}")
                        c[6].markdown(f"<p style='color:#d63384; font-weight:bold;'>{final_over:,}원</p>", unsafe_allow_html=True)

                    # 확정/삭제 버튼 배치
                    st.write("")
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(f"✅ {res} 주문 확정", key=f"conf_{res}", type="primary", use_container_width=True):
                            if to_process_res:
                                existing_batches = conn.execute("SELECT DISTINCT batch_id FROM orders WHERE order_date=? AND status='주문완료'", (today_str,)).fetchall()
                                batch_name = f"{len(existing_batches)+1}차({res})"
                                cursor = conn.cursor()
                                for item in to_process_res:
                                    cursor.execute("UPDATE orders SET status='주문완료', batch_id=?, delivery_fee=?, over_price=? WHERE id=?",
                                                 (batch_name, item['fee'], item['over'], item['id']))
                                conn.commit()
                                st.rerun()
                            else: st.warning("대상을 선택해주세요.")
                    with btn_col2:
                        if st.button(f"🗑️ {res} 주문 삭제", key=f"del_{res}", use_container_width=True):
                            if to_process_res:
                                cursor = conn.cursor()
                                for item in to_process_res:
                                    cursor.execute("DELETE FROM orders WHERE id=?", (item['id'],))
                                conn.commit()
                                st.rerun()
                            else: st.warning("삭제할 대상을 선택해주세요.")

        # 2. 확정 완료 영역 (차수별 분리)
        done = [row for row in all_today if row['status'] == '주문완료']
        if done:
            st.markdown("---")
            st.subheader("✅ 오늘 확정 완료 내역 (차수별 요약)")
            
            df_done = pd.DataFrame([dict(d) for d in done])
            batches = df_done['batch_id'].unique()
            
            for b_id in sorted(batches):
                b_df = df_done[df_done['batch_id'] == b_id]
                
                # 차수별 금액 계산
                b_food_total = b_df['total_price'].sum()
                b_delivery_total = b_df['delivery_fee'].sum()
                b_final_total = b_food_total + b_delivery_total
                
                with st.container():
                    st.markdown(f"""
                    <div style="background-color: #e8f4ea; padding: 15px; border-radius: 10px; border: 1px solid #c3e6cb; margin-bottom: 10px;">
                        <h4 style="margin:0; color: #28a745;">📋 {b_id} 결제 요약</h4>
                        <span style="font-size: 1.1em;">음식값: <b>{b_food_total:,}원</b> + 배달비: <b>{b_delivery_total:,}원</b> = 
                        <span style="color: #d63384; font-size: 1.2em;"><b>최종 결제액: {b_final_total:,}원</b></span></span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 차수별 상세 표
                    display_df = b_df[['department', 'user_name', 'items', 'total_price', 'delivery_fee', 'over_price']].copy()
                    display_df.columns = ['부서', '이름', '메뉴', '음식값', '배달비분담', '개인부담금']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    st.write("") 
    conn.close()

# --- [Tab 3: 과거 주문 내역] ---
with tab3:
    st.header("📅 지난 주문 기록")
    search_date = st.date_input("날짜를 선택하세요", today)
    conn = get_db_connection()
    history = conn.execute("SELECT * FROM orders WHERE order_date = ? AND status = '주문완료' ORDER BY batch_id ASC", (search_date.strftime('%Y-%m-%d'),)).fetchall()
    if history:
        df_hist = pd.DataFrame([dict(h) for h in history])[['batch_id', 'department', 'user_name', 'restaurant', 'items', 'total_price', 'delivery_fee', 'over_price']]
        df_hist.columns = ['차수', '부서', '성함', '식당', '메뉴', '음식값', '배달비', '초과금']
        st.table(df_hist)
        total_sum = sum([h['total_price'] for h in history])
        st.metric("총 결제 금액", f"{total_sum:,}원")
    else: st.warning("기록이 없습니다.")
    conn.close()