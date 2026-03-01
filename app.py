import streamlit as st
import pandas as pd
import os
from datetime import date, time, datetime, timedelta
import calendar
import plotly.express as px
import plotly.graph_objects as go
import random

# ==========================================
# 檔案與常數設定
# ==========================================
DATA_FILE = "delivery_records.csv"
TARGETS_FILE = "monthly_targets.csv"
USER_FILE = "user_name.txt"
FORTUNE_FILE = "daily_fortune.txt"
QUEST_FILE = "daily_quest.txt"

CUSTOM_COLORS = {"Uber Eats": "#06C167", "Foodpanda": "#FF2B85", "其他獎金": "#F6C143", "休假": "#B0B0B0"}
WEEKDAY_MAP = {0: '星期一', 1: '星期二', 2: '星期三', 3: '星期四', 4: '星期五', 5: '星期六', 6: '星期日'}

CULTIVATION_REALMS = [
    (0, "凡人武夫", "初出茅廬的跑腿", "🚶‍♂️"),
    (10000, "煉氣前期", "外送門外門弟子", "🚴‍♂️"), (30000, "煉氣中期", "外送門外門弟子", "🚴‍♂️"), (60000, "煉氣後期", "外送門外門弟子", "🚴‍♂️"),
    (100000, "築基前期", "外送門內門弟子", "🛵"), (150000, "築基中期", "外送門內門弟子", "🛵"), (200000, "築基後期", "外送門內門弟子", "🛵"),
    (300000, "結丹前期", "外送真傳弟子", "🏍️"), (400000, "結丹中期", "外送真傳弟子", "🏍️"), (500000, "結丹後期", "外送真傳弟子", "🏍️"),
    (600000, "元嬰前期", "外送堂主", "🦅"), (800000, "元嬰中期", "外送堂主", "🦅"), (1000000, "元嬰後期", "百萬靈石大長老", "🦅"),
    (1500000, "化神前期", "外送宗師", "🐉"), (2000000, "化神中期", "外送宗師", "🐉"), (3000000, "化神後期", "外送宗師", "🐉"),
    (5000000, "渡劫飛升", "外送天尊", "🌌")
]

FORTUNE_POOL = [
    "🌟 大吉：天地靈氣匯聚！一路綠燈，瘋狂連單，客人豪爽給小費！",
    "✨ 中吉：運勢平穩。單量穩定，穩紮穩打即可達成今日目標。",
    "🌤️ 小吉：略有波折。可能遇到拖餐店家，但幸好客人態度友善。",
    "🍃 平：普普通通的一天。保持平常心，注意行車安全，平安就是福。",
    "💧 末吉：勞其筋骨。可能會接到大單，但需要爬六樓，當作鍛鍊身體！",
    "⚠️ 凶：暗藏殺機！今天請盡量避開平常就愛拖餐的雷包店家，防禦駕駛！"
]

QUEST_DATA = {
    1: {"name": "【爆肝試煉】", "desc": "今日閉關（上線）需滿 8 小時"},
    2: {"name": "【清心寡慾】", "desc": "除了油錢與保養外，今日零額外開銷 (忍住不買飲料/宵夜)"},
    3: {"name": "【小有斬獲】", "desc": "今日獲取 1500 靈石"}
}

BLIND_BOX_REWARDS = [
    "🎁 獲得法寶【玄鐵保溫箱】：餐點絕對保溫，客人好感度隱藏+10",
    "🎁 獲得丹藥【九轉大腸丹】：免疫奧客精神攻擊 1 次！",
    "🎁 獲得秘笈【尋龍點穴盤】：預知爆單熱區位置，直覺力大幅提升！",
    "🎁 獲得護具【金絲避水衣】：無視暴雨天候帶來的減速 debuff！",
    "🎁 獲得符籙【神行太保符】：座騎移動速度 +10% (一路綠燈機率提升)"
]

# ==========================================
# 核心邏輯函數
# ==========================================
def load_data():
    df = pd.read_csv(DATA_FILE)
    if "上線時數" not in df.columns: df["上線時數"] = 0.0
    if "天劫" not in df.columns: df["天劫"] = False
    return df

def save_data(date_val, record_type, item, amount, hours, note, tribulation=False):
    df = load_data()
    new_row = pd.DataFrame([{"日期": date_val, "類型": record_type, "項目": item, "金額": amount, "上線時數": hours, "備註": note, "天劫": tribulation}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def delete_data(indices_to_drop):
    df = load_data()
    df = df.drop(index=indices_to_drop)
    df.to_csv(DATA_FILE, index=False)

def get_realm_info(total_exp):
    current_realm, current_title, current_avatar = "凡人武夫", "初出茅廬的跑腿", "🚶‍♂️"
    next_realm, next_exp, prev_exp = "未知", 10000, 0
    for i in range(len(CULTIVATION_REALMS)):
        if total_exp >= CULTIVATION_REALMS[i][0]:
            current_realm, current_title, current_avatar = CULTIVATION_REALMS[i][1], CULTIVATION_REALMS[i][2], CULTIVATION_REALMS[i][3]
            prev_exp = CULTIVATION_REALMS[i][0]
            if i + 1 < len(CULTIVATION_REALMS):
                next_realm, next_exp = CULTIVATION_REALMS[i+1][1], CULTIVATION_REALMS[i+1][0]
            else:
                next_realm, next_exp = "已達巔峰", total_exp
        else: break
    progress = 1.0 if next_realm == "已達巔峰" else min((total_exp - prev_exp) / (next_exp - prev_exp), 1.0)
    return current_realm, next_realm, next_exp, progress, current_title, current_avatar

def get_mount_info(total_hours):
    if total_hours >= 1000: return "九天應龍", "🐉"
    elif total_hours >= 500: return "紫電魔豹", "🐆"
    elif total_hours >= 100: return "疾風靈鶴", "🦅"
    else: return "凡鐵飛劍", "🗡️"

def get_daily_quest():
    today_str = str(date.today())
    if not os.path.exists(QUEST_FILE):
        q_id = random.randint(1, 3)
        with open(QUEST_FILE, "w") as f: f.write(f"{today_str}|{q_id}|0")
        return q_id, 0
    with open(QUEST_FILE, "r") as f:
        content = f.read().strip()
        if not content or "|" not in content:
            q_id = random.randint(1, 3)
            with open(QUEST_FILE, "w") as f: f.write(f"{today_str}|{q_id}|0")
            return q_id, 0
        parts = content.split("|")
        if parts[0] != today_str:
            q_id = random.randint(1, 3)
            with open(QUEST_FILE, "w") as f: f.write(f"{today_str}|{q_id}|0")
            return q_id, 0
        return int(parts[1]), int(parts[2])

def complete_quest(q_id):
    with open(QUEST_FILE, "w") as f: f.write(f"{date.today()}|{q_id}|1")

def load_targets(): return pd.read_csv(TARGETS_FILE)

def save_target(month, amount):
    df = load_targets()
    if month in df["月份"].values: df.loc[df["月份"] == month, "目標金額"] = amount
    else: df = pd.concat([df, pd.DataFrame([{"月份": month, "目標金額": amount}])], ignore_index=True)
    df.to_csv(TARGETS_FILE, index=False)

def get_today_fortune():
    if not os.path.exists(FORTUNE_FILE): return None, None
    with open(FORTUNE_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if "|" in content:
            return content.split("|", 1)
    return None, None

def save_today_fortune(fortune):
    with open(FORTUNE_FILE, "w", encoding="utf-8") as f: f.write(f"{date.today()}|{fortune}")

def get_prev_month_str(month_str):
    y, m = map(int, month_str.split('-'))
    if m == 1:
        return f"{y-1}-12"
    else:
        return f"{y}-{m-1:02d}"

def change_date(new_date): 
    st.session_state.selected_date = new_date

# 初始化系統檔案
if not os.path.exists(DATA_FILE): pd.DataFrame(columns=["日期", "類型", "項目", "金額", "上線時數", "備註", "天劫"]).to_csv(DATA_FILE, index=False)
if not os.path.exists(TARGETS_FILE): pd.DataFrame(columns=["月份", "目標金額"]).to_csv(TARGETS_FILE, index=False)

# --- 網頁介面開始 ---
st.set_page_config(page_title="外送記帳儀表板", layout="wide", page_icon="🛵")

st.markdown("""
<style>
    .stApp { background-color: #121212; background-image: radial-gradient(circle at 50% 0%, #2b2b2b 0%, #121212 70%); color: #E0E0E0; }
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
    .stTabs [data-baseweb="tab"] { color: #AAAAAA; }
    .stTabs [aria-selected="true"] { color: #FFD700 !important; border-bottom-color: #FFD700 !important; }
    .cp-text { font-size: 60px; font-weight: 900; color: #FF4B4B; text-align: center; text-shadow: 0 0 20px rgba(255, 75, 75, 0.6); margin: 0; line-height: 1.2; }
    .cp-label { font-size: 20px; color: #AAAAAA; text-align: center; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 2px; }
    .card-box { border: 1px solid #444; border-radius: 10px; padding: 15px; background-color: rgba(30,30,30,0.6); }
</style>
""", unsafe_allow_html=True)

if not os.path.exists(USER_FILE):
    st.markdown("<br><br><h1 style='text-align: center; color: #FFD700;'>⛩️ 歡迎踏入外送修仙界</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: #AAAAAA;'>仙途漫漫，不知這位道友如何稱呼？</h4><br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        new_name = st.text_input("請輸入你的道號 (名稱)：", placeholder="例如：車神阿嘎...")
        if st.button("🚀 正式踏入仙途", type="primary", use_container_width=True):
            if new_name.strip():
                with open(USER_FILE, "w", encoding="utf-8") as f: f.write(new_name.strip())
                st.rerun()
            else: st.warning("請輸入名稱，方可登記入冊！")
    st.stop()

with open(USER_FILE, "r", encoding="utf-8") as f: user_name = f.read().strip()

if "selected_date" not in st.session_state: st.session_state.selected_date = date.today()
if "input_key" not in st.session_state: st.session_state.input_key = 0
if "show_success" not in st.session_state: st.session_state.show_success = False
if "quest_reward" not in st.session_state: st.session_state.quest_reward = ""

st.title("🛵 外送記帳儀表板")

tab0, tab1, tab2, tab3, tab4 = st.tabs(["🐉 修仙錄", "📝 每日輸入", "📊 月度報表", "🏆 年度與分析", "⚙️ 管理與備份"])

k = st.session_state.input_key
df = load_data()
if not df.empty: df['日期'] = pd.to_datetime(df['日期'])

# ==========================================
# 分頁 0: 🐉 專屬修仙面板 
# ==========================================
with tab0:
    if df.empty:
        st.info(f"📜 仙途尚未展開... {user_name}道友，請至「每日輸入」完成你的第一次歷練！")
    else:
        total_income = df[df['類型'] == '收入']['金額'].sum()
        total_expense = df[df['類型'] == '開銷']['金額'].sum()
        total_profit = total_income - total_expense
        total_hours = df[df['類型'] == '收入']['上線時數'].sum()
        total_days = df[df['類型'] == '收入']['日期'].nunique()
        total_tribulations = df[df['天劫'] == True].shape[0] if '天劫' in df.columns else 0
        avg_wage = total_income / total_hours if total_hours > 0 else 0
        
        cp_score = int((total_income / 100) + (avg_wage * 10) + (total_days * 50) + (total_tribulations * 300))
        
        current_realm, next_realm, next_exp, progress, current_title, current_avatar = get_realm_info(total_income)
        mount_name, mount_avatar = get_mount_info(total_hours)
        
        st.markdown(f"<h2 style='text-align: center; color: #FFD700;'>✨ {user_name}道友，歡迎回到修仙界 ✨</h2>", unsafe_allow_html=True)
        
        st.markdown(f"<p class='cp-text'>{cp_score:,}</p>", unsafe_allow_html=True)
        st.markdown("<p class='cp-label'>⚔️ 綜合戰鬥力 (CP) ⚔️</p>", unsafe_allow_html=True)
        
        r_col1, r_col2, r_col3 = st.columns([1, 1, 1.5])
        
        with r_col1:
            st.markdown(f"""
            <div class="card-box" style="text-align: center;">
                <div style="font-size: 60px; margin-bottom: 5px;">{current_avatar}</div>
                <h5 style="color: #AAAAAA; margin-bottom: 5px;">當前境界</h5>
                <h3 style="color: #FFD700; margin-top: 0px;">{current_realm}</h3>
            </div>
            """, unsafe_allow_html=True)
            
        with r_col2:
            st.markdown(f"""
            <div class="card-box" style="text-align: center;">
                <div style="font-size: 60px; margin-bottom: 5px;">{mount_avatar}</div>
                <h5 style="color: #AAAAAA; margin-bottom: 5px;">專屬座騎 (上線時數)</h5>
                <h3 style="color: #06C167; margin-top: 0px;">{mount_name}</h3>
            </div>
            """, unsafe_allow_html=True)
            
        with r_col3:
            st.markdown("### ⚡ 突破進度 (靈石)")
            st.progress(progress)
            if next_realm != "已達巔峰":
                st.write(f"**目前：** `{total_income:,}` / **需求：** `{next_exp:,}`")
                st.caption(f"🚀 距離突破至 **【{next_realm}】** 還需 **{next_exp - total_income:,}** 靈石！")
            else:
                st.success("🎉 你已達到此界巔峰，傲視群雄！")
                
        st.write("---")
        
        bot_c1, bot_c2 = st.columns(2)
        
        with bot_c1:
            st.markdown("### 📜 宗門懸賞榜 (每日任務)")
            q_id, q_status = get_daily_quest()
            quest = QUEST_DATA[q_id]
            
            st.markdown(f"**今日任務：{quest['name']}**")
            st.write(f"📝 說明：{quest['desc']}")
            
            daily_df = df[df['日期'].dt.date == date.today()]
            d_inc = daily_df[daily_df['類型'] == '收入']['金額'].sum() if not daily_df.empty else 0
            d_hr = daily_df[daily_df['類型'] == '收入']['上線時數'].sum() if not daily_df.empty else 0
            
            quest_met = False
            if q_id == 1 and d_hr >= 8: 
                quest_met = True
            elif q_id == 2 and not daily_df[daily_df['類型'] == '收入'].empty:
                daily_expenses_items = daily_df[daily_df['類型'] == '開銷']['項目'].tolist()
                allowed_expenses = ["機車油錢", "機車保養", "機車貸款"]
                if all(item in allowed_expenses for item in daily_expenses_items):
                    quest_met = True
            elif q_id == 3 and d_inc >= 1500: 
                quest_met = True
            
            if q_status == 1:
                st.success("✅ 今日懸賞已完成！明日再來接取新任務。")
                if st.session_state.quest_reward != "":
                    st.info(st.session_state.quest_reward)
            else:
                if quest_met:
                    if st.button("🎁 領取懸賞盲盒", type="primary"):
                        complete_quest(q_id)
                        reward = random.choice(BLIND_BOX_REWARDS)
                        st.session_state.quest_reward = reward
                        st.balloons()
                        st.rerun()
                else:
                    st.button("⏳ 任務尚未達成", disabled=True)
            
        with bot_c2:
            st.markdown("### 🥠 天機閣 (每日外送運勢)")
            today_str = str(date.today())
            last_date, today_fortune = get_today_fortune()
            
            if last_date == today_str:
                st.success(f"🗓️ 今日卜卦結果：\n\n**{today_fortune}**")
            else:
                st.write("一日一卦，測算今日外送吉凶。")
                if st.button("🔮 抽取今日運勢", type="primary", use_container_width=True):
                    save_today_fortune(random.choice(FORTUNE_POOL))
                    st.snow()
                    st.rerun()
        
        st.divider()
        
        st.markdown("### 🏅 道宗成就牆")
        daily_income_df = df[df['類型'] == '收入'].groupby('日期')['金額'].sum()
        max_daily_income = daily_income_df.max() if not daily_income_df.empty else 0
        
        achievements = []
        if total_income > 0: achievements.append("✅ 【初入仙門】 完成第一次下山歷練")
        if max_daily_income >= 1000: achievements.append("✅ 【小試身手】 單日獲取 1000 靈石")
        if max_daily_income >= 3000: achievements.append("🌟 【拼命三郎】 單日獲取 3000 靈石 (恐怖如斯！)")
        if max_daily_income >= 5000: achievements.append("🐉 【無上神皇】 單日獲取 5000 靈石 (此子斷不可留！)")
        if total_tribulations >= 1: achievements.append("⛈️ 【初嘗天雷】 成功扛過 1 次天劫 (惡劣天氣/奧客)")
        if total_tribulations >= 10: achievements.append("⚡ 【雷劫尊者】 累計扛過 10 次天劫，道心堅如磐石！")
        
        if len(achievements) == 0: st.write("尚未解鎖任何成就，快去歷練吧！")
        else:
            for ach in achievements: st.markdown(f"**{ach}**")

# ==========================================
# 分頁 1: 每日輸入 (加入快速編輯功能)
# ==========================================
with tab1:
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.header("📝 新增紀錄") 
        if st.session_state.show_success:
            st.success("✅ 動作已成功儲存！")
            st.session_state.show_success = False
        
        temp_date = st.date_input("選擇日期", value=st.session_state.selected_date)
        if temp_date != st.session_state.selected_date:
            st.session_state.selected_date = temp_date
            st.rerun()
        record_date = st.session_state.selected_date

        record_type = st.radio("類型", ["收入", "開銷", "休假"], horizontal=True)

        if record_type == "收入" or record_type == "開銷":
            is_tribulation = st.checkbox("⛈️ 今日遭遇天劫 (暴雨/寒流/極品奧客)", key=f"trib_{k}")
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
                
            time_mode = st.radio("時數記錄方式", ["自動換算 (首單至末單)", "手動輸入時數"], horizontal=True)
            if time_mode == "自動換算 (首單至末單)":
                t_col1, t_col2 = st.columns(2)
                with t_col1: start_time = st.time_input("首單時間", time(10, 0), key=f"t1_{k}") 
                with t_col2: end_time = st.time_input("末單時間", time(22, 0), key=f"t2_{k}")   
                dt_start, dt_end = datetime.combine(date(2000, 1, 1), start_time), datetime.combine(date(2000, 1, 1), end_time)
                if dt_end < dt_start: dt_end += timedelta(days=1)
                hours = round((dt_end - dt_start).total_seconds() / 3600.0, 2)
                st.info(f"⏱️ 系統換算：**{hours} 小時**")
            else:
                h_col, m_col = st.columns(2)
                with h_col: input_hours = st.number_input("小時", min_value=0, step=1, value=None, key=f"hr_{k}")
                with m_col: input_minutes = st.number_input("分鐘", min_value=0, max_value=59, step=1, value=None, key=f"min_{k}")
                hours = round((input_hours or 0) + ((input_minutes or 0) / 60.0), 2)
                
            note = st.text_input("備註 (選填)", value="", key=f"note_{k}")

            if st.button("儲存紀錄", type="primary", use_container_width=True):
                if platform_mode == "單一平台":
                    if val_amount > 0:
                        save_data(record_date, record_type, item, val_amount, hours, note, is_tribulation)
                        st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1 
                        st.rerun()
                    else: st.warning("請輸入金額")
                else:
                    if (amount_u or 0) > 0 or (amount_f or 0) > 0:
                        if (amount_u or 0) > 0: save_data(record_date, record_type, "Uber Eats", amount_u, hours, note, is_tribulation)
                        if (amount_f or 0) > 0: save_data(record_date, record_type, "Foodpanda", amount_f, 0.0 if (amount_u or 0) > 0 else hours, note, is_tribulation)
                        st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1
                        st.rerun()
                    else: st.warning("請輸入金額")

        elif record_type == "開銷": 
            expense_choice = st.selectbox("項目", ["機車油錢", "機車保養", "機車貸款", "生財器具(如手機架/雨衣)", "其他 (手動輸入)"])
            item = st.text_input("輸入開銷名稱", key=f"item_{k}") if expense_choice == "其他 (手動輸入)" else expense_choice
            amount = st.number_input("金額 (元)", min_value=0, step=10, value=None, key=f"amt_{k}")
            note = st.text_input("備註 (選填)", value="", key=f"note_{k}")

            if st.button("儲存紀錄", type="primary", use_container_width=True):
                if (amount or 0) > 0 and item.strip() != "":
                    save_data(record_date, record_type, item, amount, 0.0, note, is_tribulation)
                    st.session_state.show_success, st.session_state.input_key = True, st.session_state.input_key + 1
                    st.rerun()
                else: st.warning("請輸入正確金額與項目")
                    
        else:
            st.info("🏖️ 標記今天為休假日") 
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
                if any(daily_df.get('天劫', False) == True): st.warning("⛈️ 此日曾遭遇天劫，挺過來了！")
                
                d_inc = daily_df[daily_df['類型'] == '收入']['金額'].sum()
                d_exp = daily_df[daily_df['類型'] == '開銷']['金額'].sum()
                d_hr = daily_df[daily_df['類型'] == '收入']['上線時數'].sum()
                d_wage = d_inc / d_hr if d_hr > 0 else 0
                h_disp = f"{int(d_hr)}h {int(round((d_hr - int(d_hr)) * 60))}m" if d_hr > 0 else "0h 0m"
                
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("當日收入", f"${d_inc:,}")
                d2.metric("當日開銷", f"${d_exp:,}")
                d3.metric("當日上線", h_disp) 
                d4.metric("當日時薪", f"${d_wage:,.0f}")
            else:
                st.info("點擊下方日曆查看數字")

            cal_year, cal_month = st.session_state.selected_date.year, st.session_state.selected_date.month
            cal_matrix = calendar.monthcalendar(cal_year, cal_month)
            
            st.write(f"**👆 {cal_year}年 {cal_month}月**")
            cols = st.columns(7)
            for i, wd in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
                cols[i].markdown(f"<div style='text-align: center'><b>{wd}</b></div>", unsafe_allow_html=True)
            
            for week in cal_matrix:
                cols = st.columns(7)
                for i, day in enumerate(week):
                    if day != 0:
                        cur_d = date(cal_year, cal_month, day)
                        is_sel = (cur_d == st.session_state.selected_date)
                        btn_type = "primary" if is_sel else "secondary"
                        btn_label = f"{day}🏖️" if cur_d in off_dates else (f"{day}✅" if cur_d in work_dates else str(day))
                        cols[i].button(btn_label, key=f"c1_{cal_year}_{cal_month}_{day}", use_container_width=True, type=btn_type, on_click=change_date, args=(cur_d,))

            # 💡 此次新增：快速編輯當日明細
            if not daily_df.empty:
                st.write("---")
                st.subheader("🛠️ 編輯今日明細")
                st.caption("💡 提示：點擊下方表格內的「金額」、「時數」、「天劫」或「備註」即可直接打字修改。")

                edit_df = daily_df.copy()
                edit_df['日期'] = edit_df['日期'].dt.strftime('%Y-%m-%d')

                edited_df = st.data_editor(
                    edit_df,
                    hide_index=True,
                    column_config={
                        "金額": st.column_config.NumberColumn("金額 ($)", format="%d"),
                        "上線時數": st.column_config.NumberColumn("時數 (h)"),
                        "天劫": st.column_config.CheckboxColumn("天劫 (打勾)")
                    },
                    disabled=["日期", "類型", "項目"],
                    use_container_width=True,
                    key=f"edit_{st.session_state.selected_date}_{k}" 
                )

                if st.button("💾 儲存修改", type="primary", use_container_width=True):
                    main_df = load_data()
                    for idx in edited_df.index:
                        main_df.loc[idx, '金額'] = edited_df.loc[idx, '金額']
                        main_df.loc[idx, '上線時數'] = edited_df.loc[idx, '上線時數']
                        main_df.loc[idx, '備註'] = edited_df.loc[idx, '備註']
                        if '天劫' in edited_df.columns:
                            main_df.loc[idx, '天劫'] = edited_df.loc[idx, '天劫']
                    main_df.to_csv(DATA_FILE, index=False)
                    st.session_state.show_success = True
                    st.session_state.input_key += 1
                    st.rerun()

# ==========================================
# 分頁 2: 月度報表
# ==========================================
with tab2:
    if not df.empty:
        months = df['日期'].dt.to_period('M').astype(str).unique()
        mc1, mc2 = st.columns([1, 1])
        with mc1: selected_month = st.selectbox("選擇月份", sorted(months, reverse=True))
        month_df = df[df['日期'].dt.to_period('M').astype(str) == selected_month]
        prev_month_df = df[df['日期'].dt.to_period('M').astype(str) == get_prev_month_str(selected_month)]
        
        targets_df = load_targets()
        target_row = targets_df[targets_df["月份"] == selected_month]
        current_target = int(target_row["目標金額"].iloc[0]) if not target_row.empty else 0

        with mc2:
            with st.expander(f"🎯 設定 {selected_month} 目標收入"):
                new_target = st.number_input("本月目標 (元)", min_value=0, step=1000, value=current_target)
                if st.button("更新目標", type="primary"): save_target(selected_month, new_target); st.rerun()

        if not month_df.empty:
            t_inc = month_df[month_df['類型'] == '收入']['金額'].sum()
            t_exp = month_df[month_df['類型'] == '開銷']['金額'].sum()
            n_prof = t_inc - t_exp
            p_inc = prev_month_df[prev_month_df['類型'] == '收入']['金額'].sum() if not prev_month_df.empty else 0
            p_exp = prev_month_df[prev_month_df['類型'] == '開銷']['金額'].sum() if not prev_month_df.empty else 0
            p_prof = p_inc - p_exp

            if current_target > 0:
                st.markdown(f"### 🚀 目標進度：`${t_inc:,}` / `${current_target:,}`")
                st.progress(min(t_inc / current_target, 1.0))
                remaining_amount = current_target - t_inc
                if remaining_amount > 0:
                    today, s_year, s_month = date.today(), int(selected_month.split('-')[0]), int(selected_month.split('-')[1])
                    last_day_of_month = calendar.monthrange(s_year, s_month)[1]
                    if today.year == s_year and today.month == s_month: days_left = last_day_of_month - today.day + 1
                    elif date(s_year, s_month, last_day_of_month) > today: days_left = last_day_of_month 
                    else: days_left = 0 
                    
                    if days_left > 0: st.info(f"🏃‍♂️ 距離目標還差 **${remaining_amount:,}** 元。本月還剩 **{days_left}** 天，每天平均需賺 **${remaining_amount/days_left:,.0f}** 才能達標！")
                    else: st.warning(f"⚠️ 這個月已經結束囉，距離目標差了 ${remaining_amount:,} 元，下個月繼續加油！")
                else: st.success(f"🎉 太神啦！已經達成設定的目標，目前超標賺了 **${-remaining_amount:,}** 元！")
            
            st.write("")
            m1, m2, m3 = st.columns(3)
            m1.metric("月總收入", f"${t_inc:,}", delta=f"{int(t_inc - p_inc)} (較上月)" if p_inc > 0 else None)
            m2.metric("月總開銷", f"${t_exp:,}", delta=f"{int(t_exp - p_exp)} (較上月)" if p_exp > 0 else None, delta_color="inverse")
            m3.metric("本月淨利", f"${n_prof:,}", delta=f"{int(n_prof - p_prof)} (較上月)" if p_prof != 0 else None)
            
            st.divider()
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("📈 每日收支趨勢")
                trend_df = month_df[month_df['類型'] != '休假'].groupby(['日期', '項目', '類型'])['金額'].sum().reset_index()
                trend_df.loc[trend_df['類型'] == '開銷', '金額'] *= -1
                if not trend_df.empty:
                    y, m = map(int, selected_month.split('-'))
                    fig_bar = px.bar(trend_df, x='日期', y='金額', color='項目', color_discrete_map=CUSTOM_COLORS, barmode='relative')
                    fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    fig_bar.update_xaxes(range=[f"{selected_month}-01", f"{selected_month}-{calendar.monthrange(y, m)[1]}"], dtick="86400000", tickformat="%m-%d")
                    st.plotly_chart(fig_bar, use_container_width=True)
            with c2:
                st.subheader("🥧 平台收入佔比")
                inc_df = month_df[month_df['類型'] == '收入']
                if not inc_df.empty:
                    pie_data = inc_df.groupby('項目')['金額'].sum().reset_index()
                    fig_pie = px.pie(pie_data, values='金額', names='項目', hole=0.4, color='項目', color_discrete_map=CUSTOM_COLORS)
                    fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_pie, use_container_width=True)
    else: st.info("目前尚無資料，請先至「每日輸入」新增紀錄。")

# ==========================================
# 分頁 3: 年度與分析
# ==========================================
with tab3:
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
            fig_yr.update_layout(barmode='group', hovermode='x unified', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_yr, use_container_width=True)
            
            st.divider()
            st.subheader("📅 星期幾最好賺？ (年度數據分析)")
            wk_df = year_df[year_df['類型'] == '收入'].copy()
            if not wk_df.empty:
                wk_df['星期號碼'] = wk_df['日期'].dt.dayofweek
                wk_df['星期'] = wk_df['星期號碼'].map(WEEKDAY_MAP)
                daily_agg = wk_df.groupby('日期').agg({'金額': 'sum', '上線時數': 'sum', '星期': 'first', '星期號碼': 'first'}).reset_index()
                wk_stats = daily_agg.groupby(['星期號碼', '星期']).agg(平均日收入=('金額', 'mean'), 總時數=('上線時數', 'sum'), 總金額=('金額', 'sum')).reset_index()
                wk_stats['平均時薪'] = (wk_stats['總金額'] / wk_stats['總時數']).fillna(0)
                
                c_wk1, c_wk2 = st.columns(2)
                with c_wk1:
                    fig_wk1 = px.bar(wk_stats, x='星期', y='平均日收入', title='各星期「平均日收入」', text_auto='.0f', color_discrete_sequence=['#06C167'])
                    fig_wk1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_wk1, use_container_width=True)
                with c_wk2:
                    fig_wk2 = px.bar(wk_stats, x='星期', y='平均時薪', title='各星期「平均時薪」', text_auto='.0f', color_discrete_sequence=['#F6C143'])
                    fig_wk2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_wk2, use_container_width=True)

# ==========================================
# 分頁 4: 管理與備份
# ==========================================
with tab4:
    st.header("⚙️ 紀錄管理與備份")
    st.subheader("👤 使用者設定")
    st.write(f"目前的名稱 (道號) 為：**{user_name}**")
    if st.button("重新設定名稱", type="secondary"):
        os.remove(USER_FILE)
        st.rerun()
    st.write("---")
    
    if not df.empty:
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 下載完整資料庫 (Excel可開)", data=csv_data, file_name=f"delivery_records_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary") 
        st.write("---")
        st.subheader("📋 批量刪除紀錄")
        if "show_del_success" not in st.session_state: st.session_state.show_del_success = False
        if st.session_state.show_del_success:
            st.success("✅ 已成功刪除紀錄！")
            st.session_state.show_del_success = False
            
        display_df = df.copy()
        display_df['日期'] = display_df['日期'].dt.strftime('%Y-%m-%d')
        display_df['上線時數'] = display_df['上線時數'].apply(lambda h: f"{int(h)}h {int(round((h - int(h)) * 60))}m" if h > 0 else "")
        display_df = display_df.sort_values(by='日期', ascending=False).reset_index()
        display_df.insert(0, "刪除", False)
        
        if '天劫' in display_df.columns: display_df['天劫'] = display_df['天劫'].map({True: '⛈️ 是', False: '無'})
        
        edited_df = st.data_editor(display_df, hide_index=True, column_config={"index": None, "刪除": st.column_config.CheckboxColumn("勾選", default=False), "金額": st.column_config.NumberColumn("金額 ($)", format="$%d")}, disabled=["日期", "類型", "項目", "金額", "上線時數", "備註", "天劫"], use_container_width=True)
        rows_to_delete = edited_df[edited_df["刪除"] == True]['index'].tolist()
        if len(rows_to_delete) > 0:
            if st.button(f"🗑️ 確認刪除已選取的 {len(rows_to_delete)} 筆紀錄", type="primary"):
                delete_data(rows_to_delete)
                st.session_state.show_del_success = True
                st.rerun()
    else: st.info("目前尚無資料可管理。")