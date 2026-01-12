import streamlit as st
import datetime
import time
import os
import json
from supabase import create_client
from groq import Groq
from PyPDF2 import PdfReader
# ==========================================
# 1. CONFIGURATION & INIT
# ==========================================
st.set_page_config(
    page_title="AI Study Buddy",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Secrets
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except FileNotFoundError:
    st.error("Secrets not found. Please set up .streamlit/secrets.toml")
    st.stop()

# Initialize Clients
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def init_groq():
    return Groq(api_key=GROQ_API_KEY)

supabase = init_supabase()
groq_client = init_groq()

# ==========================================
# 2. SESSION STATE MANAGEMENT
# ==========================================
def init_session_state():
    defaults = {
        "user": None,
        "user_id": None,
        "feature": "🏠 Home",
        "xp": 0,
        "streak": 0,
        "last_study_date": None,
        "chat_history": [],
        "quiz_data": [],      # Stores the current active quiz
        "quiz_answers": {},   # Stores user answers
        "study_timer_active": False,
        "study_start_time": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- NAVIGATION HELPER ---
def go_to(page):
    st.session_state.feature = page

# ==========================================
# 3. BACKEND HELPERS (AI, Auth, DB)
# ==========================================

def ask_ai(prompt, system_role="You are a helpful AI tutor."):
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return None
# --- AUTHENTICATION ---
def login_user(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        st.session_state.user_id = response.user.id
        sync_user_stats(response.user.id)
        st.success("Login successful!")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Login failed: {e}")

def signup_user(email, password):
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            supabase.table("user_stats").insert({
                "user_id": response.user.id,
                "xp": 0,
                "streak": 0,
                "level": "Beginner"
            }).execute()
            st.success("Account created! Please log in.")
    except Exception as e:
        st.error(f"Signup failed: {e}")

def logout_user():
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

# --- GAMIFICATION & DB SYNC ---
def sync_user_stats(user_id):
    try:
        data = supabase.table("user_stats").select("*").eq("user_id", user_id).execute()
        if data.data:
            stats = data.data[0]
            st.session_state.xp = stats.get('xp', 0)
            st.session_state.streak = stats.get('streak', 0)
            st.session_state.last_study_date = stats.get('last_study_date')
    except Exception as e:
        pass

def add_xp(amount, activity_name):
    if not st.session_state.user_id: return
    st.session_state.xp += amount
    try:
        supabase.table("user_stats").update({"xp": st.session_state.xp}).eq("user_id", st.session_state.user_id).execute()
        supabase.table("study_logs").insert({
            "user_id": st.session_state.user_id,
            "minutes": 10, 
            "activity_type": activity_name,
            "date": str(datetime.date.today())
        }).execute()
        st.toast(f"🎉 +{amount} XP for {activity_name}!", icon="⭐")
        update_streak()
    except Exception as e:
        st.error(f"Sync Error: {e}")

def update_streak():
    if not st.session_state.user_id: return
    today = str(datetime.date.today())
    if st.session_state.last_study_date == today: return
    
    new_streak = 1
    if st.session_state.last_study_date:
        last_obj = datetime.datetime.strptime(st.session_state.last_study_date, "%Y-%m-%d").date()
        if (datetime.date.today() - last_obj).days == 1:
            new_streak = st.session_state.streak + 1
            
    supabase.table("user_stats").update({"streak": new_streak, "last_study_date": today}).eq("user_id", st.session_state.user_id).execute()
    st.session_state.streak = new_streak
    st.session_state.last_study_date = today

# ==========================================
# 4. FEATURE RENDERERS
# ==========================================

def render_home():
    st.title(f"👋 Welcome Back!")
    
    # Dashboard Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("⭐ Total XP", st.session_state.xp)
    c2.metric("🔥 Streak", f"{st.session_state.streak} Days")
    level = "Master" if st.session_state.xp > 500 else "Intermediate" if st.session_state.xp > 200 else "Beginner"
    c3.metric("🏆 Rank", level)
    
    st.divider()
    st.markdown("### 🚀 Quick Access")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("📘 Explain Topic", use_container_width=True, on_click=go_to, args=("📘 Explain Topic",))
        st.button("❓ Quiz Generator", use_container_width=True, on_click=go_to, args=("❓ Quiz Generator",))
    with col2:
        st.button("📚 Flashcards", use_container_width=True, on_click=go_to, args=("📚 Flashcards",))
        st.button("⏱️ Exam Mode", use_container_width=True, on_click=go_to, args=("⏱️ Exam Mode",))
    with col3:
        st.button("💬 Chat with AI", use_container_width=True, on_click=go_to, args=("💬 Chat with AI",))
        st.button("🗺️ Study Roadmap", use_container_width=True, on_click=go_to, args=("🗺️ Study Roadmap",))

def render_quiz():
    st.header("❓ Interactive Quiz Generator")
    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input("Enter Quiz Topic")
    with col2:
        num_q = st.number_input("No. of Questions", min_value=1, max_value=10, value=3)
    
    if st.button("Generate Quiz"):
        with st.spinner("Generating Interactive Quiz..."):
            # Prompt asking for JSON format for easier parsing
            prompt = (f"Create {num_q} multiple choice questions about {topic}. "
                      "Output ONLY valid JSON format like this: "
                      "[{'question': '...', 'options': ['A', 'B', 'C', 'D'], 'correct': 'Option Text'}, ...]")
            try:
                response = ask_ai(prompt, system_role="You are a strict JSON generator.")
                # Basic cleanup to ensure we find the JSON list
                start = response.find('[')
                end = response.rfind(']') + 1
                json_str = response[start:end]
                st.session_state.quiz_data = json.loads(json_str)
                st.session_state.quiz_answers = {} # Reset answers
            except:
                st.error("AI failed to generate valid JSON. Please try again.")

    # Render the Quiz if data exists
    if st.session_state.quiz_data:
        st.markdown("---")
        for i, q in enumerate(st.session_state.quiz_data):
            st.subheader(f"Q{i+1}: {q['question']}")
            # Use a unique key for each radio button based on index
            choice = st.radio(f"Select Answer for Q{i+1}", q['options'], key=f"q_{i}")
            
            # Check Answer Button
            if st.button(f"Check Answer {i+1}", key=f"btn_{i}"):
                if choice == q['correct']:
                    st.success("✅ Correct!")
                    add_xp(10, "Correct Answer")
                else:
                    st.error(f"❌ Incorrect. The correct answer was: {q['correct']}")

def render_flashcards():
    st.header("📚 Flashcards")
    topic = st.text_input("Topic")
    if st.button("Generate Cards"):
        with st.spinner("Creating..."):
            res = ask_ai(f"Create 5 flashcards for {topic}. Format: Front | Back")
            st.session_state.flashcards = res 
            add_xp(20, "Flashcards")
    
    if "flashcards" in st.session_state:
        st.markdown(st.session_state.flashcards)

def render_explain_topic():
    st.header("📘 Explain Topic")
    topic = st.text_input("Enter Topic")
    level = st.selectbox("Level", ["5-Year Old", "High School", "University"])
    if st.button("Explain"):
        res = ask_ai(f"Explain {topic} at a {level} level.")
        st.markdown(res)
        add_xp(15, "Explanation")

# --- UPDATED SUMMARY WITH PDF UPLOAD ---
def render_summary():
    st.header("📝 Summarize Notes")
    
    tab1, tab2 = st.tabs(["✍️ Paste Text", "📂 Upload PDF"])
    
    notes_text = ""

    with tab1:
        text_input = st.text_area("Paste your notes here", height=200)
        if text_input:
            notes_text = text_input

    with tab2:
        uploaded_file = st.file_uploader("Upload PDF Notes", type=['pdf'])
        if uploaded_file is not None:
            extracted_text = extract_text_from_pdf(uploaded_file)
            if extracted_text:
                st.success("PDF Loaded Successfully!")
                with st.expander("View Extracted Text"):
                    st.write(extracted_text[:1000] + "...") # Preview
                notes_text = extracted_text
            else:
                st.error("Could not extract text from PDF.")

    if st.button("Generate Summary"):
        if notes_text:
            with st.spinner("AI is analyzing your notes..."):
                # Limit text to prevent token errors (approx 4000 chars)
                summary = ask_ai(f"Summarize these notes in structured bullet points:\n{notes_text[:12000]}")
                st.markdown(summary)
                add_xp(15, "Summary")
        else:
            st.warning("Please paste text or upload a PDF first.")

def render_exam_mode():
    st.header("⏱️ Exam Mode")
    st.info("Generates a long-form question for you to practice writing.")
    topic = st.text_input("Exam Topic")
    if st.button("Start Exam"):
        st.markdown(ask_ai(f"Give me a hard exam question about {topic}."))

def render_chat():
    st.header("💬 Chat with AI")
    for msg in st.session_state.chat_history:
        st.chat_message(msg['role']).write(msg['content'])
        
    if user_input := st.chat_input("Ask your AI Tutor..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)
        response = ask_ai(user_input)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)

def render_roadmap():
    st.header("🗺️ Study Roadmap")
    goal = st.text_input("What is your goal? (e.g., Learn Python in 30 days)")
    if st.button("Create Roadmap"):
        st.markdown(ask_ai(f"Create a week-by-week roadmap for: {goal}"))
        add_xp(30, "Roadmap Created")

def render_study_session():
    st.header("⏳ Focus Timer")
    minutes = st.number_input("Minutes", 1, 120, 25)
    
    if st.button("Start Timer"):
        st.session_state.study_timer_active = True
        st.session_state.study_start_time = time.time()
        
    if st.session_state.study_timer_active:
        elapsed = time.time() - st.session_state.study_start_time
        remaining = (minutes * 60) - elapsed
        if remaining > 0:
            st.metric("Time Remaining", f"{int(remaining // 60)}:{int(remaining % 60):02d}")
            time.sleep(1)
            st.rerun()
        else:
            st.success("Time's up!")
            st.session_state.study_timer_active = False
            add_xp(minutes, "Study Session")

def render_gamification():
    st.header("🎮 Gamification Dashboard")
    st.metric("Level", "Master" if st.session_state.xp > 500 else "Novice")
    st.progress(min(100, st.session_state.xp % 100))
    st.write(f"Total XP: {st.session_state.xp}")

def render_mistake_explainer():
    st.header("❌ Mistake Explainer")
    q = st.text_input("The Question")
    wrong = st.text_input("Your Wrong Answer")
    if st.button("Analyze Mistake"):
        st.markdown(ask_ai(f"I answered '{wrong}' to the question '{q}'. Why is it wrong?"))

def render_career():
    st.header("💼 Career Connection")
    skill = st.text_input("Skill/Subject")
    if st.button("Show Jobs"):
        st.markdown(ask_ai(f"What careers require {skill}?"))

def render_learning_outcomes():
    st.header("🎯 Learning Outcomes")
    topic = st.text_input("Topic")
    if st.button("Generate"):
        st.markdown(ask_ai(f"What are the learning outcomes for {topic}?"))

def render_revision():
    st.header("🔁 Revision Mode")
    st.info("Generates key points for quick review.")
    topic = st.text_input("Topic to Revise")
    if st.button("Revise"):
        st.markdown(ask_ai(f"Give me 5 crucial bullet points to remember about {topic}"))

def render_self_assessment():
    st.header("🧠 Self Assessment")
    st.write("Rate your confidence (1-5) on your recent topics.")
    st.slider("Confidence Level", 1, 5)
    if st.button("Save Log"):
        st.success("Logged!")
        add_xp(5, "Self Reflection")

def render_daily_challenge():
    st.header("🎯 Daily Challenge")
    st.info("Today's Challenge: Complete 1 Quiz and Study for 20 mins.")
    if st.session_state.xp > 20: # Mock logic
        st.success("Challenge Completed! (+50 XP)")
    else:
        st.warning("In Progress...")

def render_weekly_progress():
    st.header("📈 Weekly Progress")
    st.bar_chart({"Mon": 10, "Tue": 20, "Wed": 15}) # Placeholder data for visualization

def render_progress_tracker():
    st.header("📊 Progress Tracker")
    st.write(f"XP: {st.session_state.xp}")
    st.write(f"Streak: {st.session_state.streak}")

# ==========================================
# 5. MAIN NAVIGATION LOGIC
# ==========================================

def main():
    if not st.session_state.user:
        # Simple Login Page
        st.title("📘 AI Study Buddy Login")
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.button("Login"): login_user(e, p)
        with tab2:
            e2 = st.text_input("Email (Sign Up)")
            p2 = st.text_input("Password (Sign Up)", type="password")
            if st.button("Sign Up"): signup_user(e2, p2)
        return

    # SIDEBAR
    with st.sidebar:
        st.title("Study Buddy")
        st.write(f"👤 {st.session_state.user.email}")
        
        # FEATURE LIST
        features = [
            "🏠 Home", "🎮 Gamification Dashboard", "🎯 Daily Challenge", "📈 Weekly Progress",
            "📘 Explain Topic", "📝 Summarize Notes", "❓ Quiz Generator", "🧠 Self Assessment",
            "⏱️ Exam Mode", "📚 Flashcards", "🔁 Revision Mode", "🎯 Learning Outcomes",
            "💼 Career Connection", "❌ Mistake Explainer", "💬 Chat with AI",
            "⏳ Study Session", "📊 Progress Tracker", "🗺️ Study Roadmap"
        ]
        
        # Iterate to create buttons
        for f in features:
            if st.button(f, key=f"nav_{f}", use_container_width=True):
                go_to(f)
                st.rerun()

        st.divider()
        if st.button("🚪 Logout"): logout_user()

    # GLOBAL BACK BUTTON (If not home)
    if st.session_state.feature != "🏠 Home":
        if st.button("⬅️ Back to Home"):
            go_to("🏠 Home")
            st.rerun()

    # ROUTING
    f = st.session_state.feature
    if f == "🏠 Home": render_home()
    elif f == "🎮 Gamification Dashboard": render_gamification()
    elif f == "🎯 Daily Challenge": render_daily_challenge()
    elif f == "📈 Weekly Progress": render_weekly_progress()
    elif f == "📘 Explain Topic": render_explain_topic()
    elif f == "📝 Summarize Notes": render_summary()
    elif f == "❓ Quiz Generator": render_quiz()
    elif f == "🧠 Self Assessment": render_self_assessment()
    elif f == "⏱️ Exam Mode": render_exam_mode()
    elif f == "📚 Flashcards": render_flashcards()
    elif f == "🔁 Revision Mode": render_revision()
    elif f == "🎯 Learning Outcomes": render_learning_outcomes()
    elif f == "💼 Career Connection": render_career()
    elif f == "❌ Mistake Explainer": render_mistake_explainer()
    elif f == "💬 Chat with AI": render_chat()
    elif f == "⏳ Study Session": render_study_session()
    elif f == "📊 Progress Tracker": render_progress_tracker()
    elif f == "🗺️ Study Roadmap": render_roadmap()

if __name__ == "__main__":
    main()
