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
# ⚙️ 系統常數與修仙設定
# ==========================================
CUSTOM_COLORS = {"Uber Eats": "#06C167", "Foodpanda": "#FF2B85", "其他獎金": "#F6C143", "休假": "#B0B0B0", "機車油錢": "#FF9900", "機車保養": "#FF4444"}
WEEKDAY_MAP = {0: '星期一', 1: '星期二', 2: '星期三', 3: '星期四', 4: '星期五', 5: '星期六', 6: '星期日'}

CULTIVATION_REALMS = [
    (0, "凡人武夫", "初出茅廬的跑腿", "🚶‍♂️"), (10000, "煉氣前期", "外門弟子", "🚴‍♂️"), (30000, "煉氣中期", "外門弟子", "🚴‍♂️"), (60000, "煉氣後期", "外門弟子", "🚴‍♂️"),
    (100000, "築基前期", "內門弟子", "🛵"), (150000, "築基中期", "內門弟子", "🛵"), (200000, "築基後期", "內門弟子", "🛵"),
    (300000, "結丹前期", "真傳弟子", "🏍️"), (400000, "結丹中期", "真傳弟子", "🏍️"), (500000, "結丹後期", "真傳弟子", "🏍️"),
    (600000, "元嬰前期", "外送堂主", "🦅"), (800000, "元嬰中期", "外送堂主", "🦅"), (1000000, "元嬰後期", "百萬靈石大長老", "🦅"),
    (1500000, "化神前期", "外送宗師", "🐉"), (2000000, "化神中期", "外送宗師", "🐉"), (3000000, "化神後期", "外送宗師", "🐉"),
    (5000000, "渡劫飛升", "外送天尊", "🌌")
]

FORTUNE_POOL = [
    "🌟 大吉：天地靈氣匯聚！一路綠燈，無縫接單，連下暴雨都能遇到天使客人給小費！", "🌟 大吉：紫氣東來！今天接到的都是近距離高單價，宛如仙人指路，爽賺一波！", "🌟 大吉：財神庇佑！小費拿到手軟，系統瘋狂派單，破紀錄就在今天！", "🌟 大吉：萬物皆明！客人剛好都在一樓等你，地址清晰好找，如同天助！",
    "✨ 中吉：運勢平穩。單量穩定，穩紮穩打，是個累積修為的好日子。", "✨ 中吉：靈氣溫和。避開了雷包店家，取餐順利，行車平安。", "✨ 中吉：微風扶柳。雖然沒有爆單，但單單順路，油耗極佳，堪稱節能天尊！", "✨ 中吉：遇貴人相助。迷路時剛好有同行指點，順利抵達目的地。",
    "🌤️ 小吉：略有波折。轉角可能會遇到三寶，請保持防禦駕駛，阿彌陀佛。", "🌤️ 小吉：福禍相依。遇到要爬五樓的客人，當作鍛鍊體魄，修為穩步提升！", "🌤️ 小吉：靈氣波動。店家拖餐讓你多等了十分鐘，但剛好可以趁機回個訊息。", "🌤️ 小吉：偶遇陣雨。記得穿好雨衣，水滴是上天賜予的試煉！",
    "🍃 平：普普通通的一天。保持平常心，心若冰清，天塌不驚。", "🍃 平：天地無極，乾坤借法。今天沒什麼特別的，早點回家洗洗睡也是一種修行。", "🍃 平：風平浪靜。沒有奧客也沒有小費，佛系跑單，隨遇而安。",
    "💧 末吉：接到大單，但絕對是六樓沒有電梯，還要扛三桶水！當作重訓吧！", "💧 末吉：陰雨綿綿。導航可能會帶你走進死胡同，請相信自己的直覺。", "💧 末吉：靈氣枯竭。網路訊號可能不太穩，記得隨時重開 APP，以免錯失仙緣。",
    "⚠️ 凶：暗藏殺機！防禦駕駛，避開雷包店家，今天極易遇到湯汁外漏的劫數！", "⚠️ 凶：天狗食月！注意你的輪胎！今天出門前務必檢查胎壓，不然準備牽車顧路！", "⚠️ 凶：煞氣沖天！準備迎接奧客的靈魂拷問，請深呼吸，不要跟凡人計較！",
    "💀 大凶：天降神罰！手機架可能斷裂，或者遇到「現金單不給錢」魔物，建議在家閉關！", "💀 大凶：業障引爆！導航當機、店家忘記做餐、客人填錯地址，三劫臨頭，快去過香爐！"
]

# ==========================================
# 🌐 Google Sheets 雲端資料庫引擎
# ==========================================
@st.cache_resource
def get_gspread_client():
    try:
        creds_dict = json.loads(st.secrets["GOOGLE_KEY"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 雲端金鑰連線失敗，請檢查 Secrets 設定：{e}")
        st.stop()

@st.cache_resource
def get_sheet():
    client = get_gspread_client()
    try: return client.open_by_url(st.secrets["SHEET_URL"])
    except Exception as e:
        st.error(f"❌ 找不到試算表！請確認網址正確：{e}")
        st.stop()

def get_roster_ws():
    sheet = get_sheet()
    try: return sheet.worksheet("宗門名冊")
    except gspread.exceptions.WorksheetNotFound: 
        ws = sheet.add_worksheet(title="宗門名冊", rows="100", cols="20")
        ws.append_row(["User_ID", "道號", "總靈石", "總時數", "總天數", "天劫數", "戰鬥力", "境界", "座騎", "任務日期", "任務ID", "任務狀態", "運勢日期", "運勢", "目標月份", "目標金額", "額外戰力"])
        return ws

def get_user_records_ws(user_id):
    sheet = get_sheet()
    ws_name = f"records_{user_id}"
    try: return sheet.worksheet(ws_name)
    except gspread.exceptions.WorksheetNotFound: 
        ws = sheet.add_worksheet(title=ws_name, rows="1000", cols="10")
        ws.append_row(["日期", "類型", "項目", "金額", "上線時數", "備註", "天劫"])
        return ws

def get_feed_ws():
    sheet = get_sheet()
    try: return sheet.worksheet("宗門動態")
    except gspread.exceptions.WorksheetNotFound: 
        ws = sheet.add_worksheet(title="宗門動態", rows="500", cols="5")
        ws.append_row(["時間", "發送者", "接收者", "動作", "訊息"])
        return ws

@st.cache_data(ttl=60, show_spinner=False)
def get_all_sect_data():
    sheet = get_sheet()
    roster_records = get_roster_ws().get_all_records()
    user_map = {str(r["User_ID"]): str(r.get("道號", "無名修士")) for r in roster_records if str(r.get("道號", "")) != ""}
    all_data = []
    for ws in sheet.worksheets():
        if ws.title.startswith("records_"):
            uid = ws.title.replace("records_", "")
            if uid in user_map:
                records = ws.get_all_records()
                if records:
                    df_temp = pd.DataFrame(records)
                    df_temp['User_ID'] = uid
                    df_temp['道號'] = user_map[uid]
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

def save_data(date_val, record_type, item, amount, hours, note, tribulation):
    with st.spinner("⏳ 正在將玉簡傳送至雲端藏寶閣..."):
        ws = get_user_records_ws(st.session_state.user_id)
        ws.append_row([str(date_val), str(record_type), str(item), int(amount), float(hours), str(note), str(tribulation)])
        st.cache_data.clear()
        update_roster_stats()

def delete_data(indices_to_drop):
    with st.spinner("⏳ 正在從雲端抹除因果..."):
        ws = get_user_records_ws(st.session_state.user_id)
        for idx in sorted(indices_to_drop, reverse=True): ws.delete_rows(idx + 2)
        st.cache_data.clear()
        update_roster_stats()

def add_feed_interaction(sender_name, receiver_name, action, message):
    ws = get_feed_ws()
    ws.append_row([str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(sender_name), str(receiver_name), str(action), str(message)])
    st.cache_data.clear()

def get_user_profile():
    ws = get_roster_ws()
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if str(r["User_ID"]) == st.session_state.user_id: return r, i + 2
    new_row = [st.session_state.user_id, "", 0, 0, 0, 0, 0, "凡人武夫", "凡鐵飛劍", "", 0, 0, "", "", "", 0, 0]
    ws.append_row(new_row)
    return dict(zip(["User_ID", "道號", "總靈石", "總時數", "總天數", "天劫數", "戰鬥力", "境界", "座騎", "任務日期", "任務ID", "任務狀態", "運勢日期", "運勢", "目標月份", "目標金額", "額外戰力"], new_row)), len(records) + 2

def update_profile_field(col_name, value):
    ws = get_roster_ws()
    headers = ws.row_values(1)
    if col_name in headers:
        col_idx = headers.index(col_name) + 1
        _, row_idx = get_user_profile()
        if isinstance(value, (int, float)): ws.update_cell(row_idx, col_idx, float(value) if isinstance(value, float) else int(value))
        else: ws.update_cell(row_idx, col_idx, str(value))

def update_other_user_bonus_cp(target_uid, amount_change):
    ws = get_roster_ws()
    records = ws.get_all_records()
    headers = ws.row_values(1)
    if "額外戰力" not in headers: return
    col_idx = headers.index("額外戰力") + 1
    cp_idx = headers.index("戰鬥力") + 1
    for i, r in enumerate(records):
        if str(r["User_ID"]) == str(target_uid):
            curr_bonus = int(r.get("額外戰力", 0)) if str(r.get("額外戰力", "")) != "" else 0
            curr_cp = int(r.get("戰鬥力", 0)) if str(r.get("戰鬥力", "")) != "" else 0
            ws.update_cell(i + 2, col_idx, curr_bonus + amount_change)
            ws.update_cell(i + 2, cp_idx, curr_cp + amount_change)
            break

def get_realm_tier_and_buffs(total_exp):
    current_realm, _, _, _, _, _ = get_realm_info(total_exp)
    if "凡人" in current_realm or "煉氣" in current_realm: return 0, 0, 0, 1.0, 0, 1.0
    elif "築基" in current_realm: return 1, 5, 5, 0.9, 5, 1.05
    elif "結丹" in current_realm: return 2, 10, 10, 0.8, 10, 1.1
    elif "元嬰" in current_realm: return 3, 15, 20, 0.6, 20, 1.2
    else: return 4, 20, 30, 0.5, 30, 1.3

def update_roster_stats():
    df = load_data(st.session_state.user_id)
    t_inc = int(df[df['類型'] == '收入']['金額'].sum()) if not df.empty else 0
    t_hr = float(df[df['類型'] == '收入']['上線時數'].sum()) if not df.empty else 0.0
    t_days = int(df[df['類型'] == '收入']['日期'].nunique()) if not df.empty else 0
    t_tribs = int(df[df['天劫'] == 'True'].shape[0]) if not df.empty and '天劫' in df.columns else 0
    
    _, _, _, _, _, cp_mult = get_realm_tier_and_buffs(t_inc)
    avg_w = t_inc / t_hr if t_hr > 0 else 0
    base_cp = int(((t_inc / 100) + (avg_w * 10) + (t_days * 50) + (t_tribs * 300)) * cp_mult)
    
    ws = get_roster_ws()
    _, row_idx = get_user_profile()
    
    records = ws.get_all_records()
    bonus_cp = 0
    for r in records:
        if str(r["User_ID"]) == st.session_state.user_id:
            bonus_cp = int(r.get("額外戰力", 0)) if str(r.get("額外戰力", "")) != "" else 0
            break
            
    final_cp = base_cp + bonus_cp
    realm, _, _, _, _, _ = get_realm_info(t_inc)
    mount, _ = get_mount_info(t_hr)
    
    ws.update(values=[[int(t_inc), float(t_hr), int(t_days), int(t_tribs), int(final_cp), str(realm), str(mount)]], range_name=f"C{row_idx}:I{row_idx}")

def get_realm_info(total_exp):
    current_realm, current_title, current_avatar = "凡人武夫", "初出茅廬的跑腿", "🚶‍♂️"
    next_realm, next_exp, prev_exp = "未知", 10000, 0
    for i in range(len(CULTIVATION_REALMS)):
        if total_exp >= CULTIVATION_REALMS[i][0]:
            current_realm, current_title, current_avatar = CULTIVATION_REALMS[i][1], CULTIVATION_REALMS[i][2], CULTIVATION_REALMS[i][3]
            prev_exp = CULTIVATION_REALMS[i][0]
            if i + 1 < len(CULTIVATION_REALMS): next_realm, next_exp = CULTIVATION_REALMS[i+1][1], CULTIVATION_REALMS[i+1][0]
            else: next_realm, next_exp = "已達巔峰", total_exp
        else: break
    progress = 1.0 if next_realm == "已達巔峰" else min((total_exp - prev_exp) / (next_exp - prev_exp), 1.0)
    return current_realm, next_realm, next_exp, progress, current_title, current_avatar

def get_mount_info(total_hours):
    if total_hours >= 1000: return "九天應龍", "🐉"
    elif total_hours >= 500: return "紫電魔豹", "🐆"
    elif total_hours >= 100: return "疾風靈鶴", "🦅"
    else: return "凡鐵飛劍", "🗡️"

def change_date(new_date): st.session_state.selected_date = new_date

# ==========================================
# 🎨 史詩級視覺 CSS 與特效注入 (修復版)
# ==========================================
st.set_page_config(page_title="外送修仙錄 - 終極覺醒", layout="wide", page_icon="⚡")
st.markdown("""
<style>
    /* 全螢幕動態流光背景 */
    .stApp {
        background: linear-gradient(-45deg, #0b0c10, #16213e, #0f3460, #1a1a2e);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        color: #E0E0E0;
    }
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* 💡 精準鎖定 Streamlit 原生容器，賦予玻璃特效，絕對不破版！ */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(20, 25, 40, 0.45) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-left: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5) !important;
        transition: transform 0.3s ease, box-shadow 0.3s ease !important;
        padding: 1.5rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 12px 40px 0 rgba(255, 215, 0, 0.15) !important;
        border: 1px solid rgba(255, 215, 0, 0.4) !important;
    }

    /* 電競級立體 Tabs 選單 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(0, 0, 0, 0.4);
        border-radius: 12px;
        padding: 5px;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
    }
    .stTabs [data-baseweb="tab"] {
        color: #AAAAAA;
        border-radius: 8px;
        transition: all 0.3s;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #FF8C00, #FFD700);
        color: #1a1a2e !important;
        font-weight: 900;
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.5);
    }

    /* 戰鬥力金光呼吸燈 */
    .cp-text-glow {
        font-size: 65px;
        font-weight: 900;
        background: -webkit-linear-gradient(#FFE000, #FF8C00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin: 0;
        line-height: 1.1;
        filter: drop-shadow(0px 0px 10px rgba(255, 140, 0, 0.6));
        animation: pulseGlow 2.5s infinite;
    }
    @keyframes pulseGlow {
        0% { filter: drop-shadow(0px 0px 8px rgba(255, 140, 0, 0.5)); transform: scale(1); }
        50% { filter: drop-shadow(0px 0px 25px rgba(255, 215, 0, 0.9)); transform: scale(1.03); }
        100% { filter: drop-shadow(0px 0px 8px rgba(255, 140, 0, 0.5)); transform: scale(1); }
    }

    /* 圖示懸浮動畫 */
    .floating-icon {
        font-size: 45px;
        display: inline-block;
        animation: floatAnim 3s ease-in-out infinite;
        filter: drop-shadow(0px 10px 5px rgba(0,0,0,0.5));
    }
    @keyframes floatAnim {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); filter: drop-shadow(0px 20px 10px rgba(0,0,0,0.3));}
        100% { transform: translateY(0px); }
    }
    
    /* VIP 專屬金框 (純文字顯示用) */
    .vip-box {
        border: 1px solid rgba(255, 215, 0, 0.6);
        background: linear-gradient(90deg, rgba(255,215,0,0.1), rgba(0,0,0,0));
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.1);
    }
    
    /* 進度條魔法化 */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        box-shadow: 0 0 10px #00C9FF;
    }
    
    /* 動態牆項目 */
    .feed-box {
        border-left: 4px solid #00E5FF;
        background: rgba(255,255,255,0.03);
        padding: 12px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 10px;
        font-size: 14px;
        transition: background 0.3s;
    }
    .feed-box:hover { background: rgba(255,255,255,0.08); border-left: 4px solid #FFD700; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛡️ 護山大陣
# ==========================================
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_id" not in st.session_state: st.session_state.user_id = ""

if not st.session_state.authenticated:
    st.markdown("<br><br><div style='text-align: center;'><h1 style='color: #FFD700; font-size: 50px; text-shadow: 0 0 20px #FFD700;'>⛩️ 雲端外送宗門</h1><p style='color:#AAA;'>輸入密令，踏入仙途</p></div><br>", unsafe_allow_html=True)
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        pwd_input = st.text_input("接引密令：", type="password", placeholder="請輸入門派密令...")
        if st.button("🚪 破除結界", type="primary", use_container_width=True):
            app_pwd = st.secrets.get("APP_PASSWORD", "未設定")
            invites = st.secrets.get("INVITES", {})
            if pwd_input == app_pwd:
                st.session_state.authenticated, st.session_state.user_id = True, "yu_master"
                st.rerun()
            elif pwd_input in invites:
                st.session_state.authenticated, st.session_state.user_id = True, invites[pwd_input]
                st.rerun()
            else: st.error("❌ 密令錯誤，結界反噬！")
    st.stop()

# 載入資料
with st.spinner("⏳ 正在匯聚天地靈氣..."):
    profile, _ = get_user_profile()
    user_map, big_df, roster_records = get_all_sect_data()

if profile["道號"] == "":
    st.markdown("<h1 style='text-align: center; color: #00E5FF;'>📜 新弟子入宗登記</h1>", unsafe_allow_html=True)
    new_name = st.text_input("請賜予自己一個響亮的道號：")
    if st.button("🚀 登記入冊", type="primary"):
        if new_name.strip():
            update_profile_field("道號", new_name.strip())
            st.cache_data.clear()
            st.rerun()
    st.stop()

user_name = profile["道號"]
if "selected_date" not in st.session_state: st.session_state.selected_date = date.today()
if "input_key" not in st.session_state: st.session_state.input_key = 0
if "show_success" not in st.session_state: st.session_state.show_success = False

# 🔄 頂部標題與「一鍵重整按鈕」排版
t_col1, t_col2 = st.columns([4, 1])
with t_col1:
    st.markdown(f"<h1 style='margin-bottom:0;'>☁️ 宗門大殿 <span style='color:#FFD700; font-size:24px;'>[{user_name} 的洞府]</span></h1>", unsafe_allow_html=True)
with t_col2:
    st.markdown("<br>", unsafe_allow_html=True) 
    if st.button("🔄 凝聚靈氣 (重整)", type="secondary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

tab0, tab1, tab2, tab3, tab4, tab_lb = st.tabs(["🐉 宗門大殿", "📝 每日歷練", "📊 宗門財報", "🏆 年度回顧", "⚙️ 法寶設定", "👑 封神榜"])

df = load_data(st.session_state.user_id)
k = st.session_state.input_key
today = date.today()
cp_value = int(profile.get('戰鬥力', 0)) if str(profile.get('戰鬥力', '')) != '' else 0
total_stone = int(profile.get('總靈石', 0)) if str(profile.get('總靈石', '')) != '' else 0

atk_tier, alc_win_buff, alc_rug_red, def_mult, def_rebound, cp_mult = get_realm_tier_and_buffs(total_stone)
c_realm, n_realm, n_exp, prog, c_title, c_avatar = get_realm_info(total_stone)
total_hr_val = float(profile.get('總時數', 0.0)) if str(profile.get('總時數', '')) != '' else 0.0
m_name, m_avatar = get_mount_info(total_hr_val)

# ==========================================
# 分頁 0: 🐉 宗門大殿 (修復空白問題，採用原生 border=True 渲染)
# ==========================================
with tab0:
    stat_c1, stat_c2, stat_c3 = st.columns([1.2, 1.5, 1.8])
    
    with stat_c1:
        with st.container(border=True):
            st.markdown(f"""
            <div style='text-align: center; height: 110px; display:flex; flex-direction:column; justify-content:center;'>
                <div style='color: #AAAAAA; font-size: 14px; margin-bottom: 5px; letter-spacing: 2px;'>⚔️ 綜合戰鬥力</div>
                <div class='cp-text-glow'>{cp_value:,}</div>
            </div>
            """, unsafe_allow_html=True)
            
    with stat_c2:
        with st.container(border=True):
            st.markdown(f"""
            <div style='display: flex; justify-content: space-around; text-align: center; height: 110px; align-items:center;'>
                <div>
                    <div class='floating-icon'>{c_avatar}</div>
                    <div style='color: #FFD700; font-weight: bold; font-size: 15px; margin-top:5px;'>{c_realm}</div>
                </div>
                <div style='width: 1px; height: 60px; background: rgba(255,255,255,0.2);'></div>
                <div>
                    <div class='floating-icon'>{m_avatar}</div>
                    <div style='color: #00E5FF; font-weight: bold; font-size: 15px; margin-top:5px;'>{m_name}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    with stat_c3:
        with st.container(border=True):
            st.markdown("<div style='font-size: 15px; font-weight: bold; color: #E0E0E0; margin-bottom: 12px;'>⚡ 靈石突破進度</div>", unsafe_allow_html=True)
            st.progress(prog)
            st.markdown(f"<div style='font-size: 13px; color: #AAA; margin-top: 8px; text-align: right;'>累積：<span style='color:#FFD700;'>{total_stone:,}</span> / 渡劫需求：{n_exp:,}</div>", unsafe_allow_html=True)

    if atk_tier > 0:
        st.markdown(f"""
        <div class='vip-box'>
            <b style='color:#FFD700; font-size:16px;'>👑 VIP {atk_tier} 境界特權已啟用：</b><br>
            <span style='color:#AAA; font-size:14px;'>
            ✨ 每日戰力 <b>{cp_mult} 倍</b>加成 | 🎲 煉丹暴擊率 <b>+{alc_win_buff}%</b> / 炸爐率 <b>-{alc_rug_red}%</b> | 🛡️ 遭暗算減傷 <b>{int((1-def_mult)*100)}%</b> (反彈率 <b>{def_rebound}%</b>)
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### ⚔️ 宗門大亂鬥")
    play_c1, play_c2 = st.columns(2)
    
    with play_c1:
        with st.container(border=True):
            base_win = 20 + alc_win_buff
            base_rug = max(0, 50 - alc_rug_red)
            st.subheader("🎲 激進煉丹爐")
            st.caption(f"投入 50 點戰力。成功率：**{base_win}%** / 炸爐率：**{base_rug}%**")
            
            if st.button("🔥 耗費 50 CP 煉丹", use_container_width=True):
                if cp_value < 50: st.warning("戰鬥力不足，無法煉丹！")
                else:
                    roll = random.randint(1, 100)
                    current_bonus = int(profile.get("額外戰力", 0)) if str(profile.get("額外戰力", "")) != "" else 0
                    if roll <= base_win:
                        gain = random.randint(150, 300)
                        update_profile_field("額外戰力", current_bonus - 50 + gain)
                        add_feed_interaction(user_name, "自己", "煉丹大成功", f"運用境界修為煉出極品仙丹，戰力暴增 {gain}！")
                        st.success(f"🚀 大成功！仙光沖天，戰鬥力暴增 {gain} 點！")
                    elif roll <= (100 - base_rug):
                        gain = random.randint(30, 80)
                        update_profile_field("額外戰力", current_bonus - 50 + gain)
                        st.info(f"✨ 煉出普通丹藥，回收 {gain} 點。")
                    else:
                        update_profile_field("額外戰力", current_bonus - 50)
                        add_feed_interaction(user_name, "自己", "煉丹炸爐", "煉丹嚴重失誤，50 點戰力化為灰燼...")
                        st.error("💥 炸爐了！爐火失控，50 點戰力化為灰燼...")
                    update_roster_stats()
                    st.rerun()

    with play_c2:
        with st.container(border=True):
            st.subheader("🥷 宗門暗算")
            friends_dict = {uid: name for uid, name in user_map.items() if uid != st.session_state.user_id}
            
            if not friends_dict:
                st.info("宗門裡還沒有其他弟子...")
            else:
                target_uid = st.selectbox("選擇目標", options=list(friends_dict.keys()), format_func=lambda x: friends_dict[x], label_visibility="collapsed")
                target_name = friends_dict[target_uid]
                
                opt_c1, opt_c2 = st.columns(2)
                with opt_c1: attack_type = st.radio("手段", ["📌 圖釘 (-30 CP)", "🧛 吸星 (-80 CP)"], label_visibility="collapsed")
                with opt_c2: stealth_mode = st.radio("身分", ["⚔️ 實名 (必中)", "🥷 匿名 (50%失敗)"], label_visibility="collapsed")
                
                cost = 30 if "圖釘" in attack_type else 80
                
                if st.button(f"🗡️ 發動攻擊 (-{cost} CP)", type="primary", use_container_width=True):
                    if cp_value < cost: st.warning("戰鬥力不足！")
                    else:
                        current_bonus = int(profile.get("額外戰力", 0)) if str(profile.get("額外戰力", "")) != "" else 0
                        update_profile_field("額外戰力", current_bonus - cost)
                        is_stealth = "匿名" in stealth_mode
                        display_sender = "🥷 蒙面黑衣人" if is_stealth else user_name
                        
                        if is_stealth and random.randint(1, 100) <= 50:
                            st.error("💥 暗算失敗！你蒙面踩到自己撒的圖釘，戰力白白浪費！")
                            add_feed_interaction(display_sender, target_name, "暗算搞砸", "試圖暗算對方，卻自己踩空跌倒！")
                        else:
                            defender_record = next((r for r in roster_records if str(r["User_ID"]) == target_uid), None)
                            defender_stone = int(defender_record["總靈石"]) if defender_record and str(defender_record.get("總靈石","")) != "" else 0
                            def_tier, _, _, t_def_mult, t_def_rebound, _ = get_realm_tier_and_buffs(defender_stone)
                            raw_dmg = random.randint(50, 100) if "圖釘" in attack_type else random.randint(40, 80)
                            
                            if atk_tier < def_tier and random.randint(1, 100) <= t_def_rebound:
                                update_profile_field("額外戰力", current_bonus - cost - raw_dmg)
                                st.error(f"😱 攻擊被彈回！對方【護體罡氣】將傷害反彈，你額外重創 {raw_dmg} 點戰力！")
                                if not is_stealth: add_feed_interaction(display_sender, target_name, "遭罡氣反噬", "被大佬的護體罡氣震飛，自損八百！")
                            else:
                                actual_dmg = int(raw_dmg * t_def_mult)
                                update_other_user_bonus_cp(target_uid, -actual_dmg)
                                if "吸星" in attack_type:
                                    update_profile_field("額外戰力", current_bonus - cost + actual_dmg)
                                    st.success(f"🧛 吸取成功！你從 {target_name} 身上吸走了 {actual_dmg} 點戰力！")
                                    add_feed_interaction(display_sender, target_name, "吸星大法", f"吸走了 {actual_dmg} 戰力！")
                                else:
                                    msg = f"撒圖釘造成對方 {-actual_dmg} 損失！" if t_def_mult == 1.0 else f"撒圖釘，但對方護體抵消了部分傷害，造成 {-actual_dmg} 損失！"
                                    st.success(f"😈 偷襲命中！{target_name} 戰鬥力重挫 {actual_dmg}！")
                                    add_feed_interaction(display_sender, target_name, "暗器偷襲", msg)
                        update_roster_stats()
                        st.rerun()

    st.divider()

    feed_col, daily_col = st.columns([1.5, 1])
    
    with feed_col:
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>📢 宗門動態牆</h4>", unsafe_allow_html=True)
            
            sos_users = []
            if not big_df.empty:
                today_tribs = big_df[(big_df['日期'] == today) & (big_df['天劫'] == 'True') & (big_df['User_ID'] != st.session_state.user_id)]
                sos_users = today_tribs['道號'].unique().tolist()
                
            if sos_users:
                st.warning("⚠️ 以下道友今日遭遇天劫！")
                for sos_name in sos_users:
                    sc1, sc2 = st.columns([2, 1])
                    sc1.write(f"**{sos_name}** 正在渡劫中...")
                    if sc2.button("🙏 傳靈氣", key=f"qi_{sos_name}"):
                        add_feed_interaction(user_name, sos_name, "傳送靈氣", "助你渡過難關！")
                        update_other_user_bonus_cp([u for u, n in user_map.items() if n == sos_name][0], 20)
                        st.balloons()
                        st.success("已傳送靈氣！")
            
            try:
                feed_records = get_feed_ws().get_all_records()
                if feed_records:
                    for r in reversed(feed_records[-5:]): 
                        emoji = "✨" if r['动作'] in ["傳送靈氣", "煉丹大成功", "吸星大法"] else "💨"
                        st.markdown(f"<div class='feed-box'><span style='color:#00E5FF; font-size: 12px; font-weight:bold;'>{r['時間']}</span><br><b>{r['發送者']}</b> {emoji} 對 <b>{r['接收者']}</b> 施放了【{r['動作']}】<br><i style='color:#CCC;'>「{r['訊息']}」</i></div>", unsafe_allow_html=True)
                else: st.caption("宗門目前一片祥和...")
            except: st.caption("動態牆讀取中...")

    with daily_col:
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>🥠 天機閣 (運勢)</h4>", unsafe_allow_html=True)
            st.caption("外送員專屬，一日一卦！")
            if str(profile.get("運勢日期", "")) == str(today):
                st.markdown(f"<div style='background:rgba(0,0,0,0.3); padding:15px; border-radius:10px; border:1px solid #FFD700; color:#FFF;'>{profile.get('運勢', '尚未卜卦')}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button("🔮 抽取今日運勢", type="primary", use_container_width=True):
                    fortune = random.choice(FORTUNE_POOL)
                    update_profile_field("運勢日期", str(today))
                    update_profile_field("運勢", str(fortune))
                    st.snow()
                    st.rerun()

# ==========================================
# 分頁 1: 每日輸入 
# ==========================================
with tab1:
    with st.container(border=True):
        col1, col2 = st.columns([1, 1.2])
        with col1:
            st.header("📝 新增紀錄") 
            if st.session_state.show_success: st.success("✅ 雲端存檔成功！"); st.session_state.show_success = False
            
            temp_date = st.date_input("選擇日期", value=st.session_state.selected_date)
            if temp_date != st.session_state.selected_date: st.session_state.selected_date = temp_date; st.rerun()
            record_date = st.session_state.selected_date
    
            record_type = st.radio("類型", ["收入", "開銷", "休假"], horizontal=True)
            if record_type in ["收入", "開銷"]:
                is_tribulation = st.checkbox("⛈️ 今日遭遇天劫 (暴雨/寒流/奧客)", key=f"trib_{k}")
                st.write("---")
    
            if record_type == "收入":
                platform_mode = st.radio("記錄方式", ["單一平台", "雙開 (同時記錄)"], horizontal=True)
                if platform_mode == "單一平台":
                    item = st.selectbox("平台/項目", ["Uber Eats", "Foodpanda", "其他獎金"])
                    amount = st.number_input("金額 (元)", min_value=0, step=10, value=None, key=f"amt_{k}")
                    val_amount = amount if amount is not None else 0
                else:
                    st.write("雙開金額")
                    u_col, f_col = st.columns(2)
                    with u_col: amount_u = st.number_input("Uber Eats", min_value=0, step=10, value=None, key=f"amtu_{k}")
                    with f_col: amount_f = st.number_input("Foodpanda", min_value=0, step=10, value=None, key=f"amtf_{k}")
                    val_amount = (amount_u or 0) + (amount_f or 0)
                    
                time_mode = st.radio("時數記錄方式", ["自動換算 (首單至末單)", "手動輸入時數", "剩餘時數反推 (12H制)"], horizontal=True)
                
                if time_mode == "自動換算 (首單至末單)":
                    t_col1, t_col2 = st.columns(2)
                    with t_col1: start_time = st.time_input("首單時間", time(10, 0), key=f"t1_{k}") 
                    with t_col2: end_time = st.time_input("末單時間", time(22, 0), key=f"t2_{k}")   
                    dt_start, dt_end = datetime.combine(date(2000, 1, 1), start_time), datetime.combine(date(2000, 1, 1), end_time)
                    if dt_end < dt_start: dt_end += timedelta(days=1)
                    hours = round((dt_end - dt_start).total_seconds() / 3600.0, 2)
                    st.info(f"⏱️ 系統換算：**{hours} 小時**")
                elif time_mode == "手動輸入時數":
                    h_col, m_col = st.columns(2)
                    with h_col: input_hours = st.number_input("上線小時", min_value=0, step=1, value=None, key=f"hr_{k}")
                    with m_col: input_minutes = st.number_input("上線分鐘", min_value=0, max_value=59, step=1, value=None, key=f"min_{k}")
                    hours = round((input_hours or 0) + ((input_minutes or 0) / 60.0), 2)
                else: 
                    st.caption("💡 輸入 APP 顯示的「剩餘駕駛時間」反推：")
                    h_col, m_col = st.columns(2)
                    with h_col: remain_hours = st.number_input("剩餘小時", min_value=0, max_value=12, step=1, value=None, key=f"r_hr_{k}")
                    with m_col: remain_minutes = st.number_input("剩餘分鐘", min_value=0, max_value=59, step=1, value=None, key=f"r_min_{k}")
                    
                    if remain_hours is not None or remain_minutes is not None:
                        r_h = remain_hours or 0
                        r_m = remain_minutes or 0
                        total_remain_mins = r_h * 60 + r_m
                        used_mins = max(0, 720 - total_remain_mins)
                        hours = round(used_mins / 60.0, 2)
                        st.info(f"⏱️ 系統反推已上線：**{hours} 小時** (約 {used_mins // 60} 小時 {used_mins % 60} 分)")
                    else: hours = 0.0
                    
                note = st.text_input("備註 (選填)", value="", key=f"note_{k}")
    
                if st.button("上傳雲端紀錄", type="primary", use_container_width=True):
                    if platform_mode == "單一平台":
                        if val_amount > 0: save_data(record_date, record_type, item, val_amount, hours, note, is_tribulation); st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1; st.rerun()
                        else: st.warning("請輸入金額")
                    else:
                        if (amount_u or 0) > 0 or (amount_f or 0) > 0:
                            if (amount_u or 0) > 0: save_data(record_date, record_type, "Uber Eats", amount_u, hours, note, is_tribulation)
                            if (amount_f or 0) > 0: save_data(record_date, record_type, "Foodpanda", amount_f, 0.0 if (amount_u or 0) > 0 else hours, note, is_tribulation)
                            st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1; st.rerun()
                        else: st.warning("請輸入金額")
    
            elif record_type == "開銷": 
                expense_choice = st.selectbox("項目", ["機車油錢", "機車保養", "機車貸款", "生財器具(如手機架/雨衣)", "其他 (手動輸入)"])
                item = st.text_input("輸入開銷名稱", key=f"item_{k}") if expense_choice == "其他 (手動輸入)" else expense_choice
                amount = st.number_input("金額 (元)", min_value=0, step=10, value=None, key=f"amt_{k}")
                note = st.text_input("備註 (選填)", value="", key=f"note_{k}")
                if st.button("上傳雲端紀錄", type="primary", use_container_width=True):
                    if (amount or 0) > 0 and item.strip() != "": save_data(record_date, record_type, item, amount, 0.0, note, is_tribulation); st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1; st.rerun()
                    else: st.warning("請輸入正確金額與項目")
            else:
                note = st.text_input("休假備註 (選填)", value="", key=f"note_{k}")
                if st.button("標記為休假", type="primary", use_container_width=True):
                    save_data(record_date, record_type, "休假", 0, 0.0, note, False)
                    st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1
                    st.rerun()
    
        with col2:
            st.header("📅 當日表現與打卡") 
            if not df.empty:
                work_dates = set(df[(df['類型'] == '收入') | (df['類型'] == '開銷')]['日期'].dt.date)
                off_dates = set(df[df['類型'] == '休假']['日期'].dt.date)
                daily_df = df[df['日期'].dt.date == st.session_state.selected_date]
                
                if not daily_df.empty:
                    if any(daily_df['類型'] == '休假'): st.success("🏖️ 這天是你的休假日！")
                    if any(daily_df.get('天劫', "False") == "True"): st.warning("⛈️ 此日曾遭遇天劫，挺過來了！")
                    
                    d_inc = daily_df[daily_df['類型'] == '收入']['金額'].sum()
                    d_exp = daily_df[daily_df['類型'] == '開銷']['金額'].sum()
                    d_hr = daily_df[daily_df['類型'] == '收入']['上線時數'].sum()
                    d_wage = d_inc / d_hr if d_hr > 0 else 0
                    h_disp = f"{int(d_hr)}h {int(round((d_hr - int(d_hr)) * 60))}m" if d_hr > 0 else "0h 0m"
                    
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric("當日收入", f"${int(d_inc):,}")
                    d2.metric("當日開銷", f"${int(d_exp):,}")
                    d3.metric("當日上線", h_disp) 
                    d4.metric("當日時薪", f"${int(d_wage):,.0f}")
                else: st.info("點擊下方日曆查看數字")
    
                cal_year, cal_month = st.session_state.selected_date.year, st.session_state.selected_date.month
                cal_matrix = calendar.monthcalendar(cal_year, cal_month)
                st.write(f"**👆 {cal_year}年 {cal_month}月**")
                cols = st.columns(7)
                for i, wd in enumerate(["一", "二", "三", "四", "五", "六", "日"]): cols[i].markdown(f"<div style='text-align: center'><b>{wd}</b></div>", unsafe_allow_html=True)
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
                    st.subheader("🛠️ 刪除今日明細")
                    edit_df = daily_df.copy()
                    edit_df['日期'] = edit_df['日期'].dt.strftime('%Y-%m-%d')
                    edit_df.insert(0, "刪除", False)
                    edited_df = st.data_editor(edit_df, hide_index=True, column_config={"刪除": st.column_config.CheckboxColumn("勾選刪除", default=False)}, disabled=["日期", "類型", "項目", "金額", "上線時數", "備註", "天劫"], use_container_width=True, key=f"edit_{st.session_state.selected_date}_{k}")
                    rows_to_delete = edited_df[edited_df["刪除"] == True].index.tolist()
                    if len(rows_to_delete) > 0:
                        if st.button("🗑️ 確認刪除已選紀錄", type="primary", use_container_width=True):
                            delete_data(rows_to_delete)
                            st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1
                            st.rerun()

# ==========================================
# 分頁 2 & 3: 月度報表與年度分析 
# ==========================================
with tab2:
    with st.container(border=True):
        if not df.empty:
            months = df['日期'].dt.to_period('M').astype(str).unique()
            mc1, mc2 = st.columns([1, 1])
            with mc1: selected_month = st.selectbox("選擇月份", sorted(months, reverse=True))
            month_df = df[df['日期'].dt.to_period('M').astype(str) == selected_month]
            prev_month_str = f"{int(selected_month.split('-')[0])-1}-12" if selected_month.split('-')[1] == '01' else f"{selected_month.split('-')[0]}-{int(selected_month.split('-')[1])-1:02d}"
            prev_month_df = df[df['日期'].dt.to_period('M').astype(str) == prev_month_str]
            
            current_target = int(profile.get("目標金額", 0)) if str(profile.get("目標月份")) == selected_month else 0
    
            with mc2:
                with st.expander(f"🎯 設定 {selected_month} 目標收入"):
                    new_target = st.number_input("本月目標 (元)", min_value=0, step=1000, value=current_target)
                    if st.button("更新目標", type="primary"): 
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
                    st.markdown(f"### 🚀 目標進度：`${int(t_inc):,}` / `${current_target:,}`")
                    st.progress(min(t_inc / current_target, 1.0))
                    remaining_amount = current_target - t_inc
                    
                    if remaining_amount > 0:
                        today_d, s_year, s_month = date.today(), int(selected_month.split('-')[0]), int(selected_month.split('-')[1])
                        last_day_of_month = calendar.monthrange(s_year, s_month)[1]
                        if today_d.year == s_year and today_d.month == s_month: days_left = last_day_of_month - today_d.day + 1
                        elif date(s_year, s_month, last_day_of_month) > today_d: days_left = last_day_of_month 
                        else: days_left = 0 
                        
                        if days_left > 0: st.info(f"🏃‍♂️ 距離目標還差 **${int(remaining_amount):,}** 元。本月還剩 **{days_left}** 天，每天平均需賺 **${int(remaining_amount/days_left):,}**！")
                        else: st.warning(f"⚠️ 這個月已經結束囉，距離目標差了 **${int(remaining_amount):,}** 元，下個月繼續加油！")
                    else: st.success(f"🎉 已經達成設定的目標，超標賺了 **${int(-remaining_amount):,}** 元！")
                
                st.write("")
                m1, m2, m3 = st.columns(3)
                m1.metric("月總收入", f"${int(t_inc):,}", delta=f"{int(t_inc - p_inc)} (較上月)" if p_inc > 0 else None)
                m2.metric("月總開銷", f"${int(t_exp):,}", delta=f"{int(t_exp - p_exp)} (較上月)" if p_exp > 0 else None, delta_color="inverse")
                m3.metric("本月淨利", f"${int(n_prof):,}", delta=f"{int(n_prof - p_prof)} (較上月)" if p_prof != 0 else None)
                
                st.divider()
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.subheader("📈 每日收支趨勢")
                    trend_df = month_df[month_df['類型'] != '休假'].groupby(['日期', '項目', '類型'])['金額'].sum().reset_index()
                    trend_df.loc[trend_df['類型'] == '開銷', '金額'] *= -1
                    if not trend_df.empty:
                        fig_bar = px.bar(trend_df, x='日期', y='金額', color='項目', color_discrete_map=CUSTOM_COLORS, barmode='relative')
                        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF'))
                        st.plotly_chart(fig_bar, use_container_width=True)
                with c2:
                    st.subheader("🥧 平台收入佔比")
                    inc_df = month_df[month_df['類型'] == '收入']
                    if not inc_df.empty:
                        pie_data = inc_df.groupby('項目')['金額'].sum().reset_index()
                        fig_pie = px.pie(pie_data, values='金額', names='項目', hole=0.4, color='項目', color_discrete_map=CUSTOM_COLORS)
                        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF'))
                        st.plotly_chart(fig_pie, use_container_width=True)

with tab3:
    with st.container(border=True):
        if not df.empty:
            years = df['日期'].dt.year.astype(str).unique()
            selected_year = st.selectbox("選擇年份", sorted(years, reverse=True))
            year_df = df[df['日期'].dt.year.astype(str) == selected_year]
            if not year_df.empty:
                st.subheader(f"🏆 {selected_year} 年度收支總覽")
                annual_df = year_df[year_df['類型'] != '休假'].groupby([year_df['日期'].dt.strftime('%m月'), '類型'])['金額'].sum().unstack(fill_value=0).reset_index()
                annual_df.rename(columns={'日期': '月份'}, inplace=True)
                if '收入' not in annual_df: annual_df['收入'] = 0
                if '開銷' not in annual_df: annual_df['開銷'] = 0
                annual_df['淨利'] = annual_df['收入'] - annual_df['開銷']
                
                fig_yr = go.Figure()
                fig_yr.add_trace(go.Bar(x=annual_df['月份'], y=annual_df['收入'], name='收入', marker_color='#06C167'))
                fig_yr.add_trace(go.Bar(x=annual_df['月份'], y=annual_df['開銷'], name='開銷', marker_color='#FF2B85'))
                fig_yr.add_trace(go.Scatter(x=annual_df['月份'], y=annual_df['淨利'], name='淨利', mode='lines+markers', marker_color='#F6C143', line=dict(width=3)))
                fig_yr.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#FFF'))
                st.plotly_chart(fig_yr, use_container_width=True)

# ==========================================
# 分頁 4: 管理與備份
# ==========================================
with tab4:
    with st.container(border=True):
        st.header("⚙️ 紀錄管理與備份")
        st.write(f"目前的名稱 (道號) 為：**{user_name}**")
        if st.button("重新設定名稱", type="secondary"): 
            update_profile_field("道號", "")
            st.cache_data.clear()
            st.rerun()
        st.write("---")
        if not df.empty:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 從雲端下載備份 (Excel可開)", data=csv_data, file_name=f"delivery_records_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary") 

# ==========================================
# 分頁 5: 👑 宗門封神榜 
# ==========================================
with tab_lb:
    with st.container(border=True):
        st.header("👑 宗門封神榜")
        st.markdown("天下風雲出我輩，實力、運氣與特權的頂峰對決！")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1: time_filter = st.selectbox("📜 選擇時間區間：", ["日榜 (今日)", "週榜 (本週)", "月榜 (本月)", "年榜 (本年度)", "總榜 (歷史巔峰)"])
        with col_t2: rank_type = st.selectbox("⚔️ 選擇競技賽道：", ["🏆 綜合戰鬥力 (CP)", "💰 爆肝總靈石", "🛵 節能車神 (投資報酬率)"])
        
        with st.spinner("⏳ 天機閣正在運算全宗門數據..."):
            try:
                if big_df.empty:
                    st.info("宗門尚無任何紀錄。")
                else:
                    if "日榜" in time_filter: filtered_df = big_df[big_df['日期'] == today]
                    elif "週榜" in time_filter: filtered_df = big_df[(big_df['日期'] >= today - timedelta(days=today.weekday())) & (big_df['日期'] <= today)]
                    elif "月榜" in time_filter: filtered_df = big_df[(pd.to_datetime(big_df['日期']).dt.month == today.month) & (pd.to_datetime(big_df['日期']).dt.year == today.year)]
                    elif "年榜" in time_filter: filtered_df = big_df[pd.to_datetime(big_df['日期']).dt.year == today.year]
                    else: filtered_df = big_df
                    
                    lb_data = []
                    for uid, u_name in user_map.items():
                        user_df = filtered_df[filtered_df['User_ID'] == uid]
                        
                        u_bonus = 0
                        u_total_stone_for_tier = 0
                        for r in roster_records:
                            if str(r["User_ID"]) == uid:
                                u_bonus = int(r.get("額外戰力", 0)) if str(r.get("額外戰力", "")) != "" else 0
                                u_total_stone_for_tier = int(r.get("總靈石", 0)) if str(r.get("總靈石", "")) != "" else 0
                                break
                                
                        if not user_df.empty:
                            u_inc = user_df[user_df['類型'] == '收入']['金額'].sum()
                            u_hr = user_df[user_df['類型'] == '收入']['上線時數'].sum()
                            u_days = user_df[user_df['類型'] == '收入']['日期'].nunique()
                            u_tribs = user_df[user_df['天劫'] == 'True'].shape[0] if '天劫' in user_df.columns else 0
                            
                            u_exp_df = user_df[(user_df['類型'] == '開銷') & (user_df['項目'].isin(['機車油錢', '機車保養']))]
                            u_gas_exp = u_exp_df['金額'].sum() if not u_exp_df.empty else 0
                            
                            if u_inc > 0 or "總榜" in time_filter:
                                avg_w = u_inc / u_hr if u_hr > 0 else 0
                                _, _, _, _, _, u_cp_mult = get_realm_tier_and_buffs(u_total_stone_for_tier)
                                u_base_cp = int(((u_inc / 100) + (avg_w * 10) + (u_days * 50) + (u_tribs * 300)) * u_cp_mult)
                                u_cp = u_base_cp + u_bonus
                                
                                efficiency = u_inc / (u_gas_exp + 1) if u_gas_exp > 0 else u_inc
                                
                                lb_data.append({
                                    "User_ID": uid, "道號": u_name, "CP": u_cp, "Income": u_inc, "Efficiency": efficiency, "GasExp": u_gas_exp, "Tribs": u_tribs
                                })
                    
                    if lb_data:
                        lb_df = pd.DataFrame(lb_data)
                        if "綜合戰鬥力" in rank_type: lb_df = lb_df.sort_values(by="CP", ascending=False).reset_index(drop=True)
                        elif "爆肝總靈石" in rank_type: lb_df = lb_df.sort_values(by="Income", ascending=False).reset_index(drop=True)
                        else: lb_df = lb_df.sort_values(by="Efficiency", ascending=False).reset_index(drop=True)
                            
                        lb_df.index = lb_df.index + 1
                        display_data = []
                        
                        for idx, row in lb_df.iterrows():
                            title_prefix = ""
                            if idx == 1: title_prefix = "👑 [肝帝] " if "車神" not in rank_type else "👑 [節能天尊] "
                            elif idx == len(lb_df) and len(lb_df) > 1: title_prefix = "💤 [摸魚仙人] " if "車神" not in rank_type else "💸 [吃油怪獸] "
                            
                            rank_str = f"🥇" if idx==1 else (f"🥈" if idx==2 else (f"🥉" if idx==3 else str(idx)))
                            
                            if "車神" in rank_type:
                                display_data.append({
                                    "排名": rank_str, "道號": f"{title_prefix}{row['道號']}", "賺取靈石": f"${int(row['Income']):,}",
                                    "油錢與保養": f"${int(row['GasExp']):,}", "油耗轉換率": f"1 : {row['Efficiency']:.1f}"
                                })
                            else:
                                display_data.append({
                                    "排名": rank_str, "道號": f"{title_prefix}{row['道號']}", "戰鬥力 (CP)": int(row['CP']),
                                    "期間靈石": f"${int(row['Income']):,}", "挺過天劫": int(row['Tribs'])
                                })
                                
                        st.dataframe(pd.DataFrame(display_data), hide_index=True, use_container_width=True)
                        if "車神" in rank_type: st.caption("💡 【節能車神榜】計算公式：期間賺取靈石 ÷ (機車油錢 + 機車保養)。轉換率越高，代表座騎越省錢！")
                    else:
                        st.info(f"無人上榜。在『{time_filter.split(' ')[0]}』期間，宗門內尚無弟子外出歷練。")
            except Exception as e:
                st.error(f"⚠️ 天機閣運算出現殘影，請重整網頁。錯誤碼：{e}")
