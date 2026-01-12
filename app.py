import streamlit as st
import datetime
import time
import os
from supabase import create_client
from groq import Groq

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
        "quiz_data": [],
        "quiz_generated": False,
        "study_timer_running": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ==========================================
# 3. BACKEND HELPERS (Auth, DB, AI)
# ==========================================

# --- AI WRAPPER ---
def ask_ai(prompt, system_role="You are a helpful AI tutor."):
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"

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
            # Create initial stats row
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

def reset_password(email):
    try:
        supabase.auth.reset_password_for_email(email, options={"redirect_to": "http://localhost:8501"})
        st.success("Password reset link sent to email.")
    except Exception as e:
        st.error(f"Error: {e}")

# --- GAMIFICATION & DB SYNC ---
def sync_user_stats(user_id):
    """Fetch XP and Streak from DB to Session State"""
    try:
        data = supabase.table("user_stats").select("*").eq("user_id", user_id).execute()
        if data.data:
            stats = data.data[0]
            st.session_state.xp = stats.get('xp', 0)
            st.session_state.streak = stats.get('streak', 0)
            st.session_state.last_study_date = stats.get('last_study_date')
    except Exception as e:
        print(f"Sync Error: {e}")

def add_xp(amount, activity_name):
    """Update XP locally and in DB"""
    if not st.session_state.user_id:
        return

    # Update Local
    st.session_state.xp += amount
    
    # Update DB
    try:
        # Update User Stats
        supabase.table("user_stats").update({"xp": st.session_state.xp}).eq("user_id", st.session_state.user_id).execute()
        
        # Log Activity
        supabase.table("study_logs").insert({
            "user_id": st.session_state.user_id,
            "minutes": 5, # Default generic time for small tasks
            "activity_type": activity_name,
            "date": str(datetime.date.today())
        }).execute()
        
        st.toast(f"🎉 +{amount} XP for {activity_name}!", icon="⭐")
    except Exception as e:
        st.error(f"Failed to save progress: {e}")

def update_streak():
    """Check dates and update streak logic"""
    if not st.session_state.user_id: 
        return
        
    today = str(datetime.date.today())
    last_date = st.session_state.last_study_date
    
    if last_date == today:
        return # Already studied today
        
    new_streak = 1
    if last_date:
        last_date_obj = datetime.datetime.strptime(last_date, "%Y-%m-%d").date()
        if (datetime.date.today() - last_date_obj).days == 1:
            new_streak = st.session_state.streak + 1
            
    # Update DB
    supabase.table("user_stats").update({
        "streak": new_streak,
        "last_study_date": today
    }).eq("user_id", st.session_state.user_id).execute()
    
    st.session_state.streak = new_streak
    st.session_state.last_study_date = today

# ==========================================
# 4. FEATURE VIEWS (The Pages)
# ==========================================

def render_auth_page():
    st.title("📘 AI Study Buddy")
    tab1, tab2, tab3 = st.tabs(["🔐 Login", "🆕 Sign Up", "🔄 Reset Password"])
    
    with tab1:
        email = st.text_input("Email", key="l_email")
        password = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login", type="primary"):
            login_user(email, password)
            
    with tab2:
        email = st.text_input("Email", key="s_email")
        password = st.text_input("Password", type="password", key="s_pass")
        if st.button("Sign Up"):
            signup_user(email, password)
            
    with tab3:
        email = st.text_input("Enter Email for Reset Link", key="r_email")
        if st.button("Send Reset Link"):
            reset_password(email)

def render_home():
    st.title(f"Welcome back!")
    
    # Dashboard Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("⭐ XP", st.session_state.xp)
    c2.metric("🔥 Streak", f"{st.session_state.streak} Days")
    
    level = "Beginner"
    if st.session_state.xp > 500: level = "Master"
    elif st.session_state.xp > 200: level = "Intermediate"
    c3.metric("🏆 Rank", level)
    
    st.divider()
    
    # Quick Actions
    st.subheader("🚀 Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📘 Explain Topic", use_container_width=True):
            st.session_state.feature = "Explain Topic"
            st.rerun()
        if st.button("❓ Quiz Generator", use_container_width=True):
            st.session_state.feature = "Quiz Generator"
            st.rerun()
    with col2:
        if st.button("📚 Flashcards", use_container_width=True):
            st.session_state.feature = "Flashcards"
            st.rerun()
        if st.button("💬 Chat AI", use_container_width=True):
            st.session_state.feature = "Chat"
            st.rerun()

def render_explain():
    st.header("📘 Explain Topic")
    topic = st.text_input("What do you want to understand?")
    style = st.selectbox("Explanation Style", ["Simple (5 year old)", "High School", "University Expert"])
    
    if st.button("Explain"):
        with st.spinner("AI is thinking..."):
            prompt = f"Explain {topic} in a {style} style. Keep it clear and concise."
            response = ask_ai(prompt)
            st.markdown(response)
            add_xp(10, "Topic Explanation")
            update_streak()

def render_quiz():
    st.header("❓ Quiz Generator")
    topic = st.text_input("Enter Topic for Quiz")
    
    if st.button("Generate Quiz"):
        with st.spinner("Generating Questions..."):
            prompt = f"Create 3 multiple choice questions about {topic}. Format: Q1: Question? A) .. B) .. C) .. Correct: A"
            response = ask_ai(prompt)
            st.session_state.quiz_data = response
            st.session_state.quiz_generated = True
            
    if st.session_state.quiz_generated:
        st.markdown("### Your Quiz")
        st.write(st.session_state.quiz_data)
        if st.button("I Finished the Quiz"):
            add_xp(50, "Completed Quiz")
            update_streak()
            st.success("Great job! +50 XP")

def render_flashcards():
    st.header("📚 AI Flashcards")
    topic = st.text_input("Topic for Flashcards")
    
    if st.button("Create Cards"):
        with st.spinner("Creating..."):
            prompt = f"Create 5 flashcards for {topic}. Format: Front: [Term] | Back: [Definition]"
            response = ask_ai(prompt)
            st.markdown(response)
            add_xp(20, "Flashcards Generated")
            update_streak()

def render_chat():
    st.header("💬 Chat with AI Tutor")
    
    # Display History
    for role, text in st.session_state.chat_history:
        with st.chat_message(role):
            st.write(text)
            
    # Input
    user_input = st.chat_input("Ask me anything...")
    if user_input:
        # Add User msg
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.write(user_input)
            
        # Get AI Response
        with st.spinner("Thinking..."):
            ai_reply = ask_ai(user_input)
            st.session_state.chat_history.append(("assistant", ai_reply))
            with st.chat_message("assistant"):
                st.write(ai_reply)

def render_profile():
    st.header("👤 User Profile")
    st.write(f"**Email:** {st.session_state.user.email}")
    
    # Reset Password UI
    new_pass = st.text_input("New Password", type="password")
    if st.button("Update Password"):
        try:
            supabase.auth.update_user({"password": new_pass})
            st.success("Password Updated")
        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
# 5. MAIN APP FLOW
# ==========================================

def main():
    # CHECK AUTH STATUS
    if not st.session_state.user:
        render_auth_page()
        return

    # SIDEBAR NAVIGATION
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/4712/4712009.png", width=50)
        st.title("Study Buddy")
        
        st.write(f"Logged in as: {st.session_state.user.email}")
        
        options = ["🏠 Home", "📘 Explain Topic", "❓ Quiz Generator", "📚 Flashcards", "💬 Chat", "👤 Profile"]
        selected = st.radio("Navigate", options)
        
        # Handle Sidebar Navigation vs Home Page Buttons
        if selected == "🏠 Home":
            st.session_state.feature = "🏠 Home"
        elif selected == "📘 Explain Topic":
            st.session_state.feature = "Explain Topic"
        elif selected == "❓ Quiz Generator":
            st.session_state.feature = "Quiz Generator"
        elif selected == "📚 Flashcards":
            st.session_state.feature = "Flashcards"
        elif selected == "💬 Chat":
            st.session_state.feature = "Chat"
        elif selected == "👤 Profile":
            st.session_state.feature = "Profile"
            
        st.divider()
        if st.button("🚪 Logout"):
            logout_user()

    # RENDER SELECTED FEATURE
    if st.session_state.feature != "🏠 Home":
        if st.button("⬅️ Back to Home"):
            st.session_state.feature = "🏠 Home"
            st.rerun()
            
    if st.session_state.feature == "🏠 Home":
        render_home()
    elif st.session_state.feature == "Explain Topic":
        render_explain()
    elif st.session_state.feature == "Quiz Generator":
        render_quiz()
    elif st.session_state.feature == "Flashcards":
        render_flashcards()
    elif st.session_state.feature == "Chat":
        render_chat()
    elif st.session_state.feature == "Profile":
        render_profile()

if __name__ == "__main__":
    main()
