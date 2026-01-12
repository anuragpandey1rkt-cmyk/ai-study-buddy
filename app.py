# =====================================================
# 📘 AI STUDY BUDDY — ULTIMATE EDITION
# =====================================================

import streamlit as st
import datetime
from supabase import create_client
from groq import Groq

# ---------------- CONFIG ----------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
GROQ_KEY = st.secrets["GROQ_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
ai = Groq(api_key=GROQ_KEY)

st.set_page_config("AI Study Buddy", "📘", layout="wide")

# ---------------- SESSION ----------------
defaults = {
    "user": None,
    "user_id": None,
    "feature": "🏠 Home",
    "xp": 0,
    "study_active": False
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ---------------- SAFETY ----------------
def require_login():
    if not st.session_state.user_id:
        st.warning("🔒 Please login first")
        st.stop()

def ensure_user(uid):
    res = supabase.table("user_stats").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("user_stats").insert({
            "user_id": uid,
            "xp": 0,
            "streak": 0,
            "last_study_date": None
        }).execute()

def get_stats():
    res = supabase.table("user_stats").select("*").eq(
        "user_id", st.session_state.user_id
    ).execute()
    return res.data[0] if res.data else {"xp": 0, "streak": 0}

def add_xp(points):
    stats = get_stats()
    supabase.table("user_stats").update({
        "xp": stats["xp"] + points
    }).eq("user_id", st.session_state.user_id).execute()

# ---------------- AUTH ----------------
def auth():
    st.title("📘 AI Study Buddy")
    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            res = supabase.auth.sign_in_with_password({"email": e, "password": p})
            if res.user:
                st.session_state.user = res.user
                st.session_state.user_id = res.user.id
                ensure_user(res.user.id)
                st.rerun()

            else:
                st.error("Invalid credentials")

    with tab2:
        e = st.text_input("New Email")
        p = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            supabase.auth.sign_up({"email": e, "password": p})
            st.success("Confirm email & login")

# ---------------- SIDEBAR ----------------
feature_list = [
    "🏠 Home","🎮 Gamification Dashboard","🎯 Daily Challenge","📈 Weekly Progress",
    "📘 Explain Topic","📝 Summarize Notes","❓ Quiz Generator","🧠 Self Assessment",
    "⏱️ Exam Mode","📚 Flashcards","🔁 Revision Mode","🎯 Learning Outcomes",
    "💼 Career Connection","❌ Mistake Explainer","💬 Chat with AI",
    "⏳ Study Session","📊 Progress Tracker","🗺️ Study Roadmap"
]

def sidebar():
    with st.sidebar:
        st.title("📘 AI Study Buddy")
        for f in feature_list:
            st.button(f, on_click=lambda x=f: st.session_state.update(feature=x))
        if st.button("🚪 Logout"):
            supabase.auth.sign_out()
            for k in defaults:
                st.session_state[k] = defaults[k]
            st.rerun()


# ---------------- FEATURES ----------------

def home():
    stats = get_stats()
    level = stats["xp"] // 100 + 1
    st.header("🏠 Home")
    st.metric("XP", stats["xp"])
    st.metric("Level", level)
    st.progress((stats["xp"] % 100) / 100)

def explain_topic():
    require_login()
    t = st.text_input("Topic")
    if st.button("Explain"):
        r = ai.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role":"user","content":f"Explain {t} simply"}]
        )
        st.write(r.choices[0].message.content)
        add_xp(10)

def summarize_notes():
    require_login()
    n = st.text_area("Paste notes")
    if st.button("Summarize"):
        r = ai.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role":"user","content":f"Summarize:\n{n}"}]
        )
        st.write(r.choices[0].message.content)
        add_xp(10)

def quiz():
    require_login()
    topic = st.text_input("Topic")
    qn = st.slider("Questions",1,10,5)
    if st.button("Generate Quiz"):
        r = ai.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role":"user","content":f"Create {qn} MCQs on {topic}"}]
        )
        st.write(r.choices[0].message.content)
        add_xp(20)

def study_session():
    require_login()
    m = st.number_input("Minutes",5,180,25)
    if st.button("Complete Study"):
        add_xp(m)
        st.success(f"+{m} XP added")

def chat():
    require_login()
    q = st.text_input("Ask AI")
    if st.button("Ask"):
        r = ai.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role":"user","content":q}]
        )
        st.write(r.choices[0].message.content)

# ---------------- ROUTER ----------------
if st.session_state.user is None:
    auth()
else:
    sidebar()
    f = st.session_state.feature
    {
        "🏠 Home": home,
        "📘 Explain Topic": explain_topic,
        "📝 Summarize Notes": summarize_notes,
        "❓ Quiz Generator": quiz,
        "💬 Chat with AI": chat,
        "⏳ Study Session": study_session,
    }.get(f, lambda: st.info("🚧 Feature active & safe")).callable()
