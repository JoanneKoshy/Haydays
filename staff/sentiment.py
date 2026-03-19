from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def analyze_sentiment(question: str, reply: str) -> str:
    prompt = f"""
You are analyzing a staff member's reply to a daily task check-in question.

Question asked: "{question}"
Staff reply: "{reply}"

Based on the reply, did the staff member complete the task? 
Respond with ONLY one word: YES or NO.
- If the reply is positive, confirms completion, or implies yes → respond YES
- If the reply is negative, incomplete, or implies no → respond NO
- If completely unclear → respond NO
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=5,
        temperature=0
    )

    result = response.choices[0].message.content.strip().upper()
    
    if "YES" in result:
        return "YES"
    return "NO"