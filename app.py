import os
import sqlite3
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, usd

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///budget.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    id = session["user_id"]
    jars = db.execute("SELECT * FROM jars WHERE user_id = ?", id)
    if request.method == "GET":
        return render_template("index.html", jars = jars)

@app.route("/login", methods = ["GET", "POST"])
def login():
    #log user in
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", error = "Must provide a username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", error = "Must provide a password")

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return render_template("login.html", error = "Incorrect username or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/income", methods = ["GET", "POST"])
@login_required
def add_income():
    if request.method == "POST": 
        id = session["user_id"]
    if request.method == "POST":
        income = request.form.get("income")

        # Validate income
        if not income:
            return render_template("income.html", error = "Must insert a positive amount")
        try:
            income = float(income)
        except ValueError:
            return render_template("income.html", error = "Must insert a positive amount")
        if income <= 0:
            return render_template("income.html", error = "Must insert a positive amount")

        # get current balance
        current_balance = db.execute("SELECT * FROM users WHERE id = ?", id)[0]["balance"]

        # update balance
        if not current_balance: 
            new_balance = income
        elif current_balance > 0:
            new_balance = current_balance + income
        db.execute("UPDATE users SET balance = ? WHERE id = ?", new_balance, id)
        return redirect("/")
    if request.method == "GET":
        return render_template("income.html") 

@app.route("/jars", methods =  ["POST"])
@login_required
def update_jar():
    pass
    

@app.route("/logout", methods = ["GET", "POST"])
@login_required
def logout():
    #log user out

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods = ["GET", "POST"])
def register():
    session.clear()
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    if request.method == "POST":
        if not username:
            return render_template("register.html", error = "Must add a username")
        if not password or not confirmation:
            return render_template("register.html", error = "Must add a password")
        if not email: 
            return render_template("register.html", error = "Must add an email")
        if password != confirmation:
            return render_template("register.html", error = "Passwords don't match!")
        try:
            hashpas = generate_password_hash(password)
            db.execute("INSERT INTO users(username, email, hash) VALUES (?,?, ?)", username, email, hashpas)
            print("You have successfully registered!")
            return render_template("login.html")
        except ValueError:
            return render_template("register.html", error = "Username already exists")
    if request.method == "GET":
        return render_template("register.html")

@app.route("/budget", methods = ["POST"])
@login_required
def budget():
    id = session["user_id"]
    jar = request.form.get("jar")
    action = request.form.get("action")
    amount = request.form.get("amount")
    #convert amount
    try: 
        amount = float(amount)
    except ValueError: 
        return render_template("index.html", error = "Must insert a positive amount!")

    balance = db.execute("SELECT * FROM users WHERE id = ?", id)[0]["balance"]

    #convert balance if necessary
    try: 
        balance = float(balance)
    except ValueError: 
        balance = 0
    if action == "Add":
        #check balance
        if balance < amount: 
            return render_template("index", error = "Not enough money!")

        #update jar
        db.execute("UPDATE jars SET amount = amount + ? WHERE user_id = ? AND jar_name = ?", amount, id, jar)

        #update users
        new_balance = balance - amount 
        db.execute("UPDATE users SET balance = ? WHERE id = ?", new_balance, id)

        return render_template("index.html")

    elif action == "Extract":
        #check jar_balance
        jar_bal = db.execute("SELECT * FROM jars WHERE jar_name = ?", jar)[0]["amount"]
        if jar_bal < amount: 
            return render_template("index.html", error = "Not enough money in jar!")

        #update jar
        db.execute("UPDATE jars SET amount = amount - ? WHERE user_id = ? AND jar_name = ?", amount, id, jar)

        #update balance
        if balance == 0: 
           db.execute("UPDATE users SET balance = ? WHERE id = ?", amount, id) 
        elif balance > 0:
            db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", amount, id)

        return render_template("index.html")
    else: 
        return render_template("index.html", error = "Must insert a valid action")
        
        



            

@app.route("/stats", methods = ["GET", "POST"])
@login_required
def stats():
    if request.method == "GET": 
        return render_template("stats.html")


if __name__ == '__main__':
    app.run(debug=True)