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
WEEKDAY_MAP = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}

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
    st.markdown(f"<div style='color:#8E8E93; font-size:12px; margin
