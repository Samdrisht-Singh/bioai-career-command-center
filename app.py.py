import json
import os
import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Optional OpenAI SDK import (supports OpenAI, Groq Free Tier, and Gemini Free Tier)
try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False

# ==============================================================================
# 1. PAGE CONFIGURATION & ENHANCED VISUAL STYLING
# ==============================================================================
st.set_page_config(
    page_title="BioAI Career & MSc Telemetry Command Center",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main { background-color: #FFFFFF; color: #111111; }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #1A73E8;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .metric-card-alert {
        background: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 5px solid #D93025;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .memory-box {
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-left: 5px solid #16A34A;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .section-banner {
        background: #F1F5F9;
        padding: 10px 16px;
        border-radius: 6px;
        font-weight: 700;
        color: #111111;
        margin-top: 20px;
        margin-bottom: 12px;
        border-left: 4px solid #12B5CB;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DB_PATH = "career_memory.db"

# ==============================================================================
# 2. STAR-SCHEMA SQLITE PERSISTENCE ENGINE (BI DATA WAREHOUSE IMPLEMENTATION)
# ==============================================================================
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_star_schema_warehouse():
    conn = get_connection()
    cur = conn.cursor()

    # FACT TABLE: Central Daily Time, Skill & Reflection Telemetry
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_daily_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_key TEXT UNIQUE,
            study_hours_bio_core REAL DEFAULT 0.0,
            study_hours_python_ai REAL DEFAULT 0.0,
            study_hours_dsa REAL DEFAULT 0.0,
            study_hours_bi_minor REAL DEFAULT 0.0,
            leetcode_solved INTEGER DEFAULT 0,
            rosalind_solved INTEGER DEFAULT 0,
            written_reflection TEXT,
            tomorrow_priorities TEXT,
            ai_generated_schedule TEXT,
            updated_at TEXT
        )
        """
    )

    # DIMENSION TABLE 1: Academic Semesters & Amity Scholarship Audit
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_semester_grades (
            semester_id INTEGER PRIMARY KEY,
            semester_name TEXT,
            credits REAL,
            sgpa REAL,
            status TEXT
        )
        """
    )

    # DIMENSION TABLE 2: Technical & Career Roadmap Milestones
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_roadmap_tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            semester_tag TEXT,
            pillar TEXT,
            task_title TEXT,
            verification_metric TEXT,
            completed INTEGER DEFAULT 0
        )
        """
    )

    # Seed baseline academic data (Sem 1 & 2 = 9.29 CGPA baseline; Sem 3-4 targets)
    cur.execute("SELECT COUNT(*) FROM dim_semester_grades")
    if cur.fetchone()[0] == 0:
        seed_semesters = [
            (1, "Semester 1 (Completed)", 22.0, 9.28, "Completed"),
            (2, "Semester 2 (Completed)", 22.0, 9.30, "Completed"),
            (3, "Semester 3 (Current Active)", 24.0, 9.45, "Projected Target"),
            (4, "Semester 4 (Year 2 Renewal Gate)", 24.0, 9.40, "Projected Target"),
            (5, "Semester 5 (Internship App Gate)", 23.0, 9.38, "Planned"),
            (6, "Semester 6 (Year 3 Renewal Gate)", 23.0, 9.42, "Planned"),
        ]
        cur.executemany(
            "INSERT INTO dim_semester_grades VALUES (?, ?, ?, ?, ?)", seed_semesters
        )

    # Seed baseline roadmap tasks reflecting exact user profile
    cur.execute("SELECT COUNT(*) FROM dim_roadmap_tasks")
    if cur.fetchone()[0] == 0:
        seed_tasks = [
            ("Baseline", "Python & AI", "Complete Cisco Python Essentials 1 & NumPy Foundations", "Certificate & Array scripts verified", 1),
            ("Baseline", "Python & AI", "Implement OOP, Inheritance, Exception & File Handling (Voice ATM)", "Functional Python OOP codebase", 1),
            ("Baseline", "DSA", "Study Linked Lists & Legacy Turbo C Implementations", "Conceptual pointer mastery", 1),
            ("Baseline", "BI & Minor", "Study BI Theory: ETL, Star/Snowflake Schemas, Chart Selection", "Exam preparation notes", 1),
            ("Sem 3", "Academic", "Achieve >= 9.45 SGPA in Sem 3 to push CGPA from 9.29 to 9.343", "Amizone Sem 3 Grade Card", 0),
            ("Sem 3", "Python & AI", "Refactor Voice ATM OOP into Biopython Sequence Hierarchy Package", "GitHub repo with unit tests", 0),
            ("Sem 3", "DSA", "Migrate from Turbo C to Modern C++20/Python 3.12; Solve 25 LeetCode + 15 Rosalind", "Public Rosalind & LeetCode profile", 0),
            ("Sem 3", "BI & Minor", "Deploy Star-Schema SQLite/DuckDB Warehouse & Streamlit Dashboard", "Live Streamlit Cloud deployment", 0),
            ("Sem 4", "Academic", "Pass Year 2 Amity 100% Scholarship Audit (CGPA >= 9.30 & Top 5% / Rank 1)", "Amizone Scholarship Renewal Confirmation", 0),
            ("Sem 4", "Python & AI", "Master scikit-learn & scanpy Single-Cell RNA-seq PCA/UMAP Pipelines", "End-to-end Jupyter/Streamlit scRNA workflow", 0),
            ("Sem 4", "DSA", "Implement Needleman-Wunsch & Smith-Waterman DP Alignment from Scratch", "40 Rosalind + 75 LeetCode problems solved", 0),
            ("Sem 5", "Global MSc", "Submit AICTE-Mitacs GRI (Canada) & DAAD WISE (€900/mo Germany) Applications", "Submitted portal receipts + 2 Faculty LORs", 0),
            ("Sem 5", "Python & AI", "Train PyTorch CNN/GNN & ESM-2 Protein Language Models on Genomics Data", "Model checkpoints + validation ROC curves", 0),
            ("Sem 6", "Global MSc", "Execute 8-12 Week Summer Research Internship & Complete IELTS (7.5+) / GRE", "Internship completion & official test scores", 0),
            ("Sem 7", "Global MSc", "Apply to ETH Zurich ESOP (CHF 12k/sem) & Canadian Research MSc (UBC GSAT)", "November/December application submissions", 0),
            ("Sem 8", "Global MSc", "Submit Paris-Saclay IDEX (€10k/yr) & Prepare Italy ER.GO DSU (ISEE <= €25k)", "March IDEX & July/Aug DSU filings", 0),
        ]
        cur.executemany(
            "INSERT INTO dim_roadmap_tasks (semester_tag, pillar, task_title, verification_metric, completed) VALUES (?, ?, ?, ?, ?)",
            seed_tasks,
        )

    # Seed an initial daily log entry so persistent memory is immediately visible on first launch
    cur.execute("SELECT COUNT(*) FROM fact_daily_logs")
    if cur.fetchone()[0] == 0:
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        initial_reflection = (
            "Baseline Initialization Log: Currently in 3rd Semester B.Tech Bioinformatics at Amity University Jaipur "
            "with a Data Analytics Minor. Last reported CGPA is 9.29 (need 9.30+ for 100% scholarship continuation). "
            "Completed Cisco Python Essentials 1, NumPy, OOP/file/exception handling, and Voice ATM project. "
            "Studying BI theory (ETL, Star and Snowflake schemas, chart selection) for exams and transitioning "
            "DSA practice from Turbo C linked lists to independent problem solving."
        )
        initial_priorities = (
            "1) Review Star vs Snowflake schema normalization for BI exam; "
            "2) Solve 1 Linked List problem in Python 3 / C++20 on LeetCode and 1 DNA counting problem on Rosalind; "
            "3) Protect 2 hours for high-credit Bioinformatics core subject to target 9.45 SGPA."
        )
        initial_schedule = (
            "07:00 - 08:00 | Morning DSA Sprint: Migrate Linked List node class from Turbo C to Python/C++20 + 1 Rosalind problem\n"
            "09:00 - 16:30 | Amity University Jaipur Lectures & Wet/Dry Labs (100% attendance compliance)\n"
            "17:30 - 19:00 | High-Credit Core Bioinformatics Revision (Targeting A+ for 9.29 -> 9.34+ CGPA recovery)\n"
            "19:30 - 21:00 | Data Analytics Minor: ETL & Star/Snowflake Schema Diagramming + Exam Prep\n"
            "21:30 - 22:30 | Python Refactoring: Convert ATM OOP File/Exception Handling into FASTA Sequence Parser"
        )
        cur.execute(
            """
            INSERT INTO fact_daily_logs (
                date_key, study_hours_bio_core, study_hours_python_ai,
                study_hours_dsa, study_hours_bi_minor, leetcode_solved,
                rosalind_solved, written_reflection, tomorrow_priorities,
                ai_generated_schedule, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                yesterday_str, 2.0, 1.5, 1.0, 1.5, 1, 1,
                initial_reflection, initial_priorities, initial_schedule,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    conn.commit()
    conn.close()

init_star_schema_warehouse()

# ==============================================================================
# 3. MANDATORY END-OF-PAGE INSTRUCTIONS TABLE RENDERER
# ==============================================================================
def render_instructions_table(page_name: str, instructions_rows: list):
    st.markdown("---")
    st.markdown(
        f"<div class='section-banner'>📋 Operational Instructions Table — {page_name}</div>",
        unsafe_allow_html=True,
    )
    df_inst = pd.DataFrame(
        instructions_rows,
        columns=[
            "Step ID",
            "Dashboard Component / Control",
            "Operational Action Required",
            "Expected Telemetry / Persistence Outcome",
        ],
    )
    st.table(df_inst)

# ==============================================================================
# 4. SIDEBAR: API CONFIGURATION, MEMORY BACKUP & NAVIGATION
# ==============================================================================
st.sidebar.title("🧬 BioAI Command Center")
st.sidebar.caption("B.Tech Bioinformatics | Amity Jaipur | Minor: Data Analytics")

page = st.sidebar.radio(
    "Navigate Command Pages:",
    [
        "1. Executive Telemetry & CGPA Simulator",
        "2. Persistent AI Daily Scheduler & Memory",
        "3. Interactive Roadmap & Skill Matrix",
        "4. BI Warehouse (Star/Snowflake Explorer)",
        "5. Global MSc Financial & Scholarship Planner",
    ],
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔑 AI Memory Engine Configuration")
api_provider = st.sidebar.selectbox(
    "Select LLM Provider:",
    [
        "Groq Free API (llama-3.3-70b-versatile)",
        "OpenAI API (gpt-4o-mini)",
        "Google Gemini Free API (gemini-2.5-flash)",
        "Offline Rule-Based Engine (No Key Needed)",
    ],
)

api_key_input = st.sidebar.text_input(
    "Enter API Key (OpenAI / Groq / Gemini):",
    type="password",
    help="Groq (console.groq.com) and Google AI Studio offer free API keys compatible with the OpenAI client.",
)

# Portable JSON Backup / Restore for Streamlit Cloud Persistence
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Cloud Memory Snapshot")
conn_backup = get_connection()
logs_backup_df = pd.read_sql("SELECT * FROM fact_daily_logs ORDER BY date_key DESC", conn_backup)
tasks_backup_df = pd.read_sql("SELECT * FROM dim_roadmap_tasks", conn_backup)
conn_backup.close()

backup_payload = json.dumps(
    {
        "logs": logs_backup_df.to_dict(orient="records"),
        "tasks": tasks_backup_df.to_dict(orient="records"),
    },
    indent=2,
)
st.sidebar.download_button(
    label="⬇️ Download Memory Snapshot (.json)",
    data=backup_payload,
    file_name=f"bioai_memory_backup_{date.today().isoformat()}.json",
    mime="application/json",
)

uploaded_backup = st.sidebar.file_uploader("⬆️ Restore Memory Snapshot (.json)", type=["json"])
if uploaded_backup is not None:
    try:
        restored_data = json.load(uploaded_backup)
        conn_r = get_connection()
        cur_r = conn_r.cursor()
        for row in restored_data.get("logs", []):
            cur_r.execute(
                """
                INSERT OR REPLACE INTO fact_daily_logs (
                    date_key, study_hours_bio_core, study_hours_python_ai,
                    study_hours_dsa, study_hours_bi_minor, leetcode_solved,
                    rosalind_solved, written_reflection, tomorrow_priorities,
                    ai_generated_schedule, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["date_key"], row["study_hours_bio_core"], row["study_hours_python_ai"],
                    row["study_hours_dsa"], row["study_hours_bi_minor"], row["leetcode_solved"],
                    row["rosalind_solved"], row["written_reflection"], row["tomorrow_priorities"],
                    row["ai_generated_schedule"], row["updated_at"],
                ),
            )
        conn_r.commit()
        conn_r.close()
        st.sidebar.success("Memory snapshot restored into SQLite Star Schema!")
    except Exception as e:
        st.sidebar.error(f"Restore error: {e}")

# ==============================================================================
# PAGE 1: EXECUTIVE TELEMETRY & AMITY CGPA SIMULATOR
# ==============================================================================
if page == "1. Executive Telemetry & CGPA Simulator":
    st.title("📊 Executive Telemetry & Amity 9.30+ Scholarship Simulator")
    st.markdown(
        "Real-time monitoring of the **9.29 CGPA baseline** against Amity University Jaipur's **9.30+ (100% Merit Waiver)** continuation floor, integrated with cumulative problem-solving velocity."
    )

    conn = get_connection()
    df_sem = pd.read_sql("SELECT * FROM dim_semester_grades ORDER BY semester_id", conn)
    df_logs = pd.read_sql("SELECT * FROM fact_daily_logs ORDER BY date_key", conn)
    df_tasks = pd.read_sql("SELECT * FROM dim_roadmap_tasks", conn)
    conn.close()

    # Compute KPIs
    completed_sems = df_sem[df_sem["semester_id"] <= 2]
    current_cgpa = (completed_sems["credits"] * completed_sems["sgpa"]).sum() / completed_sems["credits"].sum()
    total_lc = int(df_logs["leetcode_solved"].sum())
    total_ros = int(df_logs["rosalind_solved"].sum())
    task_pct = round(100.0 * df_tasks["completed"].sum() / len(df_tasks), 1)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"<div class='metric-card-alert'><h4>Current Reported CGPA</h4><h2>{current_cgpa:.2f} / 10.0</h2><p>Deficit to 9.30 Floor: <b>-0.01</b> (Sem 4 Audit Gate)</p></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<div class='metric-card'><h4>DSA & Bio-Algorithms</h4><h2>{total_lc} LC | {total_ros} Ros</h2><p>Sem 4 Target: 75 LeetCode + 40 Rosalind</p></div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"<div class='metric-card'><h4>Roadmap Completion</h4><h2>{task_pct}%</h2><p>{int(df_tasks['completed'].sum())} of {len(df_tasks)} Milestones Verified</p></div>",
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            "<div class='metric-card'><h4>Small-Batch Rule Alert</h4><h2>Rank 1 Gate</h2><p>If Batch Size < 20, 100% Waiver requires Rank 1 + 9.30</p></div>",
            unsafe_allow_html=True,
        )

    st.subheader("🎯 Interactive Semester 3 & 4 SGPA Recovery Simulator")
    s_col1, s_col2, s_col3 = st.columns(3)
    with s_col1:
        sim_s3_sgpa = st.slider("Projected Semester 3 SGPA:", 8.50, 10.00, 9.45, 0.01)
        sim_s3_cred = st.number_input("Semester 3 Credits (incl. Minor):", 18.0, 30.0, 24.0, 1.0)
    with s_col2:
        sim_s4_sgpa = st.slider("Projected Semester 4 SGPA:", 8.50, 10.00, 9.40, 0.01)
        sim_s4_cred = st.number_input("Semester 4 Credits (incl. Minor):", 18.0, 30.0, 24.0, 1.0)
    with s_col3:
        batch_size = st.number_input("B.Tech Bioinformatics Cohort Size (N):", 5, 120, 18, 1)
        rank_rule = "Rank 1 Mandatory (Batch < 20)" if batch_size < 20 else f"Top 5% (Top {max(1, int(batch_size*0.05))} Rank)"

    base_points = 9.29 * 44.0
    cgpa_after_s3 = (base_points + sim_s3_sgpa * sim_s3_cred) / (44.0 + sim_s3_cred)
    cgpa_after_s4 = (base_points + sim_s3_sgpa * sim_s3_cred + sim_s4_sgpa * sim_s4_cred) / (44.0 + sim_s3_cred + sim_s4_cred)

    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        fig_traj = go.Figure()
        sem_labels = ["Sem 1", "Sem 2 (Baseline)", "Sem 3 (Simulated)", "Sem 4 (Audit Gate)"]
        cgpa_vals = [9.28, 9.29, round(cgpa_after_s3, 3), round(cgpa_after_s4, 3)]
        fig_traj.add_trace(
            go.Scatter(
                x=sem_labels,
                y=cgpa_vals,
                mode="lines+markers+text",
                text=[f"{v:.3f}" for v in cgpa_vals],
                textposition="top center",
                line=dict(color="#1A73E8", width=4),
                marker=dict(size=10),
                name="Simulated Cumulative CGPA",
            )
        )
        fig_traj.add_hline(
            y=9.30,
            line_dash="dash",
            line_color="#D93025",
            annotation_text="9.30 (100% Waiver Cutoff)",
            annotation_position="bottom right",
        )
        fig_traj.add_hline(
            y=8.80,
            line_dash="dot",
            line_color="#FA903E",
            annotation_text="8.80 (50% Waiver Cutoff)",
            annotation_position="bottom right",
        )
        fig_traj.update_layout(
            title=f"Cumulative CGPA Trajectory (Post-Sem 4 Audit: {cgpa_after_s4:.3f} | Cohort Rule: {rank_rule})",
            yaxis=dict(range=[8.70, 9.65], title="Cumulative CGPA"),
            template="plotly_white",
            height=380,
        )
        st.plotly_chart(fig_traj, use_container_width=True)

    with c_chart2:
        hours_totals = {
            "Core Bioinformatics": df_logs["study_hours_bio_core"].sum(),
            "Python & AI Models": df_logs["study_hours_python_ai"].sum(),
            "DSA (C++20 / Python)": df_logs["study_hours_dsa"].sum(),
            "BI & Data Analytics Minor": df_logs["study_hours_bi_minor"].sum(),
        }
        df_hours = pd.DataFrame(
            {"Domain": list(hours_totals.keys()), "Cumulative Hours": list(hours_totals.values())}
        )
        fig_bar = px.bar(
            df_hours,
            x="Cumulative Hours",
            y="Domain",
            orientation="h",
            text_auto=".1f",
            color="Domain",
            color_discrete_sequence=["#1A73E8", "#12B5CB", "#FA903E", "#81C995"],
            title="Cumulative Deep-Work Hours Logged by Technical Domain",
        )
        fig_bar.update_layout(template="plotly_white", showlegend=False, height=380)
        st.plotly_chart(fig_bar, use_container_width=True)

    render_instructions_table(
        "Page 1: Executive Telemetry & CGPA Simulator",
        [
            ["P1-A", "Semester 3 & 4 SGPA Sliders", "Adjust projected SGPA and credit weights (including Data Analytics Minor credits) to model the exact cumulative CGPA at the Year 2 audit gate.", "Live recalculation of Post-Sem 3 and Post-Sem 4 CGPA against the red 9.30 threshold line."],
            ["P1-B", "Cohort Size (N) Input", "Input exact student count in B.Tech Bioinformatics at Amity Jaipur.", "Switches the eligibility badge between Top 5% (N >= 20) and Rank 1 Only (N < 20)."],
            ["P1-C", "Deep-Work Hours Bar Chart", "Inspect cumulative hours across Core Bioinformatics, Python/AI, DSA, and BI Minor.", "Identifies neglected study pillars before mid-semester and end-semester examinations."],
        ],
    )

# ==============================================================================
# PAGE 2: PERSISTENT AI DAILY SCHEDULER & MEMORY ENGINE
# ==============================================================================
elif page == "2. Persistent AI Daily Scheduler & Memory":
    st.title("🧠 Persistent AI Daily Time-Scheduler & Memory Recall")
    st.markdown(
        "This module permanently remembers what was written in previous sessions using the embedded **SQLite Star Schema (`fact_daily_logs`)** and injects that historical memory into the LLM to synthesize an adaptive daily schedule."
    )

    conn = get_connection()
    df_history = pd.read_sql("SELECT * FROM fact_daily_logs ORDER BY date_key DESC LIMIT 7", conn)
    conn.close()

    # Display Last Recorded Entry (Proof of Persistent Memory)
    if not df_history.empty:
        last_row = df_history.iloc[0]
        st.markdown(
            f"""
            <div class='memory-box'>
                <h4>📌 Recalled Memory from Last Session ({last_row['date_key']} | Updated: {last_row['updated_at']})</h4>
                <p><b>What Was Written Last Time (Reflection & Progress):</b> {last_row['written_reflection']}</p>
                <p><b>Carried-Over Priorities for Today:</b> {last_row['tomorrow_priorities']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col_form, col_sched = st.columns([1, 1])

    with col_form:
        st.subheader("✍️ Log Today's Progress & Write Memory Notes")
        selected_date = st.date_input("Log Date:", value=date.today()).isoformat()

        # Pre-populate if entry already exists for selected_date
        existing_row = df_history[df_history["date_key"] == selected_date]
        def_bio = float(existing_row["study_hours_bio_core"].iloc[0]) if not existing_row.empty else 2.0
        def_py = float(existing_row["study_hours_python_ai"].iloc[0]) if not existing_row.empty else 1.5
        def_dsa = float(existing_row["study_hours_dsa"].iloc[0]) if not existing_row.empty else 1.0
        def_bi = float(existing_row["study_hours_bi_minor"].iloc[0]) if not existing_row.empty else 1.0
        def_lc = int(existing_row["leetcode_solved"].iloc[0]) if not existing_row.empty else 1
        def_ros = int(existing_row["rosalind_solved"].iloc[0]) if not existing_row.empty else 1
        def_ref = existing_row["written_reflection"].iloc[0] if not existing_row.empty else ""
        def_prio = existing_row["tomorrow_priorities"].iloc[0] if not existing_row.empty else ""

        h1, h2 = st.columns(2)
        with h1:
            hrs_bio = st.number_input("Core Bioinformatics Hours:", 0.0, 12.0, def_bio, 0.5)
            hrs_py = st.number_input("Python / Biopython / AI Hours:", 0.0, 12.0, def_py, 0.5)
            lc_cnt = st.number_input("LeetCode Problems Solved Today:", 0, 20, def_lc, 1)
        with h2:
            hrs_dsa = st.number_input("DSA (C++20 / Python) Hours:", 0.0, 12.0, def_dsa, 0.5)
            hrs_bi = st.number_input("BI & Data Analytics Minor Hours:", 0.0, 12.0, def_bi, 0.5)
            ros_cnt = st.number_input("Rosalind Bio-Problems Solved:", 0, 20, def_ros, 1)

        lecture_window = st.text_input(
            "Fixed Amity University Class/Lab Window Tomorrow:",
            value="09:15 - 16:30 (Lectures & Bioinformatics Labs)",
        )
        written_reflection = st.text_area(
            "What Was Accomplished or Struggled With Today? (Stored in Persistent Memory):",
            value=def_ref,
            height=110,
            placeholder="Example: Finished Star vs Snowflake schema notes for BI exam; struggled with pointer edge cases in doubly linked list deletion; need to revise Molecular Biology Unit 2.",
        )
        tomorrow_priorities = st.text_area(
            "Top 3 Non-Negotiable Targets for Tomorrow:",
            value=def_prio,
            height=90,
            placeholder="Example: 1) Implement FASTQ parser in Python; 2) Solve LeetCode #206 Reverse Linked List in C++20; 3) Complete 90-min revision of 4-credit Bioinformatics core paper.",
        )

        generate_btn = st.button("🚀 Save to SQLite Memory & Generate Adaptive AI Schedule", type="primary")

    with col_sched:
        st.subheader("🗓️ AI-Synthesized Time-Blocked Daily Schedule")

        if generate_btn:
            # Build historical context from past 5 logs
            history_context_lines = []
            for _, r in df_history.head(5).iterrows():
                history_context_lines.append(
                    f"- Date {r['date_key']}: Bio={r['study_hours_bio_core']}h, Py={r['study_hours_python_ai']}h, "
                    f"DSA={r['study_hours_dsa']}h, BI={r['study_hours_bi_minor']}h | "
                    f"Wrote: '{r['written_reflection']}' | Priorities: '{r['tomorrow_priorities']}'"
                )
            history_context = "\n".join(history_context_lines)

            system_prompt = (
                "Act as an elite Academic & AI Career Strategist for a 3rd-semester B.Tech Bioinformatics student "
                "at Amity University Jaipur (Minor: Data Analytics, Current CGPA: 9.29, immediate goal: >=9.30 CGPA "
                "for 100% scholarship renewal and preparation for an AI MSc abroad at Paris-Saclay, ETH Zurich, or Italy DSU). "
                "Review the candidate's persistent historical logs and today's newly written reflection, then output a highly "
                "structured, hour-by-hour time-blocked schedule from 06:30 to 23:00 that respects fixed university lecture hours, "
                "addresses carry-over bottlenecks from previous days, and balances 4-credit core subjects, DSA (C++20/Python + Rosalind), "
                "Python/Biopython refactoring, and BI Star/Snowflake implementation."
            )
            user_prompt = (
                f"HISTORICAL MEMORY FROM PREVIOUS SESSIONS:\n{history_context}\n\n"
                f"NEW ENTRY WRITTEN ON {selected_date}:\n"
                f"- Fixed University Window: {lecture_window}\n"
                f"- Today's Reflection: {written_reflection}\n"
                f"- Tomorrow's Non-Negotiable Priorities: {tomorrow_priorities}\n\n"
                "Generate a precise hour-by-hour schedule table and 3 tactical coaching notes referencing what was written last time."
            )

            generated_schedule_text = ""
            if api_provider != "Offline Rule-Based Engine (No Key Needed)" and api_key_input and OPENAI_SDK_AVAILABLE:
                try:
                    if "Groq" in api_provider:
                        client = OpenAI(api_key=api_key_input, base_url="https://api.groq.com/openai/v1")
                        model_name = "llama-3.3-70b-versatile"
                    elif "Gemini" in api_provider:
                        client = OpenAI(
                            api_key=api_key_input,
                            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                        )
                        model_name = "gemini-2.5-flash"
                    else:
                        client = OpenAI(api_key=api_key_input)
                        model_name = "gpt-4o-mini"

                    resp = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,
                    )
                    generated_schedule_text = resp.choices[0].message.content
                except Exception as api_err:
                    st.warning(f"API call encountered an issue ({api_err}). Using deterministic memory-aware engine.")

            if not generated_schedule_text:
                last_note = df_history.iloc[0]["written_reflection"] if not df_history.empty else "Initial baseline."
                generated_schedule_text = (
                    f"### Memory-Linked Adaptive Schedule (Target Date: {selected_date})\n"
                    f"* **Memory Continuity Check**: Incorporating prior reflection (*\"{last_note[:120]}...\"*) and today's priorities (*\"{tomorrow_priorities}\"*).\n\n"
                    "| Time Block | Allocated Track | Specific Deliverable & Cognitive Focus |\n"
                    "| :--- | :--- | :--- |\n"
                    "| **06:30 - 07:45** | **DSA & Rosalind Sprint** | 1 LeetCode Linked List/Tree problem in C++20/Python + 1 Rosalind string algorithm (Zero AI assistance). |\n"
                    "| **07:45 - 09:00** | **Morning Prep & Transit** | Nutrition, flashcard review of BI Star/Snowflake schema definitions, commute. |\n"
                    f"| **{lecture_window}** | **Amity University Academic Block** | Active note-taking in 4-credit Bioinformatics core courses; use free periods for BI ETL SQL queries. |\n"
                    "| **17:00 - 18:45** | **CGPA 9.45+ Core Theory Block** | High-weightage B.Tech Bioinformatics core revision (Directly protects the 9.30+ 100% scholarship floor). |\n"
                    "| **19:00 - 20:15** | **Data Analytics Minor (BI)** | Implement ETL & Star-Schema queries in SQLite/Streamlit; practice perceptual chart selection. |\n"
                    "| **20:45 - 22:00** | **Python & Biopython Engineering** | Refactor OOP/Exception handling into genomic sequence parsers and NumPy vectorization. |\n"
                    "| **22:00 - 22:30** | **Persistent Memory Log** | Write daily reflection in this Streamlit terminal to prime tomorrow's context window. |"
                )

            # Save into SQLite Fact Table
            conn_w = get_connection()
            cur_w = conn_w.cursor()
            cur_w.execute(
                """
                INSERT OR REPLACE INTO fact_daily_logs (
                    date_key, study_hours_bio_core, study_hours_python_ai,
                    study_hours_dsa, study_hours_bi_minor, leetcode_solved,
                    rosalind_solved, written_reflection, tomorrow_priorities,
                    ai_generated_schedule, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    selected_date, hrs_bio, hrs_py, hrs_dsa, hrs_bi,
                    lc_cnt, ros_cnt, written_reflection, tomorrow_priorities,
                    generated_schedule_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn_w.commit()
            conn_w.close()
            st.success(f"Saved entry for {selected_date} to SQLite database!")

        # Display latest saved schedule
        conn_s = get_connection()
        latest_sched_df = pd.read_sql("SELECT * FROM fact_daily_logs ORDER BY date_key DESC LIMIT 1", conn_s)
        conn_s.close()
        if not latest_sched_df.empty:
            st.markdown(latest_sched_df.iloc[0]["ai_generated_schedule"])

    st.subheader("📜 Historical Memory Log Archive (SQLite `fact_daily_logs`)")
    conn_a = get_connection()
    df_archive = pd.read_sql(
        "SELECT date_key AS Date, study_hours_bio_core AS Bio_Hrs, study_hours_python_ai AS Py_Hrs, "
        "study_hours_dsa AS DSA_Hrs, study_hours_bi_minor AS BI_Hrs, leetcode_solved AS LC, "
        "rosalind_solved AS Rosalind, written_reflection AS Written_Reflection, tomorrow_priorities AS Next_Priorities "
        "FROM fact_daily_logs ORDER BY date_key DESC",
        conn_a,
    )
    conn_a.close()
    st.dataframe(df_archive, use_container_width=True)

    render_instructions_table(
        "Page 2: Persistent AI Daily Scheduler & Memory",
        [
            ["P2-A", "Sidebar API Key & Provider Selector", "Select Groq Free API (console.groq.com), Gemini Free API, or OpenAI API and paste the key, or run in Offline Rule-Based mode.", "Activates the OpenAI-compatible client to synthesize context-aware schedules."],
            ["P2-B", "Green Recalled Memory Banner", "Review the top banner showing the exact text written during the previous session.", "Ensures zero unfinished tasks or exam bottlenecks are forgotten between days."],
            ["P2-C", "Reflection & Priority Text Areas", "Write today's study outcomes and tomorrow's 3 priorities, then click 'Save to SQLite Memory & Generate Adaptive AI Schedule'.", "Commits the record into `career_memory.db` (`fact_daily_logs`) and generates the time-blocked plan."],
            ["P2-D", "Sidebar JSON Snapshot Buttons", "Click 'Download Memory Snapshot (.json)' weekly when hosted on Streamlit Community Cloud.", "Provides a portable local backup that can be re-uploaded anytime via 'Restore Memory Snapshot'."],
        ],
    )

# ==============================================================================
# PAGE 3: INTERACTIVE ROADMAP & SKILL TRANSFORMATION MATRIX
# ==============================================================================
elif page == "3. Interactive Roadmap & Skill Matrix":
    st.title("🗺️ Interactive Semester 3–8 Roadmap & Skill Transformation Matrix")
    st.markdown(
        "Toggle milestone completion status directly below to update the persistent SQLite `dim_roadmap_tasks` dimension table."
    )

    conn = get_connection()
    df_tasks = pd.read_sql("SELECT * FROM dim_roadmap_tasks ORDER BY task_id", conn)
    conn.close()

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        sem_filter = st.multiselect(
            "Filter by Semester:",
            options=df_tasks["semester_tag"].unique().tolist(),
            default=df_tasks["semester_tag"].unique().tolist(),
        )
    with f_col2:
        pillar_filter = st.multiselect(
            "Filter by Competency Pillar:",
            options=df_tasks["pillar"].unique().tolist(),
            default=df_tasks["pillar"].unique().tolist(),
        )

    filtered_tasks = df_tasks[
        df_tasks["semester_tag"].isin(sem_filter) & df_tasks["pillar"].isin(pillar_filter)
    ]

    # Visual breakdown by pillar
    pillar_summary = (
        df_tasks.groupby("pillar")
        .agg(Total=("task_id", "count"), Completed=("completed", "sum"))
        .reset_index()
    )
    pillar_summary["Completion %"] = (100.0 * pillar_summary["Completed"] / pillar_summary["Total"]).round(1)

    fig_pillar = px.bar(
        pillar_summary,
        x="pillar",
        y="Completion %",
        color="pillar",
        text="Completion %",
        color_discrete_sequence=["#1A73E8", "#12B5CB", "#FA903E", "#81C995"],
        title="Competency Pillar Completion Percentage Across All Semesters",
    )
    fig_pillar.update_layout( yaxis=dict(range=[0, 105]), template="plotly_white", height=320)
    st.plotly_chart(fig_pillar, use_container_width=True)

    st.subheader("✅ Interactive Milestone Checklist (Persisted in SQLite)")
    conn_u = get_connection()
    cur_u = conn_u.cursor()
    for _, row in filtered_tasks.iterrows():
        checked = st.checkbox(
            f"**[{row['semester_tag']} | {row['pillar']}]** {row['task_title']} — *Verification: {row['verification_metric']}*",
            value=bool(row["completed"]),
            key=f"task_{row['task_id']}",
        )
        if int(checked) != int(row["completed"]):
            cur_u.execute(
                "UPDATE dim_roadmap_tasks SET completed = ? WHERE task_id = ?",
                (int(checked), int(row["task_id"])),
            )
            conn_u.commit()
            st.rerun()
    conn_u.close()

    render_instructions_table(
        "Page 3: Interactive Roadmap & Skill Matrix",
        [
            ["P3-A", "Semester & Pillar Multiselect Filters", "Filter milestones by specific semesters (e.g., Sem 3, Sem 4) or technical domains (DSA, Python & AI, BI & Minor, Global MSc).", "Focuses the viewport on immediate semester deliverables."],
            ["P3-B", "Interactive Milestone Checkboxes", "Click any checkbox once the corresponding verification artifact (GitHub repo, Rosalind badge, Amizone grade card) is achieved.", "Immediately updates `dim_roadmap_tasks` in SQLite and recalculates the bar chart above."],
        ],
    )

# ==============================================================================
# PAGE 4: BI WAREHOUSE (STAR & SNOWFLAKE SCHEMA EXPLORER)
# ==============================================================================
elif page == "4. BI Warehouse (Star/Snowflake Explorer)":
    st.title("🏛️ Business Intelligence Minor: Live Star & Snowflake Schema Lab")
    st.markdown(
        "Converts theoretical Business Intelligence exam topics (**ETL, Data Warehouses, Star vs. Snowflake Schemas, and Perceptual Chart Selection**) into an interactive query and visualization workbench."
    )

    schema_mode = st.radio(
        "Select Data Warehouse Schema Architecture to Inspect:",
        ["Star Schema (Denormalized Dimension Tables — Fast OLAP Queries)", "Snowflake Schema (Normalized Sub-Dimensions — Zero Redundancy)"],
        horizontal=True,
    )

    if "Star Schema" in schema_mode:
        st.info(
            "**Star Schema Architecture**: A single central Fact Table (`fact_daily_logs` or `fact_gene_expression`) links directly via foreign keys to flat, denormalized Dimension Tables (`dim_date`, `dim_semester_grades`, `dim_skill_pillar`). Optimal for fast aggregation with minimal `JOIN` overhead."
        )
    else:
        st.info(
            "**Snowflake Schema Architecture**: Dimension tables are further normalized into hierarchical sub-tables (e.g., `dim_roadmap_tasks` -> `dim_skill_pillar` -> `dim_msc_prerequisite_category`), reducing storage redundancy at the cost of multi-hop SQL joins."
        )

    c_bi1, c_bi2 = st.columns(2)
    with c_bi1:
        st.subheader("🔍 Live SQL OLAP Query Executor on `career_memory.db`")
        default_sql = (
            "SELECT date_key, \n"
            "       (study_hours_bio_core + study_hours_python_ai + study_hours_dsa + study_hours_bi_minor) AS total_study_hours,\n"
            "       leetcode_solved, rosalind_solved\n"
            "FROM fact_daily_logs\n"
            "ORDER BY date_key DESC;"
        )
        sql_query = st.text_area("Execute Custom SQL Query on Star Schema:", value=default_sql, height=130)
        if st.button("Run OLAP Query"):
            try:
                conn_q = get_connection()
                df_res = pd.read_sql(sql_query, conn_q)
                conn_q.close()
                st.dataframe(df_res, use_container_width=True)
            except Exception as sqle:
                st.error(f"SQL Execution Error: {sqle}")

    with c_bi2:
        st.subheader("📐 BI Exam Reference: Perceptual Chart Selection Matrix")
        df_chart_rules = pd.DataFrame(
            [
                ["Differential Gene Expression (Fold Change vs Significance)", "Volcano Scatter Plot (-log10 p vs log2 FC)", "Pie Chart / 3D Bar Chart (Distorts dual continuous axes)"],
                ["Single-Cell Gene Expression Distributions Across Clusters", "Violin Plot / Box Plot with Jitter", "Simple Mean Bar Chart (Hides multimodality & skew)"],
                ["Patient Cohort Survival Over Time", "Kaplan-Meier Step Curve with Censored Marks", "Standard Line Chart (Ignores right-censoring)"],
                ["Hierarchical Multi-Omics / Skill Time Allocation", "Treemap / Sunburst / Marimekko", "Multi-Series Stacked Pie Charts"],
            ],
            columns=["Analytical Question / Data Relationship", "Optimal BI Visualization", "Anti-Pattern to Avoid in Exams & Production"],
        )
        st.dataframe(df_chart_rules, use_container_width=True)

    render_instructions_table(
        "Page 4: BI Warehouse (Star/Snowflake Explorer)",
        [
            ["P4-A", "Schema Architecture Radio Toggle", "Switch between Star Schema and Snowflake Schema modes before BI theory examinations.", "Reinforces structural trade-offs (query speed vs. normalization) using the app's own backend."],
            ["P4-B", "Live SQL OLAP Query Executor", "Write `SELECT`, `GROUP BY`, and `JOIN` queries against `fact_daily_logs` and `dim_roadmap_tasks`.", "Provides hands-on SQL warehousing practice directly transferable to the Data Analytics Minor."],
            ["P4-C", "Perceptual Chart Selection Matrix", "Review the optimal vs. anti-pattern chart mappings for biological and business datasets.", "Prepares the candidate for both university BI exams and MSc research visualization standards."],
        ],
    )

# ==============================================================================
# PAGE 5: GLOBAL MSc FINANCIAL & SCHOLARSHIP PLANNER (2026/2027 VERIFIED DATA)
# ==============================================================================
elif page == "5. Global MSc Financial & Scholarship Planner":
    st.title("🌍 Global AI & Bioinformatics MSc Financial Telemetry (2026/2027)")
    st.markdown(
        "Cross-verified financial calculator incorporating **Germany's €11,904 Blocked Account & India's 2% TCS rule (effective 1 April 2026)**, **Italy's ER.GO DSU (€7,171.11–€8,246.78/yr & €25,000 ISEE cap)**, **Paris-Saclay IDEX (€10,000/yr + €1,000 travel)**, and **ETH Zurich ESOP (CHF 24,000/yr)**."
    )

    eur_inr_rate = st.slider("EUR to INR Exchange Rate (Oct 2026 Reference: ₹108.12 - ₹109.99):", 95.0, 120.0, 108.12, 0.1)

    col_g, col_i = st.columns(2)
    with col_g:
        st.subheader("🇩🇪 Germany Blocked Account & India 2% TCS Calculator")
        de_provider = st.selectbox(
            "Select Blocked Account Provider (Deutsche Bank closed; Coracle paused):",
            ["Expatrio (€119 setup + €9/mo | Full Refund on Visa Refusal)", "Fintiba (€159 setup + €9.90/mo | German Bank)", "Care Concept (€50 setup + €4.90/mo)"],
        )
        loan_funded = st.checkbox("Funded via Qualifying Education Loan? (0% TCS vs 2% TCS above ₹10L)", value=False)

        base_blocked_eur = 11904.0
        if "Expatrio" in de_provider:
            fees_eur = 119.0 + 12 * 9.0
        elif "Fintiba" in de_provider:
            fees_eur = 159.0 + 12 * 9.90
        else:
            fees_eur = 50.0 + 12 * 4.90

        total_eur = base_blocked_eur + fees_eur
        principal_inr = total_eur * eur_inr_rate
        tcs_inr = 0.0 if loan_funded else max(0.0, (principal_inr - 1000000.0) * 0.02)
        gst_inr = 1046.0
        total_outflow_inr = principal_inr + tcs_inr + gst_inr

        st.markdown(
            f"""
            <div class='metric-card'>
                <h4>Germany Total Remittance Outflow (12 Months)</h4>
                <h2>₹{total_outflow_inr:,.0f} ({total_eur:,.2f} EUR)</h2>
                <p>Blocked Principal: €11,904 (€992/mo release) | Provider Fees: €{fees_eur:.2f}</p>
                <p>TCS (2% above ₹10L from 1 Apr 2026): <b>₹{tcs_inr:,.0f}</b> (Claimable in ITR) | Est. GST: ₹{gst_inr:,.0f}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_i:
        st.subheader("🇮🇹 Italy DSU (ER.GO Bologna / Padua / Milan) Simulator")
        family_isee = st.number_input("Estimated Family ISEE Parificato (EUR/year):", 5000.0, 40000.0, 12000.0, 500.0)
        if family_isee <= 12500:
            ergo_grant = 8246.78
            band_status = "Top Band + 15% Ultra-Low Income Bonus (ISEE <= €12,500)"
        elif family_isee <= 16666.67:
            ergo_grant = 7171.11
            band_status = "Top Fuori Sede Band (ISEE <= €16,666.67)"
        elif family_isee <= 25000:
            ergo_grant = 4661.22
            band_status = "Partial Fuori Sede Band + 100% Tuition Waiver (ISEE <= €25,000)"
        else:
            ergo_grant = 0.0
            band_status = "Above ER.GO €25,000 Cap (Eligible for Bologna €1,157.04 Non-OECD Flat Tuition)"

        st.markdown(
            f"""
            <div class='metric-card'>
                <h4>Projected ER.GO (Bologna) Annual DSU Grant</h4>
                <h2>€{ergo_grant:,.2f} / yr (~₹{ergo_grant * eur_inr_rate:,.0f})</h2>
                <p>Status: <b>{band_status}</b></p>
                <p>Retention Gate: 9 CFU by Feb 28 | 30 CFU by Aug 10 (20 CFU min by Nov 30) | Visa Proof: €10,179.85</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    df_msc_comp = pd.DataFrame(
        [
            ["ETH Zurich ESOP (Switzerland)", "CHF 24,000 / yr + Tuition Waiver", "Top 10% Cohort; Nov eApply + Proposal", "Covered by ESOP Grant"],
            ["Paris-Saclay IDEX (France)", "€10,000 / yr + €1,000 Travel", "Age <=30; Coordinator Pre-Selection (Mar); No external income >€600/mo", "Covered by IDEX (Public fee €243-€380)"],
            ["France Excellence Eiffel", "€1,181 / mo (€14,172/yr) + Travel", "Hyper-competitive institutional nomination", "Covered by Eiffel Award"],
            ["Italy DSU (Bologna ER.GO / Padua)", "€7,171.11 to €8,246.78 / yr + Free Tuition", "ISEE <= €25,000 (ER.GO) / €26,306 (Padua); Jul-Aug Deadline", "€10,179.85 / yr Family Bank Proof"],
            ["Politecnico di Milano Merit (Italy)", "€8,000 to €10,000 / yr + Tuition Waiver", "Merit evaluation alongside MSc admission", "€10,179.85 / yr Family Bank Proof"],
            ["Germany Public MSc (TUM / Tübingen)", "Tuition-Free (€150-€350/sem admin fee)", "High CGPA + Curriculum match", "€11,904 / yr Blocked Account (€992/mo)"],
            ["DAAD WISE Summer Internship (UG Sem 5/6)", "€900 / mo (8-12 weeks) + Travel", "Sem 5/6 Indian B.Tech (Check 80-Institute list)", "Covered by DAAD Fellowship"],
        ],
        columns=["Program / Fellowship", "Verified Grant / Stipend Value", "Strict Eligibility & Application Gate", "Visa Proof-of-Funds Requirement"],
    )
    st.subheader("📋 Cross-Verified Global MSc & Internship Reference Matrix")
    st.dataframe(df_msc_comp, use_container_width=True)

    render_instructions_table(
        "Page 5: Global MSc Financial & Scholarship Planner",
        [
            ["P5-A", "EUR to INR Exchange Rate Slider", "Calibrate the live EUR/INR remittance rate (Oct 2026 baseline: ₹108.12–₹109.99).", "Updates INR totals across both German Blocked Account and Italian DSU calculators."],
            ["P5-B", "Germany Provider & Loan Checkbox", "Compare Expatrio vs. Fintiba vs. Care Concept and toggle education loan funding.", "Computes exact principal, provider fees, and India's 2% TCS above ₹10 lakh."],
            ["P5-C", "Italy ISEE Parificato Input", "Input estimated family ISEE in Euros based on gross household income and property assets.", "Determines exact ER.GO DSU cash band (€8,246.78 max vs. €7,171.11 base) and tuition exemption status."],
        ],
    )