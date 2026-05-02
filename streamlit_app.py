import streamlit as st
import sqlite3
import matplotlib.pyplot as plt
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import re
import pandas as pd

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(page_title="AI SQL Analyst PRO", layout="wide")

# -------------------------------
# STYLES
# -------------------------------
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #0f172a, #020617);
    color: white;
}
section[data-testid="stSidebar"] {
    background-color: #020617;
    border-right: 1px solid #1e293b;
}
.stTextInput>div>div>input {
    background-color: #1e293b;
    color: white;
    border-radius: 10px;
    padding: 12px;
    border: 1px solid #334155;
}
.stButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 10px;
    padding: 10px;
    border: none;
    font-weight: 600;
}
.card {
    background: #020617;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #1e293b;
    margin-top: 20px;
}
.result-box {
    background: #064e3b;
    padding: 15px;
    border-radius: 10px;
    font-size: 18px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# ENV + LLM
# -------------------------------
load_dotenv()

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

# -------------------------------
# CLEAN SQL
# -------------------------------
def clean_sql(sql):
    sql = sql.replace("```sql", "").replace("```", "").strip()
    match = re.search(r"(SELECT .*?;)", sql, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"(SELECT .* FROM .*?)", sql, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1) + ";"
    return ""

# -------------------------------
# SCHEMA
# -------------------------------
def get_schema(conn):
    cursor = conn.cursor()
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()
    schema = {}
    for (table,) in tables:
        cols = cursor.execute(f"PRAGMA table_info({table});").fetchall()
        schema[table] = [c[1] for c in cols]
    return schema

# -------------------------------
# AUTO FIX
# -------------------------------
def auto_fix_sql(sql, schema):
    table = list(schema.keys())[0]
    if "FROM ;" in sql.upper():
        sql = sql.replace("FROM ;", f"FROM {table};")
    if "FROM" in sql.upper() and ";" not in sql:
        sql += ";"
    return sql

# -------------------------------
# MEMORY
# -------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

def get_history():
    text = ""
    for q, s in st.session_state.history[-3:]:
        text += f"\nQ: {q}\nSQL: {s}\n"
    return text

# -------------------------------
# SIDEBAR (GENERIC NOW ✅)
# -------------------------------
with st.sidebar:
    st.header("⚙️ Controls")

    st.markdown("### 📌 Example Queries")

    if st.button("Show all data"):
        st.session_state["quick_q"] = "show all records"

    if st.button("Count rows"):
        st.session_state["quick_q"] = "count all rows"

    if st.button("Find average"):
        st.session_state["quick_q"] = "average of a numeric column"

    if st.button("Group data"):
        st.session_state["quick_q"] = "group by a column and calculate average"

    st.markdown("---")
    st.markdown("### 🧠 History")

    for q, _ in st.session_state.history[-5:]:
        st.write("•", q)

# -------------------------------
# HEADER
# -------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("<h1>🚀 AI SQL Data Analyst PRO</h1>", unsafe_allow_html=True)
st.markdown("Ask questions in plain English. Works with ANY dataset.")
st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------
# CSV UPLOAD
# -------------------------------
st.markdown("### 📂 Upload Dataset")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    st.success(f"Loaded: {uploaded_file.name}")

# -------------------------------
# DATABASE SETUP
# -------------------------------
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    conn = sqlite3.connect("dynamic.db")
    df.to_sql("data", conn, if_exists="replace", index=False)
else:
    conn = sqlite3.connect("insurance.db")

# -------------------------------
# INPUT
# -------------------------------
st.markdown("### Ask your question")

col1, col2 = st.columns([8, 2])

with col1:
    question = st.text_input(
        "",
        value=st.session_state.get("quick_q", ""),
        placeholder="Ask anything about your dataset...",
        label_visibility="collapsed"
    )

with col2:
    run = st.button("Run Query", use_container_width=True)

# -------------------------------
# MAIN EXECUTION
# -------------------------------
if run:

    if not question.strip():
        st.warning("Enter a question")
        st.stop()

    cursor = conn.cursor()
    schema = get_schema(conn)

    prompt = f"""
You are a SQL expert.

Database schema:
{schema}

Rules:
- Return ONLY SQL
- Use correct table and column names from schema
- No explanation text

Question:
{question}
"""

    response = llm.invoke(prompt)
    sql_query = clean_sql(response.content)
    sql_query = auto_fix_sql(sql_query, schema)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🧠 Generated SQL")
    st.code(sql_query, language="sql")
    st.markdown('</div>', unsafe_allow_html=True)

    try:
        cursor.execute(sql_query)
        result = cursor.fetchall()

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Result")

        if not result:
            st.write("No result")

        elif len(result) == 1 and len(result[0]) == 1:
            st.markdown(
                f'<div class="result-box">Result: {round(result[0][0], 2)}</div>',
                unsafe_allow_html=True
            )

        else:
            st.dataframe(result)

            if len(result[0]) >= 2:
                if isinstance(result[0][0], (int, float)):
                    values = [r[0] for r in result]
                    labels = [str(r[1]) for r in result]
                else:
                    labels = [str(r[0]) for r in result]
                    values = [r[1] for r in result]

                fig, ax = plt.subplots()
                ax.bar(labels, values)
                ax.set_title(question)
                st.pyplot(fig)

        st.markdown('</div>', unsafe_allow_html=True)

        st.session_state.history.append((question, sql_query))

    except Exception as e:
        st.error(f"SQL Error: {e}")

conn.close()