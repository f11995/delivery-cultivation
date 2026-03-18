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
COLOR_INCOME = "#06C167"
COLOR_EXPENSE = "#FF453A"
COLOR_BALANCE = "#00E5FF"
COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_SECONDARY = "#8E8E93"
COLOR_CARD_BG = "#1C1C1E"
COLOR_BG = "#000000"

CUSTOM_COLORS = {
    "Uber Eats": COLOR_INCOME,
    "Foodpanda": "#FF2B85",
    "其他獎金": "#FFD700",
    "休假": COLOR_TEXT_SECONDARY,
    "機車油錢": COLOR_EXPENSE,
    "機車保養": "#FF9F0A",
    "其他開銷": "#BF5AF2"
}

CATEGORY_ICONS = {
    "Uber Eats": "🍔",
    "Foodpanda": "🐼",
    "其他獎金": "💰",
    "休假": "🏖️",
    "機車油錢": "⛽",
    "機車保養": "🔧",
    "其他開銷": "📦",
    "收入": "💰",
    "開銷": "💸"
}

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

# 一鍵批量儲存功能 (秒速記帳核心)
def save_data_batch(rows):
    with st.spinner("⏳ 閃電同步至雲端伺服器..."):
        try:
            ws = get_records_ws()
            ws.append_rows(rows)
            load_data.clear()
        except Exception as e:
            st.error(f"儲存失敗：{e}")

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

# 日曆切換功能
def change_date(new_date):
    st.session_state.selected_date = new_date

# ==========================================
# 🎨 頂級 App 視覺樣式
# ==========================================
st.set_page_config(page_title="Delivery Pro", layout="wide", page_icon="📊")
st.markdown(f"""
<style>
    /* 全局設定 */
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT_PRIMARY}; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    .block-container {{ padding-top: 1rem; padding-bottom: 5rem; max-width: 1200px; }}
    h1, h2, h3, h4 {{ font-weight: 700; letter-spacing: -0.5px; }}
    
    /* 隱藏預設按鈕與 Header */
    header[data-testid="stHeader"] {{ background: transparent !important; }}
    footer {{ visibility: hidden; }}

    /* 重新設計的卡片容器 */
    .pro-card {{
        background-color: {COLOR_CARD_BG};
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.05);
    }}

    /* 關鍵指標設計 (KPI) */
    .kpi-container {{ display: flex; justify-content: space-between; align-items: center; }}
    .kpi-item {{ text-align: center; flex: 1; }}
    .kpi-title {{ font-size: 13px; font-weight: 600; color: {COLOR_TEXT_SECONDARY}; margin-bottom: 6px; }}
    .kpi-value {{ font-size: 28px; font-weight: 700; color: {COLOR_TEXT_PRIMARY}; line-height: 1.1; }}
    .kpi-value.income {{ color: {COLOR_INCOME}; }}
    .kpi-value.expense {{ color: {COLOR_EXPENSE}; }}
    .kpi-value.balance {{ color: {COLOR_BALANCE}; }}

    /* 列表樣式 */
    .list-item {{ display: flex; align-items: center; padding: 16px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }}
    .list-item:last-child {{ border-bottom: none; }}
    .list-icon {{ font-size: 24px; margin-right: 16px; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; background-color: rgba(255, 255, 255, 0.05); border-radius: 50%; }}
    .list-content {{ flex-grow: 1; }}
    .list-title {{ font-size: 16px; font-weight: 600; color: {COLOR_TEXT_PRIMARY}; }}
    .list-subtitle {{ font-size: 13px; color: {COLOR_TEXT_SECONDARY}; margin-top: 2px; }}
    .list-amount {{ font-size: 18px; font-weight: 700; text-align: right; }}
    .list-amount.income {{ color: {COLOR_INCOME}; }}
    .list-amount.expense {{ color: {COLOR_EXPENSE}; }}

    /* 側邊欄與按鈕設計 */
    section[data-testid="stSidebar"] {{ background-color: #09090B !important; border-right: 1px solid #2C2C2E; }}
    .sidebar-brand {{ font-size: 24px; font-weight: 800; color: #FFFFFF; margin-bottom: 30px; padding-left: 5px; }}
    .sidebar-brand span {{ color: {COLOR_INCOME}; }}
    
    div[data-testid="stRadio"] > div[role="radiogroup"] {{ gap: 10px; }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
        background-color: rgba(255, 255, 255, 0.03); padding: 14px 18px; border-radius: 12px; border: 1px solid transparent; transition: all 0.2s ease; width: 100%;
    }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {{ background-color: rgba(255, 255, 255, 0.08); }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {{ background-color: rgba(6, 193, 103, 0.15); border-color: {COLOR_INCOME}; }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {{ display: none; }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:nth-child(2) > p {{ font-size: 16px !important; font-weight: 600 !important; color: {COLOR_TEXT_SECONDARY} !important; margin: 0 !important; }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] > div:nth-child(2) > p {{ color: #FFFFFF !important; }}

    /* 日曆與進度條 */
    div[data-testid="stDateInput"] > div {{ border-radius: 12px; overflow: hidden; border: none; }}
    button[kind="primary"] {{ background-color: {COLOR_INCOME} !important; border: none; font-weight: 600; color: white !important;}}
    button[kind="secondary"] {{ background-color: rgba(255, 255, 255, 0.05) !important; border: none; color: {COLOR_TEXT_SECONDARY}; }}
    .stProgress > div > div > div > div {{ background-color: #06C167; }}
    .js-plotly-plot .plotly .bg {{ fill: transparent !important; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛡️ 系統登入 
# ==========================================
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown(f"""
    <br><br><br>
    <div style='text-align: center;'>
        <h1 style='color: #FFFFFF; font-size: 48px; font-weight:800; letter-spacing:-1px; margin-bottom: 8px;'>
            Delivery <span style='color:{COLOR_INCOME};'>Pro</span>
        </h1>
        <p style='color:{COLOR_TEXT_SECONDARY}; font-size: 16px; font-weight: 500;'>Personal Courier Analytics</p>
    </div>
    <br><br>
    """, unsafe_allow_html=True)
    
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        pwd_input = st.text_input("Access Token", type="password", placeholder="Enter secure token...", label_visibility="collapsed")
        st.write("")
        if st.button("Secure Login", type="primary", use_container_width=True):
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

# ==========================================
# 側邊欄導覽
# ==========================================
with st.sidebar:
    st.markdown(f"<div class='sidebar-brand'>Delivery <span>Pro</span></div>", unsafe_allow_html=True)
    
    # 恢復原本的三大分頁設計
    page = st.radio("Navigation", ["➕ 記一筆 (Add Log)", "📈 報表 (Analytics)", "⚙️ 設定 (Settings)"], label_visibility="collapsed")
    
    st.divider()
    st.markdown(f"""
    <div style='color:{COLOR_TEXT_SECONDARY}; font-size:12px; font-weight: 600; margin-top:15px; margin-bottom:5px;'>LIFETIME REVENUE</div>
    <div style='font-size:24px; font-weight:800; color:{COLOR_INCOME};'>${int(total_income):,}</div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🔄 強制同步 (Sync)", use_container_width=True):
        load_data.clear()
        load_settings.clear()
        st.rerun()

# ==========================================
# 頁面內容：➕ 記一筆 (經典打卡月曆 + 秒速表單)
# ==========================================
if page == "➕ 記一筆 (Add Log)":
    # 完美重現你最愛的 1:1.2 排版比例
    col1, col2 = st.columns([1, 1.2])
    
    # ------------------ 左側：秒速記帳區 ------------------
    with col1:
        st.markdown("### 📝 新增紀錄 (Quick Log)")
        with st.container(border=True):
            if st.session_state.show_success: 
                st.success("✅ 帳本已安全儲存！")
                st.session_state.show_success = False
            
            # 日期與狀態
            temp_date = st.date_input("選擇紀錄日期", value=st.session_state.selected_date)
            if temp_date != st.session_state.selected_date: st.session_state.selected_date = temp_date; st.rerun()
            record_date = st.session_state.selected_date
            
            is_leave = st.checkbox("🏖️ 標記今日為「休假」 (勾選後直接按儲存)", value=False)
            st.write("---")
    
            if not is_leave:
                # 收入與時數
                st.markdown("##### 💰 收入與時數")
                platform_mode = st.radio("平台模式", ["單一平台", "雙開合併"], horizontal=True)
                
                amount, amount_u, amount_f = 0, 0, 0
                item = "Uber Eats"
                hours = 0.0
                
                if platform_mode == "單一平台":
                    c_plat1, c_plat2 = st.columns([3, 2])
                    with c_plat1: item = st.selectbox("平台", ["Uber Eats", "Foodpanda", "其他獎金"], label_visibility="collapsed")
                    with c_plat2: amount = st.number_input("金額", min_value=0, step=10, value=None, key=f"amt_{k}", label_visibility="collapsed", placeholder="$ TWD")
                else:
                    c_plat1, c_plat2 = st.columns(2)
                    with c_plat1: amount_u = st.number_input("Uber Eats $", min_value=0, step=10, value=None, key=f"amtu_{k}")
                    with c_plat2: amount_f = st.number_input("Foodpanda $", min_value=0, step=10, value=None, key=f"amtf_{k}")
                
                st.write("")
                time_mode = st.radio("時數計算", ["APP 剩餘時間反推 (12H制)", "手動輸入", "系統換算"], horizontal=True)
                
                if time_mode == "系統換算":
                    t_col1, t_col2 = st.columns(2)
                    with t_col1: start_time = st.time_input("首單時間", time(10, 0), key=f"t1_{k}") 
                    with t_col2: end_time = st.time_input("末單時間", time(22, 0), key=f"t2_{k}")   
                    dt_start, dt_end = datetime.combine(date(2000, 1, 1), start_time), datetime.combine(date(2000, 1, 1), end_time)
                    if dt_end < dt_start: dt_end += timedelta(days=1)
                    hours = round((dt_end - dt_start).total_seconds() / 3600.0, 2)
                    st.info(f"⏱️ 換算實際上線：**{hours} h**")
                elif time_mode == "手動輸入":
                    h_col, m_col = st.columns(2)
                    with h_col: input_hours = st.number_input("時 (Hours)", min_value=0, step=1, value=None, key=f"hr_{k}")
                    with m_col: input_minutes = st.number_input("分 (Minutes)", min_value=0, max_value=59, step=1, value=None, key=f"min_{k}")
                    hours = round((input_hours or 0) + ((input_minutes or 0) / 60.0), 2)
                else: 
                    st.caption("💡 輸入 APP 顯示的「剩餘駕駛時間」反推：")
                    h_col, m_col = st.columns(2)
                    with h_col: remain_hours = st.number_input("剩餘 小時", min_value=0, max_value=12, step=1, value=None, key=f"r_hr_{k}")
                    with m_col: remain_minutes = st.number_input("剩餘 分鐘", min_value=0, max_value=59, step=1, value=None, key=f"r_min_{k}")
                    if remain_hours is not None or remain_minutes is not None:
                        r_h = remain_hours or 0
                        r_m = remain_minutes or 0
                        used_mins = max(0, 720 - (r_h * 60 + r_m))
                        hours = round(used_mins / 60.0, 2)
                        st.info(f"⏱️ 反推上線：**{hours} h** (約 {used_mins // 60}h {used_mins % 60}m)")
                    else: hours = 0.0

                st.write("---")
                
                # 開銷
                st.markdown("##### 💸 開銷 (選填)")
                c_exp1, c_exp2 = st.columns(2)
                with c_exp1: gas_exp = st.number_input("⛽ 油錢", min_value=0, step=10, value=None, key=f"gas_{k}")
                with c_exp2: maint_exp = st.number_input("🔧 保養", min_value=0, step=10, value=None, key=f"maint_{k}")
                c_exp3, c_exp4 = st.columns(2)
                with c_exp3: other_name = st.text_input("其他名稱", placeholder="如:雨衣", key=f"oname_{k}")
                with c_exp4: other_exp = st.number_input("金額", min_value=0, step=10, value=None, key=f"oexp_{k}")
                
                st.write("---")
                
                # 備註
                st.markdown("##### 📝 異常與備註")
                is_incident = st.checkbox("⚠️ 標記異常 (奧客/車損/惡劣天氣)", key=f"trib_{k}")
                note = st.text_input("今日備註", value="", placeholder="輸入心得...", key=f"note_{k}")
                
                st.write("")
                if st.button("🚀 一鍵儲存今日帳本", type="primary", use_container_width=True):
                    rows_to_add = []
                    val_amount = amount if platform_mode == "單一平台" else ((amount_u or 0) + (amount_f or 0))
                    
                    if val_amount > 0:
                        if platform_mode == "單一平台":
                            rows_to_add.append([str(record_date), "收入", item, int(amount), hours, note, str(is_incident)])
                        else:
                            if (amount_u or 0) > 0: rows_to_add.append([str(record_date), "收入", "Uber Eats", int(amount_u), hours, note, str(is_incident)])
                            if (amount_f or 0) > 0: rows_to_add.append([str(record_date), "收入", "Foodpanda", int(amount_f), 0.0, note, str(is_incident)])
                    
                    if (gas_exp or 0) > 0: rows_to_add.append([str(record_date), "開銷", "機車油錢", int(gas_exp), 0.0, note, str(is_incident)])
                    if (maint_exp or 0) > 0: rows_to_add.append([str(record_date), "開銷", "機車保養", int(maint_exp), 0.0, note, str(is_incident)])
                    if (other_exp or 0) > 0:
                        if other_name.strip() == "": st.warning("請輸入其他開銷名稱")
                        else: rows_to_add.append([str(record_date), "開銷", other_name.strip(), int(other_exp), 0.0, note, str(is_incident)])
                    
                    if len(rows_to_add) > 0:
                        save_data_batch(rows_to_add)
                        st.session_state.show_success = True
                        st.session_state.input_key += 1
                        st.rerun()
                    else:
                        st.warning("請至少輸入一筆有效的資料！")
            else:
                note = st.text_input("休假備註", placeholder="放鬆一下...", key=f"note_{k}")
                st.write("")
                if st.button("🚀 儲存休假", type="primary", use_container_width=True):
                    save_data_batch([[str(record_date), "休假", "休假", 0, 0.0, note, "False"]])
                    st.session_state.show_success = True
                    st.session_state.input_key += 1
                    st.rerun()

    # ------------------ 右側：經典打卡月曆區 ------------------
    with col2:
        st.markdown("### 📅 當日表現與打卡")
        
        # 1. 四大指標
        daily_df = df[df['日期'].dt.date == st.session_state.selected_date] if not df.empty else pd.DataFrame()
        d_inc = daily_df[daily_df['類型'] == '收入']['金額'].sum() if not daily_df.empty else 0
        d_exp = daily_df[daily_df['類型'] == '開銷']['金額'].sum() if not daily_df.empty else 0
        d_hr = daily_df[daily_df['類型'] == '收入']['上線時數'].sum() if not daily_df.empty else 0.0
        d_wage = d_inc / d_hr if d_hr > 0 else 0
        
        if not daily_df.empty:
            if any(daily_df['類型'] == '休假'): st.info("🏖️ 當日為排定休假。")
            if any(daily_df.get('異常', "False") == "True"): st.error("⚠️ 當日有標記異常狀況。")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("當日收入", f"${int(d_inc):,}")
        m2.metric("當日開銷", f"${int(d_exp):,}")
        m3.metric("當日上線", f"{d_hr:.1f} h") 
        m4.metric("當日時薪", f"${int(d_wage):,.0f}")
        
        st.write("---")
        
        # 2. 打卡月曆矩陣
        work_dates = set(df[(df['類型'] == '收入') | (df['類型'] == '開銷')]['日期'].dt.date) if not df.empty else set()
        off_dates = set(df[df['類型'] == '休假']['日期'].dt.date) if not df.empty else set()
        
        cal_year = st.session_state.selected_date.year
        cal_month = st.session_state.selected_date.month
        cal_matrix = calendar.monthcalendar(cal_year, cal_month)
        
        st.markdown(f"<h5 style='text-align:center; color:{COLOR_TEXT_PRIMARY}; margin-bottom:15px;'>👉 {cal_year}年 {cal_month:02d}月</h5>", unsafe_allow_html=True)
        
        cols = st.columns(7)
        for i, wd in enumerate(["一", "二", "三", "四", "五", "六", "日"]): 
            cols[i].markdown(f"<div style='text-align: center; color:{COLOR_TEXT_SECONDARY}; font-size:14px; font-weight:600;'>{wd}</div>", unsafe_allow_html=True)
        
        for week in cal_matrix:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    cur_d = date(cal_year, cal_month, day)
                    is_sel = (cur_d == st.session_state.selected_date)
                    btn_type = "primary" if is_sel else "secondary"
                    
                    if cur_d in off_dates:
                        b_label = f"{day}🏖️"
                    elif cur_d in work_dates:
                        b_label = f"{day}✅"
                    else:
                        b_label = str(day)
                        
                    cols[i].button(
                        label=b_label, 
                        key=f"cal_{cal_year}_{cal_month}_{day}_{k}", 
                        use_container_width=True, 
                        type=btn_type, 
                        on_click=change_date, 
                        args=(cur_d,)
                    )

        # 3. 歷史紀錄編輯
        if not daily_df.empty:
            st.write("---")
            with st.expander("🛠️ 編輯或移除當日紀錄"):
                edit_df = daily_df.copy()
                edit_df['日期'] = edit_df['日期'].dt.strftime('%Y-%m-%d')
                edit_df.insert(0, "移除", False)
                edited_df = st.data_editor(edit_df, hide_index=True, column_config={"移除": st.column_config.CheckboxColumn("勾選移除", default=False)}, disabled=["日期", "類型", "項目", "金額", "上線時數", "備註", "異常"], use_container_width=True, key=f"edit_{st.session_state.selected_date}_{k}")
                rows_to_delete = edited_df[edited_df["移除"] == True].index.tolist()
                if len(rows_to_delete) > 0:
                    if st.button("🗑️ 確認移除", type="primary", use_container_width=True):
                        delete_data(rows_to_delete)
                        st.session_state.show_success = True
                        st.session_state.input_key += 1
                        st.rerun()


# ==========================================
# 頁面內容：📈 報表 (Analytics) - 參考頂級金融 App 設計
# ==========================================
elif page == "📈 報表 (Analytics)":
    if not df.empty:
        months = df['日期'].dt.to_period('M').astype(str).unique()
        col_m1, col_m2 = st.columns([3, 2])
        with col_m1:
            st.markdown("<h2 style='margin: 0;'>每月報表</h2>", unsafe_allow_html=True)
        with col_m2:
            selected_month = st.selectbox("選擇月份", sorted(months, reverse=True), label_visibility="collapsed")
        
        month_df = df[df['日期'].dt.to_period('M').astype(str) == selected_month]
        
        if not month_df.empty:
            m_inc = month_df[month_df['類型'] == '收入']['金額'].sum()
            m_exp = month_df[month_df['類型'] == '開銷']['金額'].sum()
            m_balance = m_inc - m_exp
            
            # 頂部三大指標卡片
            st.markdown(f"""
            <div class='pro-card' style='margin-top: 10px; background: linear-gradient(135deg, {COLOR_CARD_BG} 0%, #2C2C2E 100%);'>
                <div class='kpi-container'>
                    <div class='kpi-item'>
                        <div class='kpi-title'>月總收入</div>
                        <div class='kpi-value income'>${int(m_inc):,}</div>
                    </div>
                    <div style='width: 1px; height: 50px; background-color: rgba(255,255,255,0.1);'></div>
                    <div class='kpi-item'>
                        <div class='kpi-title'>月淨結餘</div>
                        <div class='kpi-value balance' style='font-size: 36px;'>${int(m_balance):,}</div>
                    </div>
                    <div style='width: 1px; height: 50px; background-color: rgba(255,255,255,0.1);'></div>
                    <div class='kpi-item'>
                        <div class='kpi-title'>月總支出</div>
                        <div class='kpi-value expense'>${int(m_exp):,}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 中心結餘圓餅圖
            st.markdown("<h3 style='margin-top: 30px; margin-bottom: 16px;'>收支分析</h3>", unsafe_allow_html=True)
            with st.container():
                st.markdown(f"<div class='pro-card' style='padding: 20px 0;'>", unsafe_allow_html=True)
                
                pie_data = [
                    {"label": "總收入", "value": m_inc, "color": COLOR_INCOME},
                    {"label": "總支出", "value": m_exp, "color": COLOR_EXPENSE}
                ]
                
                fig = go.Figure(data=[go.Pie(
                    labels=[d['label'] for d in pie_data],
                    values=[d['value'] for d in pie_data],
                    hole=0.6,
                    marker=dict(colors=[d['color'] for d in pie_data]),
                    textinfo='label+percent',
                    hoverinfo='label+value+percent',
                    textfont=dict(size=14, color=COLOR_TEXT_PRIMARY),
                    showlegend=False
                )])

                fig.add_annotation(
                    text=f"月結餘<br><span style='font-size: 26px; font-weight: 700; color: {COLOR_BALANCE};'>${int(m_balance):,}</span>",
                    x=0.5, y=0.5,
                    font=dict(size=15, color=COLOR_TEXT_SECONDARY),
                    showarrow=False
                )

                fig.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=320,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown("</div>", unsafe_allow_html=True)

            # 分類明細清單
            st.markdown("<h3 style='margin-top: 30px; margin-bottom: 16px;'>分類明細</h3>", unsafe_allow_html=True)
            with st.container():
                st.markdown(f"<div class='pro-card' style='padding: 8px 24px;'>", unsafe_allow_html=True)
                
                category_df = month_df[month_df['類型'] != '休假'].groupby(['類型', '項目'])['金額'].sum().reset_index()
                category_df = category_df.sort_values(by='金額', ascending=False)
                
                for _, row in category_df.iterrows():
                    c_type = row['類型']
                    c_item = row['項目']
                    c_amount = row['金額']
                    
                    icon = CATEGORY_ICONS.get(c_item, CATEGORY_ICONS.get(c_type, "📊"))
                    amount_class = "income" if c_type == "收入" else "expense"
                    amount_str = f"${int(c_amount):,}"

                    st.markdown(f"""
                    <div class='list-item'>
                        <div class='list-icon'>{icon}</div>
                        <div class='list-content'>
                            <div class='list-title'>{c_item}</div>
                            <div class='list-subtitle'>{c_type}</div>
                        </div>
                        <div class='list-amount {amount_class}'>{amount_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.info("本月尚無數據。")
    else:
        st.info("目前無任何紀錄，請先新增資料。")

# ==========================================
# 頁面內容：⚙️ 設定 (Settings)
# ==========================================
elif page == "⚙️ 設定 (Settings)":
    st.title("設定")
    st.markdown(f"""
    <div class='pro-card'>
        <h3 style='margin-bottom: 16px;'>📥 匯出資料</h3>
        <p style='color:{COLOR_TEXT_SECONDARY}; margin-bottom: 20px;'>將您的所有原始紀錄匯出為 CSV 檔案，以便進行備份或在其他軟體中分析。</p>
    """, unsafe_allow_html=True)
    
    if not df.empty:
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="下載 CSV 備份檔", data=csv_data, file_name=f"delivery_pro_export_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary", use_container_width=True) 
    else:
        st.info("目前無資料可供下載。")
    st.markdown("</div>", unsafe_allow_html=True)
