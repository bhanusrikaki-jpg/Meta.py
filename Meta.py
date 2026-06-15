import cloudscraper
import requests
import time
import re
import os
import sys
import pytz
import gc
import feedparser
import threading
import telebot
from datetime import datetime, timedelta, timezone
from queue import Queue
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
from gtts import gTTS
from deep_translator import GoogleTranslator
from google import genai
from groq import Groq
from apscheduler.schedulers.background import BackgroundScheduler
from ecocal import Calendar # 🎯 కొత్తగా add చేసింది సర్
import pandas as pd  # 🎯 ఇది add చేయండి

# --- SYSTEM ENCODING ---
sys.stdout.reconfigure(encoding='utf-8')

# ==========================================================
# ⚙ CONFIGURATION & API KEYS
# ==========================================================
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") 
VIP_CHAT_ID = os.getenv("VIP_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([TOKEN, CHAT_ID, GEMINI_API_KEY, GROQ_API_KEY]):
    print("⚠ Warning: కొన్ని ముఖ్యమైన API Keys సెట్ చేయబడలేదు! దయచేసి చెక్ చేయండి.")

bot = telebot.TeleBot(TOKEN)
MODEL_NAME = "gemini-2.5-flash"

# --- టైమ్జోన్ సెటప్ ---
IST = pytz.timezone("Asia/Kolkata")
US = pytz.timezone("US/Eastern")
EU = pytz.timezone("Europe/Berlin")
JP = pytz.timezone("Asia/Tokyo")
HK = pytz.timezone("Asia/Hong_Kong")

# ==========================================================
# 📊 DATA STORES & WATCHLISTS
# ==========================================================
rss_news_store = []
sent_links = set()
sent_news = set()
pinned_messages_store = []
pulse_reports_store = []
sent_alerts = {}
sudden_move_sent = {}
gap_alert_sent = {}
collected_news = []
last_sent_results = set()
last_reset_date = datetime.now(IST).date()
economic_calendar_cache = {} # 🎯 Calendar cache సర్

MAX_NEWS = 5000
CLEAR_COUNT = 1000
ai_queue = Queue()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

## 🔴 చంటి గారి 100% పక్కా మాస్టర్ వాచ్లిస్ట్
MY_WATCHLIST = [
    "ANANTRAJ", "ANANT RAJ", "APOLLO", "APOLLO HOSPITALS", "BBOX", "BLACK BOX",
    "BEL", "BHARAT ELECTRONICS", "BHARTIARTL", "BHARTI AIRTEL", "AIRTEL",
    "BLS", "BLS INTERNATIONAL", "BLUECLOUD", "BLUE CLOUD", "BSE", "BSE LTD",
    "CDSL", "CGPOWER", "CG POWER", "CHOLAFIN", "CHOLAMANDALAM", "CLEANMAX", "CLEAN MAX",
    "COFORGE", "DIXON", "DIXON TECH", "E2E", "E2E NETWORKS", "EIEL", "Enviro Infra Engineers Ltd",
    "ETERNAL", "FRACTAL", "GMDCLTD", "GMDC", "GOKEX", "GOKALDAS EXPORTS",
    "GROWW", "GRSE", "EMMVEE", "EMMVEE SOLAR", "EMMVEE PHOTOVOLTAIC",
    "HAL", "HINDUSTAN AERONAUTICS", "HDFCBANK", "HDFC BANK", "HINDCOPPER", "HINDUSTAN COPPER",
    "IDEA", "VODAFONE IDEA", "IDFCFIRSTB", "IDFC FIRST", "INDIGO", "INTERGLOBE AVIATION",
    "INFY", "INFOSYS", "INTERARCH", "ITC", "ITCHOTELS", "ITC HOTELS", "JKTYRE", "JK TYRE",
    "JSWSTEEL", "JSW STEEL", "KALAMANDIR", "SAI SILKS", "KALYANKJIL", "KALYAN JEWELLERS",
    "KAYNES", "KAYNES TECH", "KEC", "KEC INTERNATIONAL",
    "LEMONTREE", "LEMON TREE", "LENSKART", "LGEINDIA", "LG ELECTRONICS", "LT", "L&T",
    "LARSEN", "M&M", "MAHINDRA", "MAZDOCK", "MAZAGON DOCK", "MCX", "MEESHO",
    "NESTLEIND", "NESTLE", "NESTLE INDIA", "NH", "NARAYANA HRUDAYALAYA",
    "NTPC", "NYKAA", "FSN E-COMMERCE","OLAELEC", "OLA ELECTRIC", "POLYCAB", "PROTEAN",
    "RELIANCE", "RIL", "PROTEAN eGOV TECHNOLOGIES", "PROTEAN eGOV", "RELIANCE INDUSTRIES", "RELIANCE JIO", "RELIANCE RETAIL",
    "SAILIFE", "SAI LIFE", "SBIN", "SBI", "STATE BANK", "SEPC", "SHAKTIPUMP", "SHakTI PUMPS",
    "SHRIRAMFIN", "SHRIRAM FINANCE", "SJS", "SJS ENTERPRISES", "SKIPPER", "SONACOMS", "SONA BLW",
    "SUZLON", "SUZLON ENERGY", "TATASTEEL", "TATA STEEL", "TCS", "TIPSMUSIC", "TIPS MUSIC",
    "TITAN", "TITAN COMPANY", "TVSMOTOR", "TVS MOTOR", "URBANCO", "URBAN COMPANY",
    "WABAG", "VA TECH WABAG", "WAAREEENER", "WAAREE ENERGIES", "YATHARTH", "YATHARTH HOSPITAL",
    "YATRA", "YATRA ONLINE", "ZAGGLE", "ZAGGLE PREPAID", "bhel", "భెల్", "bharat heavy electricals", "bharat heavy electricals limited",
    "physicswallah", "physics wallah", "pwl ", "physicswallah limited"
]

MARKET_KEYWORDS = [
    "rbi rate", "repo rate", "rate cut", "rate hike", "fed decision", "fomc", "interest rate", "rate",
    "warsh", "kevin warsh", "malhotra", "sanjay malhotra", "shaktikanta", "shaktikanta das", "monetary policy",
    "వడ్డీ రేటు", "రెపో రేటు",
    "budget 2026", "union budget", "budget", "gst rate change", "government policy", "corporate tax",
    "cabinet decision", "import duty", "export ban", "government decision", "govt decision", "gdp growth",
    "us gdp", "cpi inflation", "india gdp", "inflation", "gdp", "cabinet meeting",
    "ప్రభుత్వ నిర్ణయం", "బడ్జెట్", "ద్రవ్యోల్బణం",
    "war", "strike", "strikes", "attack", "attacks", "military", "sanctions", "iran", "us-iran",
    "crude", "oil", "brent", "opec", "omc", "dollar", "crude spike", "above $", "surge",
    "యుద్ధం", "దాడి", "దాడులు", "సైనిక", "ఆంక్షలు", "ఇరాన్", "చమురు", "క్రూడ్", "డాలర్", "crude oil",
    "market crash", "circuit breaker", "scam", "sebi ban", "emergency", "urgent", "breaking",
    "అత్యవసర", "rbi mpc", "mpc", "rupee", "రూపాయి"
]

IMPORTANT_KEYWORDS = MARKET_KEYWORDS + [stock.lower() for stock in MY_WATCHLIST]

news_feeds = [
    "https://www.forexlive.com/rss",
    "https://www.investing.com/rss/news_1.rss",
    "https://www.investing.com/rss/news_301.rss",
]

TIMINGS = {
    "GIFT Nifty": ("06:30", "02:45"),
    "Nikkei (Japan)": ("05:30", "11:30"),
    "Hang Seng (HK)": ("06:45", "13:30"),
    "DAX (Germany)": ("12:30", "21:00"),
    "FTSE (UK)": ("12:30", "21:00"),
    "Dow Jones (US)": ("19:00", "01:30"),
    "Nasdaq (US)": ("19:00", "01:30"),
    "S&P 500 (US)": ("19:00", "01:30"),
    "Gold (Commodity)": ("04:30", "03:30"),
    "Silver (Commodity)": ("04:30", "03:30"),
    "Brent Oil": ("05:30", "03:30"),
    "WTI Crude (US Oil)": ("03:30", "02:30"),
    "US 10Y Yield": ("18:30", "03:30"),
    "Bitcoin (Daily)": ("05:30", "05:29"),
}

symbols = {
    "GIFT Nifty": "^NSEI",
    "Dow Jones (US)": "^DJI",
    "Nasdaq (US)": "^IXIC",
    "S&P 500 (US)": "^GSPC",
    "Nikkei (Japan)": "^N225",
    "Hang Seng (HK)": "^HSI",
    "DAX (Germany)": "^GDAXI",
    "FTSE (UK)": "^FTSE",
    "Gold (Commodity)": "GC=F",
    "Silver (Commodity)": "SI=F",
    "Brent Oil": "BZ=F",
    "WTI Crude (US Oil)": "CL=F",
    "Bitcoin (Daily)": "BTC-USD",
    "US 10Y Yield": "^TNX",
}

# ==========================================================
# 🔍 LOGGING & CORE UTILITIES
# ==========================================================
def log(msg, level="INFO"):
    print(f"[{datetime.now(IST).strftime('%H:%M:%S')}] [{level}] {msg}")

def translate_to_telugu(text):
    try: return GoogleTranslator(source='auto', target='te').translate(text)
    except: return text

def translate(text): return translate_to_telugu(text)

def safe_html_text(text):
    if not text: return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def safe_html_url(url):
    if not url: return ""
    return str(url).replace("&", "&amp;").replace('"', '&quot;').replace("'", "&#39;")

def clean_html_tags(text):
    if not text: return ""
    return re.sub('<[^>]+>', '', text).strip()

def check_if_important(text_to_check):
    if not text_to_check: return False
    lowercase_text = text_to_check.lower()
    for keyword in IMPORTANT_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', lowercase_text): return True
    return False

def is_duplicate_news(new_title):
    if not new_title: return False
    def clean_for_compare(t): return set(re.findall(r'\w+', t.lower()))
    new_words = clean_for_compare(new_title)
    if not new_words: return False
    now = datetime.now(IST)
    cutoff = now - timedelta(minutes=15)
    for n in reversed(rss_news_store):
        if isinstance(n, dict) and n.get('time') >= cutoff:
            existing_words = clean_for_compare(n.get('title', ''))
            if not existing_words: continue
            intersection = new_words.intersection(existing_words)
            smaller_len = min(len(new_words), len(existing_words))
            if smaller_len > 0:
                match_percentage = (len(intersection) / smaller_len) * 100
                if match_percentage >= 80: return True
    return False

# ==========================================================
# 💬 TELEGRAM MESSAGE SENDING HANDLERS
# ==========================================================
def send_long_message(chat_id, text, parse_mode='HTML'):
    if len(text) <= 3800:
        try: bot.send_message(chat_id, text, parse_mode=parse_mode, disable_web_page_preview=True)
        except Exception as e:
            log(f"⚠ HTML Parse Error, sending plain text: {e}", "WARNING")
            bot.send_message(chat_id, clean_html_tags(text))
        return

    lines = text.split('\n\n')
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 2 > 3800:
            try: bot.send_message(chat_id, current_chunk, parse_mode=parse_mode, disable_web_page_preview=True)
            except: bot.send_message(chat_id, clean_html_tags(current_chunk))
            current_chunk = line + '\n\n'
        else: current_chunk += line + '\n\n'
    if current_chunk:
        try: bot.send_message(chat_id, current_chunk, parse_mode=parse_mode, disable_web_page_preview=True)
        except: bot.send_message(chat_id, clean_html_tags(current_chunk))

def safe_send(msg, chat_id=CHAT_ID, parse_mode="HTML", disable_preview=True):
    MAX_LENGTH = 4000
    parts = [msg[i:i+MAX_LENGTH] for i in range(0, len(msg), MAX_LENGTH)] if len(msg) > MAX_LENGTH else [msg]
    for part in parts:
        for i in range(3):
            try:
                bot.send_message(chat_id, part, parse_mode=parse_mode, disable_web_page_preview=True)
                break
            except Exception as e:
                print(f"Retry {i+1}: {e}")
                time.sleep(3)

def send_vip_voice_alert(text, image_url=None, source_type="NORMAL"):
    if not VIP_CHAT_ID: return
    try:
        cleaned_msg_body = text
        bad_headers = ["🚨🚨 <b>IMPORTANT MARKET ALERT</b> 🚨🚨\n\n", "🚀 <b>IMPORTANT X UPDATE</b> 🚨\n\n", "👑 <b>[VIP PREMIUM ALERT]</b> 👑\n\n", "⚡ <b>🎯 30-MINUTES MARKET PULSE</b>", "🔔 <b>లైవ్ రిజల్ట్ అప్డేట్!</b>\n\n"]
        for header in bad_headers: cleaned_msg_body = cleaned_msg_body.replace(header, "")
        if cleaned_msg_body.startswith("📌 "): cleaned_msg_body = cleaned_msg_body.replace("📌 ", "", 1)

        clean_text = clean_html_tags(cleaned_msg_body)
        clean_text = re.sub(r'https?://\S+', '', clean_text)
        clean_text = re.sub(r'Read More in Telugu\s*\|\s*English Original', '', clean_text, flags=re.IGNORECASE)

        pure_speech_text = " ".join(re.findall(r'[\u0c00-\u0c7fa-zA-Z0-9\s\.\,\-\%]+', clean_text))
        pure_speech_text = re.sub(r'\s+', ' ', pure_speech_text).strip()
        if not pure_speech_text: return

        unique_id = datetime.now(IST).strftime('%H%M%S_%f')
        audio_file = f"vip_alert_{unique_id}.ogg"

        tts = gTTS(text=pure_speech_text, lang='te', slow=False)
        tts.save(audio_file)

        if source_type == "NORMAL": vip_header = "<b>🌍 NRSS</b>\n\n"
        elif source_type == "X": vip_header = "<b>🐦 XRSS</b>\n\n"
        elif "ECONOMIC" in source_type: vip_header = f"👑 <b>{source_type}</b>\n\n"
        else: vip_header = f"<b>👑 {source_type}</b>\n\n"

        final_vip_msg = f"{vip_header}{cleaned_msg_body}"

        if image_url and str(image_url).startswith('http'):
            try: bot.send_photo(VIP_CHAT_ID, image_url, caption=final_vip_msg[:1024], parse_mode='HTML')
            except Exception:
                try: bot.send_photo(VIP_CHAT_ID, image_url, caption=clean_html_tags(final_vip_msg)[:1024])
                except:
                    preview_msg = f'<a href="{image_url}"></a>{final_vip_msg}'
                    try: bot.send_message(VIP_CHAT_ID, preview_msg, parse_mode='HTML', disable_web_page_preview=False)
                    except: bot.send_message(VIP_CHAT_ID, clean_html_tags(preview_msg), disable_web_page_preview=False)
        else:
            try: send_long_message(VIP_CHAT_ID, final_vip_msg, parse_mode='HTML')
            except: send_long_message(VIP_CHAT_ID, clean_html_tags(final_vip_msg))

        if os.path.exists(audio_file):
            try:
                with open(audio_file, 'rb') as voice:
                    bot.send_voice(VIP_CHAT_ID, voice, caption="🎙 <b>[VIP PULSE VOICE]</b>", parse_mode='HTML')
                time.sleep(0.5)
                if os.path.exists(audio_file): os.remove(audio_file)
            except Exception as file_err: log(f"⚠ Voice file clean up handling: {file_err}", "WARNING")

        log(f"🚀 VIP {source_type} Alert Sent successfully.")
    except Exception as e: log(f"❌ VIP Alert Process Error: {e}", "ERROR")

def get_image_url(entry):
    try:
        if hasattr(entry, 'media_content') and entry.media_content:
            url = entry.media_content[0]['url']
            if str(url).startswith('http'): return url
        summary_raw = entry.get('summary') or entry.get('description') or ""
        soup = BeautifulSoup(str(summary_raw), 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            url = img['src']
            if str(url).startswith('http'): return url
        if hasattr(entry, 'links'):
            for link in entry.links:
                if 'image' in link.get('type', ''): return link.get('href')
    except: return None
    return None

def manage_memory():
    global rss_news_store
    if len(rss_news_store) > MAX_NEWS:
        rss_news_store = rss_news_store[CLEAR_COUNT:]
        log(f"✅ Memory cleaned.")

def auto_unpin_old_messages():
    global pinned_messages_store
    now = datetime.now(IST)
    cutoff_time = now - timedelta(days=2)
    remaining_pins = []
    for item in pinned_messages_store:
        if item["time"] < cutoff_time:
            try: bot.unpin_chat_message(CHAT_ID, item["message_id"])
            except Exception as e: log(f"⚠ Unpin Error: {e}", "WARNING")
        else: remaining_pins.append(item)
    pinned_messages_store = remaining_pins

# ==========================================================
# 🤖 AI ENGINE CLIENTS & METHODS
# ==========================================================
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def safe_gemini(prompt):
    if not client: return "AI Key Error"
    for i in range(3):
        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            return response.text
        except Exception as e:
            print(f"Gemini Retry {i+1}: {e}")
            time.sleep(5)
    return "AI అందుబాటులో లేదు"

def ask_gemini_raw(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200: return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: log(f"Gemini API Exception: {e}", "ERROR")
    return None

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def ask_groq_raw(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200: return response.json()['choices'][0]['message']['content']
    except Exception as e: print(f"Groq Exception: {str(e)}")
    return None

def get_groq_analysis(prompt_text):
    if not groq_client: return "Groq Client Not Init"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": f"మీరు ఒక స్టాక్ మార్కెట్ నిపుణుడు. ఈ డేటాను చదివి, చంటి గారికి అర్థమయ్యేలా 2-3 సులభమైన తెలుగు వాక్యాల్లో విశ్లేషణ ఇవ్వండి. మార్కెట్ పెరుగుతుందా లేదా తగ్గుతుందా అని చెప్పండి: {prompt_text}"}],
                model="llama-3.3-70b-versatile",
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            log(f"Groq AI Error (Attempt {attempt+1}): {e}")
            time.sleep(5)
    return "AI విశ్లేషణ ప్రస్తుతం అందుబాటులో లేదు."

def get_vip_event_better_summary(event_name, country, actual, estimate, previous):
    if not groq_client: return "ఆర్థిక ఈవెంట్ విశ్లేషణ ప్రస్తుతం అందుబాటులో లేదు."
    prompt = f"""
    You are an expert global macro hedge fund manager and analyst.
    Analyze this live economic calendar event and write a highly refined, professional summary in Telugu.
    Explain what this data means for the global or regional stock market, and whether it is positive, negative, or neutral for market volatility.

    Data Details:
    Event: {event_name}
    Country: {country}
    Actual Value: {actual}
    Expected Estimate: {estimate}
    Previous Value: {previous}

    Provide a robust 4-line breakdown in clean Telugu. No English text, no markdown.
    """
    try:
        completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"ఈవెంట్ విశ్లేషణ లోడింగ్ లోపం: {str(e)[:50]}"

# ==========================================================
# 📈 MARKET DATA ENGINE & GAP ALERTS
# ==========================================================
def is_market_open(name):
    now_ist = datetime.now(IST)
    if "Bitcoin" in name or "BTC" in name: return "🟢"
    if any(x in name for x in ["GIFT Nifty", "WTI Crude", "Brent", "Gold", "Silver"]): return "🟢"

    mapping = {
        "Nikkei": (JP, "09:00", "15:00"), "Hang Seng": (HK, "09:30", "16:00"),
        "DAX": (EU, "09:00", "17:30"), "FTSE": (EU, "08:00", "16:30"),
        "Dow": (US, "09:30", "16:00"), "Nasdaq": (US, "09:30", "16:00"),
        "S&P": (US, "09:30", "16:00"), "10Y": (US, "08:00", "17:00")
    }
    for key, (tz, start, end) in mapping.items():
        if key in name:
            now_local = now_ist.astimezone(tz).time()
            if datetime.strptime(start, "%H:%M").time() <= now_local < datetime.strptime(end, "%H:%M").time(): return "🟢"
            return "🔴"
    return "🔴"

def get_data(symbol):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}", headers=HEADERS, timeout=10)
        result = r.json()["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        if (price is None or price == 0) and "indicators" in result:
            closes = [c for c in result["indicators"]["quote"][0].get("close", []) if c]
            if closes: price = closes[-1]
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
        return price, prev_close
    except: return None, None

def check_gap_alert(name, price, prev_close, current_date):
    if not price or not prev_close: return
    gap_percent = ((price - prev_close) / prev_close) * 100
    gap_key = f"{name}_{current_date}_gap"
    if gap_key not in gap_alert_sent and abs(gap_percent) >= 1.0:
        direction = "📈 **GAP UP**" if gap_percent > 0 else "📉 **GAP DOWN**"
        safe_send(f"🚨 <b>GAP ALERT!</b>\n\n{name}\n{direction}: {gap_percent:+.2f}%\nCurrent: {price:.2f} | Prev Close: {prev_close:.2f}")
        gap_alert_sent[gap_key] = True

# ==========================================================
# 📅 NEW ECOCAL INTEGRATION - 100% FREE ECONOMIC CALENDAR 🎯
# ==========================================================
def fetch_economic_calendar_data(start_date, end_date):
    """ecocal package తో economic calendar data తీసుకోవడం - API key అక్కర్లేదు సర్"""
    global economic_calendar_cache
    cache_key = f"{start_date}_{end_date}"

    # Cache check - ఒకసారి తెచ్చిన data మళ్లీ scrape చేయకుండా
    if cache_key in economic_calendar_cache:
        log("📅 Economic calendar data from cache")
        return economic_calendar_cache[cache_key]

    try:
        log(f"📅 Fetching economic calendar from {start_date} to {end_date}...")
        # nbThreads=1 పెడితే 429 error రాదు సర్
        ec = Calendar(startHorizon=start_date, endHorizon=end_date, withDetails=True, nbThreads=1)
        df = ec.getCalendar()

        if df.empty:
            log("⚠ Economic calendar empty")
            return None

        # Cache లో save చేయండి
        economic_calendar_cache[cache_key] = df
        log(f"✅ Economic calendar loaded: {len(df)} events")
        return df

    except Exception as e:
        log(f"❌ Economic calendar fetch error: {e}", "ERROR")
        return None

def fetch_economic_calendar(days=1):
    """తదుపరి 24 గంటల్లో అన్ని ఈవెంట్స్ - Low/Medium/High అన్నీ"""
    try:
        now_ist = datetime.now(IST)
        start_datetime = now_ist
        end_datetime = now_ist + timedelta(hours=24)
        
        start_date = start_datetime.strftime('%Y-%m-%d')
        end_date = end_datetime.strftime('%Y-%m-%d')
        
        log(f"📅 Fetching 24hr calendar from {start_datetime.strftime('%Y-%m-%d %H:%M')} to {end_datetime.strftime('%Y-%m-%d %H:%M')}")
        
        df = fetch_economic_calendar_data(start_date, end_date)
        
        if df is None or df.empty:
            return "☀ <b>తదుపరి 24 గంటల్లో ఎటువంటి ఈవెంట్స్ లేవు చంటి గారు.</b>"
        
        # 🎯 FIX: UTC నుండి IST కి convert చేయండి
        df['DateTime'] = pd.to_datetime(df['Start'], format='%m/%d/%Y %H:%M:%S', errors='coerce', utc=True).dt.tz_convert(IST)
        
        # ఇప్పుడు రెండూ IST timezone లో ఉన్నాయి కాబట్టి compare అవుతుంది
        df = df[df['DateTime'] >= start_datetime]
        df = df[df['DateTime'] <= end_datetime]
        
        if df.empty:
            return "☀ <b>తదుపరి 24 గంటల్లో ఈవెంట్స్ ఏవీ లేవు చంటి గారు.</b>"
        
        # Impact wise sort - HIGH ముందు, తర్వాత MEDIUM, తర్వాత LOW
        impact_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        df['ImpactOrder'] = df['Impact'].str.upper().map(impact_order)
        df = df.sort_values(by=['ImpactOrder', 'DateTime'])
        
        report = f"📅 <b>తదుపరి 24 గంటల ఆర్థిక క్యాలెండర్</b>\n"
        report += f"🕒 {start_datetime.strftime('%d-%b %I:%M %p')} నుండి {end_datetime.strftime('%d-%b %I:%M %p')} వరకు\n\n"
        
        country_names = {
            'US': 'United States 🇺🇸', 'IN': 'India 🇮🇳', 'JP': 'Japan 🇯🇵', 
            'CN': 'China 🇨🇳', 'DE': 'Germany 🇩🇪', 'GB': 'UK 🇬🇧',
            'EU': 'Euro Zone 🇪🇺', 'AU': 'Australia 🇦🇺', 'CA': 'Canada 🇨🇦',
            'CH': 'Switzerland 🇨🇭', 'NZ': 'New Zealand 🇳🇿'
        }
        
        for _, row in df.iterrows():
            impact_val = str(row['Impact']).upper()
            if impact_val == 'HIGH':
                impact_icon = "🔴 High"
            elif impact_val == 'MEDIUM':
                impact_icon = "🟡 Medium"
            else:
                impact_icon = "⚪ Low"
                
            event_time = row['DateTime'].strftime('%d %b, %I:%M %p')
            telugu_name = translate_to_telugu(row['Name'])
            country = country_names.get(row['countryCode'], row['countryCode'])
            
            actual_val = row['actual'] if pd.notna(row['actual']) else "Waiting... ⏳"
            forecast_val = row['consensus'] if pd.notna(row['consensus']) else "N/A"
            prev_val = row['previous'] if pd.notna(row['previous']) else "N/A"
            
            report += f"📅 <b>{event_time}</b>\n"
            report += f"🌍 {country} | {row['Name']}\n"
            report += f"📝 <b>వివరణ:</b> {telugu_name}\n"
            report += f"✅ Actual: <b>{actual_val}</b> | Est: {forecast_val} | Prev: {prev_val}\n"
            report += f"🔥 ఇంపాక్ట్: {impact_icon}\n"
            report += "──────────────────\n\n"
        
        return report
        
    except Exception as e:
        log(f"❌ Calendar report error: {e}", "ERROR")
        return f"❌ సమస్య వచ్చింది: {str(e)[:150]}"
    
def check_for_live_updates():
    """Live economic calendar updates - ప్రతి నిమిషం check చేస్తుంది"""
    global last_sent_results
    try:
        today = datetime.now(IST).strftime('%Y-%m-%d')
        df = fetch_economic_calendar_data(today, today)

        if df is None or df.empty:
            return

        now_ist = datetime.now(IST)

        for _, row in df.iterrows():
            # High/Medium impact మాత్రమే
            if row['Impact'] not in ['High', 'Medium']:
                continue

            event_name = row['Event']
            country = row['Country']
            actual = str(row['Actual']) if row['Actual'] and str(row['Actual'])!= 'nan' else ""

            # Actual value వచ్చిందా check చేయండి
            if not actual or actual == 'nan' or actual == 'None':
                continue

            event_id = f"{event_name}_{country}_{today}"

            # Already sent అయితే skip చేయండి
            if event_id in last_sent_results:
                continue

            estimate = str(row['Forecast']) if row['Forecast'] and str(row['Forecast'])!= 'nan' else "N/A"
            prev = str(row['Previous']) if row['Previous'] and str(row['Previous'])!= 'nan' else "N/A"
            display_time = row['Time']

            # AI analysis
            ai_analysis = get_groq_analysis(f"Event: {event_name}, Actual: {actual}, Expected: {estimate}, Country: {country}")
            telugu_event_name = translate_to_telugu(event_name)

            msg = (
                f"🔔 <b>లైవ్ రిజల్ట్ అప్డేట్! ({country})</b>\n"
                f"──────────────────────\n"
                f"📊 <b>ఈవెంట్:</b> {event_name}\n"
                f"📝 <b>వివరణ:</b> {telugu_event_name}\n"
                f"🕒 <b>సమయం:</b> {display_time}\n\n"
                f"✅ <b>Actual:</b> <code>{actual}</code>\n"
                f"📉 <b>Expected:</b> {estimate}\n"
                f"🔄 <b>Previous:</b> {prev}\n"
                f"──────────────────────\n"
                f"🤖 <b>AI విశ్లేషణ:</b>\n{ai_analysis}"
            )
            safe_send(msg, chat_id=CHAT_ID)

            # VIP Alert
            if VIP_CHAT_ID:
                log(f"🚀 VIP Important Event Detected: {event_name}. Processing Audio Alert...")
                better_summary = get_vip_event_better_summary(event_name, country, actual, estimate, prev)

                vip_msg = (
                    f"🌍 <b>ఈవెంట్:</b> {event_name} ({country})\n"
                    f"📝 <b>వివరణ:</b> {telugu_event_name}\n"
                    f"🕒 <b>సమయం:</b> {display_time}\n\n"
                    f"✅ <b>Actual:</b> <code>{actual}</code> | Est: {estimate} | Prev: {prev}\n"
                    f"──────────────────────\n"
                    f"📊 <b>VIP ఎకనామిక్ డీప్ సమ్మరీ:</b>\n{better_summary}"
                )
                send_vip_voice_alert(vip_msg, image_url=None, source_type="📊 ECONOMIC UPDATE")

            last_sent_results.add(event_id)
            log(f"🎯 Live Alert Sent for {event_name}.")

    except Exception as e:
        log(f"❌ Live Economic Update Error: {e}", "ERROR")

# ==========================================================
# 🔄 LIVE RSS LOOPS & FEEDS
# ==========================================================
RSS_FEEDS = {
    "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
}

X_RSS_FEEDS = {
    "ET NOW (X)": "https://nitter.net/ETNOWlive/rss",
    "Redbox X": "https://nitter.net/REDBOXINDIA/rss"
}

def clean_x_text(text):
    junk = [r'http\S+', r'www\.\S+', r'@\w+', r'#\w+', r'⤵', r'\|']
    for p in junk: text = re.sub(p, '', text, flags=re.IGNORECASE)
    return clean_html_tags(re.sub(r'\s+', ' ', text).strip())

def fetch_normal_rss():
    log("🌍 NORMAL RSS STARTED...")
    while True:
        for name, url in RSS_FEEDS.items():
            try:
                res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                feed = feedparser.parse(res.content)
                if not feed.entries: continue

                for entry in feed.entries[:10]:
                    link = entry.get("link", "").strip()
                    title = clean_html_tags(entry.get("title", ""))
                    tel_title = translate(title)

                    if not link or link in sent_links or is_duplicate_news(tel_title) or is_duplicate_news(title): continue
                    sent_links.add(link)
                    
                    summary_raw = entry.get("summary") or entry.get("description") or ""
                    clean_desc = clean_html_tags(summary_raw).replace("\n", " ")
                    tel_desc = translate(clean_desc[:800])
                    
                    msg = (
                        f"📌 <b>{safe_html_text(tel_title)}</b>\n\n"
                        f"🇬🇧 <b>English Title:</b>\n{safe_html_text(title)}\n\n"
                        f"🇮🇳 <b>తెలుగు సమ్మరీ:</b>\n{safe_html_text(tel_desc)}\n\n"
                        f"🌐 <b>{safe_html_text(name)}</b>\n"
                        f'🔗 <a href="https://translate.google.com/translate?sl=en&tl=te&u={link}">Read More in Telugu</a> | <a href="{link}">English Original</a>'
                    )
                    ist_now = datetime.now(IST)
                    rss_news_store.append({"time": ist_now, "type": "NORMAL", "source": name, "title": tel_title, "desc": tel_desc, "link": link, "full_text": title + " " + clean_desc})
                    manage_memory()

                    try:
                        bot.send_message(CHAT_ID, msg, parse_mode='HTML', disable_web_page_preview=False)
                    except Exception as e: log(f"❌ Telegram error: {e}", "ERROR")
                    time.sleep(1)
            except Exception as e: log(f"❌ RSS Error {name}: {e}", "ERROR")
        time.sleep(120)

def fetch_x_rss():
    log("🐦 X RSS STARTED...")
    scraper = cloudscraper.create_scraper()
    while True:
        for name, url in X_RSS_FEEDS.items():
            try:
                res = scraper.get(url, timeout=20)
                if res.status_code != 200: continue
                feed = feedparser.parse(res.content)

                for entry in feed.entries[:5]:
                    link = entry.get("link", "").strip()
                    title = clean_x_text(entry.get("title", ""))
                    tel_title = translate(title)

                    if not link or link in sent_links or is_duplicate_news(tel_title) or is_duplicate_news(title): continue
                    sent_links.add(link)
                    
                    is_important = check_if_important(title) or check_if_important(tel_title)
                    g_trans_url = f"https://translate.google.com/translate?sl=en&tl=te&u={link}"

                    header = f"🚀 <b>{safe_html_text(name)} Update</b>\n\n"
                    msg = f"{header}📌 <b>{safe_html_text(tel_title)}</b>\n\n🇬🇧 {safe_html_text(title)}\n\n🔗 <a href='{g_trans_url}'>Read More in Telugu</a> | <a href='{link}'>English Original</a>"
                    
                    ist_now = datetime.now(IST)
                    rss_news_store.append({"time": ist_now, "type": "X", "source": name, "title": tel_title, "link": link})
                    manage_memory()

                    image_url = get_image_url(entry)
                    try:
                        if image_url:
                            try: sent_msg = bot.send_photo(CHAT_ID, image_url, caption=msg[:1024], parse_mode='HTML')
                            except Exception: sent_msg = bot.send_photo(CHAT_ID, image_url, caption=clean_html_tags(msg)[:1024])
                        else:
                            sent_msg = bot.send_message(CHAT_ID, msg, parse_mode='HTML', disable_web_page_preview=False)
                        
                        if is_important and VIP_CHAT_ID:
                            if name != "Redbox X":
                                log(f"🚀 VIP Important X Alert Triggered: {title}")
                                vip_msg = (
                                    f"📌 <b>{safe_html_text(tel_title)}</b>\n\n"
                                    f"🇬🇧 {safe_html_text(title)}\n\n"
                                    f"🔗 <a href='{g_trans_url}'>Read More in Telugu</a> | <a href='{link}'>English Original</a>"
                                )
                                send_vip_voice_alert(vip_msg, image_url=image_url, source_type="X")
                                
                                bot.pin_chat_message(CHAT_ID, sent_msg.message_id, disable_notification=False)
                                pinned_messages_store.append({"message_id": sent_msg.message_id, "time": ist_now})
                                auto_unpin_old_messages()
                                
                    except Exception as e: log(f"❌ X Telegram Error: {e}", "ERROR")
                    time.sleep(2)
            except Exception as e: log(f"❌ X RSS Error {name}: {e}", "ERROR")
        time.sleep(120)
        
# ==========================================================
# ⏱️ 30 MINUTE MARKET PULSE THREAD
# ==========================================================
def half_hourly_market_pulse_loop():
    global pulse_reports_store
    log("⏱️ 30 MINUTE AI SMART PULSE THREAD STARTED...")
    while True:
        now = datetime.now(IST)
        minutes_to_add = 30 - (now.minute % 30)
        next_run = (now + timedelta(minutes=minutes_to_add)).replace(second=0, microsecond=0)
        time.sleep((next_run - now).total_seconds())
        
        if not (6 <= next_run.hour <= 22) or (next_run.hour == 22 and next_run.minute > 0): continue
        time_str = next_run.strftime('%I:%M %p')
        night_notice = "\n\n🌙 <b>చంటి గారు, ఈరోజుకు ఆటోమేటిక్ పల్స్ రిపోర్ట్స్ పూర్తయ్యాయి. మళ్లీ రేపు ఉదయం 6:00 AM ki వస్తుంది సార్.</b>" if next_run.hour == 22 and next_run.minute == 0 else ""

        try:
            if next_run.hour == 6 and next_run.minute == 0:
                cutoff_time = next_run - timedelta(hours=10)
                intro_text = "(రాత్రి 08:00 PM నుండి ఉదయం 6:00 AM వరకు వచ్చిన కీలకమైన వార్తలు)"
                pulse_reports_store = []
            else:
                cutoff_time = next_run - timedelta(minutes=30)
                intro_text = "(గత 30 నిమిషాల అత్యంత కీలకమైన వార్తలు)"
            
            recent_news_for_ai = []
            news_lookup_dict = {} 
            for n in rss_news_store:
                if isinstance(n, dict) and n.get('time') >= cutoff_time and n.get('type') == "NORMAL":
                    eng_title = n.get('full_text', '').split("   ")[0]
                    recent_news_for_ai.append(f"ID: {len(recent_news_for_ai)} | Title: {eng_title}")
                    news_lookup_dict[str(len(recent_news_for_ai)-1)] = n

            if not recent_news_for_ai:
                no_news_msg = f"⚡ <b>🎯 30-MINUTES MARKET PULSE ({time_str})</b> ⚡\n📌 <b>మార్కెట్ అప్‌డేట్:</b> ఈ అరగంటలో కీలకమైన వార్తలు ఏవీ రాలేదు సార్.\n\n{night_notice}"
                bot.send_message(CHAT_ID, no_news_msg, parse_mode='HTML')
                if VIP_CHAT_ID: send_vip_voice_alert(no_news_msg, source_type="PULSE")
                continue

            pulse_filter_prompt = f"""
            You are an elite stock market filter bot. Review these news titles.
            Strictly REMOVE/IGNORE any cinema, movies, entertainment, celebrity gossip, or pop culture news.
            Keep ONLY high-quality corporate events, major company business updates, corporate deals, mergers, policy changes, national economy, and international financial macro news.
            Return ONLY a comma-separated list of the ID numbers that pass this filter.
            """
            ai_response = ask_groq_raw(pulse_filter_prompt + "\n".join(recent_news_for_ai))
            recent_important_news = []
            
            if ai_response and ai_response.strip():
                important_ids = re.findall(r'\d+', ai_response)
                for news_id in important_ids:
                    if news_id in news_lookup_dict:
                        n = news_lookup_dict[news_id]
                        raw_title = n.get('full_text', '').split("   ")[0]
                        
                        subject_match = re.search(r'\b[a-zA-Z0-9\s\&]+', raw_title)
                        if subject_match:
                            full_subject = subject_match.group(0).strip()
                            words = full_subject.split()
                            subject_title = " ".join(words[:3]) if len(words) > 3 else full_subject
                        else: subject_title = "Market Update"
                        
                        news_block = (
                            f"<b>{subject_title}:-</b>\n"
                            f"  {safe_html_text(n.get('title', ''))}\n"
                            f"<b>సమ్మరీ:-</b>\n"
                            f"  {safe_html_text(n.get('desc', ''))}"
                        )
                        recent_important_news.append(news_block)

            if not recent_important_news:
                no_news_msg = f"⚡ <b>🎯 30-MINUTES MARKET PULSE ({time_str})</b> ⚡\n📌 <b>మార్కెట్ అప్‌డేట్:</b> ఆర్థిక లేదా కార్పొరేట్ వార్తలు ఏవీ రాలేదు సార్.\n\n{night_notice}"
                bot.send_message(CHAT_ID, no_news_msg, parse_mode='HTML')
                if VIP_CHAT_ID: send_vip_voice_alert(no_news_msg, source_type="PULSE")
                continue

            recent_important_news = list(dict.fromkeys(recent_important_news))
            for block in recent_important_news: pulse_reports_store.append({"time": next_run, "block": block})

            pulse_body = "\n\n🔹🔹🔹\n\n".join(recent_important_news)
            full_report_msg = f"⚡ <b>🎯 30-MINUTES MARKET PULSE ({time_str})</b> ⚡\n{intro_text}\n\n{pulse_body}{night_notice}"
            
            send_long_message(CHAT_ID, full_report_msg, parse_mode='HTML')
            if VIP_CHAT_ID: send_vip_voice_alert(full_report_msg, source_type="PULSE")
        except Exception as e: log(f"❌ Pulse Error: {e}", "ERROR")

def send_market_table():
    table_content = f"{'-' * 52}\n"
    table_content += f"{'Mkt':<14} {'Price':>9} {'+/-Pts':>8} {'%':>6} {'Trnd':>4}\n"
    table_content += f"{'-' * 52}\n"
    current_date = datetime.now(IST).date()
    
    for name, sym in symbols.items():
        price, prev_close = get_data(sym)
        if price and prev_close:
            diff = price - prev_close
            change = (diff / prev_close) * 100
            check_gap_alert(name, price, prev_close, current_date)
            trend = "📈" if change > 0.3 else ("📉" if change < -0.3 else "➖")
            status = is_market_open(name)
            short_name = name.split(' (')[0][:11]
            table_content += f"{status}{short_name:<12} {price:>9.1f} {diff:>8.1f} {change:>5.1f}% {trend:>2}\n"
    try: safe_send(f"📊 <b>Global Market Live</b>\n<pre>{table_content}</pre>")
    except Exception as e: print(e)

# ==========================================================
# ⚙️ QUEUE AND SECONDARY TASKS LOOPS
# ==========================================================
def ai_worker():
    while True:
        text, chat_id = ai_queue.get()
        try:
            res_text = safe_gemini(f"Explain this news in 6 lines Telugu: {text}")
            safe_send(f"🧠 <b>AI విశ్లేషణ:</b>\n{res_text}", chat_id=chat_id)
        except: pass
        ai_queue.task_done()
        time.sleep(10)

def main_loop():
    global last_reset_date
    while True:
        try:
            now_ist_str = datetime.now(IST).strftime("%H:%M")
            current_date = datetime.now(IST).date()
            if current_date > last_reset_date:
                sent_alerts.clear()
                sudden_move_sent.clear()
                gap_alert_sent.clear()
                collected_news.clear()
                last_sent_results.clear()
                last_reset_date = current_date
                log("🔄 కొత్త రోజు ప్రారంభమైంది: డేటా రీసెట్ చేయబడింది.")

            for m_name, (o_time, _) in TIMINGS.items():
                alert_id = f"{m_name}_{current_date}"
                if now_ist_str == o_time and alert_id not in sent_alerts:
                    safe_send(f"🔔 <b>MARKET OPEN ALERT</b>\n\n🚀 {m_name} ప్రారంభమైంది! (IST: {o_time})")
                    sent_alerts[alert_id] = True 

            for name, sym in symbols.items():
                if is_market_open(name) == "🟢":
                    price, prev_close = get_data(sym)
                    if price and prev_close:
                        diff = price - prev_close
                        change = (diff / prev_close) * 100
                        check_gap_alert(name, price, prev_close, current_date) 
                        if abs(change) >= 1.50 and f"{name}_{current_date}_mv" not in sudden_move_sent:
                            safe_send(f"🚨 <b>VOLATILITY ALERT!</b>\n{name}: {change:.2f}% భారీ మార్పు!")
                            sudden_move_sent[f"{name}_{current_date}_mv"] = True 

            for f_url in news_feeds:
                feed = feedparser.parse(f_url)
                for e in feed.entries[:3]:
                    if e.title not in sent_news:
                        sent_news.add(e.title)
                        collected_news.append(e.title) 
                        if len(collected_news) > 30: collected_news.pop(0) 
                        translated = translate_to_telugu(e.title)
                        safe_send(f"🌍 <b>{translated}</b>\n\n🌐 {e.title}\n🔗 <a href='{e.link}'>పూర్తి వార్త</a>", disable_preview=True)
                        if any(k in e.title.lower() for k in ["fed", "war", "oil", "inflation", "cpi", "rate cut"]):
                            ai_queue.put((e.title, CHAT_ID)) 
        except Exception as e: print(f"Error in global loop: {e}")
        gc.collect() 
        time.sleep(60)

def calculate_historical_target_time(hour_input):
    now = datetime.now(IST)
    target = now.replace(hour=hour_input, minute=0, second=0, microsecond=0)
    if hour_input >= now.hour: target = target - timedelta(days=1)
    return target

# ==========================================================
# 🤖 TELEGRAM BOT COMMAND HANDLERS
# ==========================================================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    safe_send("🚀 <b>బాట్ రెడీ చంటి గారు! అన్ని ఫిల్టర్స్ లోడ్ అయ్యాయి.</b>", chat_id=message.chat.id)

def trigger_all_pulse_history_logic(chat_id_to_send):
    global pulse_reports_store
    try:
        now = datetime.now(IST)
        today_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
        filtered_blocks = [p for p in pulse_reports_store if p["time"] >= today_6am]
        
        if not filtered_blocks:
            safe_send("⏳ <b>చంటి గారు, ఈరోజు ఉదయం 6:00 AM నుండి ఇప్పటివరకు ఎటువంటి మార్కెట్ పల్స్ వార్తలు రికార్డ్ అవ్వలేదు సార్.</b>", chat_id=chat_id_to_send)
            return
            
        unique_blocks = list(dict.fromkeys([p["block"] for p in filtered_blocks]))
        time_now_str = now.strftime('%I:%M %p')
        
        report_header = (
            f"📋 <b>MARKET ALL PULSE HISTORY (మొత్తం వార్తలు)</b> 📋\n"
            f"📅 <b>సమయం:</b> ఉదయం 06:00 AM నుండి ఇప్పటివరకు ({time_now_str})\n"
            f"──────────────────────"
        )
        safe_send(report_header, chat_id=chat_id_to_send)
        
        for block in unique_blocks:
            safe_send(block, chat_id=chat_id_to_send)
            time.sleep(0.3)
            
        bot.send_message(chat_id_to_send, "🔍 <b>ఇప్పుడు ఈ లిస్ట్ నుండి అతి ముఖ్యమైన వార్తలను ఏఐ చాలా లోతుగా విశ్లేషించి విడదీస్తోంది...</b>", parse_mode='HTML')
        
        history_payload = ""
        for idx, block in enumerate(unique_blocks):
            clean_block = clean_html_tags(block).replace('\n', ' ')
            history_payload += f"INDEX: {idx} | {clean_block}\n"
            
        prompt = f"""
        You are an expert financial filter. Look at today's corporate pulse.
        Select only 5 to 8 extremely critical, market-shaping, company-deal breaking news.
        Return ONLY a comma-separated list of INDEX numbers.
        """
        ai_response = ask_groq_raw(prompt + f"\n\nDATA:\n{history_payload}")
        selected_critical_blocks = []
        if ai_response and ai_response.strip():
            important_indexes = re.findall(r'\d+', ai_response)
            for index_str in important_indexes:
                idx = int(index_str)
                if 0 <= idx < len(unique_blocks): selected_critical_blocks.append(unique_blocks[idx])
                    
        if not selected_critical_blocks: selected_critical_blocks = unique_blocks[:5]
            
        critical_header = f"💥 <b>ఈరోజు వచ్చిన పల్స్ లిస్ట్‌లో అతి ముఖ్యమైనవి (AI డీప్ ఫిల్టర్డ్):</b> 💥\n──────────────────────"
        safe_send(critical_header, chat_id=chat_id_to_send)
        
        for block in selected_critical_blocks:
            safe_send(block, chat_id=chat_id_to_send)
            time.sleep(0.3)
            
        end_note = (
            f"╔════════════════════════╗\n"
            f"    🔚 <b>ALL PULSE COMPLETED</b> 📊\n"
            f"╚════════════════════════╝\n"
            f"📌 <i>చంటి గారు, రోజంతటి మొత్తం పల్స్ హిస్టరీ లిస్ట్ ఇక్కడితో పూర్తయింది సార్!</i>"
        )
        safe_send(end_note, chat_id=chat_id_to_send)
        log("🚀 Complete Pulse List Sent via Separate Messages successfully.")
    except Exception as e:
        log(f"❌ All Pulse History Logic Error: {e}", "ERROR")
        
@bot.message_handler(commands=['allpulsehistory'])
def unified_all_pulse_history_command(message):
    args = message.text.split()
    if len(args) >= 2 and args[1].isdigit():
        hour = int(args[1])
        target_time = calculate_historical_target_time(hour)
        
        raw_date_part = target_time.strftime('%d-%m-%Y')
        clean_date_part = "-".join([str(int(x)) for x in raw_date_part.split('-')])
        time_part = target_time.strftime('%I %p').lstrip('0')
        cutoff_display_str = f"{clean_date_part} {time_part}"

        log(f"🔮 Manual Pulse History triggered via command for past {hour} hours...")
        bot.send_message(message.chat.id, f"⚡ <b>గత {hour} గంటల నుండి ({cutoff_display_str}) వచ్చిన మొత్తం పల్స్ డేటాను ఏఐ విశ్లేషిస్తోంది... సార్</b>", parse_mode='HTML')
        
        valid_news = [n for n in rss_news_store if isinstance(n, dict) and n.get('time') >= target_time]
        if not valid_news:
            bot.send_message(message.chat.id, f"⏳ ఈ సమయం ({cutoff_display_str}) నుండి ఎటువంటి వార్తలు స్టోర్‌లో లేవు సార్.", parse_mode='HTML')
            return

        normal_rss_count = 0
        redbox_count = 0
        x_count = 0
        ai_payload = ""

        for idx, n in enumerate(valid_news):
            ntype = n.get('type', 'NORMAL')
            src = n.get('source', '')
            if ntype == 'NORMAL': normal_rss_count += 1
            elif src == 'Redbox X': redbox_count += 1
            elif ntype == 'X': x_count += 1
            ai_payload += f"INDEX: {idx} | Source: {src if src else ntype} | Title: {n['title']}\n"

        prompt = f"""
        You are an expert market analyst. Review the following {len(valid_news)} recent financial news items items fetched since {cutoff_display_str}.
        Identify only the highly critical, index-moving, or mega corporate events.
        Return ONLY a comma-separated list of the INDEX numbers that represent these critical updates. Keep it clean.
        """
        ai_response = ask_groq_raw(prompt + f"\n\nLIST:\n{ai_payload}")
        
        selected_critical_blocks = []
        if ai_response and ai_response.strip():
            important_indexes = re.findall(r'\d+', ai_response)
            critical_counter = 1
            for index_str in important_indexes:
                idx = int(index_str)
                if 0 <= idx < len(valid_news):
                    n = valid_news[idx]
                    src = n.get('source', 'NORMAL')
                    
                    if n.get('type') == "NORMAL":
                        raw_title = n.get('full_text', '').split("   ")[0]
                        subject_match = re.search(r'\b[a-zA-Z0-9\s\&]+', raw_title)
                        subject_title = subject_match.group(0).strip() if subject_match else "Market Update"
                        g_url = f"https://translate.google.com/translate?sl=en&tl=te&u={n.get('link','')}"
                        
                        block = (
                            f"💥 <b>ముఖ్యమైన వార్త #{critical_counter} ({src}):-</b>\n"
                            f"  <b>{subject_title}:-</b>\n"
                            f"  {safe_html_text(n['title'])}\n\n"
                            f"🔗 <a href='{g_url}'>Read More in Telugu</a> | <a href='{n.get('link','')}'>English Original</a>"
                        )
                    else:
                        icon = "🚩" if src == "Redbox X" else "🐦"
                        block = f"{icon} <b>ముఖ్యమైన వార్త #{critical_counter} ({src})</b>\n\n<b>{safe_html_text(n['title'])}</b>"
                    
                    selected_critical_blocks.append(block)
                    critical_counter += 1

        bot.send_message(message.chat.id, f"📊 <b>పల్స్ రిపోర్ట్ సమ్మరీ (గత {hour} గంటలు):</b>\n──────────────────────\n🕒 Normal RSS: {normal_rss_count}\n🚩 Redbox: {redbox_count}\n🐦 X RSS: {x_count}\n🔥 AI క్రిటికల్: {len(selected_critical_blocks)}\n──────────────────────", parse_mode='HTML')
        
        if selected_critical_blocks:
            bot.send_message(message.chat.id, f"💥 <b>అతి ముఖ్యమైన వార్తలు (AI ఫిల్టర్డ్):</b> 💥\n──────────────────────", parse_mode='HTML')
            for block in selected_critical_blocks:
                safe_send(block, chat_id=message.chat.id, disable_preview=True)
                time.sleep(0.3)
        else:
            bot.send_message(message.chat.id, "✨ ఈ టైమ్ విండోలో అంత ఆందోళనకరమైన లేదా అతి ముఖ్యమైన వార్తలు ఏవీ లేవు సార్.", parse_mode='HTML')

    else:
        log("🕒 No hours specified. Running original 6:00 AM pulse history logic...")
        trigger_all_pulse_history_logic(message.chat.id)

@bot.message_handler(commands=['summary'])
def summary(message):
    normal_news = [n['full_text'] for n in rss_news_store if isinstance(n, dict) and n.get('type') == "NORMAL"]
    if not normal_news:
        bot.reply_to(message, "⚠️ విశ్లేషించడానికి Normal RSS వార్తలు లేవు.")
        return
    args = message.text.split()
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    per_page = 50
    total_pages = (len(normal_news) + per_page - 1) // per_page
    if page > total_pages: return

    sliced_news = list(reversed(normal_news))[(page - 1) * per_page : page * per_page]
    bot.send_message(CHAT_ID, f"🔍 AI విశ్లేషణ జరుగుతోంది - పేజీ: {page}/{total_pages}...")
    response_text = ask_gemini_raw(f"Analyze each news separately and organize into 4 sections in Telugu. No markdown.\nDATA:\n" + "\n".join(sliced_news))
    if response_text: send_long_message(CHAT_ID, f"📊 <b>AI విశ్లేషణ (Normal RSS) - పేజీ: {page}/{total_pages}</b>\n\n" + safe_html_text(response_text), parse_mode='HTML')

@bot.message_handler(commands=['globalsummary'])
def global_summary(message):
    safe_send("⏳ గ్లోబల్ వార్తలను విశ్లేషిస్తున్నాను...", chat_id=message.chat.id)
    if not collected_news:
        safe_send("వార్తలు లేవు.", chat_id=message.chat.id)
        return
    res_text = safe_gemini(f"క్రిింది సమాచారాన్ని విశ్లేషించి, స్పష్టమైన తెలుగులో పూర్తి గ్లోబల్ మార్కెట్ సమరీ ఇవ్వండి:\n {' '.join(collected_news[-10:])}")
    safe_send(f"📊 <b>గ్లోబల్ మార్కెట్ రిపోర్ట్:</b>\n\n{res_text}", chat_id=message.chat.id)

@bot.message_handler(commands=['summaryred'])
def redbox_summary(message):
    args = message.text.split()
    hour = int(args[1]) if len(args) > 1 and args[1].isdigit() else 6
    target_time = calculate_historical_target_time(hour)
    filtered_news = [f"Title: {n['title']}" for n in rss_news_store if isinstance(n, dict) and n.get('source') == "Redbox X" and n.get('time') >= target_time]
    if not filtered_news:
        bot.reply_to(message, f"⚠️ {hour}:00 నుండి ఎటువంటి Redbox వార్తలు లేవు సార్.")
        return
    bot.send_message(message.chat.id, f"🚩 Redbox గ్లోబల్ వార్తలను AI విశ్లేషిస్తోంది...")
    prompt = f"You are a macro trader. Process corporate flashes, insights, visual gap in Telugu format strictly. DATA:\n" + "\n".join(filtered_news[-10:])
    response_text = ask_gemini_raw(prompt)
    if response_text: send_long_message(message.chat.id, f"🚩 <b>Smart AI Insights (ONLY REDBOX)</b>\n\n" + response_text, parse_mode='HTML')

@bot.message_handler(commands=['today', 'events'])
def handle_calendar_commands(message):
    days = 1 if 'today' in message.text else 7
    bot.reply_to(message, "⏳ ఆర్థిక క్యాలెండర్ లోడ్ అవుతోంది, దయచేసి వేచి ఉండండి...")
    calendar_report = fetch_economic_calendar(days)
    send_long_message(message.chat.id, calendar_report, parse_mode='HTML')
    
@bot.message_handler(commands=['getxvoice'])
def get_x_news_voice_summary(message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        bot.reply_to(message, "📌 చంటి గారు, దయచేసి కమాండ్ పక్కన గంటల నంబర్ ఇవ్వండి సార్. ఉదాహరణకు: <code>/getxvoice 2</code>", parse_mode='HTML')
        return
    
    hour = int(args[1])
    target_time = calculate_historical_target_time(hour)
    
    raw_date_part = target_time.strftime('%d-%m-%Y')
    clean_date_part = "-".join([str(int(x)) for x in raw_date_part.split('-')])
    time_part = target_time.strftime('%I %p').lstrip('0')
    cutoff_display_str = f"{clean_date_part} {time_part}"
    
    log(f"🎙️ Manual X Voice Summary triggered via command for past {hour} hours...")
    bot.send_message(message.chat.id, f"⏳ <b>గత {hour} గంటల నుండి ({cutoff_display_str}) వచ్చిన X RSS వార్తల లిస్ట్ మరియు వాయిస్ నోట్ సిద్ధమౌతోంది సార్...</b>", parse_mode='HTML')

    filtered = [n for n in rss_news_store if isinstance(n, dict) and n.get('time') >= target_time and n.get('type') == "X" and n.get('source') != "Redbox X"]
    
    if not filtered:
        bot.send_message(message.chat.id, f"⏳ ఈ సమయం ({cutoff_display_str}) నుండి ఎటువంటి X RSS వార్తలు రికార్డ్ అవ్వలేదు సార్.", parse_mode='HTML')
        return
        
    filtered.sort(key=lambda x: x['time'], reverse=True)
    
    combined_text_message = f"🐦 <b>X RSS Voice Summary ({cutoff_display_str} నుండి ఇప్పటివరకు):</b>\n──────────────────────\n"
    voice_speech_text = f"చంటి గారు, గత {hour} గంటలలో ఎక్స్ ప్లాట్‌ఫారమ్ నుండి వచ్చిన ముఖ్యమైన వార్తల వివరాలు."
    
    for i, n in enumerate(filtered, 1):
        news_title = clean_html_tags(n['title'])
        combined_text_message += f"🔹 <b>News #{i}:</b> {safe_html_text(news_title)}\n\n"
        voice_speech_text += f" వార్త నంబర్ {i}. {news_title}. "

    send_long_message(message.chat.id, combined_text_message, parse_mode='HTML')

    try:
        voice_speech_text = re.sub(r'https?://\S+', '', voice_speech_text)
        pure_voice_text = " ".join(re.findall(r'[\u0c00-\u0c7fa-zA-Z0-9\s\.\,\-\%]+', voice_speech_text))
        pure_voice_text = re.sub(r'\s+', ' ', pure_voice_text).strip()
        
        if pure_voice_text:
            unique_id = datetime.now(IST).strftime('%H%M%S')
            audio_file = f"x_voice_{unique_id}.ogg"
            
            tts = gTTS(text=pure_voice_text, lang='te', slow=False)
            tts.save(audio_file)
            
            if os.path.exists(audio_file):
                with open(audio_file, 'rb') as voice:
                    bot.send_voice(message.chat.id, voice, caption=f"🎙️ <b>గత {hour} గంటల X RSS ఆడియో పల్స్ రిపోర్ట్</b>", parse_mode='HTML')
                time.sleep(0.5)
                if os.path.exists(audio_file): os.remove(audio_file)
            log("🚀 /getxvoice command processed and audio sent successfully.")
    except Exception as voice_err:
        log(f"❌ Command Voice Process Error: {voice_err}", "ERROR")
        
@bot.message_handler(commands=['getredvoice'])
def get_redbox_voice_summary(message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        bot.reply_to(message, "📌 దయచేసి కమాండ్ పక్కన గంటల నంబర్ ఇవ్వండి చంటి గారు. ఉదాహరణకు: <code>/getredvoice 2</code>", parse_mode='HTML')
        return
    
    hour = int(args[1])
    target_time = calculate_historical_target_time(hour)
    
    raw_date_part = target_time.strftime('%d-%m-%Y')
    clean_date_part = "-".join([str(int(x)) for x in raw_date_part.split('-')])
    time_part = target_time.strftime('%I %p').lstrip('0')
    cutoff_display_str = f"{clean_date_part} {time_part}"
    
    log(f"🎙️ Manual Redbox Short Voice Summary triggered for past {hour} hours...")
    bot.send_message(message.chat.id, f"⏳ <b>గత {hour} గంటల Redbox ఫ్లాషెస్ ని ఏఐ సింగిల్ లైన్ లోకి మారుస్తోంది... సార్</b>", parse_mode='HTML')

    redbox_news = [n for n in rss_news_store if isinstance(n, dict) and n.get('time') >= target_time and n.get('source') == "Redbox X"]
    
    if not redbox_news:
        bot.send_message(message.chat.id, f"⏳ ఈ సమయం ({cutoff_display_str}) నుండి ఎటువంటి Redbox వార్తలు స్టోర్‌లో లేవు సార్.", parse_mode='HTML')
        return
        
    raw_payload = ""
    for idx, n in enumerate(redbox_news):
        raw_payload += f"- {n['title']}\n"
        
    gemini_prompt = f"""
    You are a fast market data parser. 
    Combine the following raw financial flashes from Redbox. Many flashes belong to the same company (revenue, profit, margins).
    For each unique company or major news event, provide ONLY a single-line summary in simple Telugu.
    
    Format like this:
    - Company Name: Main Event (Positive/Negative/Neutral for stock)
    
    CRITICAL FORMATTING RULE: Put a blank newline space (double enter) between each company bullet point so it looks clean and separated. Do not bunch them together.
    Strictly keep it to 1 short line per company. No long explanations. Do not use Markdown like asterisks or hashtags.
    
    DATA:
    {raw_payload}
    """
    
    ai_analysis_text = ask_gemini_raw(gemini_prompt)
    if not ai_analysis_text or ai_analysis_text.strip() == "" or "AI అందుబాటులో లేదు" in ai_analysis_text:
        ai_analysis_text = safe_gemini(gemini_prompt)

    report_header = (
        f"🚩 <b>REDBOX 1-LINE AI SUMMARY ({cutoff_display_str} నుండి):</b>\n"
        f"──────────────────────\n\n"
    )
    
    final_text_message = report_header + ai_analysis_text
    send_long_message(message.chat.id, final_text_message, parse_mode='HTML')

    try:
        clean_voice_text = clean_html_tags(ai_analysis_text)
        clean_voice_text = re.sub(r'https?://\S+', '', clean_voice_text)
        pure_voice_text = " ".join(re.findall(r'[\u0c00-\u0c7fa-zA-Z0-9\s\.\,\-\%]+', clean_voice_text))
        pure_voice_text = re.sub(r'\s+', ' ', pure_voice_text).strip()
        
        voice_intro = f"చంటి గారు, గత {hour} గంటల రెడ్‌బాక్స్ ముఖ్యాంశాలు. "
        final_speech_text = voice_intro + pure_voice_text
        
        if pure_voice_text:
            unique_id = datetime.now(IST).strftime('%H%M%S')
            audio_file = f"red_short_{unique_id}.ogg"
            
            tts = gTTS(text=final_speech_text, lang='te', slow=False)
            tts.save(audio_file)
            
            if os.path.exists(audio_file):
                with open(audio_file, 'rb') as voice:
                    bot.send_voice(message.chat.id, voice, caption=f"🎙️ <b>రెండు గంటల రెడ్‌బాక్స్ షార్ట్ వాయిస్ రిపోర్ట్ ({hour} Hours)</b>", parse_mode='HTML')
                time.sleep(0.5)
                if os.path.exists(audio_file): os.remove(audio_file)
            log("🚀 /getredvoice command processed successfully.")
    except Exception as voice_err:
        log(f"❌ Redbox Voice Process Error: {voice_err}", "ERROR")

# ==========================================================
# ⏱️ 3-IN-1 MASTER COMMAND: /get, /getx, /getred (ఇంగ్లీష్ సోది రహిత పక్కా కోడ్ 🚀)
# ==========================================================
@bot.message_handler(commands=['get', 'getx', 'getred'])
def get_news_by_time_master(message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        cmd = message.text.split()[0]
        bot.reply_to(message, f"📌 దయచేసి కమాండ్ పక్కన గంటల నంబర్ ఇవ్వండి చంటి గారు. ఉదాహరణకు: <code>{cmd} 2</code>", parse_mode='HTML')
        return

    hour = int(args[1])
    target_time = calculate_historical_target_time(hour)

    raw_date_part = target_time.strftime('%d-%m-%Y')
    clean_date_part = "-".join([str(int(x)) for x in raw_date_part.split('-')])
    time_part = target_time.strftime('%I %p').lstrip('0')
    cutoff_display_str = f"{clean_date_part} {time_part}"

    source_type = "NORMAL"
    if 'getred' in message.text: source_type = "REDBOX"
    elif 'getx' in message.text: source_type = "X"

    # డేటా ఫిల్టరింగ్
    filtered = []
    for n in rss_news_store:
        if isinstance(n, dict) and n.get('time') >= target_time:
            if source_type == "REDBOX" and n.get('source') == "Redbox X":
                filtered.append(n)
            elif source_type == "X" and n.get('type') == "X" and n.get('source')!= "Redbox X":
                filtered.append(n)
            elif source_type == "NORMAL" and n.get('type') == "NORMAL":
                filtered.append(n)

    # 🎯 లేటెస్ట్ ఫస్ట్
    filtered.sort(key=lambda x: x['time'], reverse=True)

    if not filtered:
        bot.send_message(message.chat.id, f"⏳ ఈ సమయం ({cutoff_display_str}) నుండి ఎటువంటి వార్తలు లేవు సార్.")
        return

    # 🎯 SIMPLE SUBJECT GROUPING - First 3 words match
    grouped = {}
    for item in filtered:
        title = item.get('title', '').lower()
        words = title.split()[:3] # మొదటి 3 words
        subject_key = ' '.join(words) if words else 'general'

        if subject_key not in grouped:
            grouped[subject_key] = []
        grouped[subject_key].append(item)

    # 🎯 SIMPLE FORMAT లో SEND చేయి - మీ Screenshot లాగా
    news_counter = 1
    for subject_key, items in grouped.items():
        for n in items:
            news_time = n['time'].strftime('%H:%M') # 15:24 లాగా

            # English Title
            eng_title = n.get('title', '')

            # Telugu Title - Google Translator
            try:
                tel_title = GoogleTranslator(source='auto', target='te').translate(eng_title)
            except:
                tel_title = eng_title

            # Description ఉంటే
            desc = ""
            if source_type == "NORMAL" and n.get('desc'):
                try:
                    tel_desc = GoogleTranslator(source='auto', target='te').translate(n.get('desc', '')[:400])
                    desc = f"\n\n{tel_desc}"
                except:
                    desc = f"\n\n{n.get('desc', '')[:400]}"

            # 🎯 మీ Screenshot Format
            msg = f"<b>News #{news_counter}</b>\n\n{safe_html_text(tel_title)}{desc}\n\n{news_time}"

            bot.send_message(message.chat.id, msg, parse_mode='HTML', disable_web_page_preview=True)
            news_counter += 1
            time.sleep(0.3)

    bot.send_message(message.chat.id, f"──────────────────────\n📌 <b>మొత్తం వార్తలు: {len(filtered)}</b>\n\n<i>చంటి గారు, అన్ని వార్తలు ఇక్కడితో విజయవంతంగా వచ్చేశాయి సార్!</i>", parse_mode='HTML')

def get_commands_list_text():
    return ("╔════════════════════════╗\n    🤖  <b>MARKET BOT COMMANDS</b>    📊\n╚════════════════════════╝\n\n"
            "🧠 <b>AI SMART SUMMARIES</b>\n🔹 <code>/summary [page]</code>\n🔹 <code>/globalsummary</code> (Global Market)\n🔹 <code>/summaryred [hour]</code>\n"
            "🌟 <code>/allpulsehistory</code> (అన్ని వార్తలు + అతి ముఖ్యమైనవి 🚀)\n\n"
            "📅 <b>ECONOMIC CALENDARS</b>\n🔹 <code>/today</code>\n🔹 <code>/events</code>\n\n"
            "⏱ <b>FETCH NEWS BY HOUR</b>\n🔸 <code>/get [hour]</code>\n🔸 <code>/getx [hour]</code>\n🔸 <code>/getred [hour]</code>\n"
            "🎙️ <b>NEW AUDIO PULSE</b>\n🔸 <code>/getxvoice [hour]</code> (X లిస్ట్ + వాయిస్ నోట్ 🎧)\n"
            "🚩 <code>/getredvoice [hour]</code> (రెడ్‌బాక్స్ కంబైన్డ్ ఏఐ విశ్లేషణ + వాయిస్ 🎙️)\n"
            "──────────────────────\n📌 <i>చంటి గారు, కమాండ్ కాపీ చేయడానికి Tap చేయండి!</i>")
    
@bot.message_handler(commands=['list'])
def list_commands(message): safe_send(get_commands_list_text(), chat_id=message.chat.id)

# ==========================================================
# ⏱️ SMART DYNAMIC ALERTS ENGINE & SERVER (429 ని ఆపే పక్కా ప్లాన్ 🚀)
# ==========================================================
job_defaults = {
    'misfire_grace_time': 900,
    'coalesce': True,
    'max_instances': 3
}
scheduler = BackgroundScheduler(timezone="Asia/Kolkata", job_defaults=job_defaults)

# ఈరోజు ఉన్న లైవ్ ఈవెంట్స్ యొక్క ఒరిజినల్ టైమింగ్స్ స్టోర్ చేయడానికి గ్లోబల్ లిస్ట్ సార్
today_active_event_windows = []

def schedule_today_live_events():
    """
    ఉదయం రన్ అయ్యి, ఈరోజు ఏ ఏ సమయాల్లో హై/మీడియం ఈవెంట్స్ ఉన్నాయో 
    వాటి టైమ్ విండోస్ ని ముందే పక్కాగా నోట్ చేసి పెట్టుకుంటుంది సార్.
    """
    global today_active_event_windows
    log("🔮 Loading Today's Live Event Windows Dynamically...")
    
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        if res.status_code != 200: return
        
        events = res.json()
        now_ist = datetime.now(IST)
        today_str = now_ist.strftime('%Y-%m-%d')
        
        today_active_event_windows.clear()
        
        for item in events:
            impact_level = item.get('impact', '').lower()
            if impact_level not in ['high', 'medium']: continue
            
            full_date_raw = item.get('date', '')
            clean_date = full_date_raw.split('T')[0] if 'T' in full_date_raw else full_date_raw
            
            # కేవలం ఈరోజు ఈవెంట్స్ మాత్రమే చూస్తాం
            if clean_date != today_str: continue
            
            event_time_raw = item.get("time", "").strip()
            if not event_time_raw or event_time_raw.lower() in ["all day", "tentative"]: continue
            
            try:
                dt_obj = datetime.fromisoformat(full_date_raw)
                event_ist = dt_obj.astimezone(IST)
                
                # 🎯 ఈవెంట్ కి 10 నిమిషాల ముందు నుండి, జరిగిన 25 నిమిషాల తర్వాత వరకు విండో లాక్ సార్!
                # దీనివల్ల వాడు 7:30 ఈవెంట్ ని 7:32 కి అప్‌డేట్ చేసినా బాట్ అస్సలు మిస్ చేయదు.
                start_check = event_ist - timedelta(minutes=10)
                end_check = event_ist + timedelta(minutes=25)
                
                today_active_event_windows.append((start_check, end_check, item.get("title", "")))
                log(f"📅 Locked Window for {item.get('title')}: {start_check.strftime('%H:%M')} to {end_check.strftime('%H:%M')} IST")
            except:
                continue
    except Exception as e:
        log(f"❌ Error in Loading Windows: {e}", "ERROR")

def smart_live_checker_master():
    """
    ప్రతి 1 నిమిషానికి ఒకసారి బ్యాక్‌గ్రౌండ్ లో రన్ అవుతుంది చంటి గారు. 
    ప్రస్తుత టైమ్ ఏదైనా ఈవెంట్ విండో లోపల ఉంటేనే సైట్ నుండి డేటా తెస్తుంది సార్!
    దీనివల్ల 429 ఎర్రర్ రాదు, లైవ్ రిజల్ట్ అస్సలు మిస్ అవ్వదు.
    """
    now_ist = datetime.now(IST)
    is_in_window = False
    active_event_name = ""
    
    for start_t, end_t, e_name in today_active_event_windows:
        if start_t <= now_ist <= end_t:
            is_in_window = True
            active_event_name = e_name
            break
            
    if is_in_window:
        log(f"🎯 Inside Live Event Window for '{active_event_name}'. Checking Forex Factory Feed...")
        check_for_live_updates() # మన మెయిన్ ఒరిజినల్ లైవ్ అప్‌డేట్ ఫంక్షన్ రన్ అవుతుంది సార్
    else:
        # విండో లేనప్పుడు బాట్ సైలెంట్ గా ఉంటుంది, సర్వర్ మీద అస్సలు లోడ్ పడదు
        pass

def morning_master_job():
    """
    ఈ మాస్టర్ జాబ్ ఉదయం 7:15 కి రన్ అయ్యి ఛానెల్ కి మెసేజ్ పంపుతుంది,
    అలాగే నేటి ఈవెంట్ టైమ్ విండోస్ అన్నింటినీ లోడ్ చేస్తుంది సార్.
    """
    safe_send(f"☀️ <b>నేటి ముఖ్యమైన ఆర్థిక వార్తలు (Today Events):</b>\n\n{fetch_economic_calendar(1)}", chat_id=CHAT_ID)
    schedule_today_live_events()

# --- BACKGROUND SCHEDULE JOBS ---
# ఉదయం 7:15 కి డైలీ క్యాలెండర్ వెళ్తుంది + విండోస్ లాక్ అవుతాయి సార్
scheduler.add_job(morning_master_job, 'cron', hour=5, minute=50)

# ఆదివారం ఉదయం వీక్లీ క్యాలెండర్ వెళ్తుంది సార్
scheduler.add_job(lambda: safe_send(f"📅 <b>వారపు ఆర్థిక క్యాలెండర్:</b>\n\n{fetch_economic_calendar(7)}", chat_id=CHAT_ID), 'cron', day_of_week='sun', hour=9, minute=20)

# 🚀 ప్రతి 1 నిమిషానికి రన్ అయ్యే మాస్టర్ స్మార్ట్ చెక్కర్ (తిరుగులేని పక్కా సేఫ్టీ లాజిక్)
scheduler.add_job(smart_live_checker_master, 'interval', minutes=1)

# మార్కెట్ టేబుల్ ఇంటర్వెల్ (ప్రతి 10 నిమిషాలకి)
scheduler.add_job(send_market_table, 'interval', minutes=10)
scheduler.start()

# బాట్ ఆన్ అవ్వగానే ఈరోజు మిగిలిన విండోస్ ని ముందే ఒకసారి ఆటోమేటిక్ గా లోడ్ చేసుకుంటుంది సార్
try: schedule_today_live_events()
except: pass

# --- FLASK SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running perfectly with Smart Window Logic!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================================
# 🏁 MAIN EXECUTION EXECUTOR
# ==========================================================
if __name__ == "__main__":
    log("🚀 Starting Combined Master Market Bot with Smart Dynamic Windows...")
    try: safe_send("✅ చంటి గారు, కంబైన్డ్ మాస్టర్ బాట్ స్మార్ట్ టైమ్ విండో లాజిక్‌తో విజయవంతంగా ప్రారంభమైంది!")
    except: pass

    Thread(target=run_server).start()
    Thread(target=ai_worker, daemon=True).start()
    Thread(target=main_loop, daemon=True).start()
    Thread(target=fetch_normal_rss, daemon=True).start()
    Thread(target=fetch_x_rss, daemon=True).start()
    Thread(target=half_hourly_market_pulse_loop, daemon=True).start()
    
    while True:
        try: bot.infinity_polling(timeout=90, long_polling_timeout=15, skip_pending=True)
        except Exception as e:
            log(f"⚠️ Connection lost, reconnecting in 10s: {e}", "WARNING")
            time.sleep(10)
