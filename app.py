# ==================================================
# 📘 AI STUDY BUDDY — FIXED & COMPLETE VERSION
# ==================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
from dotenv import load_dotenv
load_dotenv()


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
def save_study(user_id, minutes):
    today = datetime.date.today()

    # log study
    supabase.table("study_logs").insert({
        "user_id": user_id,
        "date": str(today),
        "minutes": minutes
    }).execute()

    # fetch stats
    stats = supabase.table("user_stats").select("*").eq("user_id", user_id).execute().data[0]

    xp_gain = minutes * 2
    new_xp = stats["xp"] + xp_gain

    # streak logic
    last_date = stats["last_study_date"]
    if last_date == str(today - datetime.timedelta(days=1)):
        streak = stats["streak"] + 1
    elif last_date == str(today):
        streak = stats["streak"]
    else:
        streak = 1

    supabase.table("user_stats").update({
        "xp": new_xp,
        "streak": streak,
        "last_study_date": str(today)
    }).eq("user_id", user_id).execute()
    
def ensure_user_exists(user_id):
    res = supabase.table("user_stats").select("*").eq("user_id", user_id).execute()
    if not res.data:
        supabase.table("user_stats").insert({
            "user_id": user_id,
            "xp": 0,
            "streak": 0,
            "last_study_date": None
        }).execute()


from supabase import create_client
import streamlit as st
import time
import datetime
from groq import Groq

#helper functions

def complete_weekly_challenge(user_id):
    week_id = datetime.date.today().strftime("%Y-%W")

    existing = (
        supabase
        .table("weekly_challenges")
        .select("*")
        .eq("user_id", user_id)
        .eq("week", week_id)
        .execute()
        .data
    )

    if existing:
        return False  # already completed

    supabase.table("weekly_challenges").insert({
        "user_id": user_id,
        "week": week_id,
        "completed": True,
        "xp": 100
    }).execute()

    # update XP
    supabase.rpc("add_xp", {"uid": user_id, "points": 100}).execute()
    return True

def register_activity():
    today = datetime.date.today()

    # ---------- DAILY CHALLENGE ----------
    if st.session_state.daily_challenge_date != today:
        st.session_state.daily_challenge_date = today
        st.session_state.daily_challenge_done = False

    if not st.session_state.daily_challenge_done:
        add_xp(25)
        st.session_state.daily_challenge_done = True
        st.success("🎯 Daily Challenge Completed! +25 XP")

    # ---------- WEEKLY CHALLENGE ----------
    st.session_state.weekly_activity_count += 1

    if (
        st.session_state.weekly_activity_count >= 3
        and not st.session_state.weekly_reward_claimed
    ):
        add_xp(100)
        st.session_state.weekly_reward_claimed = True
        st.success("🏆 Weekly Challenge Completed! +100 XP")

    # ---------- SAVE TO BACKEND ----------
    save_progress(minutes=0)
#SIMPLE LOGIN UI (EMAIL MAGIC LINK)
st.title("📘 AI Study Buddy")

if "user" not in st.session_state:
    email = st.text_input("📧 Enter your email")
    if st.button("🔐 Send Magic Link"):
        supabase.auth.sign_in_with_otp({"email": email})
        st.success("Check your email for the login link")
    st.stop()
session = supabase.auth.get_session()

if session and session.user:
    st.session_state.user = session.user
    user_id = session.user.id
ensure_user_exists(user_id)


# ---------------- SESSION STATE INIT ----------------
import datetime

defaults = {
    "feature": "🏠 Home",
    "xp": 0,
    "streak": 0,
    "last_study_date": None,
    "daily_challenge_date": datetime.date.today(),
    "daily_challenge_done": False,
    "weekly_activity_count": 0,
    "weekly_reward_claimed": False,
    "study_log": [],
    "chat": [],
    "quiz": []
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def go_home():
    st.session_state.feature = "🏠 Home"

def go_to(name):
    st.session_state.feature = name

# =========================
# ⬅️ GLOBAL BACK BUTTON
# =========================
if st.session_state.feature != "🏠 Home":
    st.button("🏠 Home", key="global_home", on_click=go_home)
    st.divider()

# ===============================
# 🔐 REQUIRED SESSION STATE INIT
# ===============================

def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

# Core navigation
init_state("feature", "🏠 Home")

# Gamification
init_state("xp", 0)
init_state("streak", 0)
init_state("level", 1)
init_state("badges", set())

# Daily challenge
init_state("daily_challenge_done", False)
init_state("daily_challenge_date", datetime.date.today())

# Weekly challenge
init_state("weekly_activity_count", 0)
init_state("weekly_reward_claimed", False)
init_state("weekly_start_date", datetime.date.today())

# Study tracking
init_state("study_log", [])
init_state("last_study_date", None)

# Chat
init_state("chat", [])


# =============================
# DAILY CHALLENGE STATE (SAFE INIT)
# =============================
if "daily_challenge_done" not in st.session_state:
    st.session_state.daily_challenge_done = False

if "last_study_date" not in st.session_state:
    st.session_state.last_study_date = None
if "daily_challenge_done" not in st.session_state:
    st.session_state.daily_challenge_done = False

if "daily_challenge_date" not in st.session_state:
    st.session_state.daily_challenge_date = datetime.date.today()

if "weekly_activity_count" not in st.session_state:
    st.session_state.weekly_activity_count = 0

if "weekly_reward_claimed" not in st.session_state:
    st.session_state.weekly_reward_claimed = False


# ===============================
# 🎮 GAMIFICATION HELPERS
# ===============================
def add_xp(user_id, xp, reason):
    supabase.table("xp_logs").insert({
        "user_id": user_id,
        "xp": xp,
        "reason": reason
    }).execute()

    supabase.rpc("increment_xp", {
        "uid": user_id,
        "xp": xp
    }).execute()


def get_level():
    xp = st.session_state.xp
    if xp >= 600:
        return "Master"
    elif xp >= 300:
        return "Advanced"
    elif xp >= 100:
        return "Intermediate"
    return "Beginner"


def unlock_badges():
    if st.session_state.xp >= 50:
        st.session_state.badges.add("🥉 First Steps")
    if st.session_state.streak >= 7:
        st.session_state.badges.add("🔥 7-Day Streak")
    if st.session_state.xp >= 300:
        st.session_state.badges.add("🥇 XP Pro")



def check_daily_challenge():
    today = datetime.date.today()

    if st.session_state.last_study_date == today:
        if not st.session_state.daily_challenge_done:
            st.session_state.daily_challenge_done = True
            add_xp(25)
            animate_xp_gain(25)

# =============================
# SESSION STATE INITIALIZATION (REQUIRED)
# =============================
if "last_study_date" not in st.session_state:
    st.session_state.last_study_date = None

if "daily_challenge_done" not in st.session_state:
    st.session_state.daily_challenge_done = False

if "daily_challenge_date" not in st.session_state:
    st.session_state.daily_challenge_date = None

def animate_xp_gain(points):
    with st.spinner("⭐ Updating XP..."):
        time.sleep(0.6)
    st.toast(f"+{points} XP earned 🎉", icon="⭐")


get_or_create_user()

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="📘",
    layout="wide"
)

# ---------------- STYLES ----------------
st.markdown("""
<style>
button { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- GROQ ----------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.1-8b-instant"

def ai(prompt):
    res = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": f"You are a {st.session_state.persona} AI tutor."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=900
    )
    return res.choices[0].message.content.strip()

# ---------------- SESSION STATE ----------------
defaults = {
    "feature": "🏠 Home",
    "chat": [],
    "study_log": [],
    "xp": 0,
    "streak": 0,
    "last_date": None,
    "quiz": []
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("## 📘 AI Study Buddy")
    st.caption("Your all-in-one learning assistant")

    st.divider()

    feature_list = [
        "🏠 Home",
        "🎮 Gamification Dashboard",
        "🎯 Daily Challenge",
        "📈 Weekly Progress",
        "📘 Explain Topic",
        "📝 Summarize Notes",
        "❓ Quiz Generator",
        "🧠 Self Assessment",
        "⏱️ Exam Mode",
        "📚 Flashcards",
        "🔁 Revision Mode",
        "🎯 Learning Outcomes",
        "💼 Career Connection",
        "❌ Mistake Explainer",
        "💬 Chat with AI",
        "⏳ Study Session",
        "📊 Progress Tracker",
        "🗺️ Study Roadmap"
    ]

    selected = st.radio(
        "✨ Choose Feature",
        feature_list,
        index=feature_list.index(st.session_state.feature)
    )

    if selected != st.session_state.feature:
        st.session_state.feature = selected


    st.divider()

    st.session_state.language = st.selectbox("Language", ["English", "Hinglish", "Hindi"])
    st.session_state.difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Advanced"])
    st.session_state.persona = st.selectbox(
        "Teacher Persona",
        ["Friendly Tutor", "Strict Teacher", "Interview Coach"]
    )


# ==================================================
# 🏠 HOME
# ==================================================
    
if st.session_state.feature == "🏠 Home":
     stats = supabase.table("user_stats").select("*").eq("user_id", user_id).execute().data[0]

     st.metric("⭐ XP", stats["xp"])
     st.metric("🔥 Streak", stats["streak"])

    # =============================
# ===============================
# 🎯 DAILY CHALLENGE (AUTO)
# ===============================
     today = datetime.date.today()

     if st.session_state.daily_challenge_date != today:
         st.session_state.daily_challenge_done = False
         st.session_state.daily_challenge_date = today

     if (
         st.session_state.last_study_date == today
         and not st.session_state.daily_challenge_done
        ):
        st.session_state.daily_challenge_done = True
        add_xp(25)
        st.success("🎯 Daily Challenge Completed! +25 XP")




# =============================
# 📅 WEEKLY CHALLENGE CARD
# =============================
    st.subheader("🏆 Weekly Challenge")

    if st.button("Complete Weekly Challenge"):
        if complete_weekly_challenge(user_id):
            st.success("🎉 Weekly Challenge Completed! +100 XP")
        else:
            st.info("✅ Already completed this week")

    


    st.markdown("<h1 style='text-align:center'>📘 AI Study Buddy</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:gray'>Click any feature</p>", unsafe_allow_html=True)
   
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("📘 Explain Topic", use_container_width=True, on_click=go_to, args=("📘 Explain Topic",))
        st.button("❓ Quiz Generator", use_container_width=True, on_click=go_to, args=("❓ Quiz Generator",))
    with c2:
        st.button("📚 Flashcards", use_container_width=True, on_click=go_to, args=("📚 Flashcards",))
        st.button("⏱️ Exam Mode", use_container_width=True, on_click=go_to, args=("⏱️ Exam Mode",))
    with c3:
        st.button("🔁 Revision Mode", use_container_width=True, on_click=go_to, args=("🔁 Revision Mode",))
        st.button("💬 Chat with AI", use_container_width=True, on_click=go_to, args=("💬 Chat with AI",))
    # =============================
# 📊 YOUR PROGRESS SNAPSHOT
# =============================
    st.markdown("### 📊 Your Progress")

    col1, col2, col3 = st.columns(3)

    col1.metric("⭐ XP", st.session_state.xp)
    col2.metric("🔥 Streak", f"{st.session_state.streak} days")
    col3.metric("🏆 Level", get_level())

    st.progress(min(st.session_state.xp / 600, 1.0))


# ==================================================
# 📘 EXPLAIN TOPIC
# ==================================================
elif st.session_state.feature == "📘 Explain Topic":
    st.header("📘 Explain Topic")
    topic = st.text_input("Enter topic")
    if st.button("Explain"):
        st.write(ai(f"Explain {topic} at {st.session_state.difficulty} level in {st.session_state.language}"))

# ==================================================
# 📝 SUMMARIZE NOTES
# ==================================================
elif st.session_state.feature == "📝 Summarize Notes":
    st.header("📝 Summarize Notes")
    notes = st.text_area("Paste notes")
    if st.button("Summarize"):
        st.write(ai(f"Summarize:\n{notes}"))

# ==================================================
# ❓ QUIZ GENERATOR (SAFE)
# ==================================================
elif st.session_state.feature == "❓ Quiz Generator":
    topic = st.text_input("Quiz Topic")
    st.header("❓ Quiz Generator")
    if st.button("Generate Quiz"):
        text = ai(
            f"Create 5 MCQ questions on {topic}. "
            "Format exactly:\nQ:...\nA)...\nB)...\nC)...\nD)...\nCorrect:A"
        )
        st.session_state.quiz = text.split("Q:")
        register_activity()
        add_xp(25)
        animate_xp_gain(25)
        st.session_state.weekly_activity_count += 1

    for i, q in enumerate(st.session_state.quiz):
        if not q.strip():
            continue
        lines = [l for l in q.split("\n") if l.strip()]
        if len(lines) < 6:
            continue

        st.markdown(f"**Q{i}. {lines[0]}**")
        options = lines[1:5]
        correct = lines[-1].replace("Correct:", "").strip()

        choice = st.radio("", options, key=f"quiz_{i}")
        if st.button("Submit", key=f"sub_{i}"):
            if correct in choice:
                st.success("Correct ✅")
            else:
                st.error(f"Wrong ❌ (Correct: {correct})")
        st.session_state.last_study_date = datetime.date.today()
    if st.button("✅ Finish Study"):
        save_study(user_id, minutes=25)
        st.success("Study saved! XP updated 🔥")



# ==================================================
# 📚 FLASHCARDS
# ==================================================
elif st.session_state.feature == "📚 Flashcards":
    topic = st.text_input("Topic")
    st.header("📚 Flashcards")
    if st.button("Generate Flashcards"):
        st.write(ai(f"Create 5 flashcards (Q&A) on {topic}"))
        st.session_state.last_study_date = datetime.date.today()
        add_xp(25)
        animate_xp_gain(25)
        st.session_state.weekly_activity_count += 1


    

# ==================================================
# 🔁 REVISION MODE
# ==================================================
elif st.session_state.feature == "🔁 Revision Mode":
    topic = st.text_input("Topic")
    st.header("🔁 Revision Mode")
    if st.button("Start Revision"):
        st.write(ai(f"Create revision notes with examples and mistakes for {topic}"))
        add_xp(25)
        animate_xp_gain(25)
        st.session_state.weekly_activity_count += 1
        register_activity()


# ==================================================
# 🎯 LEARNING OUTCOMES
# ==================================================
elif st.session_state.feature == "🎯 Learning Outcomes":
    topic = st.text_input("Topic")
    st.header("🎯 Learning Outcomes")
    if st.button("Generate Outcomes"):
        st.write(ai(f"Generate learning outcomes for {topic} using Bloom taxonomy"))

# ==================================================
# 💼 CAREER CONNECTION
# ==================================================
elif st.session_state.feature == "💼 Career Connection":
    topic = st.text_input("Topic")
    st.header("💼 Career Connection")
    if st.button("Show Careers"):
        st.write(ai(f"Explain career relevance of {topic}"))

# ==================================================
# ⏱️ EXAM MODE
# ==================================================
elif st.session_state.feature == "⏱️ Exam Mode":
    topic = st.text_input("Topic")
    st.header("⏱️ Exam Mode")
    exam_type = st.selectbox("Exam Type", ["Short Answer", "Long Answer", "MCQ"])
    if st.button("Generate Answer"):
        st.write(ai(f"Write {exam_type} exam answer on {topic}"))
        st.session_state.last_study_date = datetime.date.today()
        add_xp(25)
        animate_xp_gain(25)
        st.session_state.weekly_activity_count += 1
        register_activity()



# ==================================================
# ⏳ STUDY SESSION (CUSTOM)
# ==================================================
elif st.session_state.feature == "⏳ Study Session":
    st.header("⏳ Study Session")
    study = st.number_input("Study minutes", 1, 120, 25)
    brk = st.number_input("Break minutes", 1, 60, 5)
    cycles = st.number_input("Cycles", 1, 10, 2)

    if st.button("Start Session"):
        total_minutes = study * cycles

        st.success("Session Completed 🎉")
        st.session_state.last_study_date = datetime.date.today()
        st.session_state.weekly_activity_count += 1

        add_xp(25)
        save_progress(total_minutes)
    if st.button("✅ Finish Study"):
        save_study(user_id, minutes=25)
        st.success("Study saved! XP updated 🔥")

    


# ==================================================
# 💬 CHAT
# ==================================================
elif st.session_state.feature == "💬 Chat with AI":
    st.header("💬 Chat with AI")
    msg = st.text_input("Ask anything")
    if st.button("Send"):
        st.session_state.chat.append(("You", msg))
        st.session_state.chat.append(("AI", ai(msg)))
    

    for r, t in st.session_state.chat:
        st.markdown(f"**{r}:** {t}")
#📊 Progress Tracker
elif st.session_state.feature == "📊 Progress Tracker":

    st.subheader("📊 Your Real Progress")

    progress = fetch_progress()

    if not st.session_state.study_log:
       st.info("No study data yet")
    else:
       total_minutes = sum(i["minutes"] for i in st.session_state.study_log)
       st.metric("⏱️ Total Study Time", f"{total_minutes} mins")
       st.metric("⭐ XP", st.session_state.xp)
       st.metric("🔥 Streak", f"{st.session_state.streak} days")


    
#Weekly Progress
elif st.session_state.feature == "📈 Weekly Progress":

    st.subheader("📈 Weekly Progress")

    if not st.session_state.study_log:
        st.info("No weekly data available yet.")
    else:
        for log in st.session_state.study_log[-7:]:
            st.write(f"📅 {log['date']} → ⏱ {log['minutes']} mins") 
             
#🗺️ Study Roadmap
elif st.session_state.feature == "🗺️ Study Roadmap":

    st.subheader("🗺️ Study Roadmap")

    subject = st.text_input("Enter subject")
    days = st.number_input("Number of days", 1, 30, 7)

    if st.button("Generate Roadmap"):
        st.write(
            ai(
                f"Create a {days}-day structured study roadmap for {subject}"
            )
        )
    
#💼 Career Connection
elif st.session_state.feature == "💼 Career Connection":

    st.subheader("💼 Career Connection")

    topic = st.text_input("Enter topic")

    if st.button("Show Career Uses"):
        st.write(
            ai(
                f"Explain real-world career applications of {topic}"
            )
        )     

             
#❌ Mistake Explainer
elif st.session_state.feature == "❌ Mistake Explainer":

    st.subheader("❌ Mistake Explainer")

    wrong_answer = st.text_area("Paste the wrong answer")

    if st.button("Explain Mistake"):
        st.write(
            ai(
                f"Explain why this answer is wrong and how to correct it:\n{wrong_answer}"
            )
        )
    
#🧠 Self Assessment
elif st.session_state.feature == "🧠 Self Assessment":

    st.subheader("🧠 Self Assessment")

    topic = st.text_input("Topic studied")

    if st.button("Generate Questions"):
        qs = ai(
            f"Generate 3 self-assessment questions for {topic}"
        )
        st.write(qs)
        st.session_state.last_study_date = datetime.date.today()
        add_xp(25)
        animate_xp_gain(25)
        st.session_state.weekly_activity_count += 1
        register_activity()

#🎮 Gamification Dashboard
elif st.session_state.feature == "🎮 Gamification Dashboard":

    st.subheader("🎮 Gamification Dashboard")

    st.metric("XP", st.session_state.xp)
    st.metric("Streak", f"{st.session_state.streak} days")

    level = "Beginner"
    if st.session_state.xp >= 500:
        level = "Master"
    elif st.session_state.xp >= 300:
        level = "Advanced"
    elif st.session_state.xp >= 100:
        level = "Intermediate"

    st.success(f"🏆 Level: {level}")
#🎯 Daily Challenge (AUTO COMPLETE – NO BUTTON)
elif st.session_state.feature == "🎯 Daily Challenge":

    st.subheader("🎯 Daily Challenge")

    today = datetime.date.today()

    # ---- SAFE INITIALIZATION ----
    if "last_study_date" not in st.session_state:
        st.session_state.last_study_date = None

    if "daily_challenge_done" not in st.session_state:
        st.session_state.daily_challenge_done = False

    if "daily_challenge_date" not in st.session_state:
        st.session_state.daily_challenge_date = today

    # ---- RESET IF NEW DAY ----
    if st.session_state.daily_challenge_date != today:
        st.session_state.daily_challenge_done = False
        st.session_state.daily_challenge_date = today

    # ---- UI ----
    if st.session_state.daily_challenge_done:
        st.success("✅ Today's challenge already completed")
    else:
        st.info("👉 Complete any study activity today to auto-complete this challenge")

    # ---- AUTO-COMPLETE LOGIC ----
    if (
        st.session_state.last_study_date == today
        and not st.session_state.daily_challenge_done
    ):
        st.session_state.daily_challenge_done = True
        add_xp(25)
        animate_xp_gain(25)

        st.balloons()
        st.success("🎉 Daily Challenge Completed! +25 XP")

        motivation = ai(
            "Give a short motivational message for a student who completed today's study goal."
        )
        st.write(motivation)

