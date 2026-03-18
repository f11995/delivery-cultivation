import streamlit as st
import pandas as pd
from datetime import date, time, datetime, timedelta
import calendar
import plotly.express as px
import plotly.graph_objects as go
import json
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# ⚙️ 系統常數與專業設定
# ==========================================
CUSTOM_COLORS = {"Uber Eats": "#06C167", "Foodpanda": "#FF2B85", "其他獎金": "#F6C143", "休假": "#8E8E93", "開銷": "#FF453A"}

DRIVER_TIERS = [
    (0, "新手駕駛", "Rookie", "🔰"), (10000, "青銅夥伴 I", "Bronze I", "🥉"), (30000, "青銅夥伴 II", "Bronze II", "🥉"), (60000, "青銅夥伴 III", "Bronze III", "🥉"),
    (100000, "白銀專家 I", "Silver I", "🥈"), (150000, "白銀專家 II", "Silver II", "🥈"), (200000, "白銀專家 III", "Silver III", "🥈"),
    (300000, "黃金菁英 I", "Gold I", "🥇"), (400000, "黃金菁英 II", "Gold II", "🥇"), (500000, "黃金菁英 III", "Gold III", "🥇"),
    (600000, "白金先鋒 I", "Platinum I", "💠"), (800000, "白金先鋒 II", "Platinum II", "💠"), (1000000, "白金先鋒 III", "Platinum III", "💠"),
    (1500000, "鑽石大師 I", "Diamond I", "💎"), (2000000, "鑽石大師 II", "Diamond II", "💎"), (3000000, "鑽石大師 III", "Diamond III", "💎"),
    (5000000, "巔峰傳奇", "Apex Legend", "👑")
]

# ==========================================
# 🌐 單機版專屬資料庫引擎 (極速、無冗餘)
# ==========================================
@st.cache_resource
def get_gspread_client():
    try:
        creds_dict = json.loads(st.secrets["GOOGLE_KEY"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 資料庫連線失敗：{e}")
        st.stop()

@st.cache_resource
def get_sheet():
    client = get_gspread_client()
    try: return client.open_by_url(st.secrets["SHEET_URL"])
    except Exception as e:
        st.error(f"❌ 找不到試算表！請確認網址正確：{e}")
        st.stop()

@st.cache_resource
def get_records_ws():
    sheet = get_sheet()
    try: return sheet.worksheet("Records")
    except gspread.exceptions.WorksheetNotFound: 
        ws = sheet.add_worksheet(title="Records", rows="1000", cols="10")
        ws.append_row(["日期", "類型", "項目", "金額", "上線時數", "備註", "異常"])
        return ws

@st.cache_resource
def get_settings_ws():
    sheet = get_sheet()
    try: return sheet.worksheet("Settings")
    except gspread.exceptions.WorksheetNotFound: 
        ws = sheet.add_worksheet(title="Settings", rows="100", cols="5")
        ws.append_row(["目標月份", "目標金額"])
        return ws

@st.cache_data(ttl=10, show_spinner=False)
def load_data():
    ws = get_records_ws()
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        if "上線時數" not in df.columns: df["上線時數"] = 0.0
        if "異常" not in df.columns: df["異常"] = "False"
        df['日期'] = pd.to_datetime(df['日期'])
    return df

@st.cache_data(ttl=10, show_spinner=False)
def load_settings():
    ws = get_settings_ws()
    records = ws.get_all_records()
    if not records:
        ws.append_row(["", 0])
        return {"目標月份": "", "目標金額": 0}
    return records[0]

def save_data(date_val, record_type, item, amount, hours, note, is_incident):
    with st.spinner("⏳ 同步至雲端..."):
        ws = get_records_ws()
        ws.append_row([str(date_val), str(record_type), str(item), int(amount), float(hours), str(note), str(is_incident)])
        load_data.clear()

def delete_data(indices_to_drop):
    with st.spinner("⏳ 移除紀錄中..."):
        ws = get_records_ws()
        for idx in sorted(indices_to_drop, reverse=True): ws.delete_rows(idx + 2)
        load_data.clear()

def update_setting(col_name, value):
    ws = get_settings_ws()
    headers = ws.row_values(1)
    if col_name in headers:
        col_idx = headers.index(col_name) + 1
        if isinstance(value, (int, float)): ws.update_cell(2, col_idx, float(value) if isinstance(value, float) else int(value))
        else: ws.update_cell(2, col_idx, str(value))
        load_settings.clear()

# ==========================================
# 輔助計算函數
# ==========================================
def get_driver_tier_info(total_exp):
    current_tier, current_title, current_avatar = "新手駕駛", "Rookie", "🔰"
    next_tier, next_exp, prev_exp = "N/A", 10000, 0
    for i in range(len(DRIVER_TIERS)):
        if total_exp >= DRIVER_TIERS[i][0]:
            current_tier, current_title, current_avatar = DRIVER_TIERS[i][1], DRIVER_TIERS[i][2], DRIVER_TIERS[i][3]
            prev_exp = DRIVER_TIERS[i][0]
            if i + 1 < len(DRIVER_TIERS): next_tier, next_exp = DRIVER_TIERS[i+1][1], DRIVER_TIERS[i+1][0]
            else: next_tier, next_exp = "MAX TIER", total_exp
        else: break
    progress = 1.0 if next_tier == "MAX TIER" else min((total_exp - prev_exp) / (next_exp - prev_exp), 1.0)
    return current_tier, next_tier, next_exp, progress, current_title, current_avatar

# ==========================================
# 🎨 頂級 App 視覺樣式 (Fintech Style)
# ==========================================
st.set_page_config(page_title="Delivery Pro", layout="wide", page_icon="📊")
st.markdown("""
<style>
    /* 全局背景黑化、系統字體 */
    .stApp { background-color: #000000; color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px;}
    
    /* 質感卡片 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1C1C1E !important;
        border: none !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1.2rem;
    }

    /* 關鍵指標設計 */
    .kpi-title { font-size: 13px; font-weight: 600; color: #8E8E93; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
    .kpi-value { font-size: 40px; font-weight: 700; color: #FFFFFF; line-height: 1.1; letter-spacing: -1px;}
    .kpi-sub { font-size: 14px; color: #06C167; font-weight: 600; margin-top: 4px;}
    
    /* 側邊欄設計 */
    section[data-testid="stSidebar"] { background-color: #121212 !important; border-right: 1px solid #2C2C2E;}
    .sidebar-brand { font-size: 24px; font-weight: 800; color: #FFFFFF; margin-bottom: 30px; padding-left: 5px; letter-spacing: -0.5px;}
    .sidebar-brand span { color: #06C167; }
    
    /* 進度條美化 */
    .stProgress > div > div > div > div { background-color: #06C167; }
    
    /* 隱藏預設圖表背景 */
    .js-plotly-plot .plotly .bg { fill: transparent !important; }
    
    /* 帳本清單設計 */
    .ledger-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #2C2C2E; align-items: center;}
    .ledger-row:last-child { border-bottom: none; }
    .l-date { font-weight: 600; font-size: 16px; color: #FFF; width: 100px;}
    .l-detail { flex-grow: 1; color: #8E8E93; font-size: 14px; }
    .l-amount { font-weight: 700; font-size: 18px; text-align: right;}
    .c-green { color: #06C167; }
    .c-red { color: #FF453A; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛡️ 系統登入 
# ==========================================
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<br><br><div style='text-align: center;'><h1 style='color: #FFFFFF; font-size: 48px; font-weight:800; letter-spacing:-1px;'>Delivery <span style='color:#06C167;'>Pro</span></h1><p style='color:#8E8E93; font-size: 16px;'>Professional Courier Analytics</p></div><br>", unsafe_allow_html=True)
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        pwd_input = st.text_input("Access Token", type="password", placeholder="Enter secure token...")
        if st.button("Log In", type="primary", use_container_width=True):
            app_pwd = st.secrets.get("APP_PASSWORD", "")
            if pwd_input == app_pwd:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("❌ Invalid Token.")
    st.stop()

# ==========================================
# 資料讀取與前置運算
# ==========================================
df = load_data()
settings = load_settings()

if "selected_date" not in st.session_state: st.session_state.selected_date = date.today()
if "input_key" not in st.session_state: st.session_state.input_key = 0
if "show_success" not in st.session_state: st.session_state.show_success = False

k = st.session_state.input_key
today = date.today()

# 計算終身數據
total_income = df[df['類型'] == '收入']['金額'].sum() if not df.empty else 0
total_hours = df[df['類型'] == '收入']['上線時數'].sum() if not df.empty else 0.0
total_gas_maint = df[(df['類型'] == '開銷') & (df['項目'].isin(['機車油錢', '機車保養']))]['金額'].sum() if not df.empty else 0

roi = (total_income / total_gas_maint) if total_gas_maint > 0 else total_income
driver_tier, next_tier, next_exp, prog, d_title, d_icon = get_driver_tier_info(total_income)

# ==========================================
# 側邊欄導覽
# ==========================================
with st.sidebar:
    st.markdown("<div class='sidebar-brand'>Delivery <span>Pro</span></div>", unsafe_allow_html=True)
    page = st.radio("Navigation", ["📊 總覽 (Dashboard)", "➕ 記一筆 (Add Log)", "📈 報表 (Analytics)", "⚙️ 設定 (Settings)"], label_visibility="collapsed")
    
    st.divider()
    st.markdown(f"<div style='color:#8E8E93; font-size:12px; margin-bottom:5px;'>DRIVER TIER</div><div style='font-size:18px; font-weight:600; color:#FFF;'>{d_icon} {driver_tier}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:#8E8E93; font-size:12px; margin-top:15px; margin-bottom:5px;'>LIFETIME REVENUE</div><div style='font-size:18px; font-weight:600; color:#06C167;'>${int(total_income):,}</div>", unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🔄 強制同步 (Sync)", use_container_width=True):
        load_data.clear()
        load_settings.clear()
        st.rerun()

# ==========================================
# 頁面內容：📊 總覽 (Dashboard)
# ==========================================
if page == "📊 總覽 (Dashboard)":
    st.title("Dashboard")
    
    # 計算本週與今日數據
    start_of_week = today - timedelta(days=today.weekday())
    this_week_df = df[(df['日期'].dt.date >= start_of_week) & (df['日期'].dt.date <= today)] if not df.empty else pd.DataFrame()
    today_df = df[df['日期'].dt.date == today] if not df.empty else pd.DataFrame()
    
    w_inc = this_week_df[this_week_df['類型'] == '收入']['金額'].sum() if not this_week_df.empty else 0
    t_inc = today_df[today_df['類型'] == '收入']['金額'].sum() if not today_df.empty else 0
    
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("<div class='kpi-title'>今日收入 (Today)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-value'>${int(t_inc):,}</div>", unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("<div class='kpi-title'>本週累積 (This Week)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-value'>${int(w_inc):,}</div>", unsafe_allow_html=True)
    with c3:
        with st.container(border=True):
            st.markdown("<div class='kpi-title'>投資報酬率 (Fuel ROI)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-value'>1 : {roi:.1f}</div>", unsafe_allow_html=True)
            
    with st.container(border=True):
        st.markdown("#### 🏆 駕駛評級進度 (Tier Progress)")
        st.markdown(f"<div style='font-size:24px; font-weight:700;'>{d_icon} {driver_tier}</div>", unsafe_allow_html=True)
        st.progress(prog)
        st.markdown(f"<div style='font-size: 13px; color: #8E8E93; margin-top: 8px; display:flex; justify-content:space-between;'><span>累積：${int(total_income):,}</span><span>距離 {next_tier} 還差：${int(next_exp - total_income):,}</span></div>", unsafe_allow_html=True)

# ==========================================
# 頁面內容：➕ 記一筆 (Add Log)
# ==========================================
elif page == "➕ 記一筆 (Add Log)":
    st.title("Log Shift")
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        with st.container(border=True):
            if st.session_state.show_success: st.success("✅ 紀錄已安全儲存。"); st.session_state.show_success = False
            
            temp_date = st.date_input("🗓️ 選擇日期", value=st.session_state.selected_date)
            if temp_date != st.session_state.selected_date: st.session_state.selected_date = temp_date; st.rerun()
            record_date = st.session_state.selected_date
    
            record_type = st.radio("類別", ["收入", "開銷", "休假"], horizontal=True)
            st.write("---")
    
            if record_type == "收入":
                platform_mode = st.radio("平台模式", ["單一平台", "雙開合併"], horizontal=True)
                if platform_mode == "單一平台":
                    item = st.selectbox("選擇平台", ["Uber Eats", "Foodpanda", "其他獎金"])
                    amount = st.number_input("💰 總收入 (TWD)", min_value=0, step=10, value=None, key=f"amt_{k}")
                    val_amount = amount if amount is not None else 0
                else:
                    u_col, f_col = st.columns(2)
                    with u_col: amount_u = st.number_input("Uber Eats", min_value=0, step=10, value=None, key=f"amtu_{k}")
                    with f_col: amount_f = st.number_input("Foodpanda", min_value=0, step=10, value=None, key=f"amtf_{k}")
                    val_amount = (amount_u or 0) + (amount_f or 0)
                    
                time_mode = st.radio("時數計算", ["APP 剩餘時間反推 (12H制)", "手動輸入", "系統換算 (首至末單)"], horizontal=True)
                
                if time_mode == "系統換算 (首至末單)":
                    t_col1, t_col2 = st.columns(2)
                    with t_col1: start_time = st.time_input("首單時間", time(10, 0), key=f"t1_{k}") 
                    with t_col2: end_time = st.time_input("末單時間", time(22, 0), key=f"t2_{k}")   
                    dt_start, dt_end = datetime.combine(date(2000, 1, 1), start_time), datetime.combine(date(2000, 1, 1), end_time)
                    if dt_end < dt_start: dt_end += timedelta(days=1)
                    hours = round((dt_end - dt_start).total_seconds() / 3600.0, 2)
                    st.info(f"⏱️ 系統換算：**{hours} h**")
                elif time_mode == "手動輸入":
                    h_col, m_col = st.columns(2)
                    with h_col: input_hours = st.number_input("小時", min_value=0, step=1, value=None, key=f"hr_{k}")
                    with m_col: input_minutes = st.number_input("分鐘", min_value=0, max_value=59, step=1, value=None, key=f"min_{k}")
                    hours = round((input_hours or 0) + ((input_minutes or 0) / 60.0), 2)
                else: 
                    st.caption("💡 輸入 APP 上方顯示的「剩餘可用駕駛時間」：")
                    h_col, m_col = st.columns(2)
                    with h_col: remain_hours = st.number_input("剩餘小時", min_value=0, max_value=12, step=1, value=None, key=f"r_hr_{k}")
                    with m_col: remain_minutes = st.number_input("剩餘分鐘", min_value=0, max_value=59, step=1, value=None, key=f"r_min_{k}")
                    if remain_hours is not None or remain_minutes is not None:
                        r_h = remain_hours or 0
                        r_m = remain_minutes or 0
                        used_mins = max(0, 720 - (r_h * 60 + r_m))
                        hours = round(used_mins / 60.0, 2)
                        st.info(f"⏱️ 反推上線：**{hours} h**")
                    else: hours = 0.0
                    
                is_incident = st.checkbox("⚠️ 標記異常 (奧客/車損/惡劣天氣)", key=f"trib_{k}")
                note = st.text_input("備註", value="", key=f"note_{k}")
    
                if st.button("📤 儲存收入紀錄", type="primary", use_container_width=True):
                    if platform_mode == "單一平台":
                        if val_amount > 0: save_data(record_date, record_type, item, val_amount, hours, note, is_incident); st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1; st.rerun()
                        else: st.warning("請輸入有效金額。")
                    else:
                        if (amount_u or 0) > 0 or (amount_f or 0) > 0:
                            if (amount_u or 0) > 0: save_data(record_date, record_type, "Uber Eats", amount_u, hours, note, is_incident)
                            if (amount_f or 0) > 0: save_data(record_date, record_type, "Foodpanda", amount_f, 0.0 if (amount_u or 0) > 0 else hours, note, is_incident)
                            st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1; st.rerun()
                        else: st.warning("請輸入有效金額。")
    
            elif record_type == "開銷": 
                expense_choice = st.selectbox("費用分類", ["機車油錢", "機車保養", "機車貸款", "設備耗材", "其他"])
                item = st.text_input("自訂名稱", key=f"item_{k}") if expense_choice == "其他" else expense_choice
                amount = st.number_input("金額 (TWD)", min_value=0, step=10, value=None, key=f"amt_{k}")
                note = st.text_input("備註", value="", key=f"note_{k}")
                if st.button("📤 儲存開銷", type="primary", use_container_width=True):
                    if (amount or 0) > 0 and item.strip() != "": save_data(record_date, record_type, item, amount, 0.0, note, False); st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1; st.rerun()
                    else: st.warning("請檢查金額與項目。")
            else:
                note = st.text_input("休假備註", value="", key=f"note_{k}")
                if st.button("📤 標記休假", type="primary", use_container_width=True):
                    save_data(record_date, record_type, "休假", 0, 0.0, note, False)
                    st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1
                    st.rerun()
    
    with col2:
        with st.container(border=True):
            st.markdown("#### 📅 當日明細總覽") 
            if not df.empty:
                daily_df = df[df['日期'].dt.date == st.session_state.selected_date]
                if not daily_df.empty:
                    d_inc = daily_df[daily_df['類型'] == '收入']['金額'].sum()
                    d_exp = daily_df[daily_df['類型'] == '開銷']['金額'].sum()
                    d_hr = daily_df[daily_df['類型'] == '收入']['上線時數'].sum()
                    d_wage = d_inc / d_hr if d_hr > 0 else 0
                    
                    c_sum1, c_sum2 = st.columns(2)
                    c_sum1.markdown(f"<div class='kpi-title'>當日總收入</div><div class='kpi-value text-green'>${int(d_inc):,}</div>", unsafe_allow_html=True)
                    c_sum2.markdown(f"<div class='kpi-title'>換算時薪</div><div class='kpi-value'>${int(d_wage):,}</div>", unsafe_allow_html=True)
                    st.write("")
                    c_sum3, c_sum4 = st.columns(2)
                    c_sum3.markdown(f"<div class='kpi-title'>總上線時數</div><div class='kpi-value' style='font-size:24px;'>{d_hr:.1f} h</div>", unsafe_allow_html=True)
                    c_sum4.markdown(f"<div class='kpi-title'>當日總開銷</div><div class='kpi-value text-red' style='font-size:24px;'>${int(d_exp):,}</div>", unsafe_allow_html=True)
                else: st.caption("此日期尚無紀錄。")
    
                if not daily_df.empty:
                    st.write("---")
                    st.markdown("##### 🛠️ 編輯歷史紀錄")
                    edit_df = daily_df.copy()
                    edit_df['日期'] = edit_df['日期'].dt.strftime('%Y-%m-%d')
                    edit_df.insert(0, "移除", False)
                    edited_df = st.data_editor(edit_df, hide_index=True, column_config={"移除": st.column_config.CheckboxColumn("勾選移除", default=False)}, disabled=["日期", "類型", "項目", "金額", "上線時數", "備註", "異常"], use_container_width=True, key=f"edit_{st.session_state.selected_date}_{k}")
                    rows_to_delete = edited_df[edited_df["移除"] == True].index.tolist()
                    if len(rows_to_delete) > 0:
                        if st.button("🗑️ 移除選取資料", type="primary", use_container_width=True):
                            delete_data(rows_to_delete)
                            st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1
                            st.rerun()

# ==========================================
# 頁面內容：📈 報表 (Analytics)
# ==========================================
elif page == "📈 報表 (Analytics)":
    st.title("Analytics")
    tab_m, tab_y = st.tabs(["📊 月度分析 (Monthly)", "📈 年度分析 (Yearly)"])
    
    with tab_m:
        if not df.empty:
            months = df['日期'].dt.to_period('M').astype(str).unique()
            mc1, mc2 = st.columns([1, 1])
            with mc1: selected_month = st.selectbox("📅 選擇檢視月份", sorted(months, reverse=True), label_visibility="collapsed")
            month_df = df[df['日期'].dt.to_period('M').astype(str) == selected_month]
            
            current_target = int(settings.get("目標金額", 0)) if str(settings.get("目標月份")) == selected_month else 0
    
            with mc2:
                with st.expander(f"🎯 設定 {selected_month} 預期目標收入"):
                    new_target = st.number_input("目標金額 (TWD)", min_value=0, step=1000, value=current_target)
                    if st.button("💾 儲存目標", type="primary"): 
                        update_setting("目標月份", str(selected_month))
                        update_setting("目標金額", int(new_target))
                        st.rerun()
    
            if not month_df.empty:
                t_inc = month_df[month_df['類型'] == '收入']['金額'].sum()
                t_exp = month_df[month_df['類型'] == '開銷']['金額'].sum()
                t_hr = month_df[month_df['類型'] == '收入']['上線時數'].sum()
                m_wage = t_inc / t_hr if t_hr > 0 else 0
                n_prof = t_inc - t_exp
    
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f"<div class='kpi-title'>月總收入</div><div class='kpi-value text-green'>${int(t_inc):,}</div>", unsafe_allow_html=True)
                    c2.markdown(f"<div class='kpi-title'>月淨利潤</div><div class='kpi-value'>${int(n_prof):,}</div>", unsafe_allow_html=True)
                    c3.markdown(f"<div class='kpi-title'>月總開銷</div><div class='kpi-value text-red'>${int(t_exp):,}</div>", unsafe_allow_html=True)
                    c4.markdown(f"<div class='kpi-title'>平均時薪</div><div class='kpi-value'>${int(m_wage):,}</div>", unsafe_allow_html=True)
                    
                    if current_target > 0:
                        st.write("")
                        st.progress(min(t_inc / current_target, 1.0))
                        rem = current_target - t_inc
                        if rem > 0: st.caption(f"🎯 距離目標還差 **${int(rem):,}**")
                        else: st.caption("🎉 已達成設定目標！")

                # 圖表區
                with st.container(border=True):
                    st.markdown("#### 📈 每日收支圖表")
                    trend_df = month_df[month_df['類型'] != '休假'].groupby(['日期', '項目', '類型'])['金額'].sum().reset_index()
                    trend_df.loc[trend_df['類型'] == '開銷', '金額'] *= -1
                    if not trend_df.empty:
                        fig_bar = px.bar(trend_df, x='日期', y='金額', color='項目', color_discrete_map=CUSTOM_COLORS, barmode='relative')
                        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF'), margin=dict(l=0, r=0, t=20, b=0), hovermode="x unified")
                        st.plotly_chart(fig_bar, use_container_width=True)

                # 🌟 每日明細清單 (App 帳本風格)
                st.markdown("### 📅 該月每日明細帳本 (Daily Ledger)")
                with st.container(border=True):
                    # 彙整每一天的數據
                    daily_agg = month_df.groupby(month_df['日期'].dt.date).apply(lambda x: pd.Series({
                        '收入': x[x['類型'] == '收入']['金額'].sum(),
                        '開銷': x[x['類型'] == '開銷']['金額'].sum(),
                        '時數': x[x['類型'] == '收入']['上線時數'].sum()
                    })).reset_index()
                    daily_agg = daily_agg.sort_values(by='日期', ascending=False)
                    
                    for _, row in daily_agg.iterrows():
                        d_str = row['日期'].strftime('%m/%d')
                        wd_str = WEEKDAY_MAP[row['日期'].weekday()]
                        inc = int(row['收入'])
                        exp = int(row['開銷'])
                        hrs = row['時數']
                        wage = int(inc/hrs) if hrs > 0 else 0
                        
                        html_row = f"""
                        <div class='ledger-row'>
                            <div class='l-date'>{d_str} <span style='font-size:12px; color:#8E8E93; font-weight:400;'>{wd_str}</span></div>
                            <div class='l-detail'>時薪: ${wage} / 時數: {hrs}h</div>
                            <div style='text-align:right;'>
                                <div class='l-amount c-green'>+${inc:,}</div>
                                <div class='l-amount c-red' style='font-size:14px;'>-${exp:,}</div>
                            </div>
                        </div>
                        """
                        st.markdown(html_row, unsafe_allow_html=True)

        else: st.info("尚無數據。")
        
    with tab_y:
        if not df.empty:
            with st.container(border=True):
                years = df['日期'].dt.year.astype(str).unique()
                selected_year = st.selectbox("選擇年度", sorted(years, reverse=True), label_visibility="collapsed")
                year_df = df[df['日期'].dt.year.astype(str) == selected_year]
                if not year_df.empty:
                    st.markdown(f"#### 📊 {selected_year} 年度財務總覽")
                    annual_df = year_df[year_df['類型'] != '休假'].groupby([year_df['日期'].dt.strftime('%m月'), '類型'])['金額'].sum().unstack(fill_value=0).reset_index()
                    annual_df.rename(columns={'日期': '月份'}, inplace=True)
                    if '收入' not in annual_df: annual_df['收入'] = 0
                    if '開銷' not in annual_df: annual_df['開銷'] = 0
                    annual_df['淨利'] = annual_df['收入'] - annual_df['開銷']
                    
                    fig_yr = go.Figure()
                    fig_yr.add_trace(go.Bar(x=annual_df['月份'], y=annual_df['收入'], name='收入 (Rev)', marker_color='#06C167'))
                    fig_yr.add_trace(go.Bar(x=annual_df['月份'], y=annual_df['開銷'], name='開銷 (Exp)', marker_color='#FF453A'))
                    fig_yr.add_trace(go.Scatter(x=annual_df['月份'], y=annual_df['淨利'], name='淨利 (Net)', mode='lines+markers', marker_color='#00E5FF', line=dict(width=3)))
                    fig_yr.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF'), barmode='group', margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_yr, use_container_width=True)

# ==========================================
# 頁面內容：⚙️ 設定 (Settings)
# ==========================================
elif page == "⚙️ 設定 (Settings)":
    st.title("Settings")
    with st.container(border=True):
        st.markdown("#### 📥 匯出原始資料 (Export)")
        st.caption("將雲端資料庫的原始紀錄匯出為 CSV 檔案，便於在 Excel 中進行進階交叉分析。")
        if not df.empty:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 下載 CSV 備份", data=csv_data, file_name=f"delivery_pro_export_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary") 
        else: st.info("目前無資料可供下載。")
