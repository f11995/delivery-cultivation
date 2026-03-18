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
# 擴充顏色定義，用於新的 UI
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

# 定義類別圖示
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

# 💡 全新的一鍵批量儲存功能 (秒速記帳核心)
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

# 💡 修復：補回切換日期的重要核心函數
def change_date(new_date):
    st.session_state.selected_date = new_date

# ==========================================
# 🎨 頂級 App 視覺樣式 (Advanced Fintech Style)
# ==========================================
st.set_page_config(page_title="Delivery Pro", layout="wide", page_icon="📊")
st.markdown(f"""
<style>
    /* 全局設定 */
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT_PRIMARY}; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    .block-container {{ padding-top: 1rem; padding-bottom: 5rem; max-width: 1000px; }}
    h1, h2, h3 {{ font-weight: 700; letter-spacing: -0.5px; }}
    
    /* 隱藏不必要的元素 */
    header {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    .stDeployButton {{ display: none; }}

    /* 重新設計的卡片容器 */
    .pro-card {{
        background-color: {COLOR_CARD_BG};
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.05);
    }}

    /* 關鍵指標設計 (KPI) */
    .kpi-container {{ display: flex; justify-content: space-between; align-items: center; }}
    .kpi-item {{ text-align: center; flex: 1; }}
    .kpi-title {{ font-size: 14px; font-weight: 500; color: {COLOR_TEXT_SECONDARY}; margin-bottom: 8px; }}
    .kpi-value {{ font-size: 32px; font-weight: 700; color: {COLOR_TEXT_PRIMARY}; line-height: 1.1; }}
    .kpi-value.income {{ color: {COLOR_INCOME}; }}
    .kpi-value.expense {{ color: {COLOR_EXPENSE}; }}
    .kpi-value.balance {{ color: {COLOR_BALANCE}; }}

    /* 新版列表樣式 (List Item) - 參考圖一、二 */
    .list-item {{
        display: flex;
        align-items: center;
        padding: 16px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }}
    .list-item:last-child {{ border-bottom: none; }}
    .list-icon {{
        font-size: 24px;
        margin-right: 16px;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 50%;
    }}
    .list-content {{ flex-grow: 1; }}
    .list-title {{ font-size: 16px; font-weight: 600; color: {COLOR_TEXT_PRIMARY}; }}
    .list-subtitle {{ font-size: 13px; color: {COLOR_TEXT_SECONDARY}; margin-top: 2px; }}
    .list-amount {{ font-size: 18px; font-weight: 700; text-align: right; }}
    .list-amount.income {{ color: {COLOR_INCOME}; }}
    .list-amount.expense {{ color: {COLOR_EXPENSE}; }}

    /* 側邊欄設計優化 */
    section[data-testid="stSidebar"] {{ background-color: #09090B !important; border-right: 1px solid #2C2C2E; }}
    .sidebar-brand {{ font-size: 22px; font-weight: 800; color: #FFFFFF; margin-bottom: 30px; padding-left: 5px; }}
    .sidebar-brand span {{ color: {COLOR_INCOME}; }}
    
    /* 側邊欄模塊化按鈕 */
    div[data-testid="stRadio"] > div[role="radiogroup"] {{ gap: 10px; }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
        background-color: rgba(255, 255, 255, 0.03);
        padding: 14px 18px;
        border-radius: 14px;
        border: 1px solid transparent;
        transition: all 0.2s ease;
        width: 100%;
    }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {{
        background-color: rgba(255, 255, 255, 0.08);
    }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {{
        background-color: rgba(6, 193, 103, 0.15);
        border-color: {COLOR_INCOME};
    }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {{ display: none; }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:nth-child(2) > p {{
        font-size: 16px !important; font-weight: 600 !important; color: {COLOR_TEXT_SECONDARY} !important; margin: 0 !important;
    }}
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] > div:nth-child(2) > p {{ color: #FFFFFF !important; }}

    /* 懸浮動作按鈕 (FAB) - 模擬 */
    .fab-container {{
        position: fixed;
        bottom: 30px;
        right: 20px;
        z-index: 999;
    }}
    .fab-button {{
        background-color: {COLOR_INCOME};
        color: white;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 30px;
        box-shadow: 0 4px 12px rgba(6, 193, 103, 0.4);
        cursor: pointer;
        transition: transform 0.2s;
    }}
    .fab-button:hover {{ transform: scale(1.05); }}

    /* 日曆樣式微調 */
    div[data-testid="stDateInput"] > div {{ border-radius: 12px; overflow: hidden; border: none; }}
    button[kind="primary"] {{ background-color: {COLOR_INCOME} !important; border: none; font-weight: 600; }}
    button[kind="secondary"] {{ background-color: rgba(255, 255, 255, 0.05) !important; border: none; color: {COLOR_TEXT_SECONDARY}; }}

    /* Plotly 圖表背景透明 */
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
        <h1 style='color: #FFFFFF; font-size: 42px; font-weight:800; letter-spacing:-1px; margin-bottom: 8px;'>
            Delivery <span style='color:{COLOR_INCOME};'>Pro</span>
        </h1>
        <p style='color:{COLOR_TEXT_SECONDARY}; font-size: 16px; font-weight: 500;'>Professional Courier Analytics</p>
    </div>
    <br><br>
    """, unsafe_allow_html=True)
    
    col_p1, col_p2, col_p3 = st.columns([1, 3, 1])
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
if "show_add_log" not in st.session_state: st.session_state.show_add_log = False # 控制記帳表單顯示

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
    st.markdown(f"<div class='sidebar-brand'>Delivery <span>Pro</span></div>", unsafe_allow_html=True)
    # 將 "➕ 記一筆" 從導覽中移除，改用 FAB 觸發
    page = st.radio("Navigation", ["📊 總覽 (Dashboard)", "📈 報表 (Analytics)", "⚙️ 設定 (Settings)"], label_visibility="collapsed")
    
    st.divider()
    
    st.markdown(f"""
    <div style='margin-bottom: 20px;'>
        <div style='color:{COLOR_TEXT_SECONDARY}; font-size:12px; font-weight: 600; margin-bottom:6px;'>DRIVER TIER</div>
        <div style='display: flex; align-items: center;'>
            <span style='font-size: 28px; margin-right: 10px;'>{d_icon}</span>
            <div>
                <div style='font-size:18px; font-weight:700; color:#FFF;'>{driver_tier}</div>
                <div style='font-size:13px; color:{COLOR_TEXT_SECONDARY};'>{d_title}</div>
            </div>
        </div>
    </div>
    <div style='margin-bottom: 20px;'>
        <div style='color:{COLOR_TEXT_SECONDARY}; font-size:12px; font-weight: 600; margin-bottom:6px;'>LIFETIME REVENUE</div>
        <div style='font-size:22px; font-weight:800; color:{COLOR_INCOME};'>${int(total_income):,}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 強制同步 (Sync)", use_container_width=True):
        load_data.clear()
        load_settings.clear()
        st.rerun()

# ==========================================
# 頁面內容：📊 總覽 (Dashboard) - 參考圖一設計
# ==========================================
if page == "📊 總覽 (Dashboard)":
    # 標題與日期選擇
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.markdown(f"<h2 style='margin: 0;'>{st.session_state.selected_date.strftime('%Y年%m月%d日')}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:{COLOR_TEXT_SECONDARY}; margin: 0;'>{WEEKDAY_CHINESE_MAP[st.session_state.selected_date.weekday()]}</p>", unsafe_allow_html=True)
    with col_t2:
        temp_date = st.date_input("選擇日期", value=st.session_state.selected_date, label_visibility="collapsed")
        if temp_date != st.session_state.selected_date: st.session_state.selected_date = temp_date; st.rerun()

    # 計算當日數據
    daily_df = df[df['日期'].dt.date == st.session_state.selected_date] if not df.empty else pd.DataFrame()
    d_inc = daily_df[daily_df['類型'] == '收入']['金額'].sum() if not daily_df.empty else 0
    d_exp = daily_df[daily_df['類型'] == '開銷']['金額'].sum() if not daily_df.empty else 0
    d_hr = daily_df[daily_df['類型'] == '收入']['上線時數'].sum() if not daily_df.empty else 0.0
    d_balance = d_inc - d_exp
    
    # 1. 當日概況卡片
    st.markdown(f"""
    <div class='pro-card' style='margin-top: 20px;'>
        <div class='kpi-container'>
            <div class='kpi-item'>
                <div class='kpi-title'>本日收入</div>
                <div class='kpi-value income'>${int(d_inc):,}</div>
            </div>
            <div style='width: 1px; height: 40px; background-color: rgba(255,255,255,0.1);'></div>
            <div class='kpi-item'>
                <div class='kpi-title'>本日開銷</div>
                <div class='kpi-value expense'>${int(d_exp):,}</div>
            </div>
            <div style='width: 1px; height: 40px; background-color: rgba(255,255,255,0.1);'></div>
            <div class='kpi-item'>
                <div class='kpi-title'>本日結餘</div>
                <div class='kpi-value balance'>${int(d_balance):,}</div>
            </div>
        </div>
        <div style='margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; color: {COLOR_TEXT_SECONDARY}; font-size: 14px;'>
            <span>上線時數: <span style='color: {COLOR_TEXT_PRIMARY}; font-weight: 600;'>{d_hr:.1f}h</span></span>
            <span>換算時薪: <span style='color: {COLOR_TEXT_PRIMARY}; font-weight: 600;'>${int(d_inc/d_hr) if d_hr > 0 else 0}/h</span></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. 當日明細列表 (仿照圖一)
    st.markdown("<h3 style='margin-top: 30px; margin-bottom: 16px;'>本日明細</h3>", unsafe_allow_html=True)
    
    if not daily_df.empty:
        with st.container():
            st.markdown(f"<div class='pro-card' style='padding: 8px 24px;'>", unsafe_allow_html=True)
            for _, row in daily_df.sort_values(by='日期', ascending=False).iterrows():
                r_type = row['類型']
                r_item = row['項目']
                r_amount = row['金額']
                r_note = row['備註']
                r_incident = row.get('異常', 'False') == 'True'
                
                icon = CATEGORY_ICONS.get(r_item, CATEGORY_ICONS.get(r_type, "📝"))
                amount_class = "income" if r_type == "收入" else ("expense" if r_type == "開銷" else "")
                amount_sign = "+" if r_type == "收入" else ("-" if r_type == "開銷" else "")
                amount_str = f"{amount_sign}${int(r_amount):,}" if r_type != "休假" else "休假"
                
                subtitle = r_note if r_note else r_item
                if r_incident: subtitle = f"⚠️ {subtitle}"
                if r_type == '收入' and row['上線時數'] > 0: subtitle += f" ({row['上線時數']}h)"

                st.markdown(f"""
                <div class='list-item'>
                    <div class='list-icon'>{icon}</div>
                    <div class='list-content'>
                        <div class='list-title'>{r_item}</div>
                        <div class='list-subtitle'>{subtitle}</div>
                    </div>
                    <div class='list-amount {amount_class}'>{amount_str}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # 編輯/刪除功能 (保持原樣，但放入 Expander)
            with st.expander("🛠️ 編輯或移除紀錄"):
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
    else:
        st.info("本日尚無任何紀錄，點擊右下角按鈕新增。")

    # ==========================================
    # 懸浮動作按鈕 (FAB) 與 記帳表單
    # ==========================================
    # 模擬 FAB 的觸發開關
    if st.button("➕", key="fab_trigger", help="記一筆"):
        st.session_state.show_add_log = not st.session_state.show_add_log
    
    # 透過 CSS 將按鈕樣式化為 FAB
    st.markdown("""
    <style>
    div.stButton > button[kind="secondary"] {
        position: fixed;
        bottom: 30px;
        right: 20px;
        width: 64px;
        height: 64px;
        border-radius: 50%;
        background-color: #06C167;
        color: white;
        font-size: 32px;
        font-weight: 300;
        border: none;
        box-shadow: 0 4px 16px rgba(6, 193, 103, 0.5);
        z-index: 9999;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: #05ad5c;
        box-shadow: 0 6px 20px rgba(6, 193, 103, 0.6);
        border: none;
    }
    div.stButton > button[kind="secondary"]:focus:not(:active) {
        border: none;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    # 記帳表單彈出視窗 (使用 Expander 模擬)
    if st.session_state.show_add_log:
        with st.expander("📝 快速記一筆 (Quick Log)", expanded=True):
            if st.session_state.show_success: 
                st.success("✅ 紀錄已成功儲存！")
                st.session_state.show_success = False

            # 直接使用當前選擇的日期
            record_date = st.session_state.selected_date
            st.caption(f"紀錄日期: {record_date.strftime('%Y-%m-%d')} ({WEEKDAY_CHINESE_MAP[record_date.weekday()]})")
            
            is_leave = st.checkbox("🏖️ 標記為「休假」 (勾選後直接儲存)", value=False)
            st.divider()
    
            if not is_leave:
                st.markdown("#### 💰 收入與時數")
                platform_mode = st.radio("模式", ["單一", "雙開"], horizontal=True, label_visibility="collapsed")
                
                amount, amount_u, amount_f = 0, 0, 0
                item = "Uber Eats"
                hours = 0.0
                
                if platform_mode == "單一":
                    c1, c2 = st.columns([3, 2])
                    with c1: item = st.selectbox("平台", ["Uber Eats", "Foodpanda", "其他獎金"], label_visibility="collapsed")
                    with c2: amount = st.number_input("金額", min_value=0, step=10, value=None, key=f"amt_{k}", label_visibility="collapsed", placeholder="$")
                else:
                    c1, c2 = st.columns(2)
                    with c1: amount_u = st.number_input("Uber Eats $", min_value=0, step=10, value=None, key=f"amtu_{k}")
                    with c2: amount_f = st.number_input("Foodpanda $", min_value=0, step=10, value=None, key=f"amtf_{k}")
                
                st.write("")
                time_mode = st.radio("時數", ["APP反推", "手動", "系統換算"], horizontal=True, label_visibility="collapsed")
                
                if time_mode == "系統換算":
                    t_col1, t_col2 = st.columns(2)
                    with t_col1: start_time = st.time_input("首單", time(10, 0), key=f"t1_{k}") 
                    with t_col2: end_time = st.time_input("末單", time(22, 0), key=f"t2_{k}")   
                    dt_start, dt_end = datetime.combine(date(2000, 1, 1), start_time), datetime.combine(date(2000, 1, 1), end_time)
                    if dt_end < dt_start: dt_end += timedelta(days=1)
                    hours = round((dt_end - dt_start).total_seconds() / 3600.0, 2)
                    st.caption(f"⏱️ 計算時數: {hours}h")
                elif time_mode == "手動":
                    h_col, m_col = st.columns(2)
                    with h_col: input_hours = st.number_input("時", min_value=0, step=1, value=None, key=f"hr_{k}")
                    with m_col: input_minutes = st.number_input("分", min_value=0, max_value=59, step=1, value=None, key=f"min_{k}")
                    hours = round((input_hours or 0) + ((input_minutes or 0) / 60.0), 2)
                else: 
                    h_col, m_col = st.columns(2)
                    with h_col: remain_hours = st.number_input("剩餘時", min_value=0, max_value=12, step=1, value=None, key=f"r_hr_{k}")
                    with m_col: remain_minutes = st.number_input("剩餘分", min_value=0, max_value=59, step=1, value=None, key=f"r_min_{k}")
                    if remain_hours is not None or remain_minutes is not None:
                        r_h = remain_hours or 0
                        r_m = remain_minutes or 0
                        used_mins = max(0, 720 - (r_h * 60 + r_m))
                        hours = round(used_mins / 60.0, 2)
                        st.caption(f"⏱️ 反推時數: {hours}h")

                st.divider()
                st.markdown("#### 💸 開銷 (選填)")
                c_exp1, c_exp2 = st.columns(2)
                with c_exp1: gas_exp = st.number_input("⛽ 油錢", min_value=0, step=10, value=None, key=f"gas_{k}")
                with c_exp2: maint_exp = st.number_input("🔧 保養", min_value=0, step=10, value=None, key=f"maint_{k}")
                c_exp3, c_exp4 = st.columns(2)
                with c_exp3: other_name = st.text_input("其他名稱", placeholder="如:雨衣", key=f"oname_{k}")
                with c_exp4: other_exp = st.number_input("金額", min_value=0, step=10, value=None, key=f"oexp_{k}")
                
                st.divider()
                st.markdown("#### 📝 備註")
                c_note1, c_note2 = st.columns([3, 1])
                with c_note1: note = st.text_input("備註內容", placeholder="輸入心得...", key=f"note_{k}", label_visibility="collapsed")
                with c_note2: is_incident = st.checkbox("⚠️ 異常", key=f"trib_{k}")
                
                st.write("")
                if st.button("🚀 儲存紀錄", type="primary", use_container_width=True):
                    rows_to_add = []
                    val_amount = amount if platform_mode == "單一" else ((amount_u or 0) + (amount_f or 0))
                    
                    if val_amount > 0:
                        if platform_mode == "單一":
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
                        st.session_state.show_add_log = False # 儲存後關閉
                        st.rerun()
                    else:
                        st.warning("請至少輸入一筆資料")
            else:
                note = st.text_input("休假備註", placeholder="放鬆一下...", key=f"note_{k}")
                if st.button("🚀 儲存休假", type="primary", use_container_width=True):
                    save_data_batch([[str(record_date), "休假", "休假", 0, 0.0, note, "False"]])
                    st.session_state.show_success = True
                    st.session_state.input_key += 1
                    st.session_state.show_add_log = False
                    st.rerun()

# ==========================================
# 頁面內容：📈 報表 (Analytics) - 參考圖二設計
# ==========================================
elif page == "📈 報表 (Analytics)":
    # 月份選擇器
    if not df.empty:
        months = df['日期'].dt.to_period('M').astype(str).unique()
        col_m1, col_m2 = st.columns([3, 2])
        with col_m1:
            st.markdown("<h2 style='margin: 0;'>每月報表</h2>", unsafe_allow_html=True)
        with col_m2:
            selected_month = st.selectbox("選擇月份", sorted(months, reverse=True), label_visibility="collapsed")
        
        month_df = df[df['日期'].dt.to_period('M').astype(str) == selected_month]
        
        if not month_df.empty:
            # 計算月度數據
            m_inc = month_df[month_df['類型'] == '收入']['金額'].sum()
            m_exp = month_df[month_df['類型'] == '開銷']['金額'].sum()
            m_balance = m_inc - m_exp
            
            # 1. 月度概況卡片 (仿照圖一上方)
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

            # 2. 收支甜甜圈圖 (仿照圖二，中心顯示結餘)
            st.markdown("<h3 style='margin-top: 30px; margin-bottom: 16px;'>收支分析</h3>", unsafe_allow_html=True)
            with st.container():
                st.markdown(f"<div class='pro-card' style='padding: 20px 0;'>", unsafe_allow_html=True)
                
                # 準備圖表數據
                pie_data = [
                    {"label": "總收入", "value": m_inc, "color": COLOR_INCOME},
                    {"label": "總支出", "value": m_exp, "color": COLOR_EXPENSE}
                ]
                
                fig = go.Figure(data=[go.Pie(
                    labels=[d['label'] for d in pie_data],
                    values=[d['value'] for d in pie_data],
                    hole=0.6, # 設定為甜甜圈圖
                    marker=dict(colors=[d['color'] for d in pie_data]),
                    textinfo='label+percent',
                    hoverinfo='label+value+percent',
                    textfont=dict(size=14, color=COLOR_TEXT_PRIMARY),
                    showlegend=False
                )])

                # 在中心添加文字
                fig.add_annotation(
                    text=f"月結餘<br><span style='font-size: 24px; font-weight: 700; color: {COLOR_BALANCE};'>${int(m_balance):,}</span>",
                    x=0.5, y=0.5,
                    font=dict(size=14, color=COLOR_TEXT_SECONDARY),
                    showarrow=False
                )

                fig.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=300,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown("</div>", unsafe_allow_html=True)

            # 3. 分類明細列表 (仿照圖二下方)
            st.markdown("<h3 style='margin-top: 30px; margin-bottom: 16px;'>分類明細</h3>", unsafe_allow_html=True)
            with st.container():
                st.markdown(f"<div class='pro-card' style='padding: 8px 24px;'>", unsafe_allow_html=True)
                
                # 彙整分類數據
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
# 頁面內容：⚙️ 設定 (Settings) - 保持原樣
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
