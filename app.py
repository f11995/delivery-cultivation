import streamlit as st
import pandas as pd
from datetime import date, time, datetime, timedelta
import calendar
import plotly.express as px
import plotly.graph_objects as go
import random
import json
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# ⚙️ 系統常數與專業設定
# ==========================================
CUSTOM_COLORS = {"Uber Eats": "#06C167", "Foodpanda": "#FF2B85", "其他獎金": "#F6C143", "休假": "#B0B0B0", "機車油錢": "#FF9900", "機車保養": "#FF4444"}
WEEKDAY_MAP = {0: '星期一', 1: '星期二', 2: '星期三', 3: '星期四', 4: '星期五', 5: '星期六', 6: '星期日'}

# 將原本的修仙境界轉換為專業的駕駛等級
DRIVER_TIERS = [
    (0, "新手駕駛", "Rookie", "🔰"), (10000, "青銅夥伴 I", "Bronze I", "🥉"), (30000, "青銅夥伴 II", "Bronze II", "🥉"), (60000, "青銅夥伴 III", "Bronze III", "🥉"),
    (100000, "白銀專家 I", "Silver I", "🥈"), (150000, "白銀專家 II", "Silver II", "🥈"), (200000, "白銀專家 III", "Silver III", "🥈"),
    (300000, "黃金菁英 I", "Gold I", "🥇"), (400000, "黃金菁英 II", "Gold II", "🥇"), (500000, "黃金菁英 III", "Gold III", "🥇"),
    (600000, "白金先鋒 I", "Platinum I", "💠"), (800000, "白金先鋒 II", "Platinum II", "💠"), (1000000, "白金先鋒 III", "Platinum III", "💠"),
    (1500000, "鑽石大師 I", "Diamond I", "💎"), (2000000, "鑽石大師 II", "Diamond II", "💎"), (3000000, "鑽石大師 III", "Diamond III", "💎"),
    (5000000, "巔峰傳奇", "Apex Legend", "👑")
]

# 將原本的運勢轉換為系統的專業引導與提示
SYSTEM_TIPS = [
    "✅ 系統分析：今日特定熱區點單需求高，建議前往商圈待命。",
    "✅ 效率提示：保持良好的接單率有助於提升演算法派單優先級。",
    "✅ 安全宣導：路口減速慢行，防禦駕駛是長期穩定收入的基石。",
    "✅ 節能建議：平穩起步可有效降低油耗，提升整體投資報酬率。",
    "⚠️ 天候預警：今日局部地區有降雨機率，請提前準備雨具並注意防滑。",
    "⚠️ 尖峰提醒：即將進入用餐尖峰時段，請確保手機電量與設備正常運作。",
    "💡 系統提示：定期檢查車輛胎壓與煞車，可避免突發性的營業中斷。",
    "💡 帳戶分析：設定每日或每週的收入目標，有助於維持穩定的上線節奏。",
    "📊 數據洞察：週末晚餐時段通常具備最高的客單價與加成倍率。",
    "📊 績效提醒：減少非必要的拒單，能有效維持系統綜合評分。"
]

# ==========================================
# 🌐 雲端資料庫引擎 (保留舊有 sheet 名稱以防數據遺失)
# ==========================================
@st.cache_resource
def get_gspread_client():
    try:
        creds_dict = json.loads(st.secrets["GOOGLE_KEY"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 資料庫連線失敗，請檢查環境變數：{e}")
        st.stop()

@st.cache_resource
def get_sheet():
    client = get_gspread_client()
    try: return client.open_by_url(st.secrets["SHEET_URL"])
    except Exception as e:
        st.error(f"❌ 找不到試算表！請確認網址正確：{e}")
        st.stop()

@st.cache_resource
def get_roster_ws():
    sheet = get_sheet()
    try: return sheet.worksheet("宗門名冊") # 保持原名不變，保護舊資料
    except gspread.exceptions.WorksheetNotFound: 
        ws = sheet.add_worksheet(title="宗門名冊", rows="100", cols="20")
        ws.append_row(["User_ID", "道號", "總靈石", "總時數", "總天數", "天劫數", "戰鬥力", "境界", "座騎", "任務日期", "任務ID", "任務狀態", "運勢日期", "運勢", "目標月份", "目標金額", "額外戰力"])
        return ws

@st.cache_resource
def get_user_records_ws(user_id):
    sheet = get_sheet()
    ws_name = f"records_{user_id}"
    try: return sheet.worksheet(ws_name)
    except gspread.exceptions.WorksheetNotFound: 
        ws = sheet.add_worksheet(title=ws_name, rows="1000", cols="10")
        ws.append_row(["日期", "類型", "項目", "金額", "上線時數", "備註", "天劫"])
        return ws

@st.cache_resource
def get_feed_ws():
    sheet = get_sheet()
    try: return sheet.worksheet("宗門動態") # 保持原名不變
    except gspread.exceptions.WorksheetNotFound: 
        ws = sheet.add_worksheet(title="宗門動態", rows="500", cols="5")
        ws.append_row(["時間", "發送者", "接收者", "動作", "訊息"])
        return ws

@st.cache_data(ttl=30, show_spinner=False)
def get_roster_data():
    return get_roster_ws().get_all_records()

@st.cache_data(ttl=30, show_spinner=False)
def get_feed_data():
    try: return get_feed_ws().get_all_records()
    except: return []

@st.cache_data(ttl=60, show_spinner=False)
def get_all_team_data():
    sheet = get_sheet()
    roster_records = get_roster_data()
    # 內部將 "道號" 映射為 "Driver_Name"
    user_map = {str(r["User_ID"]): str(r.get("道號", "Unknown Driver")) for r in roster_records if str(r.get("道號", "")) != ""}
    all_data = []
    for ws in sheet.worksheets():
        if ws.title.startswith("records_"):
            uid = ws.title.replace("records_", "")
            if uid in user_map:
                records = ws.get_all_records()
                if records:
                    df_temp = pd.DataFrame(records)
                    df_temp['User_ID'] = uid
                    df_temp['Driver_Name'] = user_map[uid]
                    all_data.append(df_temp)
    big_df = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
    if not big_df.empty: big_df['日期'] = pd.to_datetime(big_df['日期']).dt.date
    return user_map, big_df, roster_records

@st.cache_data(ttl=30, show_spinner=False)
def load_data(user_id):
    ws = get_user_records_ws(user_id)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        if "上線時數" not in df.columns: df["上線時數"] = 0.0
        if "天劫" not in df.columns: df["天劫"] = "False"
        df['日期'] = pd.to_datetime(df['日期'])
    return df

def save_data(date_val, record_type, item, amount, hours, note, is_incident):
    with st.spinner("⏳ 資料同步至雲端伺服器中..."):
        ws = get_user_records_ws(st.session_state.user_id)
        ws.append_row([str(date_val), str(record_type), str(item), int(amount), float(hours), str(note), str(is_incident)])
        load_data.clear(st.session_state.user_id)
        update_roster_stats()

def delete_data(indices_to_drop):
    with st.spinner("⏳ 正在移除指定紀錄..."):
        ws = get_user_records_ws(st.session_state.user_id)
        for idx in sorted(indices_to_drop, reverse=True): ws.delete_rows(idx + 2)
        load_data.clear(st.session_state.user_id)
        update_roster_stats()

def add_feed_interaction(sender_name, receiver_name, action, message):
    ws = get_feed_ws()
    ws.append_row([str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(sender_name), str(receiver_name), str(action), str(message)])
    get_feed_data.clear()

def get_user_profile():
    ws = get_roster_ws()
    records = get_roster_data()
    for i, r in enumerate(records):
        if str(r["User_ID"]) == st.session_state.user_id: return r, i + 2
    new_row = [st.session_state.user_id, "", 0, 0, 0, 0, 0, "新手駕駛", "一般車輛", "", 0, 0, "", "", "", 0, 0]
    ws.append_row(new_row)
    get_roster_data.clear()
    return dict(zip(["User_ID", "道號", "總靈石", "總時數", "總天數", "天劫數", "戰鬥力", "境界", "座騎", "任務日期", "任務ID", "任務狀態", "運勢日期", "運勢", "目標月份", "目標金額", "額外戰力"], new_row)), len(records) + 2

def update_profile_field(col_name, value):
    ws = get_roster_ws()
    records = get_roster_data()
    headers = list(records[0].keys()) if records else ws.row_values(1)
    if col_name in headers:
        col_idx = headers.index(col_name) + 1
        row_idx = next((i + 2 for i, r in enumerate(records) if str(r["User_ID"]) == st.session_state.user_id), None)
        if row_idx:
            if isinstance(value, (int, float)): ws.update_cell(row_idx, col_idx, float(value) if isinstance(value, float) else int(value))
            else: ws.update_cell(row_idx, col_idx, str(value))
            get_roster_data.clear()

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

def get_vehicle_tier_info(total_hours):
    if total_hours >= 1000: return "旗艦重機", "🏍️"
    elif total_hours >= 500: return "黃牌重機", "🛵"
    elif total_hours >= 100: return "白牌速克達", "🛵"
    else: return "一般輕型車輛", "🚲"

def update_roster_stats():
    df = load_data(st.session_state.user_id)
    t_inc = int(df[df['類型'] == '收入']['金額'].sum()) if not df.empty else 0
    t_hr = float(df[df['類型'] == '收入']['上線時數'].sum()) if not df.empty else 0.0
    t_days = int(df[df['類型'] == '收入']['日期'].nunique()) if not df.empty else 0
    t_incidents = int(df[df['天劫'] == 'True'].shape[0]) if not df.empty and '天劫' in df.columns else 0
    
    avg_w = t_inc / t_hr if t_hr > 0 else 0
    
    # 專業版表現分數計算 (原戰鬥力)
    base_score = int(((t_inc / 100) + (avg_w * 10) + (t_days * 50)))
    
    ws = get_roster_ws()
    records = get_roster_data()
    
    legacy_bonus = 0
    row_idx = None
    for i, r in enumerate(records):
        if str(r["User_ID"]) == st.session_state.user_id:
            row_idx = i + 2
            legacy_bonus = int(r.get("額外戰力", 0)) if str(r.get("額外戰力", "")) != "" else 0
            break
            
    final_score = base_score + legacy_bonus
    tier, _, _, _, _, _ = get_driver_tier_info(t_inc)
    vehicle, _ = get_vehicle_tier_info(t_hr)
    
    if row_idx:
        # 將資料依序寫回試算表對應位置以相容舊資料結構
        ws.update(values=[[int(t_inc), float(t_hr), int(t_days), int(t_incidents), int(final_score), str(tier), str(vehicle)]], range_name=f"C{row_idx}:I{row_idx}")
        get_roster_data.clear()

def change_date(new_date): st.session_state.selected_date = new_date

# ==========================================
# 🎨 專業版 UI (Uber Pro Style)
# ==========================================
st.set_page_config(page_title="Delivery Pro Dashboard", layout="wide", page_icon="📈")
st.markdown("""
<style>
    /* 專業深色背景 */
    .stApp { background-color: #121212; color: #FFFFFF; }
    
    /* 隱藏預設上方邊距 */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    /* 商務卡片風格 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1C1C1E !important;
        border: 1px solid #2C2C2E !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2) !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem;
    }

    /* 標籤頁 (Tabs) 專業化 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        border-bottom: 2px solid #2C2C2E;
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8E8E93;
        font-weight: 500;
        padding: 10px 0;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #06C167 !important;
        border-bottom: 2px solid #06C167 !important;
    }

    /* 主指標數值 */
    .metric-value {
        font-size: 42px;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.2;
    }
    .metric-label {
        font-size: 13px;
        font-weight: 600;
        color: #8E8E93;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .text-green { color: #06C167; }
    .text-red { color: #FF453A; }

    /* 團隊日誌卡片 */
    .log-item {
        border-left: 3px solid #06C167;
        background-color: #242426;
        padding: 12px 16px;
        border-radius: 4px 8px 8px 4px;
        margin-bottom: 8px;
        font-size: 14px;
    }
    .log-time { color: #8E8E93; font-size: 12px; margin-bottom: 4px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛡️ 系統登入認證
# ==========================================
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_id" not in st.session_state: st.session_state.user_id = ""

if not st.session_state.authenticated:
    st.markdown("<br><br><div style='text-align: center;'><h1 style='color: #FFFFFF; font-size: 40px; font-weight:700;'>Delivery Pro Analytics</h1><p style='color:#8E8E93;'>Enter your Driver Access Token to continue</p></div><br>", unsafe_allow_html=True)
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        pwd_input = st.text_input("Access Token", type="password", placeholder="Token...")
        if st.button("Secure Login", type="primary", use_container_width=True):
            app_pwd = st.secrets.get("APP_PASSWORD", "未設定")
            invites = st.secrets.get("INVITES", {})
            if pwd_input == app_pwd:
                st.session_state.authenticated, st.session_state.user_id = True, "yu_master"
                st.rerun()
            elif pwd_input in invites:
                st.session_state.authenticated, st.session_state.user_id = True, invites[pwd_input]
                st.rerun()
            else: st.error("❌ Authentication Failed.")
    st.stop()

# 載入資料
with st.spinner("⏳ Synchronizing data..."):
    profile, _ = get_user_profile()
    user_map, big_df, roster_records = get_all_team_data()

if profile["道號"] == "":
    st.markdown("<h2 style='text-align: center;'>📋 Driver Registration</h2>", unsafe_allow_html=True)
    new_name = st.text_input("Please enter your Display Name:")
    if st.button("Register Account", type="primary"):
        if new_name.strip():
            update_profile_field("道號", new_name.strip())
            get_roster_data.clear()
            get_all_team_data.clear()
            st.rerun()
    st.stop()

driver_name = profile["道號"] # 介面顯示為駕駛代號
if "selected_date" not in st.session_state: st.session_state.selected_date = date.today()
if "input_key" not in st.session_state: st.session_state.input_key = 0
if "show_success" not in st.session_state: st.session_state.show_success = False

# 🔄 頂部大廳列
t_col1, t_col2 = st.columns([4, 1])
with t_col1:
    st.markdown(f"<h2>📊 Overview <span style='color:#8E8E93; font-size:20px; font-weight:400;'>| Driver: {driver_name}</span></h2>", unsafe_allow_html=True)
with t_col2:
    st.markdown("<br>", unsafe_allow_html=True) 
    if st.button("🔄 Sync Data", type="secondary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

tab_dash, tab_input, tab_report, tab_year, tab_settings, tab_team = st.tabs(["🏠 儀表板", "➕ 新增紀錄", "📊 財務報表", "📈 年度分析", "⚙️ 帳號設定", "🏆 團隊排行榜"])

df = load_data(st.session_state.user_id)
k = st.session_state.input_key
today = date.today()

# 映射舊有資料名稱
perf_score = int(profile.get('戰鬥力', 0)) if str(profile.get('戰鬥力', '')) != '' else 0
total_income = int(profile.get('總靈石', 0)) if str(profile.get('總靈石', '')) != '' else 0
total_hours = float(profile.get('總時數', 0.0)) if str(profile.get('總時數', '')) != '' else 0.0
total_incidents = int(profile.get('天劫數', 0)) if str(profile.get('天劫數', '')) != '' else 0

driver_tier, next_tier, next_exp, prog, d_title, d_icon = get_driver_tier_info(total_income)
vehicle_tier, v_icon = get_vehicle_tier_info(total_hours)

# ==========================================
# 分頁：🏠 儀表板 (Dashboard)
# ==========================================
with tab_dash:
    stat_c1, stat_c2, stat_c3 = st.columns([1, 1, 1.5])
    
    with stat_c1:
        with st.container(border=True):
            st.markdown(f"<div class='metric-label'>⭐ 綜合表現分數 (Performance Score)</div><div class='metric-value'>{perf_score:,}</div>", unsafe_allow_html=True)
            
    with stat_c2:
        with st.container(border=True):
            st.markdown(f"<div class='metric-label'>🏆 當前駕駛等級 (Driver Tier)</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='display:flex; align-items:center; gap:10px;'><span style='font-size:32px;'>{d_icon}</span><span style='font-size:24px; font-weight:600;'>{driver_tier}</span></div>", unsafe_allow_html=True)
            
    with stat_c3:
        with st.container(border=True):
            st.markdown("<div class='metric-label'>🎯 累積收入進度 (Income Progress)</div>", unsafe_allow_html=True)
            st.progress(prog)
            st.markdown(f"<div style='font-size: 13px; color: #8E8E93; margin-top: 8px; text-align: right;'>Current: <span style='color:#FFF;'>${total_income:,}</span> / Next Tier: ${next_exp:,}</div>", unsafe_allow_html=True)

    st.divider()

    feed_col, tip_col = st.columns([1.5, 1])
    
    with feed_col:
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>📋 團隊活動日誌 (Activity Log)</h4>", unsafe_allow_html=True)
            
            sos_users = []
            if not big_df.empty:
                today_tribs = big_df[(big_df['日期'] == today) & (big_df['天劫'] == 'True') & (big_df['User_ID'] != st.session_state.user_id)]
                sos_users = today_tribs['Driver_Name'].unique().tolist()
                
            if sos_users:
                st.error("⚠️ [系統警報] 以下駕駛員今日回報異常狀況！")
                for sos_name in sos_users:
                    sc1, sc2 = st.columns([2, 1])
                    sc1.write(f"Driver **{sos_name}** 提報了突發狀況。")
                    if sc2.button("👍 發送支援鼓勵", key=f"support_{sos_name}"):
                        add_feed_interaction(driver_name, sos_name, "系統支援", "已向您發送鼓勵，請注意行車安全。")
                        st.toast("已發送鼓勵訊息。")
            
            try:
                feed_records = get_feed_data()
                if feed_records:
                    for r in reversed(feed_records[-6:]):
                        # 清理舊有修仙術語，若有舊紀錄直接顯示
                        action_text = r['動作']
                        if action_text == "傳送靈氣": action_text = "發送鼓勵"
                        if action_text == "煉丹大成功": action_text = "達成收入目標"
                        if action_text == "吸星大法": action_text = "獲取系統加成"
                        
                        st.markdown(f"<div class='log-item'><div class='log-time'>{r['時間']}</div><b>{r['發送者']}</b> 觸發了事件 [<b>{action_text}</b>]<br><span style='color:#CCC;'>{r['訊息']}</span></div>", unsafe_allow_html=True)
                else: st.caption("No recent activity.")
            except: st.caption("Loading logs...")

    with tip_col:
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>💡 系統指引 (System Forecast)</h4>", unsafe_allow_html=True)
            st.caption("根據大數據模型提供的上線建議")
            
            # 使用原「運勢」欄位儲存系統提示
            current_tip = str(profile.get('運勢', ''))
            if str(profile.get("運勢日期", "")) == str(today) and current_tip:
                # 過濾掉可能殘留的舊有修仙字眼
                if "靈氣" in current_tip or "大吉" in current_tip or "凶" in current_tip:
                    current_tip = random.choice(SYSTEM_TIPS)
                    update_profile_field("運勢", current_tip)
                st.markdown(f"<div style='background-color:#242426; padding:15px; border-radius:8px; border-left:4px solid #06C167; margin-top:10px;'>{current_tip}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 獲取今日最新指引", type="primary", use_container_width=True):
                    new_tip = random.choice(SYSTEM_TIPS)
                    update_profile_field("運勢日期", str(today))
                    update_profile_field("運勢", str(new_tip))
                    st.rerun()

# ==========================================
# 分頁：➕ 新增紀錄 (Add Record)
# ==========================================
with tab_input:
    with st.container(border=True):
        col1, col2 = st.columns([1, 1.2])
        with col1:
            st.markdown("### 📝 Input Daily Metrics") 
            if st.session_state.show_success: st.success("✅ 數據已成功同步至伺服器。"); st.session_state.show_success = False
            
            temp_date = st.date_input("選擇日期 (Date)", value=st.session_state.selected_date)
            if temp_date != st.session_state.selected_date: st.session_state.selected_date = temp_date; st.rerun()
            record_date = st.session_state.selected_date
    
            record_type = st.radio("資料類型 (Type)", ["收入", "開銷", "休假"], horizontal=True)
            if record_type in ["收入", "開銷"]:
                # 原「天劫」改為異常狀況
                is_incident = st.checkbox("⚠️ 標記異常狀況 (如：奧客、車輛故障、極端天氣)", key=f"trib_{k}")
                st.write("---")
    
            if record_type == "收入":
                platform_mode = st.radio("輸入模式 (Mode)", ["單一平台", "雙開合併 (Split)"], horizontal=True)
                if platform_mode == "單一平台":
                    item = st.selectbox("平台 (Platform)", ["Uber Eats", "Foodpanda", "其他獎金"])
                    amount = st.number_input("金額 (Revenue)", min_value=0, step=10, value=None, key=f"amt_{k}")
                    val_amount = amount if amount is not None else 0
                else:
                    st.write("輸入各平台金額 (Split Revenue)")
                    u_col, f_col = st.columns(2)
                    with u_col: amount_u = st.number_input("Uber Eats", min_value=0, step=10, value=None, key=f"amtu_{k}")
                    with f_col: amount_f = st.number_input("Foodpanda", min_value=0, step=10, value=None, key=f"amtf_{k}")
                    val_amount = (amount_u or 0) + (amount_f or 0)
                    
                time_mode = st.radio("時數計算 (Time Calculation)", ["系統換算 (首單至末單)", "手動輸入", "剩餘駕駛時間反推 (12H制)"], horizontal=True)
                
                if time_mode == "系統換算 (首單至末單)":
                    t_col1, t_col2 = st.columns(2)
                    with t_col1: start_time = st.time_input("上線時間 (Start)", time(10, 0), key=f"t1_{k}") 
                    with t_col2: end_time = st.time_input("下線時間 (End)", time(22, 0), key=f"t2_{k}")   
                    dt_start, dt_end = datetime.combine(date(2000, 1, 1), start_time), datetime.combine(date(2000, 1, 1), end_time)
                    if dt_end < dt_start: dt_end += timedelta(days=1)
                    hours = round((dt_end - dt_start).total_seconds() / 3600.0, 2)
                    st.info(f"⏱️ 系統計算總時數：**{hours} 小時**")
                elif time_mode == "手動輸入":
                    h_col, m_col = st.columns(2)
                    with h_col: input_hours = st.number_input("小時 (HH)", min_value=0, step=1, value=None, key=f"hr_{k}")
                    with m_col: input_minutes = st.number_input("分鐘 (MM)", min_value=0, max_value=59, step=1, value=None, key=f"min_{k}")
                    hours = round((input_hours or 0) + ((input_minutes or 0) / 60.0), 2)
                else: 
                    st.caption("💡 輸入 APP 顯示的「剩餘可用駕駛時間」由系統自動反推：")
                    h_col, m_col = st.columns(2)
                    with h_col: remain_hours = st.number_input("剩餘小時 (HH)", min_value=0, max_value=12, step=1, value=None, key=f"r_hr_{k}")
                    with m_col: remain_minutes = st.number_input("剩餘分鐘 (MM)", min_value=0, max_value=59, step=1, value=None, key=f"r_min_{k}")
                    
                    if remain_hours is not None or remain_minutes is not None:
                        r_h = remain_hours or 0
                        r_m = remain_minutes or 0
                        total_remain_mins = r_h * 60 + r_m
                        used_mins = max(0, 720 - total_remain_mins)
                        hours = round(used_mins / 60.0, 2)
                        st.info(f"⏱️ 系統反推實際上線：**{hours} 小時** (約 {used_mins // 60}h {used_mins % 60}m)")
                    else: hours = 0.0
                    
                note = st.text_input("備註 (Notes - Optional)", value="", key=f"note_{k}")
    
                if st.button("📤 送出紀錄 (Submit)", type="primary", use_container_width=True):
                    if platform_mode == "單一平台":
                        if val_amount > 0: save_data(record_date, record_type, item, val_amount, hours, note, is_incident); st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1; st.rerun()
                        else: st.warning("⚠️ 請輸入有效金額。")
                    else:
                        if (amount_u or 0) > 0 or (amount_f or 0) > 0:
                            if (amount_u or 0) > 0: save_data(record_date, record_type, "Uber Eats", amount_u, hours, note, is_incident)
                            if (amount_f or 0) > 0: save_data(record_date, record_type, "Foodpanda", amount_f, 0.0 if (amount_u or 0) > 0 else hours, note, is_incident)
                            st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1; st.rerun()
                        else: st.warning("⚠️ 請輸入有效金額。")
    
            elif record_type == "開銷": 
                expense_choice = st.selectbox("費用項目 (Category)", ["機車油錢", "機車保養", "機車貸款", "設備耗材(如手機架/雨衣)", "其他 (手動輸入)"])
                item = st.text_input("自訂費用名稱", key=f"item_{k}") if expense_choice == "其他 (手動輸入)" else expense_choice
                amount = st.number_input("金額 (Cost)", min_value=0, step=10, value=None, key=f"amt_{k}")
                note = st.text_input("備註 (Notes - Optional)", value="", key=f"note_{k}")
                if st.button("📤 送出開銷 (Submit)", type="primary", use_container_width=True):
                    if (amount or 0) > 0 and item.strip() != "": save_data(record_date, record_type, item, amount, 0.0, note, is_incident); st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1; st.rerun()
                    else: st.warning("⚠️ 請輸入正確的金額與項目名稱。")
            else:
                note = st.text_input("休假備註 (Notes - Optional)", value="", key=f"note_{k}")
                if st.button("📤 記錄休假 (Mark Off-Day)", type="primary", use_container_width=True):
                    save_data(record_date, record_type, "休假", 0, 0.0, note, False)
                    st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1
                    st.rerun()
    
        with col2:
            st.markdown("### 📅 當日總覽 (Daily Summary)") 
            if not df.empty:
                work_dates = set(df[(df['類型'] == '收入') | (df['類型'] == '開銷')]['日期'].dt.date)
                off_dates = set(df[df['類型'] == '休假']['日期'].dt.date)
                daily_df = df[df['日期'].dt.date == st.session_state.selected_date]
                
                if not daily_df.empty:
                    if any(daily_df['類型'] == '休假'): st.info("🏖️ 系統紀錄：當日為排定休假日。")
                    if any(daily_df.get('天劫', "False") == "True"): st.error("⚠️ 系統紀錄：當日有提報異常狀況。")
                    
                    d_inc = daily_df[daily_df['類型'] == '收入']['金額'].sum()
                    d_exp = daily_df[daily_df['類型'] == '開銷']['金額'].sum()
                    d_hr = daily_df[daily_df['類型'] == '收入']['上線時數'].sum()
                    d_wage = d_inc / d_hr if d_hr > 0 else 0
                    h_disp = f"{int(d_hr)}h {int(round((d_hr - int(d_hr)) * 60))}m" if d_hr > 0 else "0h 0m"
                    
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric("總收入 (Rev)", f"${int(d_inc):,}")
                    d2.metric("總開銷 (Exp)", f"${int(d_exp):,}")
                    d3.metric("上線時數 (Hrs)", h_disp) 
                    d4.metric("換算時薪 (Rate)", f"${int(d_wage):,.0f}")
                else: st.caption("選擇下方日期以檢視詳細數據。")
    
                cal_year, cal_month = st.session_state.selected_date.year, st.session_state.selected_date.month
                cal_matrix = calendar.monthcalendar(cal_year, cal_month)
                st.markdown(f"<h5 style='text-align:center; color:#8E8E93;'>{cal_year} - {cal_month:02d}</h5>", unsafe_allow_html=True)
                cols = st.columns(7)
                for i, wd in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]): cols[i].markdown(f"<div style='text-align: center; color:#8E8E93; font-size:12px;'><b>{wd}</b></div>", unsafe_allow_html=True)
                for week in cal_matrix:
                    cols = st.columns(7)
                    for i, day in enumerate(week):
                        if day != 0:
                            cur_d = date(cal_year, cal_month, day)
                            is_sel = (cur_d == st.session_state.selected_date)
                            btn_type = "primary" if is_sel else "secondary"
                            btn_label = f"{day}🏖️" if cur_d in off_dates else (f"{day}✅" if cur_d in work_dates else str(day))
                            cols[i].button(btn_label, key=f"c1_{cal_year}_{cal_month}_{day}", use_container_width=True, type=btn_type, on_click=change_date, args=(cur_d,))
    
                if not daily_df.empty:
                    st.write("---")
                    st.markdown("#### 🛠️ 編輯或移除紀錄")
                    edit_df = daily_df.copy()
                    edit_df['日期'] = edit_df['日期'].dt.strftime('%Y-%m-%d')
                    edit_df.insert(0, "移除", False)
                    # UI 映射更改
                    edit_df = edit_df.rename(columns={"天劫": "異常"})
                    edited_df = st.data_editor(edit_df, hide_index=True, column_config={"移除": st.column_config.CheckboxColumn("勾選移除", default=False)}, disabled=["日期", "類型", "項目", "金額", "上線時數", "備註", "異常"], use_container_width=True, key=f"edit_{st.session_state.selected_date}_{k}")
                    rows_to_delete = edited_df[edited_df["移除"] == True].index.tolist()
                    if len(rows_to_delete) > 0:
                        if st.button("🗑️ 執行資料移除 (Delete)", type="primary", use_container_width=True):
                            delete_data(rows_to_delete)
                            st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1
                            st.rerun()

# ==========================================
# 分頁：📊 財務報表 (Financial Reports)
# ==========================================
with tab_report:
    with st.container(border=True):
        if not df.empty:
            months = df['日期'].dt.to_period('M').astype(str).unique()
            mc1, mc2 = st.columns([1, 1])
            with mc1: selected_month = st.selectbox("選擇檢視月份 (Period)", sorted(months, reverse=True))
            month_df = df[df['日期'].dt.to_period('M').astype(str) == selected_month]
            prev_month_str = f"{int(selected_month.split('-')[0])-1}-12" if selected_month.split('-')[1] == '01' else f"{selected_month.split('-')[0]}-{int(selected_month.split('-')[1])-1:02d}"
            prev_month_df = df[df['日期'].dt.to_period('M').astype(str) == prev_month_str]
            
            current_target = int(profile.get("目標金額", 0)) if str(profile.get("目標月份")) == selected_month else 0
    
            with mc2:
                with st.expander(f"🎯 設定 {selected_month} 預期目標收入 (Set Target)"):
                    new_target = st.number_input("目標金額 (Target Rev)", min_value=0, step=1000, value=current_target)
                    if st.button("💾 儲存目標設定", type="primary"): 
                        update_profile_field("目標月份", str(selected_month))
                        update_profile_field("目標金額", int(new_target))
                        st.rerun()
    
            if not month_df.empty:
                t_inc = month_df[month_df['類型'] == '收入']['金額'].sum()
                t_exp = month_df[month_df['類型'] == '開銷']['金額'].sum()
                n_prof = t_inc - t_exp
                p_inc = prev_month_df[prev_month_df['類型'] == '收入']['金額'].sum() if not prev_month_df.empty else 0
                p_exp = prev_month_df[prev_month_df['類型'] == '開銷']['金額'].sum() if not prev_month_df.empty else 0
                p_prof = p_inc - p_exp
    
                if current_target > 0:
                    st.markdown(f"#### 🚀 目標達成率：`${int(t_inc):,}` / `${current_target:,}`")
                    st.progress(min(t_inc / current_target, 1.0))
                    remaining_amount = current_target - t_inc
                    
                    if remaining_amount > 0:
                        today_d, s_year, s_month = date.today(), int(selected_month.split('-')[0]), int(selected_month.split('-')[1])
                        last_day_of_month = calendar.monthrange(s_year, s_month)[1]
                        if today_d.year == s_year and today_d.month == s_month: days_left = last_day_of_month - today_d.day + 1
                        elif date(s_year, s_month, last_day_of_month) > today_d: days_left = last_day_of_month 
                        else: days_left = 0 
                        
                        if days_left > 0: st.info(f"📈 距離目標差額：**${int(remaining_amount):,}**。本月剩餘 **{days_left}** 天，建議每日目標：**${int(remaining_amount/days_left):,}**。")
                        else: st.warning(f"⚠️ 結算：未達設定目標，差額為 **${int(remaining_amount):,}**。")
                    else: st.success(f"🎉 達標！超出預期目標 **${int(-remaining_amount):,}**。")
                
                st.write("")
                m1, m2, m3 = st.columns(3)
                m1.metric("本月總收入 (Total Revenue)", f"${int(t_inc):,}", delta=f"{int(t_inc - p_inc)} (MoM)" if p_inc > 0 else None)
                m2.metric("本月總開銷 (Total Expenses)", f"${int(t_exp):,}", delta=f"{int(t_exp - p_exp)} (MoM)" if p_exp > 0 else None, delta_color="inverse")
                m3.metric("本月淨利 (Net Profit)", f"${int(n_prof):,}", delta=f"{int(n_prof - p_prof)} (MoM)" if p_prof != 0 else None)
                
                st.divider()
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown("#### 📈 每日收支趨勢 (Daily Trend)")
                    trend_df = month_df[month_df['類型'] != '休假'].groupby(['日期', '項目', '類型'])['金額'].sum().reset_index()
                    trend_df.loc[trend_df['類型'] == '開銷', '金額'] *= -1
                    if not trend_df.empty:
                        fig_bar = px.bar(trend_df, x='日期', y='金額', color='項目', color_discrete_map=CUSTOM_COLORS, barmode='relative')
                        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF'), margin=dict(l=0, r=0, t=30, b=0))
                        st.plotly_chart(fig_bar, use_container_width=True)
                with c2:
                    st.markdown("#### 🥧 收入來源佔比 (Source Mix)")
                    inc_df = month_df[month_df['類型'] == '收入']
                    if not inc_df.empty:
                        pie_data = inc_df.groupby('項目')['金額'].sum().reset_index()
                        fig_pie = px.pie(pie_data, values='金額', names='項目', hole=0.4, color='項目', color_discrete_map=CUSTOM_COLORS)
                        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF'), margin=dict(l=0, r=0, t=30, b=0))
                        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# 分頁：📈 年度分析 (Yearly Analysis)
# ==========================================
with tab_year:
    with st.container(border=True):
        if not df.empty:
            years = df['日期'].dt.year.astype(str).unique()
            selected_year = st.selectbox("選擇年份 (Year)", sorted(years, reverse=True))
            year_df = df[df['日期'].dt.year.astype(str) == selected_year]
            if not year_df.empty:
                st.markdown(f"### 📊 {selected_year} 年度財務總覽 (Annual Overview)")
                annual_df = year_df[year_df['類型'] != '休假'].groupby([year_df['日期'].dt.strftime('%m月'), '類型'])['金額'].sum().unstack(fill_value=0).reset_index()
                annual_df.rename(columns={'日期': '月份'}, inplace=True)
                if '收入' not in annual_df: annual_df['收入'] = 0
                if '開銷' not in annual_df: annual_df['開銷'] = 0
                annual_df['淨利'] = annual_df['收入'] - annual_df['開銷']
                
                fig_yr = go.Figure()
                fig_yr.add_trace(go.Bar(x=annual_df['月份'], y=annual_df['收入'], name='收入 (Rev)', marker_color='#06C167'))
                fig_yr.add_trace(go.Bar(x=annual_df['月份'], y=annual_df['開銷'], name='開銷 (Exp)', marker_color='#FF453A'))
                fig_yr.add_trace(go.Scatter(x=annual_df['月份'], y=annual_df['淨利'], name='淨利 (Net)', mode='lines+markers', marker_color='#00E5FF', line=dict(width=3)))
                fig_yr.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF'), barmode='group')
                st.plotly_chart(fig_yr, use_container_width=True)

# ==========================================
# 分頁：⚙️ 帳號設定 (Settings)
# ==========================================
with tab_settings:
    with st.container(border=True):
        st.header("⚙️ Account Settings & Export")
        st.write(f"當前駕駛代號 (Display Name)：**{driver_name}**")
        if st.button("重新設定代號 (Reset Name)", type="secondary"): 
            update_profile_field("道號", "")
            get_roster_data.clear()
            get_all_team_data.clear()
            st.rerun()
        st.write("---")
        st.markdown("#### 📥 匯出原始數據 (Export Data)")
        st.caption("匯出 CSV 格式，可使用 Excel 或 Google Sheets 開啟進行進階分析。")
        if not df.empty:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="下載備份檔 (Download CSV)", data=csv_data, file_name=f"delivery_pro_records_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary") 

# ==========================================
# 分頁：🏆 團隊排行榜 (Team Leaderboard)
# ==========================================
with tab_team:
    with st.container(border=True):
        st.header("🏆 團隊表現分析 (Team Leaderboard)")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1: time_filter = st.selectbox("📅 時間區間 (Period)：", ["今日結算 (Today)", "本週結算 (This Week)", "本月結算 (This Month)", "本年度結算 (This Year)", "歷史總和 (All Time)"])
        with col_t2: rank_type = st.selectbox("📊 排序指標 (Sort by)：", ["⭐ 綜合表現分數 (Performance Score)", "💰 總收入 (Total Revenue)", "📈 投資報酬率 (Efficiency/ROI)"])
        
        with st.spinner("⏳ 正在整合團隊數據..."):
            try:
                if big_df.empty:
                    st.info("系統尚無足夠的資料建立報表。")
                else:
                    if "今日" in time_filter: filtered_df = big_df[big_df['日期'] == today]
                    elif "本週" in time_filter: filtered_df = big_df[(big_df['日期'] >= today - timedelta(days=today.weekday())) & (big_df['日期'] <= today)]
                    elif "本月" in time_filter: filtered_df = big_df[(pd.to_datetime(big_df['日期']).dt.month == today.month) & (pd.to_datetime(big_df['日期']).dt.year == today.year)]
                    elif "本年度" in time_filter: filtered_df = big_df[pd.to_datetime(big_df['日期']).dt.year == today.year]
                    else: filtered_df = big_df
                    
                    lb_data = []
                    for uid, u_name in user_map.items():
                        user_df = filtered_df[filtered_df['User_ID'] == uid]
                        
                        u_legacy_bonus = 0
                        for r in roster_records:
                            if str(r["User_ID"]) == uid:
                                u_legacy_bonus = int(r.get("額外戰力", 0)) if str(r.get("額外戰力", "")) != "" else 0
                                break
                                
                        if not user_df.empty:
                            u_inc = user_df[user_df['類型'] == '收入']['金額'].sum()
                            u_hr = user_df[user_df['類型'] == '收入']['上線時數'].sum()
                            u_days = user_df[user_df['類型'] == '收入']['日期'].nunique()
                            u_incidents = user_df[user_df['天劫'] == 'True'].shape[0] if '天劫' in user_df.columns else 0
                            
                            u_exp_df = user_df[(user_df['類型'] == '開銷') & (user_df['項目'].isin(['機車油錢', '機車保養']))]
                            u_gas_exp = u_exp_df['金額'].sum() if not u_exp_df.empty else 0
                            
                            if u_inc > 0 or "總和" in time_filter:
                                avg_w = u_inc / u_hr if u_hr > 0 else 0
                                
                                # 專業版基本評分
                                u_base_score = int(((u_inc / 100) + (avg_w * 10) + (u_days * 50)))
                                # 保留過往的「額外戰力」作為隱藏加權，以相容舊有排名
                                u_score = u_base_score + u_legacy_bonus
                                
                                efficiency = u_inc / (u_gas_exp + 1) if u_gas_exp > 0 else u_inc
                                
                                lb_data.append({
                                    "User_ID": uid, "Driver_Name": u_name, "Score": u_score, "Income": u_inc, "Efficiency": efficiency, "GasExp": u_gas_exp, "Incidents": u_incidents
                                })
                    
                    if lb_data:
                        lb_df = pd.DataFrame(lb_data)
                        if "綜合表現" in rank_type: lb_df = lb_df.sort_values(by="Score", ascending=False).reset_index(drop=True)
                        elif "總收入" in rank_type: lb_df = lb_df.sort_values(by="Income", ascending=False).reset_index(drop=True)
                        else: lb_df = lb_df.sort_values(by="Efficiency", ascending=False).reset_index(drop=True)
                            
                        lb_df.index = lb_df.index + 1
                        display_data = []
                        
                        for idx, row in lb_df.iterrows():
                            title_prefix = ""
                            if idx == 1: title_prefix = "🏆 [Top Driver] "
                            
                            rank_str = f"🥇" if idx==1 else (f"🥈" if idx==2 else (f"🥉" if idx==3 else str(idx)))
                            
                            if "投資報酬率" in rank_type:
                                display_data.append({
                                    "Rank": rank_str, "Driver": f"{title_prefix}{row['Driver_Name']}", "Revenue": f"${int(row['Income']):,}",
                                    "Vehicle Exp (Gas/Maint)": f"${int(row['GasExp']):,}", "ROI Ratio": f"1 : {row['Efficiency']:.1f}"
                                })
                            else:
                                display_data.append({
                                    "Rank": rank_str, "Driver": f"{title_prefix}{row['Driver_Name']}", "Perf. Score": int(row['Score']),
                                    "Revenue": f"${int(row['Income']):,}", "Incidents": int(row['Incidents'])
                                })
                                
                        st.dataframe(pd.DataFrame(display_data), hide_index=True, use_container_width=True)
                        if "投資報酬率" in rank_type: st.caption("💡 投資報酬率計算公式：收入 ÷ (油錢 + 保養費用)。比例越高代表車輛與接單效率極佳。")
                    else:
                        st.info(f"報表建立中：在指定區間內查無活動紀錄。")
            except Exception as e:
                st.error(f"⚠️ 報表建立失敗，請嘗試同步數據。錯誤碼：{e}")
