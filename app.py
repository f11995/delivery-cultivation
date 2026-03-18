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
# 🌐 單機版專屬資料庫引擎
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

def change_date(new_date):
    st.session_state.selected_date = new_date

# ==========================================
# 🎨 頂級桌面版 App 視覺樣式
# ==========================================
st.set_page_config(page_title="Delivery Pro", layout="wide", page_icon="📊")
st.markdown(f"""
<style>
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT_PRIMARY}; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    .block-container {{ padding-top: 2rem; padding-bottom: 5rem; max-width: 1400px; }}
    h1, h2, h3, h4 {{ font-weight: 700; letter-spacing: -0.5px; }}
    header[data-testid="stHeader"] {{ background: transparent !important; }}
    footer {{ visibility: hidden; }}

    /* 頂部標籤頁 Tabs 樣式重構 (無側邊欄) */
    .stTabs [data-baseweb="tab-list"] {{ gap: 20px; background-color: transparent; border-bottom: 2px solid #2C2C2E; margin-bottom: 20px; }}
    .stTabs [data-baseweb="tab"] {{ color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 18px; padding-bottom: 12px; border-bottom: 2px solid transparent; }}
    .stTabs [aria-selected="true"] {{ color: {COLOR_INCOME} !important; border-bottom: 2px solid {COLOR_INCOME} !important; }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {COLOR_CARD_BG} !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
    }}

    /* 帶漸層背景的 KPI 卡片 */
    .kpi-card-green {{ background: linear-gradient(135deg, rgba(6,193,103,0.15) 0%, rgba(28,28,30,0) 100%); border-left: 4px solid {COLOR_INCOME}; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; }}
    .kpi-card-blue {{ background: linear-gradient(135deg, rgba(0,229,255,0.15) 0%, rgba(28,28,30,0) 100%); border-left: 4px solid {COLOR_BALANCE}; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; }}
    .kpi-card-purple {{ background: linear-gradient(135deg, rgba(191,90,242,0.15) 0%, rgba(28,28,30,0) 100%); border-left: 4px solid #BF5AF2; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; }}
    .kpi-card-orange {{ background: linear-gradient(135deg, rgba(255,159,10,0.15) 0%, rgba(28,28,30,0) 100%); border-left: 4px solid #FF9F0A; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; }}

    .kpi-container {{ display: flex; justify-content: space-between; align-items: center; }}
    .kpi-item {{ text-align: center; flex: 1; }}
    .kpi-title {{ font-size: 14px; font-weight: 600; color: {COLOR_TEXT_SECONDARY}; margin-bottom: 6px; }}
    .kpi-value {{ font-size: 32px; font-weight: 700; color: {COLOR_TEXT_PRIMARY}; line-height: 1.1; }}
    .kpi-value.income {{ color: {COLOR_INCOME}; }}
    .kpi-value.expense {{ color: {COLOR_EXPENSE}; }}
    .kpi-value.balance {{ color: {COLOR_BALANCE}; }}

    .list-item {{ display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}
    .list-item:last-child {{ border-bottom: none; }}
    .list-icon {{ font-size: 22px; margin-right: 16px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background-color: rgba(255, 255, 255, 0.05); border-radius: 50%; }}
    .list-content {{ flex-grow: 1; line-height: 1.2; }}
    .list-title {{ font-size: 15px; font-weight: 600; color: {COLOR_TEXT_PRIMARY}; }}
    .list-subtitle {{ font-size: 12px; color: {COLOR_TEXT_SECONDARY}; margin-top: 4px; }}
    .list-amount {{ font-size: 16px; font-weight: 700; text-align: right; }}
    .list-amount.income {{ color: {COLOR_INCOME}; }}
    .list-amount.expense {{ color: {COLOR_EXPENSE}; }}

    div[data-testid="stDateInput"] > div {{ border-radius: 8px; overflow: hidden; border: none; }}
    button[kind="primary"] {{ background-color: {COLOR_INCOME} !important; border: none; font-weight: 600; color: white !important;}}
    button[kind="secondary"] {{ background-color: rgba(255, 255, 255, 0.05) !important; border: none; color: {COLOR_TEXT_SECONDARY}; }}
    .stProgress > div > div > div > div {{ background-color: #06C167; }}
    .js-plotly-plot .plotly .bg {{ fill: transparent !important; }}
    div[data-testid="column"] {{ padding: 0 4px; }}
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
        <p style='color:{COLOR_TEXT_SECONDARY}; font-size: 16px; font-weight: 500;'>Professional Desktop Analytics</p>
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
total_gas_maint = df[(df['類型'] == '開銷') & (df['項目'].isin(['機車油錢', '機車保養']))]['金額'].sum() if not df.empty else 0

roi = (total_income / total_gas_maint) if total_gas_maint > 0 else total_income
driver_tier, next_tier, next_exp, prog, d_title, d_icon = get_driver_tier_info(total_income)

# 頂部標題與狀態列 (完美取代側邊欄，橫向展開)
col_title, col_sync = st.columns([5, 1])
with col_title:
    st.markdown(f"""
    <h2 style='margin:0;'>Delivery <span style='color:{COLOR_INCOME};'>Pro</span> 
    <span style='font-size:16px; color:{COLOR_TEXT_SECONDARY}; font-weight:500; margin-left:15px;'>
    {d_icon} 評級: {driver_tier} &nbsp;|&nbsp; 💰 終身收入: ${int(total_income):,} &nbsp;|&nbsp; 📈 總投資報酬: 1:{roi:.1f}
    </span></h2>
    """, unsafe_allow_html=True)
with col_sync:
    if st.button("🔄 同步數據", use_container_width=True):
        load_data.clear()
        load_settings.clear()
        st.rerun()
st.write("")

# 建立頂部分頁 (Tabs)
tab_dash, tab_add, tab_report, tab_settings = st.tabs(["📊 總覽 (Dashboard)", "➕ 記一筆 (Add Log)", "📈 報表 (Analytics)", "⚙️ 設定 (Settings)"])

# ==========================================
# 分頁：📊 總覽 (Dashboard) - 豐富視覺化重構
# ==========================================
with tab_dash:
    # 準備總覽所需的數據
    start_of_week = today - timedelta(days=today.weekday())
    this_week_df = df[(df['日期'].dt.date >= start_of_week) & (df['日期'].dt.date <= today)] if not df.empty else pd.DataFrame()
    today_df = df[df['日期'].dt.date == today] if not df.empty else pd.DataFrame()
    last_7_days = today - timedelta(days=6)
    l7_df = df[(df['日期'].dt.date >= last_7_days) & (df['日期'].dt.date <= today)] if not df.empty else pd.DataFrame()
    
    d_inc = today_df[today_df['類型'] == '收入']['金額'].sum() if not today_df.empty else 0
    d_hr = today_df[today_df['類型'] == '收入']['上線時數'].sum() if not today_df.empty else 0
    d_wage = d_inc / d_hr if d_hr > 0 else 0
    w_inc = this_week_df[this_week_df['類型'] == '收入']['金額'].sum() if not this_week_df.empty else 0
    
    # 1. 頂部四大指標卡片 (帶有漸層背景)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='kpi-card-green'><div class='kpi-title'>今日收入 (Today)</div><div class='kpi-value'>${int(d_inc):,}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='kpi-card-blue'><div class='kpi-title'>今日時薪 (Hourly Rate)</div><div class='kpi-value'>${int(d_wage):,}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='kpi-card-purple'><div class='kpi-title'>本週累積 (This Week)</div><div class='kpi-value'>${int(w_inc):,}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='kpi-card-orange'><div class='kpi-title'>整體投資報酬 (ROI)</div><div class='kpi-value'>1 : {roi:.1f}</div></div>", unsafe_allow_html=True)
    
    st.write("")

    # 2. 中間板塊：趨勢圖 與 成就中心
    col_trend, col_tier = st.columns([2, 1.2])
    with col_trend:
        st.markdown("### 📈 近七日收入趨勢")
        with st.container(border=True):
            if not l7_df.empty:
                l7_inc_df = l7_df[l7_df['類型'] == '收入'].groupby('日期')['金額'].sum().reset_index()
                # 補齊 7 天日期避免斷層
                date_range = pd.date_range(start=last_7_days, end=today)
                l7_inc_df = l7_inc_df.set_index('日期').reindex(date_range).fillna(0).reset_index()
                l7_inc_df.columns = ['日期', '金額']
                l7_inc_df['日期字串'] = l7_inc_df['日期'].dt.strftime('%m-%d')
                
                fig_l7 = px.bar(l7_inc_df, x='日期字串', y='金額', text_auto='.0f')
                fig_l7.update_traces(marker_color=COLOR_INCOME, textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
                fig_l7.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color=COLOR_TEXT_SECONDARY), margin=dict(l=0, r=0, t=15, b=0),
                    xaxis=dict(title="", showgrid=False, type='category'),
                    yaxis=dict(title="", showgrid=True, gridcolor='#2C2C2E', zeroline=False),
                    height=260
                )
                st.plotly_chart(fig_l7, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("近七日尚無收入紀錄。")

    with col_tier:
        st.markdown("### 🏆 駕駛成就中心")
        with st.container(border=True):
            st.markdown(f"""
            <div style='display: flex; align-items: center; margin-bottom: 20px;'>
                <span style='font-size: 45px; margin-right: 15px;'>{d_icon}</span>
                <div>
                    <div style='font-size: 22px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};'>{driver_tier}</div>
                    <div style='font-size: 14px; color: {COLOR_TEXT_SECONDARY};'>{d_title}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(prog)
            st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:13px; color:{COLOR_TEXT_SECONDARY}; margin-top:8px;'><span>累積: ${int(total_income):,}</span><span>距離下級差: ${int(next_exp - total_income):,}</span></div>", unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color: #2C2C2E; margin: 15px 0;'>", unsafe_allow_html=True)
            
            # 動態智能洞察
            insight = "穩定發揮，保持這個節奏！繼續累積你的駕駛評級。"
            if d_wage > 250: insight = "🔥 狀態極佳！今日時薪突破 250 元，堪稱接單大師！"
            elif d_inc == 0: insight = "🛵 準備好上線了嗎？安全第一，祝你今天單單順路！"
            elif w_inc > 5000: insight = "🌟 本週累積已突破 5,000 元，距離財務目標又近了一大步！"
                
            st.markdown(f"<div style='font-size: 14px; color: {COLOR_BALANCE}; line-height: 1.5;'>💡 系統洞察：<br><span style='color: {COLOR_TEXT_PRIMARY};'>{insight}</span></div>", unsafe_allow_html=True)

    # 3. 底部板塊：最近紀錄
    st.markdown("### 🕒 最近動態 (Recent Logs)")
    with st.container(border=True):
        if not df.empty:
            recent_df = df.sort_values(by='日期', ascending=False).head(5)
            recent_html = ""
            for _, row in recent_df.iterrows():
                r_date = row['日期'].strftime('%Y-%m-%d')
                r_type = row['類型']
                r_item = row['項目']
                r_amount = row['金額']
                icon = CATEGORY_ICONS.get(r_item, CATEGORY_ICONS.get(r_type, "📝"))
                amount_class = "income" if r_type == "收入" else ("expense" if r_type == "開銷" else "")
                amount_str = f"${int(r_amount):,}" if r_type != '休假' else '休假'
                sign = "+" if r_type == '收入' else ("-" if r_type == "開銷" else "")
                
                recent_html += f"<div class='list-item' style='padding: 10px 0;'>"
                recent_html += f"<div class='list-icon' style='width:36px; height:36px; font-size:18px;'>{icon}</div>"
                recent_html += f"<div class='list-content'><div class='list-title' style='font-size: 15px;'>{r_item}</div><div class='list-subtitle'>{r_date} · {r_type}</div></div>"
                recent_html += f"<div class='list-amount {amount_class}' style='font-size:16px;'>{sign}{amount_str}</div>"
                recent_html += f"</div>"
            st.markdown(recent_html, unsafe_allow_html=True)
        else:
            st.caption("目前無任何紀錄。")

# ==========================================
# 分頁：➕ 記一筆 (高密度並排表單)
# ==========================================
with tab_add:
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("### 📝 快速記帳 (Quick Log)")
        with st.container(border=True):
            if st.session_state.show_success: 
                st.success("✅ 帳本已安全儲存！")
                st.session_state.show_success = False
            
            c_date, c_leave = st.columns([2, 1])
            with c_date:
                temp_date = st.date_input("🗓️ 紀錄日期", value=st.session_state.selected_date)
                if temp_date != st.session_state.selected_date: st.session_state.selected_date = temp_date; st.rerun()
                record_date = st.session_state.selected_date
            with c_leave:
                st.write("")
                st.write("")
                is_leave = st.checkbox("🏖️ 標記為「休假」", value=False)
    
            if not is_leave:
                st.divider()
                st.markdown("##### 💰 營業收入與時數")
                
                c_mod, c_p1, c_p2 = st.columns([1, 1, 1])
                platform_mode = c_mod.radio("模式", ["單一", "雙開"], horizontal=True)
                
                amount, amount_u, amount_f = 0, 0, 0
                item = "Uber Eats"
                
                if platform_mode == "單一":
                    item = c_p1.selectbox("平台", ["Uber Eats", "Foodpanda", "其他獎金"])
                    amount = c_p2.number_input("金額 ($)", min_value=0, step=10, value=None, key=f"amt_{k}")
                else:
                    amount_u = c_p1.number_input("Uber Eats ($)", min_value=0, step=10, value=None, key=f"amtu_{k}")
                    amount_f = c_p2.number_input("Foodpanda ($)", min_value=0, step=10, value=None, key=f"amtf_{k}")
                
                c_tmod, c_t1, c_t2 = st.columns([1, 1, 1])
                time_mode = c_tmod.radio("時數", ["手動", "首末單", "反推"], horizontal=True)
                hours = 0.0
                
                if time_mode == "手動":
                    input_hours = c_t1.number_input("時", min_value=0, step=1, value=None, key=f"hr_{k}")
                    input_minutes = c_t2.number_input("分", min_value=0, max_value=59, step=1, value=None, key=f"min_{k}")
                    hours = round((input_hours or 0) + ((input_minutes or 0) / 60.0), 2)
                elif time_mode == "首末單":
                    start_time = c_t1.time_input("首單", time(10, 0), key=f"t1_{k}") 
                    end_time = c_t2.time_input("末單", time(22, 0), key=f"t2_{k}")   
                    dt_start, dt_end = datetime.combine(date(2000, 1, 1), start_time), datetime.combine(date(2000, 1, 1), end_time)
                    if dt_end < dt_start: dt_end += timedelta(days=1)
                    hours = round((dt_end - dt_start).total_seconds() / 3600.0, 2)
                    c_tmod.caption(f"⏱️ {hours} h")
                else: 
                    remain_hours = c_t1.number_input("剩時", min_value=0, max_value=12, step=1, value=None, key=f"r_hr_{k}")
                    remain_minutes = c_t2.number_input("剩分", min_value=0, max_value=59, step=1, value=None, key=f"r_min_{k}")
                    if remain_hours is not None or remain_minutes is not None:
                        used_mins = max(0, 720 - ((remain_hours or 0) * 60 + (remain_minutes or 0)))
                        hours = round(used_mins / 60.0, 2)
                        c_tmod.caption(f"⏱️ {hours} h")
                    else: hours = 0.0

                st.divider()
                st.markdown("##### 💸 開銷與備註")
                
                c_e1, c_e2, c_e3, c_e4 = st.columns([1, 1, 1, 1])
                gas_exp = c_e1.number_input("⛽ 油錢", min_value=0, step=10, value=None, key=f"gas_{k}")
                maint_exp = c_e2.number_input("🔧 保養", min_value=0, step=10, value=None, key=f"maint_{k}")
                other_name = c_e3.text_input("📦 其他名稱", placeholder="雨衣", key=f"oname_{k}")
                other_exp = c_e4.number_input("📦 其他金額", min_value=0, step=10, value=None, key=f"oexp_{k}")
                
                c_n1, c_n2, c_sub = st.columns([2, 1, 1])
                note = c_n1.text_input("備註", placeholder="輸入心得...", label_visibility="collapsed", key=f"note_{k}")
                is_incident = c_n2.checkbox("⚠️ 異常狀況", key=f"trib_{k}")
                
                if c_sub.button("🚀 儲存", type="primary", use_container_width=True):
                    rows_to_add = []
                    val_amount = amount if platform_mode == "單一" else ((amount_u or 0) + (amount_f or 0))
                    
                    if val_amount > 0:
                        if platform_mode == "單一": rows_to_add.append([str(record_date), "收入", item, int(amount), hours, note, str(is_incident)])
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
                    else: st.warning("請輸入有效資料！")
            else:
                note = st.text_input("休假備註", placeholder="放鬆一下...", key=f"note_{k}")
                if st.button("🚀 儲存休假", type="primary", use_container_width=True):
                    save_data_batch([[str(record_date), "休假", "休假", 0, 0.0, note, "False"]])
                    st.session_state.show_success = True
                    st.session_state.input_key += 1
                    st.rerun()

    # ------------------ 右側：經典打卡月曆區 ------------------
    with col2:
        st.markdown("### 📅 當日表現與打卡")
        
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
        m3.metric("當日上線", f"{d_hr:.1f}h") 
        m4.metric("當日時薪", f"${int(d_wage):,}")
        
        st.write("---")
        
        work_dates = set(df[(df['類型'] == '收入') | (df['類型'] == '開銷')]['日期'].dt.date) if not df.empty else set()
        off_dates = set(df[df['類型'] == '休假']['日期'].dt.date) if not df.empty else set()
        
        cal_year = st.session_state.selected_date.year
        cal_month = st.session_state.selected_date.month
        cal_matrix = calendar.monthcalendar(cal_year, cal_month)
        
        st.markdown(f"<h5 style='text-align:center; color:{COLOR_TEXT_PRIMARY}; margin-bottom:10px;'>👉 {cal_year}年 {cal_month:02d}月</h5>", unsafe_allow_html=True)
        
        cols = st.columns(7)
        for i, wd in enumerate(["一", "二", "三", "四", "五", "六", "日"]): 
            cols[i].markdown(f"<div style='text-align: center; color:{COLOR_TEXT_SECONDARY}; font-size:13px; font-weight:600;'>{wd}</div>", unsafe_allow_html=True)
        
        for week in cal_matrix:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    cur_d = date(cal_year, cal_month, day)
                    is_sel = (cur_d == st.session_state.selected_date)
                    btn_type = "primary" if is_sel else "secondary"
                    
                    if cur_d in off_dates: b_label = f"{day}🏖️"
                    elif cur_d in work_dates: b_label = f"{day}✅"
                    else: b_label = str(day)
                        
                    cols[i].button(label=b_label, key=f"cal_{cal_year}_{cal_month}_{day}_{k}", use_container_width=True, type=btn_type, on_click=change_date, args=(cur_d,))

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
# 分頁：📈 報表 (Analytics) - HTML 完全無縮排防雷版
# ==========================================
with tab_report:
    if not df.empty:
        months = df['日期'].dt.to_period('M').astype(str).unique()
        col_m1, col_m2 = st.columns([4, 1])
        with col_m1: st.markdown("### 每月報表")
        with col_m2: selected_month = st.selectbox("選擇月份", sorted(months, reverse=True), label_visibility="collapsed")
        
        current_target = int(settings.get("目標金額", 0)) if str(settings.get("目標月份")) == selected_month else 0
        with st.expander(f"🎯 設定 {selected_month} 預期目標"):
            col_t1, col_t2 = st.columns([3, 1])
            new_target = col_t1.number_input("目標金額 (TWD)", min_value=0, step=1000, value=current_target, label_visibility="collapsed")
            if col_t2.button("💾 儲存", type="primary", use_container_width=True): 
                update_setting("目標月份", str(selected_month))
                update_setting("目標金額", int(new_target))
                st.rerun()

        month_df = df[df['日期'].dt.to_period('M').astype(str) == selected_month]
        
        if not month_df.empty:
            m_inc = month_df[month_df['類型'] == '收入']['金額'].sum()
            m_exp = month_df[month_df['類型'] == '開銷']['金額'].sum()
            m_balance = m_inc - m_exp
            
            # 頂部三大指標
            st.markdown(f"<div class='pro-card' style='background: linear-gradient(135deg, {COLOR_CARD_BG} 0%, #2C2C2E 100%); padding: 25px;'><div class='kpi-container'><div class='kpi-item'><div class='kpi-title'>月總收入</div><div class='kpi-value income'>${int(m_inc):,}</div></div><div style='width: 1px; height: 50px; background-color: rgba(255,255,255,0.1);'></div><div class='kpi-item'><div class='kpi-title'>月淨結餘</div><div class='kpi-value balance' style='font-size: 36px;'>${int(m_balance):,}</div></div><div style='width: 1px; height: 50px; background-color: rgba(255,255,255,0.1);'></div><div class='kpi-item'><div class='kpi-title'>月總支出</div><div class='kpi-value expense'>${int(m_exp):,}</div></div></div>", unsafe_allow_html=True)
            
            if current_target > 0:
                progress_val = min(m_inc / current_target, 1.0)
                rem = current_target - m_inc
                st.markdown(f"<div style='margin-top: 25px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 15px;'><div style='display:flex; justify-content:space-between; font-size:13px; color:{COLOR_TEXT_SECONDARY}; margin-bottom:8px; font-weight:600;'><span>🎯 收入目標進度：${int(m_inc):,} / ${current_target:,}</span><span>{int(progress_val*100)}%</span></div>", unsafe_allow_html=True)
                st.progress(progress_val)
                if rem > 0: st.markdown(f"<div style='font-size:13px; color:{COLOR_TEXT_SECONDARY}; text-align:right; margin-top:6px;'>距離目標還差 <span style='color:{COLOR_TEXT_PRIMARY}; font-weight:700;'>${int(rem):,}</span></div>", unsafe_allow_html=True)
                else: st.markdown(f"<div style='font-size:13px; color:{COLOR_INCOME}; text-align:right; margin-top:6px; font-weight:700;'>🎉 已達成設定目標！</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            col_pie, col_list = st.columns([1, 1.2])

            with col_pie:
                st.markdown("#### 收支分析")
                with st.container(border=True):
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
                        showlegend=False
                    )])
                    fig.add_annotation(
                        text=f"月結餘<br><span style='font-size: 26px; font-weight: 700; color: {COLOR_BALANCE};'>${int(m_balance):,}</span>",
                        x=0.5, y=0.5, font=dict(size=15, color=COLOR_TEXT_SECONDARY), showarrow=False
                    )
                    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            with col_list:
                st.markdown("#### 分類明細")
                # 💡 修復：嚴格將所有 HTML 濃縮為單行組裝，徹底阻絕 Markdown Code Block 渲染問題
                category_df = month_df[month_df['類型'] != '休假'].groupby(['類型', '項目'])['金額'].sum().reset_index()
                category_df = category_df.sort_values(by='金額', ascending=False)
                
                html_list = "<div style='height: 360px; overflow-y: auto; padding: 0 10px;'>"
                for _, row in category_df.iterrows():
                    c_type = row['類型']
                    c_item = row['項目']
                    c_amount = row['金額']
                    icon = CATEGORY_ICONS.get(c_item, CATEGORY_ICONS.get(c_type, "📊"))
                    amount_class = "income" if c_type == "收入" else "expense"
                    html_list += f"<div class='list-item'><div class='list-icon'>{icon}</div><div class='list-content'><div class='list-title'>{c_item}</div><div class='list-subtitle'>{c_type}</div></div><div class='list-amount {amount_class}'>${int(c_amount):,}</div></div>"
                html_list += "</div>"
                
                with st.container(border=True):
                    st.markdown(html_list, unsafe_allow_html=True)

            # 每日收支趨勢圖 (可伸縮)
            with st.expander("📊 每日收支趨勢 (點擊展開)", expanded=True):
                trend_df = month_df[month_df['類型'] != '休假'].copy()
                trend_df.loc[trend_df['類型'] == '開銷', '金額'] *= -1
                if not trend_df.empty:
                    trend_df['日期字串'] = trend_df['日期'].dt.strftime('%m-%d')
                    fig_bar = px.bar(
                        trend_df, x='日期字串', y='金額', color='項目', 
                        color_discrete_map=CUSTOM_COLORS, barmode='relative',
                        hover_data=['備註']
                    )
                    fig_bar.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                        font=dict(color='#8E8E93'), margin=dict(l=0, r=0, t=20, b=0), 
                        hovermode="x unified",
                        xaxis=dict(title="", showgrid=False, type='category'),
                        yaxis=dict(title="TWD", showgrid=True, gridcolor='#2C2C2E', zeroline=True, zerolinecolor='#8E8E93'),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title="")
                    )
                    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.caption("尚無資料可繪製趨勢圖。")
        else:
            st.info("本月尚無數據。")
    else:
        st.info("目前無任何紀錄，請先新增資料。")

# ==========================================
# 分頁：⚙️ 設定 (Settings)
# ==========================================
with tab_settings:
    st.markdown("### ⚙️ 帳號設定與資料匯出")
    with st.container(border=True):
        st.markdown("#### 📥 備份原始數據")
        st.caption("將雲端資料庫的原始紀錄匯出為 CSV 檔案，可使用 Excel 或 Google Sheets 開啟。")
        if not df.empty:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 下載 CSV 備份", data=csv_data, file_name=f"delivery_pro_export_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary") 
        else: st.info("目前無資料可供下載。")
