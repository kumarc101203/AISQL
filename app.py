import sqlite3
import matplotlib.pyplot as plt
from langchain_groq import ChatGroq

# -------------------------------
# Utility: Clean SQL from LLM output
# -------------------------------
def clean_sql(sql):
    return sql.replace("```sql", "").replace("```", "").strip()


# -------------------------------
# Step 1: Connect Database
# -------------------------------
conn = sqlite3.connect("insurance.db")
cursor = conn.cursor()

# -------------------------------
# Step 2: Initialize LLM
# -------------------------------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0
)

# -------------------------------
# Step 3: User Input
# -------------------------------
question = input("Ask your question: ")

# -------------------------------
# Step 4: Prompt (Improved)
# -------------------------------
prompt = f"""
You are a SQL expert.

Database has a table named 'insurance' with columns:
age, sex, bmi, children, smoker, region, charges

RULES:
- Return ONLY SQL query (no explanation, no markdown)
- If grouping (by smoker, region, sex), ALWAYS include that column in SELECT
- Prefer format: SELECT category, AGG(value)
- Use correct SQL syntax

Question:
{question}
"""

response = llm.invoke(prompt)
sql_query = clean_sql(response.content)

print("\nGenerated SQL:")
print(sql_query)

# -------------------------------
# Step 5: Execute SQL
# -------------------------------
try:
    cursor.execute(sql_query)
    result = cursor.fetchall()

    print("\nFinal Answer:")

    # -------------------------------
    # Case 0: No result
    # -------------------------------
    if not result:
        print("No result found.")

    # -------------------------------
    # Case 1: Single value (1 row, 1 column)
    # -------------------------------
    elif len(result) == 1 and len(result[0]) == 1:
        value = result[0][0]
        print(f"Result: {round(value, 2)}")

    # -------------------------------
    # Case 2: Multiple rows, single column
    # -------------------------------
    elif len(result) > 1 and len(result[0]) == 1:
        print("Multiple values returned:")
        for i, row in enumerate(result):
            print(f"Value {i+1}: {round(row[0], 2)}")

    # -------------------------------
    # Case 3: Label + Value (Robust Chart Handling)
    # -------------------------------
    elif len(result[0]) >= 2:
        for row in result:
            print(row)

        # 🔥 Robust detection (NO assumption about column order)
        if isinstance(result[0][0], (int, float)):
            values = [row[0] for row in result]
            labels = [str(row[1]) for row in result]
        else:
            labels = [str(row[0]) for row in result]
            values = [row[1] for row in result]

        # Plot chart
        plt.figure()
        plt.bar(labels, values)
        plt.title(question)
        plt.xlabel("Category")
        plt.ylabel("Value")
        plt.xticks(rotation=30)

        plt.show()

except Exception as e:
    print("\nSQL Error:", e)

# -------------------------------
# Step 6: Close Connection
# -------------------------------
conn.close()