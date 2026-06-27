import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

# Ensure root directory is in python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from src.database import SessionLocal, User, StudentProfile, AcademicMarks, FacultyRemarks, Assignment, AlertLog, hash_password, verify_password, Announcement, engine, Base, seed_database
Base.metadata.create_all(bind=engine)
seed_database()
from src.ml_models import predict_student_risk, get_explainable_ai, train_and_select_best_model
from src.analytics import run_student_clustering, analyze_remark_sentiment, predict_exam_pass_probability
from src.alerts import send_email, send_sms, send_whatsapp, generate_personalized_ai_alert
from src.automation.face_recognition import FaceAttendanceManager
from src.automation.ocr_marks import OCRMarksUploader
from src.automation.assignment_tracker import check_pending_assignments_and_alert
from src.reporting import generate_student_pdf_report

# Page Config
st.set_page_config(
    page_title="EduInsight AI - Student Performance & Monitoring System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme Choice Selection
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "🌙 Dark Mode"

# Sidebar selector for theme
st.sidebar.markdown("### 🎨 Interface Theme")
theme_choice = st.sidebar.selectbox(
    "Theme Mode",
    ["☀️ Light Mode", "🌙 Dark Mode"],
    index=0 if st.session_state.theme_mode == "☀️ Light Mode" else 1,
    key="theme_mode_selector",
    label_visibility="collapsed"
)
st.session_state.theme_mode = theme_choice
is_dark = (theme_choice == "🌙 Dark Mode") and st.session_state.get("authenticated", False)
plotly_font_color = "#F8FAFC" if is_dark else "#1E293B"

if is_dark:
    # --- DARK MODE CSS ---
    theme_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
        
        /* ═══ BASE TYPOGRAPHY ═══ */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #F8FAFC !important;
        }
        
        /* ═══ MAIN BACKGROUND ═══ */
        .main {
            background-color: #0F172A !important;
            background-image: 
                radial-gradient(at 0% 0%, rgba(30, 41, 59, 0.7) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(15, 23, 42, 0.8) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(30, 41, 59, 0.5) 0px, transparent 50%),
                radial-gradient(at 0% 100%, rgba(17, 24, 39, 0.9) 0px, transparent 50%) !important;
            background-attachment: fixed !important;
            color: #F8FAFC !important;
        }
        .main .block-container {
            padding-top: 2rem;
        }
        
        /* ═══ FORCE ALL TEXT LIGHT ═══ */
        .main p, .main span, .main label, .main li, .main blockquote,
        .main th, .main td, .main div, .main a {
            color: #F8FAFC !important;
        }
        
        /* ═══ HEADINGS ═══ */
        h1 {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            color: #FFFFFF !important;
            font-weight: 800 !important;
            font-size: 2rem !important;
        }
        h2, h3 {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }
        h4, h5, h6 {
            font-family: 'Inter', sans-serif !important;
            color: #E2E8F0 !important;
            font-weight: 600 !important;
        }
        
        /* ═══ METRIC CARDS ═══ */
        [data-testid="stMetricValue"] {
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: 1.8rem !important;
        }
        [data-testid="stMetricLabel"] {
            color: #94A3B8 !important;
            font-weight: 500 !important;
        }
        [data-testid="stMetricDelta"] {
            color: #34D399 !important;
        }
        div[data-testid="metric-container"] {
            background-color: #1E293B !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
            padding: 16px !important;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06) !important;
        }
        
        /* ═══ INPUTS / SELECTS / TEXTAREAS ═══ */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        input, select, textarea {
            background-color: #1E293B !important;
            color: #F8FAFC !important;
            border: 1.5px solid #475569 !important;
            border-radius: 8px !important;
        }
        input::placeholder, textarea::placeholder {
            color: #64748B !important;
        }
        
        /* ═══ BUTTONS ═══ */
        .stButton > button {
            background: linear-gradient(135deg, #3B82F6, #2563EB) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.5rem !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
            transform: translateY(-1px) !important;
        }
        
        /* ═══ SIDEBAR ═══ */
        section[data-testid="stSidebar"] {
            background-color: #0F172A !important;
            border-right: 1px solid #1E293B;
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] label,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li {
            color: #F8FAFC !important;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #FFFFFF !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            background: rgba(255,255,255,0.05) !important;
            color: #F8FAFC !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255,255,255,0.1) !important;
        }
        
        /* ═══ PREMIUM CARD ═══ */
        .premium-card {
            background: #1E293B;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3), 0 4px 6px -2px rgba(0,0,0,0.05);
            border-left: 4px solid #3B82F6;
        }
        
        .text-muted {
            color: #94A3B8 !important;
            font-size: 0.9rem;
        }
        
        /* ═══ TABS ═══ */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #1E293B;
            border-radius: 10px;
            padding: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            color: #94A3B8 !important;
            font-weight: 500;
            padding: 8px 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0F172A !important;
            color: #FFFFFF !important;
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
        }
        
        /* ═══ TABLES ═══ */
        .stDataFrame, .stTable {
            background-color: #1E293B !important;
            border-radius: 8px !important;
        }
        .stDataFrame th {
            background-color: #0F172A !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }
        .stDataFrame td {
            color: #F8FAFC !important;
        }
        
        /* ═══ RADIO BUTTONS ═══ */
        .stRadio > div {
            color: #F8FAFC !important;
        }
        .stRadio label {
            color: #F8FAFC !important;
        }
        
        /* ═══ STATUS BADGES ═══ */
        .status-high {
            background-color: #7F1D1D;
            color: #FCA5A5 !important;
            border: 1px solid #991B1B;
            padding: 4px 14px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
            font-size: 0.85rem;
        }
        .status-medium {
            background-color: #78350F;
            color: #FDE68A !important;
            border: 1px solid #92400E;
            padding: 4px 14px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
            font-size: 0.85rem;
        }
        .status-low {
            background-color: #064E3B;
            color: #A7F3D0 !important;
            border: 1px solid #065F46;
            padding: 4px 14px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
            font-size: 0.85rem;
        }
        
        /* ═══ EXPANDER ═══ */
        .streamlit-expanderHeader {
            color: #F8FAFC !important;
            font-weight: 600 !important;
            background-color: #1E293B !important;
            border-radius: 8px !important;
        }
        
        /* ═══ SELECTBOX DROPDOWN TEXT ═══ */
        [data-baseweb="menu"] li {
            color: #F8FAFC !important;
            background-color: #1E293B !important;
        }
        [data-baseweb="menu"] li:hover {
            background-color: #334155 !important;
        }
        
        /* ═══ PLOTLY CHART BACKGROUNDS ═══ */
        .js-plotly-plot .plotly .main-svg {
            background: transparent !important;
        }
    </style>
    """
else:
    # --- LIGHT MODE CSS ---
    theme_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
        
        /* ═══ BASE TYPOGRAPHY ═══ */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #1a1a2e !important;
        }
        
        /* ═══ MAIN BACKGROUND ═══ */
        .main {
            background-color: #FFFFFF !important;
            background-image: none !important;
            color: #1a1a2e !important;
        }
        .main .block-container {
            padding-top: 2rem;
        }
        
        /* ═══ FORCE ALL TEXT DARK ═══ */
        .main p, .main span, .main label, .main li, .main blockquote,
        .main th, .main td, .main div, .main a {
            color: #1a1a2e !important;
        }
        
        /* ═══ HEADINGS ═══ */
        h1 {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            color: #1a1a2e !important;
            font-weight: 800 !important;
            font-size: 2rem !important;
        }
        h2, h3 {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            color: #1a1a2e !important;
            font-weight: 700 !important;
        }
        h4, h5, h6 {
            font-family: 'Inter', sans-serif !important;
            color: #334155 !important;
            font-weight: 600 !important;
        }
        
        /* ═══ METRIC CARDS ═══ */
        [data-testid="stMetricValue"] {
            color: #1a1a2e !important;
            font-weight: 700 !important;
            font-size: 1.8rem !important;
        }
        [data-testid="stMetricLabel"] {
            color: #475569 !important;
            font-weight: 500 !important;
        }
        [data-testid="stMetricDelta"] {
            color: #059669 !important;
        }
        div[data-testid="metric-container"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px !important;
            padding: 16px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
        }
        
        /* ═══ INPUTS / SELECTS / TEXTAREAS ═══ */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        input, select, textarea {
            background-color: #FFFFFF !important;
            color: #1a1a2e !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }
        input::placeholder, textarea::placeholder {
            color: #94A3B8 !important;
        }
        
        /* ═══ BUTTONS ═══ */
        .stButton > button {
            background: linear-gradient(135deg, #3B82F6, #2563EB) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.5rem !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
            transform: translateY(-1px) !important;
        }
        
        /* ═══ SIDEBAR ═══ */
        section[data-testid="stSidebar"] {
            background-color: #1E293B !important;
            border-right: 1px solid #334155;
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] label,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li {
            color: #E2E8F0 !important;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #F1F5F9 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            background: rgba(255,255,255,0.1) !important;
            color: #F1F5F9 !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255,255,255,0.2) !important;
        }
        
        /* ═══ PREMIUM CARD ═══ */
        .premium-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
            border-left: 4px solid #3B82F6;
        }
        
        .text-muted {
            color: #64748B !important;
            font-size: 0.9rem;
        }
        
        /* ═══ TABS ═══ */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #F1F5F9;
            border-radius: 10px;
            padding: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            color: #475569 !important;
            font-weight: 500;
            padding: 8px 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF !important;
            color: #1a1a2e !important;
            font-weight: 600;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        /* ═══ TABLES ═══ */
        .stDataFrame, .stTable {
            background-color: #FFFFFF !important;
            border-radius: 8px !important;
        }
        .stDataFrame th {
            background-color: #F1F5F9 !important;
            color: #1a1a2e !important;
            font-weight: 600 !important;
        }
        .stDataFrame td {
            color: #1a1a2e !important;
        }
        
        /* ═══ RADIO BUTTONS ═══ */
        .stRadio > div {
            color: #1a1a2e !important;
        }
        .stRadio label {
            color: #1a1a2e !important;
        }
        
        /* ═══ STATUS BADGES ═══ */
        .status-high {
            background-color: #FEF2F2;
            color: #DC2626 !important;
            border: 1px solid #FECACA;
            padding: 4px 14px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
            font-size: 0.85rem;
        }
        .status-medium {
            background-color: #FFFBEB;
            color: #D97706 !important;
            border: 1px solid #FDE68A;
            padding: 4px 14px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
            font-size: 0.85rem;
        }
        .status-low {
            background-color: #F0FDF4;
            color: #16A34A !important;
            border: 1px solid #BBF7D0;
            padding: 4px 14px;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
            font-size: 0.85rem;
        }
        
        /* ═══ EXPANDER ═══ */
        .streamlit-expanderHeader {
            color: #1a1a2e !important;
            font-weight: 600 !important;
            background-color: #F8FAFC !important;
            border-radius: 8px !important;
        }
        
        /* ═══ SELECTBOX DROPDOWN TEXT ═══ */
        [data-baseweb="menu"] li {
            color: #1a1a2e !important;
        }
        
        /* ═══ PLOTLY CHART BACKGROUNDS ═══ */
        .js-plotly-plot .plotly .main-svg {
            background: transparent !important;
        }
    </style>
    """

st.markdown(theme_css, unsafe_allow_html=True)


# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.name = None

db = SessionLocal()

# --- AUTHENTICATION SHIELD ---
def auth_page():
    # Logo and Header
    import base64
    logo_path = os.path.join(BASE_DIR, "data", "logo.jpg")
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                logo_base64 = base64.b64encode(f.read()).decode()
            logo_html = f"""
            <div style='text-align: center; margin-bottom: 10px;'>
                <img src="data:image/jpeg;base64,{logo_base64}" style='width: 140px; height: 140px; border-radius: 50%; object-fit: cover; border: 3px solid #3B82F6; box-shadow: 0 8px 24px rgba(59, 130, 246, 0.35); margin-bottom: 15px;' />
                <h1>EduInsight AI</h1>
                <p class='text-muted'>AI Based Academic Monitoring & Alert System</p>
            </div>
            """
            st.markdown(logo_html, unsafe_allow_html=True)
        except Exception:
            st.markdown("""
            <div style='text-align: center; margin-bottom: 10px;'>
                <div style='display: inline-block; background: linear-gradient(135deg, #3B82F6, #8B5CF6); padding: 16px 18px; border-radius: 20px; box-shadow: 0 10px 30px rgba(139, 92, 246, 0.4); margin-bottom: 15px;'>
                    <span style='font-size: 2.5rem; line-height: 1;'>🧠</span>
                </div>
                <h1>EduInsight AI</h1>
                <p class='text-muted'>AI Based Academic Monitoring & Alert System</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 10px;'>
            <div style='display: inline-block; background: linear-gradient(135deg, #3B82F6, #8B5CF6); padding: 16px 18px; border-radius: 20px; box-shadow: 0 10px 30px rgba(139, 92, 246, 0.4); margin-bottom: 15px;'>
                <span style='font-size: 2.5rem; line-height: 1;'>🧠</span>
            </div>
            <h1>EduInsight AI</h1>
            <p class='text-muted'>AI Based Academic Monitoring & Alert System</p>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.get("forgot_password_mode", False):
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.subheader("Reset Password")
            st.markdown("<p class='text-muted' style='font-size: 0.85rem;'>Provide your registered username and email to securely set a new password.</p>", unsafe_allow_html=True)
            reset_username = st.text_input("👤 Username", key="reset_username")
            reset_email = st.text_input("📧 Registered Email Address", key="reset_email")
            new_pwd = st.text_input("🔒 New Password", type="password", key="reset_new_pwd")
            new_pwd_confirm = st.text_input("🔒 Confirm New Password", type="password", key="reset_new_pwd_confirm")
            
            c_res_btn, c_back_btn = st.columns(2)
            with c_res_btn:
                if st.button("Reset Password", use_container_width=True, type="primary"):
                    if not reset_username or not reset_email or not new_pwd:
                        st.warning("Please fill in all fields.")
                    elif new_pwd != new_pwd_confirm:
                        st.error("New passwords do not match.")
                    elif len(new_pwd) < 4:
                        st.error("Password must be at least 4 characters.")
                    else:
                        user = db.query(User).filter(User.username == reset_username, User.email == reset_email).first()
                        if user:
                            user.hashed_password = hash_password(new_pwd)
                            db.commit()
                            st.success("✅ Password updated successfully! Please log in with your new password.")
                            st.session_state.forgot_password_mode = False
                            st.rerun()
                        else:
                            st.error("User with specified Username and Registered Email not found.")
            with c_back_btn:
                if st.button("Back to Login", use_container_width=True):
                    st.session_state.forgot_password_mode = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # Custom Tabs using side-by-side buttons
        c_login_toggle, c_signup_toggle = st.columns(2)
        with c_login_toggle:
            is_login = (st.session_state.get("auth_tab", "Login") == "Login")
            if st.button("🔑 Login", type="primary" if is_login else "secondary", use_container_width=True, key="tab_login_btn"):
                st.session_state.auth_tab = "Login"
                st.rerun()
        with c_signup_toggle:
            is_signup = (st.session_state.get("auth_tab", "Login") == "Sign Up")
            if st.button("📝 Sign Up", type="primary" if is_signup else "secondary", use_container_width=True, key="tab_signup_btn"):
                st.session_state.auth_tab = "Sign Up"
                st.rerun()

        if st.session_state.get("auth_tab", "Login") == "Login":
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.subheader("Welcome Back")
            login_method = st.radio("Login with", ["Username", "Email"], horizontal=True, key="login_method")
            
            if login_method == "Username":
                login_id = st.text_input("👤 Username / Email", key="login_user")
            else:
                login_id = st.text_input("📧 Email Address", key="login_email")
            
            password = st.text_input("🔒 Password", type="password", key="login_pass")
            
            # Remember Me & Forgot Password Layout
            c_rem, c_forg = st.columns([1.2, 1])
            with c_rem:
                remember_me = st.checkbox("Remember Me", value=True, key="remember_me")
            with c_forg:
                if st.button("Forgot Password?", key="btn_forgot_trigger", use_container_width=True):
                    st.session_state.forgot_password_mode = True
                    st.rerun()
            
            st.markdown("<br/>", unsafe_allow_html=True)
            if st.button("Log In", use_container_width=True, key="btn_login"):
                if not login_id or not password:
                    st.warning("Please enter your credentials.")
                else:
                    # Look up user by username or email
                    if login_method == "Username":
                        user = db.query(User).filter(User.username == login_id).first()
                    else:
                        user = db.query(User).filter(User.email == login_id).first()
                    
                    if user and verify_password(password, user.hashed_password):
                        st.session_state.authenticated = True
                        st.session_state.user_role = user.role
                        st.session_state.username = user.username
                        st.session_state.user_id = user.id
                        st.session_state.name = user.name
                        st.session_state.department = user.department or "CSE"
                        st.success(f"Welcome, {user.name}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please check and try again.")
            
            # Sign Up Link below the form
            st.markdown("<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
            if st.button("Don't have an account? Sign Up", key="link_to_signup", use_container_width=True):
                st.session_state.auth_tab = "Sign Up"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # ────────── SIGN UP VIEW ──────────
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.subheader("Create New Account")
        
        su_role = st.selectbox("I am a", ["Student", "Faculty", "Parent", "HOD"], key="su_role")
        
        su_col1, su_col2 = st.columns(2)
        with su_col1:
            su_fullname = st.text_input("Full Name *", key="su_name")
            su_username = st.text_input("Username *", key="su_user", help="Unique login ID — no spaces")
        with su_col2:
            su_email = st.text_input("Email *", key="su_email")
            su_phone = st.text_input("Phone / Telegram Chat ID", key="su_phone", help="Enter your numeric Telegram Chat ID (e.g. 1688994372) to receive free messages via Telegram")
        
        su_pass = st.text_input("Password *", type="password", key="su_pass")
        su_pass2 = st.text_input("Confirm Password *", type="password", key="su_pass2")
        
        # ── Student-specific fields ──
        if su_role == "Student":
            st.markdown("---")
            st.markdown("**📋 Student Details**")
            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                su_roll = st.text_input("Roll Number *", key="su_roll")
            with sc2:
                su_dept = st.text_input("Department Code", key="su_dept", help="e.g. CSE, ECE, DS")
            with sc3:
                su_year = st.selectbox("Year", [1, 2, 3, 4], key="su_year")
            with sc4:
                su_section = st.text_input("Section", value="A", key="su_section")
        
        # ── Parent-specific fields ──
        if su_role == "Parent":
            st.markdown("---")
            st.markdown("**🔗 Link to Student**")
            su_child_roll = st.text_input("Your Child's Roll Number *", key="su_child_roll", help="Must match an existing student roll number")
        
        st.markdown("")
        if st.button("Create Account", use_container_width=True, type="primary", key="btn_signup"):
            # ── Validation ──
            errors = []
            if not su_fullname:
                errors.append("Full Name is required.")
            if not su_username:
                errors.append("Username is required.")
            elif " " in su_username:
                errors.append("Username cannot contain spaces.")
            if not su_email:
                errors.append("Email is required.")
            if not su_pass:
                errors.append("Password is required.")
            elif len(su_pass) < 4:
                errors.append("Password must be at least 4 characters.")
            if su_pass != su_pass2:
                errors.append("Passwords do not match.")
            
            # Check username uniqueness
            if su_username and db.query(User).filter(User.username == su_username).first():
                errors.append(f"Username '{su_username}' is already taken.")
            # Check email uniqueness
            if su_email and db.query(User).filter(User.email == su_email).first():
                errors.append(f"Email '{su_email}' is already registered.")
            
            # Student-specific validation
            if su_role == "Student":
                if not su_roll:
                    errors.append("Roll Number is required for students.")
                elif db.query(StudentProfile).filter(StudentProfile.roll_number == su_roll).first():
                    errors.append(f"Roll Number '{su_roll}' already exists.")
            
            # Parent-specific validation
            if su_role == "Parent":
                if not su_child_roll:
                    errors.append("Your child's Roll Number is required.")
                else:
                    child_profile = db.query(StudentProfile).filter(StudentProfile.roll_number == su_child_roll).first()
                    if not child_profile:
                        errors.append(f"No student found with Roll Number '{su_child_roll}'.")
            
            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    # Create the User
                    new_user = User(
                        username=su_username,
                        hashed_password=hash_password(su_pass),
                        role=su_role,
                        name=su_fullname,
                        email=su_email,
                        phone=su_phone or ""
                    )
                    db.add(new_user)
                    db.flush()
                    
                    # Create StudentProfile if Student
                    if su_role == "Student":
                        dept = su_dept.strip().upper() if su_dept else ""
                        class_section = f"{dept}-Y{su_year}{su_section}" if dept else f"Y{su_year}{su_section}"
                        profile = StudentProfile(
                            user_id=new_user.id,
                            roll_number=su_roll,
                            class_section=class_section,
                            attendance_pct=0.0
                        )
                        db.add(profile)
                    
                    # Link Parent to existing student
                    if su_role == "Parent":
                        child_profile = db.query(StudentProfile).filter(StudentProfile.roll_number == su_child_roll).first()
                        if child_profile:
                            child_profile.parent_id = new_user.id
                    
                    db.commit()
                    st.success(f"✅ Account created successfully! You can now log in with username: **{su_username}**")
                    st.balloons()
                except Exception as ex:
                    db.rollback()
                    st.error(f"Registration failed: {ex}")
        
        # Log In Link below the form
        st.markdown("<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
        if st.button("Already have an account? Log In", key="link_to_login", use_container_width=True):
            st.session_state.auth_tab = "Login"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.authenticated:
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
        
        /* ═══ HIDE SIDEBAR ON LOGIN ═══ */
        [data-testid="stSidebar"], section[data-testid="stSidebar"] {
            display: none !important;
        }
        
        /* ═══ TYPOGRAPHY ═══ */
        html, body, [class*="css"], .main * {
            font-family: 'Poppins', sans-serif !important;
            color: #F8FAFC !important;
        }
        
        /* ═══ FULL SCREEN BACKGROUND GRADIENT WITH BLUR BLOBS ═══ */
        .main {
            background-color: #0F172A !important;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 50% 50%, rgba(6, 182, 212, 0.1) 0%, transparent 50%),
                radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px) !important;
            background-size: auto, auto, auto, 24px 24px !important;
            background-attachment: fixed !important;
        }
        
        /* Animated Blurred Blobs */
        .main::before {
            content: "";
            position: fixed;
            top: -10%;
            left: -10%;
            width: 50vw;
            height: 50vw;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.25) 0%, transparent 70%);
            filter: blur(80px);
            z-index: 0;
            pointer-events: none;
            animation: float-blob-1 25s infinite alternate ease-in-out;
        }
        
        .main::after {
            content: "";
            position: fixed;
            bottom: -10%;
            right: -10%;
            width: 50vw;
            height: 50vw;
            background: radial-gradient(circle, rgba(6, 182, 212, 0.25) 0%, transparent 70%);
            filter: blur(80px);
            z-index: 0;
            pointer-events: none;
            animation: float-blob-2 20s infinite alternate ease-in-out;
        }
        
        @keyframes float-blob-1 {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(15vw, 10vh) scale(1.1); }
        }
        @keyframes float-blob-2 {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(-10vw, -15vh) scale(1.2); }
        }
        
        /* ═══ MAIN LAYOUT CONTAINER ═══ */
        .main .block-container {
            max-width: 520px !important;
            margin: auto !important;
            padding-top: 6vh !important;
            padding-bottom: 6vh !important;
            z-index: 10 !important;
            position: relative !important;
        }
        
        /* ═══ GLASSMORPHISM LOGIN CARD ═══ */
        .premium-card {
            background: rgba(30, 41, 59, 0.45) !important;
            backdrop-filter: blur(25px) saturate(190%) !important;
            -webkit-backdrop-filter: blur(25px) saturate(190%) !important;
            border: 1px solid rgba(255, 255, 255, 0.09) !important;
            border-radius: 20px !important;
            padding: 35px 30px !important;
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4) !important;
            margin-top: 15px !important;
            transition: all 0.3s ease !important;
        }
        
        /* ═══ LOGO & HEADINGS ═══ */
        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.5px !important;
            background: linear-gradient(135deg, #FFFFFF 30%, #E2E8F0 60%, #3B82F6 100%);
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            font-size: 2.2rem !important;
            margin-bottom: 8px !important;
            text-align: center !important;
            text-shadow: 0 0 30px rgba(59, 130, 246, 0.2);
        }
        .text-muted {
            color: #94A3B8 !important;
            font-weight: 400 !important;
            font-size: 0.95rem !important;
            text-align: center !important;
            margin-bottom: 20px !important;
        }
        
        h2, h3 {
            font-weight: 700 !important;
            color: #FFFFFF !important;
        }
        
        /* ═══ INPUTS ═══ */
        div[data-baseweb="input"] > div, input, select, textarea {
            background-color: rgba(15, 23, 42, 0.5) !important;
            color: #FFFFFF !important;
            border: 1.5px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            padding: 2px 5px !important;
        }
        div[data-baseweb="input"] > div:focus-within, input:focus {
            border-color: #3B82F6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25) !important;
            background-color: rgba(15, 23, 42, 0.75) !important;
        }
        
        input::placeholder {
            color: #64748B !important;
        }
        
        /* ═══ GRADIENT BUTTON ═══ */
        .stButton > button {
            background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 50%, #06B6D4 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            letter-spacing: 0.3px !important;
            padding: 0.7rem 2rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3) !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 25px rgba(139, 92, 246, 0.55) !important;
            background: linear-gradient(135deg, #2563EB 0%, #7C3AED 50%, #0891B2 100%) !important;
        }
        .stButton > button:active {
            transform: translateY(0) !important;
        }
        
        /* ═══ TABS ═══ */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            background-color: rgba(15, 23, 42, 0.45) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 14px;
            padding: 6px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            color: #94A3B8 !important;
            font-weight: 500;
            padding: 10px 20px;
            transition: all 0.3s ease !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: #FFFFFF !important;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        /* ═══ RADIO BUTTONS ═══ */
        .stRadio label {
            color: #E2E8F0 !important;
            font-size: 0.95rem !important;
        }
        
        .forgot-link {
            float: right;
            color: #3B82F6 !important;
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
            transition: color 0.2s ease;
        }
        .forgot-link:hover {
            color: #60A5FA !important;
            text-decoration: underline;
        }
    </style>
    """, unsafe_allow_html=True)
    auth_page()
    sys.exit()

# Sidebar Logout
st.sidebar.markdown(f"### Logged in as:<br/>**{st.session_state.name}**<br/>`<span class='text-muted'>{st.session_state.user_role}</span>`", unsafe_allow_html=True)
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.name = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗄️ Database Status")
from src.database import DB_PATH
import sqlite3

# Test if database is writable from app.py
db_writable = False
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS _write_test_app (id INTEGER)")
    cursor.execute("DROP TABLE _write_test_app")
    conn.commit()
    conn.close()
    db_writable = True
except Exception:
    db_writable = False

status_emoji = "🟢 Writable" if db_writable else "🔴 Read-Only"
st.sidebar.markdown(f"**Path:** `{DB_PATH}`")
st.sidebar.markdown(f"**Status:** {status_emoji}")

st.sidebar.markdown("---")

def render_announcement_hub(db, current_user):
    st.subheader("📢 Announcement Hub")
    db_user = db.query(User).filter(User.id == current_user.user_id).first()
    if not db_user:
        st.error("User session invalid.")
        return
    
    # Form to create new announcement
    st.markdown("### Create New Announcement")
    with st.form("announcement_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Announcement Title", placeholder="e.g. Remedial Class Schedule")
            priority = st.selectbox("Priority Level", ["Normal", "Important", "Urgent"])
            publish_date = st.date_input("Publish Date", date.today())
            
        with col2:
            target_dept = st.selectbox("Target Department", ["All", "CSE", "ECE", "EEE", "DS", "AIML", "CS"])
            target_year = st.selectbox("Target Year", ["All", "1", "2", "3", "4"])
            target_sec = st.selectbox("Target Section", ["All", "A", "B", "C"])
            expiry_date = st.date_input("Expiry Date", date.today() + timedelta(days=7))
            
        description = st.text_area("Announcement Description", placeholder="Enter description here...", height=120)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            generate_voice = st.form_submit_button("Generate AI Voice")
        with col_btn2:
            publish = st.form_submit_button("Publish Announcement")
            
    # Session state to store temp tts generation flag
    if "temp_tts_generated" not in st.session_state:
        st.session_state.temp_tts_generated = False
        
    temp_audio_path = os.path.join(BASE_DIR, "data", "announcements", "temp_tts.mp3")
    
    if generate_voice:
        if not title or not description:
            st.error("Please enter both Title and Description first.")
        else:
            with st.spinner("Generating AI Voice via Edge-TTS..."):
                from src.tts_service import generate_voice_file
                text_to_speak = f"Announcement: {title}. {description}"
                # Ensure directories exist
                os.makedirs(os.path.dirname(temp_audio_path), exist_ok=True)
                success = generate_voice_file(text_to_speak, temp_audio_path)
                if success:
                    st.session_state.temp_tts_generated = True
                    st.success("AI Neural Voice generated successfully!")
                else:
                    st.error("Failed to generate AI voice.")
                    
    # Render audio player if generated
    if st.session_state.temp_tts_generated and os.path.exists(temp_audio_path):
        st.write("#### AI Voice Preview")
        st.audio(temp_audio_path, format="audio/mp3")
        
    if publish:
        if not title or not description:
            st.error("Please enter both Title and Description.")
        else:
            with st.spinner("Publishing announcement..."):
                # Save to db
                new_ann = Announcement(
                    title=title,
                    description=description,
                    created_by=db_user.id,
                    role=db_user.role,
                    target_department=target_dept,
                    target_year=target_year,
                    target_section=target_sec,
                    priority=priority,
                    publish_date=publish_date,
                    expiry_date=expiry_date
                )
                db.add(new_ann)
                db.commit()
                db.refresh(new_ann)
                
                # If voice was pre-generated, copy to final path
                if st.session_state.temp_tts_generated and os.path.exists(temp_audio_path):
                    filename = f"announcement_{new_ann.id}.mp3"
                    relative_path = os.path.join("data", "announcements", filename)
                    final_path = os.path.join(BASE_DIR, relative_path)
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    try:
                        import shutil
                        shutil.copy2(temp_audio_path, final_path)
                        new_ann.audio_url = relative_path.replace("\\", "/")
                        db.commit()
                        # Clean temp tts flag
                        st.session_state.temp_tts_generated = False
                        if os.path.exists(temp_audio_path):
                            os.remove(temp_audio_path)
                    except Exception as e:
                        st.warning(f"Failed to link audio file: {e}")
                
                st.success("Announcement published successfully!")
                
                # Trigger Telegram broadcast
                from src.alerts import broadcast_announcement_to_telegram
                sent_alerts = broadcast_announcement_to_telegram(db, new_ann.id)
                if sent_alerts > 0:
                    st.info(f"Broadcasted text and voice memo to {sent_alerts} Telegram Chat IDs!")
                    
                st.rerun()

    # Display list of existing announcements created by this user
    st.markdown("### Manage Published Announcements")
    user_announcements = db.query(Announcement).filter(
        Announcement.created_by == db_user.id
    ).order_by(Announcement.created_at.desc()).all()
    
    if user_announcements:
        for ann in user_announcements:
            priority_color = "red" if ann.priority == "Urgent" else ("orange" if ann.priority == "Important" else "blue")
            st.markdown(f"""
            <div style='border: 1px solid rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 15px; background: rgba(255, 255, 255, 0.02);'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h4 style='margin: 0; color: #3B82F6;'>{ann.title}</h4>
                    <span style='background-color: {priority_color}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold;'>
                        {ann.priority}
                    </span>
                </div>
                <p style='color: #888; font-size: 0.85rem; margin-top: 5px; margin-bottom: 10px;'>
                    <b>Target:</b> Dept: {ann.target_department} | Year: {ann.target_year} | Section: {ann.target_section} <br>
                    <b>Active:</b> {ann.publish_date} to {ann.expiry_date}
                </p>
                <p style='margin-bottom: 10px;'>{ann.description}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show audio player if exists
            if ann.audio_url:
                audio_full_path = os.path.join(BASE_DIR, ann.audio_url)
                if os.path.exists(audio_full_path):
                    st.audio(audio_full_path, format="audio/mp3")
                else:
                    st.warning("Audio file not found on disk.")
            else:
                # Add a button to generate audio post-publish
                if st.button(f"🔊 Generate AI Voice for '{ann.title[:20]}...'", key=f"tts_btn_{ann.id}"):
                    with st.spinner("Generating AI Voice..."):
                        from src.tts_service import generate_voice_file
                        filename = f"announcement_{ann.id}.mp3"
                        relative_path = os.path.join("data", "announcements", filename)
                        audio_path = os.path.join(BASE_DIR, relative_path)
                        text_to_speak = f"Announcement: {ann.title}. {ann.description}"
                        if generate_voice_file(text_to_speak, audio_path):
                            ann.audio_url = relative_path.replace("\\", "/")
                            db.commit()
                            st.success("AI voice generated!")
                            st.rerun()
                            
            if st.button(f"🗑️ Delete Announcement", key=f"del_btn_{ann.id}", use_container_width=True):
                # Delete voice file
                if ann.audio_url:
                    audio_full_path = os.path.join(BASE_DIR, ann.audio_url)
                    if os.path.exists(audio_full_path):
                        try:
                            os.remove(audio_full_path)
                        except Exception:
                            pass
                db.delete(ann)
                db.commit()
                st.success("Announcement deleted successfully!")
                st.rerun()
    else:
        st.write("You have not published any announcements yet.")

def render_announcements_viewer(db, student_profile):
    st.subheader("📢 Active Academic Announcements")
    if not student_profile:
        st.warning("No student profile associated with this account. Cannot retrieve filtered announcements.")
        return
    
    # Search and Filter
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Search Announcements", placeholder="Search by title or content...")
    with col_filter:
        priority_filter = st.selectbox("Filter by Priority", ["All", "Normal", "Important", "Urgent"])
        
    # Get active announcements matching target audience
    today_date = date.today()
    query = db.query(Announcement).filter(
        Announcement.publish_date <= today_date,
        Announcement.expiry_date >= today_date
    )
    
    dept = student_profile.class_section.split("-")[0] if "-" in student_profile.class_section else "CSE"
    sec_part = student_profile.class_section.split("-")[1] if "-" in student_profile.class_section else student_profile.class_section
    year = "All"
    section = "All"
    if len(sec_part) >= 3 and sec_part.startswith("Y"):
        year = sec_part[1]
        section = sec_part[2:]
        
    query = query.filter(
        (Announcement.target_department == "All") | (Announcement.target_department == dept),
        (Announcement.target_year == "All") | (Announcement.target_year == year),
        (Announcement.target_section == "All") | (Announcement.target_section == section)
    )
    
    # Priority filter
    if priority_filter != "All":
        query = query.filter(Announcement.priority == priority_filter)
        
    # Search query
    if search_query:
        query = query.filter(
            (Announcement.title.like(f"%{search_query}%")) | 
            (Announcement.description.like(f"%{search_query}%"))
        )
        
    announcements = query.order_by(Announcement.created_at.desc()).all()
    
    if announcements:
        for ann in announcements:
            priority_color = "#E53E3E" if ann.priority == "Urgent" else ("#DD6B20" if ann.priority == "Important" else "#3182CE")
            border_style = f"border-left: 5px solid {priority_color};"
            
            st.markdown(f"""
            <div style='background-color: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); {border_style} padding: 20px; border-radius: 8px; margin-bottom: 20px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h3 style='margin: 0; font-size: 1.25rem;'>{ann.title}</h3>
                    <span style='background-color: {priority_color}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: bold;'>
                        {ann.priority}
                    </span>
                </div>
                <p style='color: #888; font-size: 0.85rem; margin-top: 8px; margin-bottom: 12px;'>
                    📅 <b>Posted:</b> {ann.publish_date} | 👤 <b>By:</b> {ann.creator.name if ann.creator else 'Admin'} ({ann.role})
                </p>
                <div style='font-size: 0.95rem; line-height: 1.6; margin-bottom: 15px;'>
                    {ann.description.replace(chr(10), '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Embed audio player if available
            if ann.audio_url:
                audio_full_path = os.path.join(BASE_DIR, ann.audio_url)
                if os.path.exists(audio_full_path):
                    st.audio(audio_full_path, format="audio/mp3")
    else:
        st.write("No active announcements found matching your target audience.")

# --- PORTALS ORCHESTRATION ---

# Fetch details if student or parent
student_profile = None
if st.session_state.user_role == "Student":
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == st.session_state.user_id).first()
elif st.session_state.user_role == "Parent":
    student_profile = db.query(StudentProfile).filter(StudentProfile.parent_id == st.session_state.user_id).first()

# Helper for risk details
def get_student_ml_data(profile):
    marks = profile.marks
    avg_internal = sum(m.internal_marks for m in marks) / len(marks) if marks else 0.0
    avg_assign = sum(m.assignment_scores for m in marks) / len(marks) if marks else 0.0
    avg_exam = sum(m.exam_marks for m in marks if m.exam_marks is not None) / len(marks) if marks else 0.0
    
    assignments = profile.assignments
    sub_rate = sum(1 for a in assignments if a.status in ["Submitted", "Graded"]) / len(assignments) if assignments else 1.0
    remarks = profile.remarks
    avg_sentiment = sum(r.sentiment_score for r in remarks) / len(remarks) if remarks else 0.0
    
    return {
        "attendance_pct": profile.attendance_pct,
        "internal_marks_avg": avg_internal,
        "assignment_score_avg": avg_assign,
        "exam_marks_avg": avg_exam,
        "assignment_completion_rate": sub_rate,
        "sentiment_score_avg": avg_sentiment,
        "overall_academic": avg_internal + avg_assign + avg_exam
    }


# ==================== STUDENT PORTAL ====================
if st.session_state.user_role == "Student":
    st.title("👨‍🎓 Student Dashboard")
    st.write(f"Welcome back, **{st.session_state.name}** | Roll Number: **{student_profile.roll_number}** | Section: **{student_profile.class_section}**")
    
    tab1, tab2 = st.tabs(["📊 Performance Dashboard", "📢 Announcements"])
    
    with tab1:
        # 1. Row cards
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.metric("Attendance", f"{student_profile.attendance_pct:.1f}%", help="Required: 75%")
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            # Predict risk
            ml_data = get_student_ml_data(student_profile)
            pred = predict_student_risk(ml_data)
            risk = pred["risk_label"]
            score = pred["risk_score"]
            
            status_class = "status-low" if risk == "Low" else ("status-medium" if risk == "Medium" else "status-high")
            st.write("AI Risk Status:")
            st.markdown(f"<span class='{status_class}'>{risk} Risk ({score:.1f}/100)</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with c3:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            pass_prob = predict_exam_pass_probability(student_profile.attendance_pct, ml_data["internal_marks_avg"], ml_data["assignment_completion_rate"])
            st.metric("Final Exam Pass Probability", f"{pass_prob*100:.1f}%")
            st.markdown("</div>", unsafe_allow_html=True)
            
        # 2. Charts and explanations
        col_left, col_right = st.columns([1.5, 1])
        
        with col_left:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.subheader("Academic Marks Trend")
            
            # Load marks
            marks_records = student_profile.marks
            if marks_records:
                subjects = [m.subject for m in marks_records]
                internals = [m.internal_marks for m in marks_records]
                assignments = [m.assignment_scores for m in marks_records]
                exams = [m.exam_marks or 0.0 for m in marks_records]
                
                fig = go.Figure(data=[
                    go.Bar(name='Internals (30)', x=subjects, y=internals, marker_color='#3B82F6'),
                    go.Bar(name='Assignments (20)', x=subjects, y=assignments, marker_color='#10B981'),
                    go.Bar(name='Exams (50)', x=subjects, y=exams, marker_color='#8B5CF6')
                ])
                fig.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color=plotly_font_color)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No grades recorded yet.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_right:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.subheader("AI Performance Diagnostics")
            explain = get_explainable_ai(ml_data)
            
            for r in explain["reasons"]:
                impact_color = "🔴" if "High" in r["impact"] else ("🟡" if "Moderate" in r["impact"] else "🟢")
                st.markdown(f"**{impact_color} {r['feature']}:** {r['value']} | *{r['impact']}*")
                st.caption(r["description"])
                st.write("")
            st.markdown("</div>", unsafe_allow_html=True)
            
        # 3. Actions and Report
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.subheader("Actionable Recommendations")
        
        if risk == "High":
            st.error("Immediate attention required! Attendance and marks are critical. Attend remedial coaching sessions daily.")
        elif risk == "Medium":
            st.warning("Keep monitor on your grade trends and ensure assignments are submitted before deadline.")
        else:
            st.success("Great job! Keep up the excellent work. Consider mentoring fellow classmates.")
            
        # Report generation
        if st.button("Download PDF Progress Report", use_container_width=True):
            pdf_file = generate_student_pdf_report(db, student_profile.id)
            with open(pdf_file, "rb") as f:
                st.download_button(
                    label="Click here to save PDF",
                    data=f,
                    file_name=os.path.basename(pdf_file),
                    mime="application/pdf",
                    use_container_width=True
                )
        st.markdown("</div>", unsafe_allow_html=True)
        
    with tab2:
        render_announcements_viewer(db, student_profile)


# ==================== PARENT PORTAL ====================
elif st.session_state.user_role == "Parent":
    st.title("👪 Parent Dashboard")
    st.write(f"Logged in as parent for student: **{student_profile.user.name}** (Roll Number: **{student_profile.roll_number}**)")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.metric("Child Attendance", f"{student_profile.attendance_pct:.1f}%")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c2:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        ml_data = get_student_ml_data(student_profile)
        pred = predict_student_risk(ml_data)
        st.write("AI-generated Academic Risk Evaluation:")
        status_class = "status-low" if pred["risk_label"] == "Low" else ("status-medium" if pred["risk_label"] == "Medium" else "status-high")
        st.markdown(f"<span class='{status_class}'>{pred['risk_label']} Risk ({pred['risk_score']:.1f}/100)</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    # Notification logs
    st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
    st.subheader("Notification & Alert Log History")
    alerts = db.query(AlertLog).filter(AlertLog.student_id == student_profile.id).order_by(AlertLog.timestamp.desc()).all()
    if alerts:
        alert_data = [{"Timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M"), "Type": a.type, "Message Content": a.message, "Status": a.status} for a in alerts]
        st.dataframe(pd.DataFrame(alert_data), use_container_width=True)
    else:
        st.write("No notifications dispatched to parent accounts this term.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Telegram Bot Onboarding Call to Action
    st.markdown(f"""
    <div class='premium-card' style='border-left: 4px solid #0088cc; background: rgba(0, 136, 204, 0.05); margin-top: 20px;'>
        <h4 style='color: #0088cc; margin-top: 0; font-family: "Plus Jakarta Sans", sans-serif; font-weight: 700;'>✈️ Receive Instant Telegram Alerts</h4>
        <p style='margin-bottom: 12px; font-size: 0.95rem;'>To receive free academic status alerts and attendance warnings instantly on your mobile phone, please click the button below and tap <b>Start</b> in your Telegram app:</p>
        <a href="https://t.me/eduinsights_ai_bot" target="_blank" style="text-decoration: none;">
            <button style="background: linear-gradient(135deg, #0088cc 0%, #00a6ff 100%) !important; color: white !important; border: none !important; border-radius: 8px !important; padding: 10px 20px !important; font-weight: 600 !important; cursor: pointer !important; box-shadow: 0 4px 10px rgba(0, 136, 204, 0.2) !important;">
                💬 Start Telegram Bot
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    # Configure Telegram settings card
    with st.expander("⚙️ Configure your Telegram Alerts Connection"):
        st.markdown("""
        To connect your account to our Telegram bot:
        1. Click the **Start Telegram Bot** button above (tap **Start** in Telegram).
        2. Get your unique numeric **Chat ID** (find it by sending a message to `@userinfobot` on Telegram).
        3. Paste your Chat ID below and click **Save Connection Settings**.
        """)
        parent_phone = student_profile.parent.phone if (student_profile.parent and student_profile.parent.phone) else ""
        default_chat_id = parent_phone if (parent_phone and not parent_phone.startswith("910000")) else ""
        new_chat_id = st.text_input("Enter your Telegram Chat ID", value=default_chat_id, placeholder="e.g. 1688994372", key="parent_tg_chat_id")
        
        if st.button("Save Connection Settings", use_container_width=True, key="btn_save_tg_chat_id"):
            if new_chat_id:
                # Save to database
                parent_user = db.query(User).filter(User.id == student_profile.parent_id).first()
                if parent_user:
                    parent_user.phone = new_chat_id
                    db.commit()
                    st.success("✅ Telegram Chat ID updated successfully! You will now receive alerts directly here.")
                    st.rerun()
            else:
                st.warning("Please enter a valid Chat ID.")


# ==================== FACULTY PORTAL ====================
elif st.session_state.user_role == "Faculty":
    faculty_dept_display = st.session_state.get("department", "CSE")
    st.title(f"👩‍🏫 Faculty Portal — {faculty_dept_display} Department")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Grades & Attendance Input", "📷 OpenCV Face Attendance", "📝 OCR Marks Upload", "📢 Publish Announcements"])
    
    with tab1:
        st.subheader("Student Grades & remarks Management")
        
        # Dropdown selection of students
        # Filter students to only show those in the faculty's department
        faculty_dept = st.session_state.get("department", "CSE")
        student_list = db.query(StudentProfile).filter(
            StudentProfile.class_section.like(f"{faculty_dept}-%")
        ).all()
        selected_stud = st.selectbox("Select Student", student_list, format_func=lambda x: f"{x.user.name} ({x.roll_number})")
        
        if selected_stud:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
                st.subheader("Academic Scores")
                subject = st.selectbox("Subject", ['Mathematics', 'Science', 'English', 'History', 'Computer Science'])
                
                # Fetch existing score
                curr_score = db.query(AcademicMarks).filter(AcademicMarks.student_id == selected_stud.id, AcademicMarks.subject == subject).first()
                curr_internal = curr_score.internal_marks if curr_score else 15.0
                curr_assign = curr_score.assignment_scores if curr_score else 10.0
                curr_exam = curr_score.exam_marks if curr_score else 30.0
                
                internal = st.number_input("Internal Marks (out of 30)", min_value=0.0, max_value=30.0, value=curr_internal)
                assignment = st.number_input("Assignment Scores (out of 20)", min_value=0.0, max_value=20.0, value=curr_assign)
                exam = st.number_input("Term Exam Marks (out of 50)", min_value=0.0, max_value=50.0, value=curr_exam)
                
                if st.button("Save Marks", use_container_width=True):
                    if curr_score:
                        curr_score.internal_marks = internal
                        curr_score.assignment_scores = assignment
                        curr_score.exam_marks = exam
                    else:
                        new_score = AcademicMarks(student_id=selected_stud.id, subject=subject, internal_marks=internal, assignment_scores=assignment, exam_marks=exam)
                        db.add(new_score)
                    db.commit()
                    st.success("Marks saved successfully!")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col2:
                st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
                st.subheader("Faculty Remarks & Attendance")
                
                # Attendance
                attendance = st.slider("Class Attendance %", 0.0, 100.0, selected_stud.attendance_pct)
                if st.button("Update Attendance", use_container_width=True):
                    selected_stud.attendance_pct = attendance
                    db.commit()
                    st.success("Attendance updated!")
                    
                # Faculty remarks NLP
                remark_text = st.text_area("Add Observation Remark")
                if st.button("Analyze & Save Remark", use_container_width=True):
                    sentiment_score = analyze_remark_sentiment(remark_text)
                    new_remark = FacultyRemarks(
                        student_id=selected_stud.id,
                        faculty_id=st.session_state.user_id,
                        remark_text=remark_text,
                        sentiment_score=sentiment_score
                    )
                    db.add(new_remark)
                    db.commit()
                    
                    st.success("Remark recorded!")
                    st.write(f"Analyzed NLP Sentiment Rating: {sentiment_score:.2f} (Positive: >0.2, Negative: <-0.2)")
                st.markdown("</div>", unsafe_allow_html=True)
                
    with tab2:
        st.subheader("Automated Face Recognition Attendance Scan")
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.write("Scan student classroom images or camera frames to auto-verify presence and update the database.")
        
        # File uploader
        # Input Method: File upload or Live camera capture
        input_method = st.radio("Select Attendance Input Source", ["📁 Upload Image File", "📸 Take Live Photo"], horizontal=True)
        
        camera_file = None
        if input_method == "📁 Upload Image File":
            camera_file = st.file_uploader("Upload Classroom Image File", type=["jpg", "png", "jpeg"])
        else:
            mirror_preview = st.checkbox("Mirror Camera Preview", value=True)
            if mirror_preview:
                st.markdown("""
                <style>
                    [data-testid="stCameraInput"] video {
                        transform: scaleX(-1) !important;
                    }
                </style>
                """, unsafe_allow_html=True)
            camera_file = st.camera_input("Open Camera Viewer")
        
        if st.button("Run Face Scan Attendance", use_container_width=True):
            manager = FaceAttendanceManager()
            manager.load_known_faces(db)
            
            # Save uploaded image to temp path to run cv2
            temp_path = os.path.join(BASE_DIR, "data", "known_faces", "temp_scan.jpg")
            
            if camera_file:
                with open(temp_path, "wb") as f:
                    f.write(camera_file.getbuffer())
            else:
                # Mock scanning image
                temp_img = np.zeros((480, 640, 3), dtype=np.uint8) + 120
                cv2.imwrite(temp_path, temp_img)
                
            detected_names = manager.scan_image_and_mark_attendance(db, temp_path, original_filename=camera_file.name if camera_file else None)
            
            if detected_names:
                st.success(f"Scanning complete! Detected and marked present:")
                st.write(detected_names)
            else:
                st.error("Face Is Not Found Try Again")
            
            # Show image if exists
            if os.path.exists(temp_path):
                st.image(temp_path, caption="Scan Grid Output")
                os.remove(temp_path)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with tab3:
        st.subheader("OCR-Based Table Marks Sheet Upload")
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.write("Upload a scanned report card or gradeheet, and the OCR engine will automatically extract the marks table.")
        
        target_student = st.selectbox("Upload destination student", student_list, format_func=lambda x: f"{x.user.name} ({x.roll_number})", key="ocr_dest")
        ocr_file = st.file_uploader("Upload Grade Sheet Scanned Image", type=["jpg", "png", "jpeg"], key="ocr_uploader")
        
        if st.button("Extract and Save Table Marks", use_container_width=True):
            if target_student:
                temp_path = os.path.join(BASE_DIR, "data", "temp_ocr.png")
                
                if ocr_file:
                    with open(temp_path, "wb") as f:
                        f.write(ocr_file.getbuffer())
                else:
                    # Mock an OCR file
                    with open(temp_path, "w") as f:
                        f.write("mock")
                        
                uploader = OCRMarksUploader()
                result = uploader.extract_and_save_marks(db, target_student.id, temp_path)
                
                st.success("OCR Table Extraction Complete!")
                st.json(result)
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with tab4:
        render_announcement_hub(db, st.session_state)


# ==================== HOD PORTAL ====================
elif st.session_state.user_role == "HOD":
    st.title(f"🏛️ {st.session_state.get('department', 'CSE')} Department — HOD Analytics Dashboard")
    
    # 1. Overview stats
    # Filter students to only show those in the HOD's department
    hod_dept = st.session_state.get("department", "CSE")
    student_list = db.query(StudentProfile).filter(
        StudentProfile.class_section.like(f"{hod_dept}-%")
    ).all()
    n_students = len(student_list)
    avg_dept_attendance = sum(s.attendance_pct for s in student_list) / n_students if n_students else 0.0
    
    # Build dataframe for summary
    data = []
    for s in student_list:
        ml = get_student_ml_data(s)
        pred = predict_student_risk(ml)
        data.append({
            "id": s.id,
            "name": s.user.name,
            "roll": s.roll_number,
            "attendance": s.attendance_pct,
            "internal_avg": ml["internal_marks_avg"],
            "assignment_completion": ml["assignment_completion_rate"],
            "overall_academic": ml["overall_academic"],
            "risk_label": pred["risk_label"],
            "risk_score": pred["risk_score"]
        })
    df = pd.DataFrame(data)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.metric("Total Students Enrolled", n_students)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.metric("Department Average Attendance", f"{avg_dept_attendance:.1f}%")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        high_risk_count = sum(1 for d in data if d["risk_label"] == "High")
        st.metric("Critical High-Risk Students", high_risk_count)
        st.markdown("</div>", unsafe_allow_html=True)
        
    tab1, tab2, tab3, tab4 = st.tabs(["🛡️ Risk & Alerts Manager", "📊 Clustering & Performance Groups", "📈 Academic Failure Rates", "📢 Publish Announcements"])
    
    with tab1:
        st.subheader("Department Risk Auditing Panel")
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        
        # Alert trigger
        st.write("### Broadcast Automated Academic Status Warnings")
        target_risk = st.selectbox("Select Target Risk Category", ["High", "Medium", "Low", "All"])
        
        if st.button("Dispatch Automated SMS, WhatsApp & Email Alerts", use_container_width=True):
            sent_count = 0
            for student in student_list:
                ml = get_student_ml_data(student)
                pred = predict_student_risk(ml)
                
                if target_risk != "All" and pred["risk_label"] != target_risk:
                    continue
                    
                student_email = student.user.email if student.user else ""
                student_phone = student.user.phone if (student.user and student.user.phone) else ""
                parent_email = student.parent.email if student.parent else ""
                parent_phone = student.parent.phone if student.parent else ""
                
                # Fetch weak subjects
                weak_subs = [m.subject for m in student.marks if (m.internal_marks + m.assignment_scores + (m.exam_marks or 0)) < 40]
                
                # Dynamic HOD and Department lookup
                DEPT_MAP = {
                    "CSE": "Computer Science Engineering",
                    "ECE": "Electronic Communication Engineering",
                    "EEE": "Electrical Electronic Engineering",
                    "DS": "Data Science",
                    "AIML": "Artificial Intelligence",
                    "CS": "Cyber Security"
                }
                dept_code = student.class_section.split("-")[0] if (student.class_section and "-" in student.class_section) else "CSE"
                dept_name = DEPT_MAP.get(dept_code, "Computer Science & Engineering")
                hod_name = st.session_state.name if st.session_state.name else "Head of Department"
                
                # Generate custom alerts for student vs parent
                student_alert_text = generate_personalized_ai_alert(
                    student.user.name,
                    student.attendance_pct,
                    pred["risk_label"],
                    weak_subs,
                    pred["risk_score"],
                    recipient_type="student",
                    hod_name=hod_name,
                    dept_name=dept_name
                )
                
                parent_alert_text = generate_personalized_ai_alert(
                    student.user.name,
                    student.attendance_pct,
                    pred["risk_label"],
                    weak_subs,
                    pred["risk_score"],
                    recipient_type="parent",
                    hod_name=hod_name,
                    dept_name=dept_name
                )
                
                # Dispatch alerts
                if student_email:
                    send_email(db, student.id, student_email, f"URGENT: Academic Status Warning - {student.user.name}", student_alert_text)
                if parent_email and parent_email != student_email:
                    send_email(db, student.id, parent_email, f"URGENT: Student Academic Warning - {student.user.name}", parent_alert_text)
                
                # Student phone/Telegram alerts
                if student_phone:
                    student_sms_summary = f"EduInsight AI Alert: {student.user.name}, you are identified in the {pred['risk_label']} Risk zone (Risk Score: {pred['risk_score']:.1f}). Action plan sent to your email."
                    send_sms(db, student.id, student_phone, student_sms_summary, full_body=student_alert_text)
                    send_whatsapp(db, student.id, student_phone, student_sms_summary)
                
                # Parent phone/Telegram alerts
                if parent_phone:
                    sms_summary = f"EduInsight AI Alert: {student.user.name} identified in {pred['risk_label']} Risk zone (Risk Score: {pred['risk_score']:.1f}). Action plan dispatched via email."
                    send_sms(db, student.id, parent_phone, sms_summary, full_body=parent_alert_text)
                    send_whatsapp(db, student.id, parent_phone, sms_summary)
                    
                sent_count += 1
                
            st.success(f"Alert Broadcast Dispatch complete! Distributed alerts to {sent_count} Parent/Student accounts.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with tab2:
        st.subheader("Student Academic Clustering Visualizer")
        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        
        if not df.empty:
            clustered_df = run_student_clustering(df, n_clusters=3)
            
            fig = px.scatter(
                clustered_df,
                x="attendance",
                y="overall_academic",
                color="cluster_name",
                hover_data=["name", "roll", "risk_score"],
                title="Department Academic Clusters (Attendance vs Academic Score)",
                labels={"attendance": "Attendance %", "overall_academic": "Overall Academic Mark (Max 100)"},
                color_discrete_map={
                    "High Achievers": "#10B981",
                    "Average Achievers": "#3B82F6",
                    "High Risk Group": "#EF4444"
                }
            )
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color=plotly_font_color)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No student records available for clustering.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with tab3:
        st.subheader("Subject-wise Performance Analytics")
        
        # Load marks to plot subject performance
        marks_query = db.query(AcademicMarks).all()
        if marks_query:
            m_df = pd.DataFrame([{
                "subject": m.subject,
                "total": m.internal_marks + m.assignment_scores + (m.exam_marks or 0.0)
            } for m in marks_query])
            
            # Subject average marks
            avg_sub = m_df.groupby("subject")["total"].mean().reset_index()
            fig1 = px.bar(avg_sub, x="subject", y="total", title="Average Score by Subject (out of 100)", color_discrete_sequence=['#3B82F6'])
            fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color=plotly_font_color)
            
            # Pass/Fail percentage
            m_df["status"] = m_df["total"].apply(lambda x: "Pass" if x >= 40 else "Fail")
            status_df = m_df.groupby(["subject", "status"]).size().reset_index(name="count")
            
            fig2 = px.bar(status_df, x="subject", y="count", color="status", title="Pass vs Fail Count by Subject", barmode="group", color_discrete_map={"Pass": "#10B981", "Fail": "#EF4444"})
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color=plotly_font_color)
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
                st.plotly_chart(fig1, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
                st.plotly_chart(fig2, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("No grades recorded for subject analysis.")
            
    with tab4:
        render_announcement_hub(db, st.session_state)

db.close()
