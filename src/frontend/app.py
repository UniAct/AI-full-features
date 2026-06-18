import streamlit as st
import requests
import json

# ==========================================
# 1. Page Configuration & Custom CSS (Apple-like & Navy Blue)
# ==========================================
st.set_page_config(page_title="UniAct AI System", page_icon="🧠", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Background and Text */
    .stApp {
        background-color: #FAFAFA;
        color: #111827;
    }
    
    /* Navy Blue Buttons */
    .stButton>button {
        background-color: #0F172A; /* Deep Navy */
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #1E293B;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.2);
        transform: translateY(-1px);
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        border-bottom: 2px solid #E5E7EB;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #6B7280;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #0F172A;
        border-bottom-color: #0F172A !important;
    }
    
    /* Clean Text Areas and Inputs */
    .stTextInput>div>div>input, .stTextArea>div>textarea {
        border-radius: 8px;
        border: 1px solid #D1D5DB;
        background-color: #FFFFFF;
        padding: 0.5rem;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>textarea:focus {
        border-color: #0F172A;
        box-shadow: 0 0 0 1px #0F172A;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #0F172A;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Global Settings & State
# ==========================================
API_BASE_URL = "http://localhost:8000/api/v1/nlp"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ==========================================
# 3. Sidebar (Settings & Context)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103138.png", width=60)
    st.title("UniAct Core")
    st.markdown("---")
    
    st.subheader("⚙️ System Settings")
    project_id = st.text_input("Project ID (Collection)", value="default_project")
    limit_docs = st.slider("Retrieval Limit (RAG)", min_value=1, max_value=10, value=5)
    
    st.markdown("---")
    st.caption("Status: API Connected 🟢")

# ==========================================
# 4. Main Interface (Tabs)
# ==========================================
tab1, tab2, tab3 = st.tabs(["💬 AI Chat & Search", "📝 Smart Summarization", "🎓 Generate Exam"])

# ------------------------------------------
# Tab 1: RAG Chat
# ------------------------------------------
with tab1:
    st.header("Interactive RAG Assistant")
    st.markdown("Ask questions based on your indexed documents.")
    
    # Display Chat History
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Input Area
    if prompt := st.chat_input("What would you like to know?"):
        # Add User message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Call API
        with st.chat_message("assistant"):
            with st.spinner("Searching and generating..."):
                try:
                    payload = {"text": prompt, "limit": limit_docs}
                    res = requests.post(f"{API_BASE_URL}/index/answer/{project_id}", json=payload)
                    res.raise_for_status()
                    answer = res.json().get("answer", "No answer generated.")
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"Error connecting to backend: {str(e)}")

# ------------------------------------------
# Tab 2: Summarization
# ------------------------------------------
with tab2:
    st.header("Document Summarization")
    st.markdown("Paste long texts below to get a concise, professional summary.")
    
    text_to_summarize = st.text_area("Original Text:", height=250, placeholder="Paste your text here...")
    
    if st.button("Generate Summary"):
        if text_to_summarize.strip():
            with st.spinner("Analyzing and summarizing..."):
                try:
                    res = requests.post(f"{API_BASE_URL}/summarize", json={"text": text_to_summarize})
                    res.raise_for_status()
                    summary = res.json().get("summary", "")
                    
                    st.success("Summary Generated Successfully!")
                    st.info(summary)
                except Exception as e:
                    st.error(f"Failed to generate summary: {str(e)}")
        else:
            st.warning("Please enter some text to summarize.")

# ------------------------------------------
# Tab 3: MCQ & Exam Generator
# ------------------------------------------
with tab3:
    st.header("Exam Generation")
    st.markdown("Generate dynamic exams from your knowledge base.")
    
    col1, col2 = st.columns(2)
    with col1:
        exam_topic = st.text_input("Exam Topic / Context:", placeholder="e.g., Artificial Neural Networks")
        mcq_count = st.number_input("Number of MCQs", min_value=1, max_value=20, value=3)
    with col2:
        exam_diff = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"])
        written_count = st.number_input("Number of Written Questions", min_value=0, max_value=10, value=2)
        
    if st.button("Generate Exam"):
        if exam_topic.strip():
            with st.spinner("Drafting exam questions..."):
                try:
                    payload = {
                        "content": exam_topic,
                        "difficulty": exam_diff.lower(),
                        "num_mcq": mcq_count,
                        "num_written": written_count
                    }
                    res = requests.post(f"{API_BASE_URL}/index/exam/{project_id}", json=payload)
                    res.raise_for_status()
                    
                    exam_data = res.json().get("exam", {})
                    
                    st.success("Exam Drafted!")
                    
                    # Display the exam dynamically
                    if isinstance(exam_data, dict) and "raw_output" not in exam_data:
                        st.json(exam_data) # Pretty print JSON exam
                    else:
                        st.markdown("### Raw Output")
                        st.write(exam_data.get("raw_output") or exam_data)
                        
                except Exception as e:
                    st.error(f"Failed to generate exam: {str(e)}")
        else:
            st.warning("Please enter an exam topic.")