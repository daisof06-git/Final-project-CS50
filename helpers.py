from flask import redirect, render_template, session
from functools import wraps
from datetime import date
from cs50 import SQL

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///budget.db")

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def usd(value):
    #Format value as usd
    return f"${value:,.2f}"

def get_month_summary(user_id, year_month = None): 
    if year_month == None:
        year_month = date.today().strftime('%Y-%m')

    row = db.execute("""
    SELECT 
        SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS income,
        SUM(CASE WHEN type = 'savings' THEN amount ELSE 0 END) AS savings,
        SUM(CASE WHEN type = 'jar' THEN amount ELSE 0 END) AS jars_total
    FROM movements
    WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, user_id, year_month)[0]

    income = float(row["income"] or 0)
    savings = float(row["savings"] or 0)
    jars_total = float(row["jars_total"] or 0)

    balance = income - savings - jars_total

    return{
        "income": income,
        "savings": savings,
        "jars_total": jars_total,
        "balance": balance,
    }