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
    "Uber Eats": COLOR_INCOME, "Foodpanda": "#FF2B85", "其他獎金": "#FFD700",
    "休假": COLOR_TEXT_SECONDARY, "機車油錢": COLOR_EXPENSE, "機車保養": "#FF9F0A", "其他開銷": "#BF5AF2"
}

CATEGORY_ICONS = {
    "Uber Eats": "🍔", "Foodpanda": "🐼", "其他獎金": "💰", "休假": "🏖️",
    "機車油錢": "⛽", "機車保養": "🔧", "其他開銷": "📦", "收入": "💰", "開銷": "💸"
}

WEEKDAY_MAP = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
WEEKDAY_CHINESE_MAP = {0: '週一', 1: '週二', 2: '週三', 3: '週四', 4: '週五', 5: '週六', 6: '週日'}

DRIVER_TIERS = [
    (0, "新手駕駛", "Rookie", "🔰"), (10000, "青銅夥伴 I", "Bronze I", "🥉"), (30000, "青銅夥伴 II", "Bronze II", "🥉"), (60000, "青銅夥伴 III", "Bronze III", "🥉"),
    (100000, "白銀專家 I", "Silver I", "🥈"), (150000, "白銀專家 II", "Silver II", "🥈"), (200000, "白銀專家 III", "Silver III", "🥈"),
    (300000, "黃金菁英 I", "Gold I", "🥇"), (400000, "黃金菁英 II", "Gold II", "🥇"), (500000, "黃金菁英 III", "Gold III", "🥇"),
    (600000, "白金先鋒 I", "Platinum I", "💠"), (800000, "白金先鋒 II", "Platinum II", "💠"), (1000000, "白金先鋒 III", "Platinum III", "💠"),
    (1500000, "鑽石大師 I", "Diamond I", "💎"), (2000000, "鑽石大師 II", "Diamond II", "💎"), (3000000, "鑽石大師 III", "Diamond III", "💎"),
    (5000000, "巔峰傳奇", "Apex Legend", "👑")
]

# ==========================================
# 🌐 單機版專屬資料庫引擎 (含小費拆解升級)
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
        ws = sheet.add_worksheet(title="Records", rows="1000", cols="12")
        ws.append_row(["日期", "類型", "項目", "金額", "上線時數", "備註", "異常", "單量", "趟獎", "系統小費", "現金小費"])
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
    headers = ws.row_values(1)
    
    # 💡 小費拆解升級：確保有「系統小費」與「現金小費」欄位
    expected_headers = ["日期", "類型", "項目", "金額", "上線時數", "備註", "異常", "單量", "趟獎", "系統小費", "現金小費"]
    missing = [h for h in expected_headers if h not in headers]
    if missing:
        for i, h in enumerate(missing):
            ws.update_cell(1, len(headers) + i + 1, h)
        headers.extend(missing)

    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        for col in expected_headers:
            if col not in df.columns: df[col] = 0 if col in ["單量", "趟獎", "系統小費", "現金小費", "上線時數", "金額"] else ""
        
        num_cols = ["單量", "趟獎", "系統小費", "現金小費", "金額", "上線時數"]
        for c in num_cols: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
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

def save_data_batch(rows):
    with st.spinner("⏳ 閃電同步至雲端伺服器..."):
        try:
            ws = get_records_ws()
            ws.append_rows(rows)
            load_data.clear()
        except Exception as e: st.error(f"儲存失敗：{e}")

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
        ws.update_cell(2, col_idx, value)
        load_settings.clear()

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

def change_date(new_date): st.session_state.selected_date = new_date

# ==========================================
# 🎨 頂級視覺樣式
# ==========================================
st.set_page_config(page_title="Delivery Pro", layout="wide", page_icon="📊")
st.markdown(f"""
<style>
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT_PRIMARY}; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    .block-container {{ padding-top: 1.5rem; padding-bottom: 5rem; max-width: 1400px; }}
    header[data-testid="stHeader"] {{ background: transparent !important; }}
    footer {{ visibility: hidden; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 20px; background-color: transparent; border-bottom: 2px solid #2C2C2E; margin-bottom: 20px; }}
    .stTabs [data-baseweb="tab"] {{ color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 18px; padding-bottom: 12px; }}
    .stTabs [aria-selected="true"] {{ color: {COLOR_INCOME} !important; border-bottom: 2px solid {COLOR_INCOME} !important; }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{ background-color: {COLOR_CARD_BG} !important; border: 1px solid rgba(255, 255, 255, 0.05) !important; border-radius: 16px !important; }}
    .kpi-card-green {{ background: linear-gradient(135deg, rgba(6,193,103,0.15) 0%, rgba(28,28,30,0) 100%); border-left: 4px solid {COLOR_INCOME}; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; }}
    .kpi-card-blue {{ background: linear-gradient(135deg, rgba(0,229,255,0.15) 0%, rgba(28,28,30,0) 100%); border-left: 4px solid {COLOR_BALANCE}; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; }}
    .kpi-card-purple {{ background: linear-gradient(135deg, rgba(191,90,242,0.15) 0%, rgba(28,28,30,0) 100%); border-left: 4px solid #BF5AF2; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; }}
    .kpi-card-orange {{ background: linear-gradient(135deg, rgba(255,159,10,0.15) 0%, rgba(28,28,30,0) 100%); border-left: 4px solid #FF9F0A; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; }}
    .list-item {{ display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}
    .list-icon {{ font-size: 20px; margin-right: 12px; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background-color: rgba(255, 255, 255, 0.05); border-radius: 50%; }}
    .list-amount {{ font-size: 16px; font-weight: 700; text-align: right; flex-grow: 0; }}
    .income {{ color: {COLOR_INCOME}; }} .expense {{ color: {COLOR_EXPENSE}; }}
</style>
""", unsafe_allow_html=True)

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

total_income = df[df['類型'] == '收入']['金額'].sum() if not df.empty else 0
total_gas_maint = df[(df['類型'] == '開銷') & (df['項目'].isin(['機車油錢', '機車保養']))]['金額'].sum() if not df.empty else 0
roi = (total_income / total_gas_maint) if total_gas_maint > 0 else total_income

current_month_str = today.strftime('%Y-%m')
current_target = int(settings.get("目標金額", 0)) if str(settings.get("目標月份")) == current_month_str else 0
m_inc_total = df[(df['日期'].dt.to_period('M').astype(str) == current_month_str) & (df['類型'] == '收入')]['金額'].sum() if not df.empty else 0
target_str = f"{(m_inc_total/current_target)*100:.1f}%" if current_target > 0 else "未設定"

driver_tier, next_tier, next_exp, prog, d_title, d_icon = get_driver_tier_info(total_income)

col_title, col_sync = st.columns([5, 1])
with col_title:
    st.markdown(f"## Delivery <span style='color:{COLOR_INCOME};'>Pro</span> <span style='font-size:16px; color:{COLOR_TEXT_SECONDARY}; margin-left:15px;'>{d_icon} {driver_tier} | 💰 ${int(total_income):,} | 🎯 {target_str}</span>", unsafe_allow_html=True)
with col_sync:
    if st.button("🔄 同步數據", use_container_width=True):
        load_data.clear(); load_settings.clear(); st.rerun()

tab_dash, tab_add, tab_report, tab_settings = st.tabs(["📊 總覽 (Dashboard)", "➕ 記一筆 (Add Log)", "📈 報表 (Analytics)", "⚙️ 設定 (Settings)"])

# ==========================================
# 分頁：📊 總覽 (Dashboard)
# ==========================================
with tab_dash:
    this_week_df = df[df['日期'].dt.date >= (today - timedelta(days=today.weekday()))] if not df.empty else pd.DataFrame()
    today_df = df[df['日期'].dt.date == today] if not df.empty else pd.DataFrame()
    d_inc = today_df[today_df['類型'] == '收入']['金額'].sum() if not today_df.empty else 0
    d_hr = today_df[today_df['類型'] == '收入']['上線時數'].sum() if not today_df.empty else 0
    d_ord = today_df[today_df['類型'] == '收入']['單量'].sum() if not today_df.empty else 0
    w_inc = this_week_df[this_week_df['類型'] == '收入']['金額'].sum() if not this_week_df.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-card-green'><div class='kpi-title'>今日收入</div><div class='kpi-value'>${int(d_inc):,}</div><div style='font-size:12px; color:{COLOR_TEXT_SECONDARY};'>{int(d_ord)}單 | 均單${int(d_inc/d_ord) if d_ord>0 else 0}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card-blue'><div class='kpi-title'>今日時薪</div><div class='kpi-value'>${int(d_inc/d_hr) if d_hr>0 else 0}</div><div style='font-size:12px; color:{COLOR_TEXT_SECONDARY};'>上線 {d_hr:.1f}h</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card-purple'><div class='kpi-title'>本週累積</div><div class='kpi-value'>${int(w_inc):,}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-card-orange'><div class='kpi-title'>當月目標</div><div class='kpi-value'>{target_str}</div></div>", unsafe_allow_html=True)

    col_trend, col_tier = st.columns([2, 1])
    with col_trend:
        st.markdown("### 📈 近七日趨勢")
        l7_df = df[df['日期'].dt.date >= (today - timedelta(days=6))] if not df.empty else pd.DataFrame()
        if not l7_df.empty:
            l7_inc = l7_df[l7_df['類型']=='收入'].groupby('日期')['金額'].sum().reset_index()
            l7_inc['日期字串'] = l7_inc['日期'].dt.strftime('%m-%d')
            fig = px.bar(l7_inc, x='日期字串', y='金額', color_discrete_sequence=[COLOR_INCOME])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color=COLOR_TEXT_SECONDARY, height=250, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    with col_tier:
        st.markdown("### 🏆 評級進度")
        with st.container(border=True):
            st.markdown(f"**{d_icon} {driver_tier}** ({d_title})")
            st.progress(prog)
            st.caption(f"距下一級還差 ${int(next_exp - total_income):,}")

# ==========================================
# 分頁：➕ 記一筆 (雙平台獨立輸入 + 小費拆解)
# ==========================================
with tab_add:
    col_input, col_cal = st.columns([1.8, 1])
    
    with col_input:
        st.markdown("### 📝 快速記帳 (無跑單平台留空即可)")
        with st.container(border=True):
            if st.session_state.show_success: st.success("✅ 紀錄已成功儲存！"); st.session_state.show_success = False
            
            # 日期與休假
            c_d, c_l = st.columns([2, 1])
            temp_date = c_d.date_input("🗓️ 紀錄日期", value=st.session_state.selected_date)
            if temp_date != st.session_state.selected_date: st.session_state.selected_date = temp_date; st.rerun()
            is_leave = c_l.checkbox("🏖️ 本日休假", value=False)
            
            if not is_leave:
                # Uber Eats 區塊
                st.markdown(f"#### <span style='color:{COLOR_INCOME};'>Uber Eats 數據</span>", unsafe_allow_html=True)
                cue1, cue2, cue3, cue4, cue5 = st.columns(5)
                ue_ord = cue1.number_input("UE 單量", min_value=0, step=1, key=f"ue_o_{k}")
                ue_hr = cue2.number_input("UE 時數", min_value=0.0, step=0.5, key=f"ue_h_{k}")
                ue_bonus = cue3.number_input("UE 趟獎", min_value=0, step=10, key=f"ue_b_{k}")
                ue_sys_tip = cue4.number_input("UE 系統小費", min_value=0, step=10, key=f"ue_st_{k}")
                ue_cash_tip = cue5.number_input("UE 現金小費", min_value=0, step=10, key=f"ue_ct_{k}")
                ue_base = st.number_input("UE 基本車資 (不含獎金/小費)", min_value=0, step=10, key=f"ue_ba_{k}")
                
                # Foodpanda 區塊
                st.markdown(f"#### <span style='color:#FF2B85;'>Foodpanda 數據</span>", unsafe_allow_html=True)
                cfp1, cfp2, cfp3, cfp4, cfp5 = st.columns(5)
                fp_ord = cfp1.number_input("熊貓 單量", min_value=0, step=1, key=f"fp_o_{k}")
                fp_hr = cfp2.number_input("熊貓 時數", min_value=0.0, step=0.5, key=f"fp_h_{k}")
                fp_bonus = cfp3.number_input("熊貓 趟獎", min_value=0, step=10, key=f"fp_b_{k}")
                fp_sys_tip = cfp4.number_input("熊貓 系統小費", min_value=0, step=10, key=f"fp_st_{k}")
                fp_cash_tip = cfp5.number_input("熊貓 現金小費", min_value=0, step=10, key=f"fp_ct_{k}")
                fp_base = st.number_input("熊貓 基本車資 (不含獎金/小費)", min_value=0, step=10, key=f"fp_ba_{k}")
                
                st.divider()
                st.markdown("##### 💸 其他支出與備註")
                ce1, ce2, ce3, ce4 = st.columns(4)
                gas = ce1.number_input("⛽ 油錢", min_value=0, step=10, key=f"gas_{k}")
                maint = ce2.number_input("🔧 保養", min_value=0, step=10, key=f"maint_{k}")
                o_name = ce3.text_input("📦 其他名稱", key=f"on_{k}")
                o_amt = ce4.number_input("📦 其他金額", min_value=0, step=10, key=f"oa_{k}")
                
                cn1, cn2 = st.columns([3, 1])
                note = cn1.text_input("備註心得", key=f"note_{k}")
                is_inc = cn2.checkbox("⚠️ 異常", key=f"inc_{k}")
                
                if st.button("🚀 一鍵儲存今日帳本", type="primary", use_container_width=True):
                    rows = []
                    d_str = str(st.session_state.selected_date)
                    # UE 判定：有單量或有基本車資才存
                    if ue_ord > 0 or ue_base > 0:
                        ue_total = ue_base + ue_bonus + ue_sys_tip + ue_cash_tip
                        rows.append([d_str, "收入", "Uber Eats", ue_total, ue_hr, note, str(is_inc), ue_ord, ue_bonus, ue_sys_tip, ue_cash_tip])
                    # FP 判定
                    if fp_ord > 0 or fp_base > 0:
                        fp_total = fp_base + fp_bonus + fp_sys_tip + fp_cash_tip
                        rows.append([d_str, "收入", "Foodpanda", fp_total, fp_hr, note, str(is_inc), fp_ord, fp_bonus, fp_sys_tip, fp_cash_tip])
                    # 支出判定
                    if gas > 0: rows.append([d_str, "開銷", "機車油錢", gas, 0, note, str(is_inc), 0, 0, 0, 0])
                    if maint > 0: rows.append([d_str, "開銷", "機車保養", maint, 0, note, str(is_inc), 0, 0, 0, 0])
                    if o_amt > 0: rows.append([d_str, "開銷", o_name if o_name else "其他", o_amt, 0, note, str(is_inc), 0, 0, 0, 0])
                    
                    if rows: save_data_batch(rows); st.session_state.show_success, st.session_state.input_key = True, k+1; st.rerun()
                    else: st.warning("請至少輸入一個平台的數據！")
            else:
                note = st.text_input("休假備註", key=f"note_{k}")
                if st.button("🚀 儲存休假", type="primary"):
                    save_data_batch([[str(st.session_state.selected_date), "休假", "休假", 0, 0, note, "False", 0, 0, 0, 0]])
                    st.session_state.show_success, st.session_state.input_key = True, k+1; st.rerun()

    with col_cal:
        st.markdown("### 📅 打卡月曆")
        work_dates = set(df[df['類型']=='收入']['日期'].dt.date) if not df.empty else set()
        off_dates = set(df[df['類型']=='休假']['日期'].dt.date) if not df.empty else set()
        cal_y, cal_m = st.session_state.selected_date.year, st.session_state.selected_date.month
        matrix = calendar.monthcalendar(cal_y, cal_m)
        cols = st.columns(7)
        for i, wd in enumerate(["一","二","三","四","五","六","日"]): cols[i].markdown(f"<center><small>{wd}</small></center>", unsafe_allow_html=True)
        for week in matrix:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_obj = date(cal_y, cal_m, day)
                    label = f"{day}🏖️" if d_obj in off_dates else (f"{day}✅" if d_obj in work_dates else str(day))
                    cols[i].button(label, key=f"c_{day}_{k}", use_container_width=True, type="primary" if d_obj==st.session_state.selected_date else "secondary", on_click=change_date, args=(d_obj,))

# ==========================================
# 分頁：📈 報表 (Analytics) - 小費細分分析
# ==========================================
with tab_report:
    if not df.empty:
        months = sorted(df['日期'].dt.to_period('M').astype(str).unique(), reverse=True)
        sel_m = st.selectbox("選擇月份", months, label_visibility="collapsed")
        m_df = df[df['日期'].dt.to_period('M').astype(str) == sel_m]
        
        m_inc = m_df[m_df['類型']=='收入']['金額'].sum()
        m_exp = m_df[m_df['類型']=='開銷']['金額'].sum()
        
        st.markdown(f"<div class='pro-card' style='padding:25px;'><div style='display:flex; justify-content:space-around; text-align:center;'><div><small>月總收入</small><h2 class='income'>${int(m_inc):,}</h2></div><div style='border-left:1px solid #2C2C2E;'></div><div><small>月淨利潤</small><h2>${int(m_inc-m_exp):,}</h2></div><div style='border-left:1px solid #2C2C2E;'></div><div><small>月總支出</small><h2 class='expense'>${int(m_exp):,}</h2></div></div>", unsafe_allow_html=True)
        
        # 🎯 目標進度計算與天數提醒
        target_val = int(settings.get("目標金額", 0)) if str(settings.get("目標月份")) == sel_m else 0
        if target_val > 0:
            prog_v = min(m_inc / target_val, 1.0); rem = target_val - m_inc
            st.progress(prog_v)
            if rem > 0:
                y, m = map(int, sel_m.split('-'))
                days_in_m = calendar.monthrange(y, m)[1]
                days_left = (days_in_m - today.day + 1) if today.month == m else (days_in_m if today.month < m else 0)
                msg = f"距離目標還差 ${int(rem):,}。本月還剩 {days_left} 天，日均需賺 ${int(rem/days_left) if days_left>0 else 0} 才能達標！"
                st.caption(msg)
        st.markdown("</div>", unsafe_allow_html=True)

        c_p, c_l = st.columns([1, 1.2])
        with c_p:
            st.markdown("#### 收入結構拆解")
            m_bonus = m_df['趟獎'].sum()
            m_sys_tip = m_df['系統小費'].sum()
            m_cash_tip = m_df['現金小費'].sum()
            m_base = m_inc - m_bonus - m_sys_tip - m_cash_tip
            fig_p = go.Figure(data=[go.Pie(labels=["基本車資", "趟獎獎金", "系統小費", "現金小費"], values=[m_base, m_bonus, m_sys_tip, m_cash_tip], hole=0.6, marker_colors=["#00E5FF", "#F6C143", "#BF5AF2", "#FF9F0A"], textinfo='percent')])
            fig_p.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=True)
            st.plotly_chart(fig_p, use_container_width=True)
        with c_l:
            st.markdown("#### 分類明細")
            cat_df = m_df[m_df['類型']!='休假'].groupby(['類型','項目'])['金額'].sum().reset_index().sort_values('金額', ascending=False)
            html = "<div style='height:300px; overflow-y:auto;'>"
            for _, r in cat_df.iterrows():
                icon = CATEGORY_ICONS.get(r['項目'], "📊")
                cls = "income" if r['類型']=="收入" else "expense"
                html += f"<div class='list-item'><div class='list-icon'>{icon}</div><div style='flex-grow:1;'><b>{r['項目']}</b><br><small>{r['類型']}</small></div><div class='list-amount {cls}'>${int(r['金額']):,}</div></div>"
            st.markdown(html + "</div>", unsafe_allow_html=True)

# ==========================================
# 分頁：⚙️ 設定 (Settings)
# ==========================================
with tab_settings:
    st.markdown("### ⚙️ 系統設定")
    with st.container(border=True):
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 匯出 CSV 備份資料", csv, f"delivery_pro_{today}.csv", "text/csv", type="primary")
