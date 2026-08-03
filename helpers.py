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


def get_budget_summary(user_id):
    row = db.execute("""
        SELECT 
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN type = 'savings' THEN amount ELSE 0 END) AS savings,
            SUM(CASE WHEN type = 'jar' THEN amount ELSE 0 END) AS jars_total
        FROM budget
        WHERE user_id = ?
        """, user_id)[0]
    
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


def get_savings_rate(user_id):
    summary = get_month_summary(user_id)
    income = summary["income"]

    if income > 0:
        rate = (summary["savings"]/income) * 100
        return round(rate,1)

    else:
        return None


def get_budget_deviation(actual, budget):
    if budget["jars"] == 0:
        return None

    else:
        deviation = ((actual["jars"] - budget["jars"])/budget["jars"])*100
        return round(deviation,1)


def get_top_jar(user_id):
    year_month = date.today().strftime('%Y-%m')
    rows = db.execute("""
    SELECT jars.jar_name AS jar_name, SUM(movements.amount) AS total
    FROM jars
    JOIN movements 
    ON jars.id = movements.jar_id
    WHERE movements.user_id = ? AND movements.type = 'jar' AND strftime('%Y-%m', movements.date) = ?
    ORDER BY total DESC
    LIMIT 1 
    """, user_id, year_month)

    if not rows: 
        return None

    return{"jar_name": rows[0]["jar_name"], "amount": float(rows[0]["total"])}


def get_total_saved(user_id):
    year = date.today().strftime('%Y')

    total_saved = db.execute("""
    SELECT SUM(amount) AS total
    FROM movements
    WHERE user_id = ? AND type = 'savings' AND strftime('%Y', date) = ?
    """, user_id, year)[0]["total"]

    return float(total_saved or 0)
