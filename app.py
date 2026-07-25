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

# Custom filter
app.jinja_env.filters["usd"] = usd

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/register", methods = ["GET", "POST"])
def register():
    session.clear()

    #get username, email, password and confirmation
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")


    if request.method == "POST":
        #validate username
        if not username:
            flash("Must add a username", "error")
            return render_template("register.html")

        #validate password
        if not password or not confirmation:
            flash("Must add a password", "error")
            return render_template("register.html")

        #validate email
        if not email: 
            flash("Must add an email", "error")
            return render_template("register.html")

        #validate password = confirmation
        if password != confirmation:
            flash("Passwords don't match!", "error")
            return render_template("register.html")

        #generate password and account
        try:
            hashpas = generate_password_hash(password)
            db.execute("INSERT INTO users(username, email, hash) VALUES (?,?, ?)", username, email, hashpas)
            flash("You have successfully registered!", "success")
            return redirect("/login")
        except ValueError:
            flash("Username or email already exists!", "error")
            return render_template("register.html")

    if request.method == "GET":
        return render_template("register.html")


@app.route("/login", methods = ["GET", "POST"])
def login():
    #log user in
    # Forget any user_id
    session.pop("user_id", None)

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must provide a username", "error")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must provide a password", "error")
            return render_template("login.html")
        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            flash("Incorrect username or password", "error")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/", methods = ["GET", "POST"])
@login_required
def index():

    #get user id, jars, and balance
    id = session["user_id"]
    jars = db.execute("SELECT * FROM jars WHERE user_id = ?", id)
    balance = db.execute("SELECT * FROM users WHERE id = ?", id)[0]["balance"]
    savings = db.execute("SELECT * FROM users WHERE id = ?", id)[0]["savings"]

    #check balance
    try: 
        balance = float(balance)
    except (ValueError, TypeError): 
        balance = 0
    
    return render_template("index.html", jars = jars, balance = balance, savings = savings)


@app.route("/budget", methods = ["GET","POST"])
@login_required
def budget():
    id = session["user_id"]
    jar = request.form.get("jar")
    action = request.form.get("action")
    amount = request.form.get("amount")
    
    #check jar
    if not jar: 
        flash("Must select a jar!", "error")
        redirect("/") 

    #check action
    if not action:
        flash("Must select an action!", "error")
        redirect("/")
    
    #convert amount
    try: 
        amount = float(amount)
    except ValueError: 
        flash("Must insert a positive amount", "error")
        return redirect("/")

    balance = db.execute("SELECT * FROM users WHERE id = ?", id)[0]["balance"]

    #convert balance if necessary
    try: 
        balance = float(balance)
    except ValueError: 
        balance = 0
    if action == "Add":
        #check balance
        if balance < amount: 
            flash("Not enough money!", "error")
            return redirect("/")

        #update jar
        db.execute("UPDATE jars SET amount = amount + ? WHERE user_id = ? AND jar_name = ?", amount, id, jar)

        #update users
        new_balance = balance - amount 
        db.execute("UPDATE users SET balance = ? WHERE id = ?", new_balance, id)

        flash("You have updated your jars successfully!", "success")
        return redirect("/")

    elif action == "Extract":
        #check jar_balance
        jar_bal = db.execute("SELECT * FROM jars WHERE jar_name = ?", jar)[0]["amount"]
        if jar_bal < amount: 
            flash("Not enough money in jar!", "error")
            return redirect("/")

        #update jar
        db.execute("UPDATE jars SET amount = amount - ? WHERE user_id = ? AND jar_name = ?", amount, id, jar)

        #update balance
        if balance == 0: 
           db.execute("UPDATE users SET balance = ? WHERE id = ?", amount, id) 
        elif balance > 0:
            db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", amount, id)

        flash("You have updated your jars successfully!", "success")
        return redirect("/")
    else: 
        flash("Must insert a valid action", "error")
        return redirect("/")


@app.route("/income", methods = ["GET", "POST"])
@login_required
def add_income():
    if request.method == "POST": 
        id = session["user_id"]
        income = request.form.get("income")

        # Validate income
        if not income:
            flash("Must insert a positive amount", "error")
            return redirect("/income")
        try:
            income = float(income)
        except ValueError:
            flash("Must insert a positive amount", "error")
            return redirect("/income")
        if income <= 0:
            flash("Must insert a positive amount", "error")
            return redirect("/income")

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


@app.route("/savings", methods = ["GET", "POST"])
@login_required
def add_savings():
    if request.method == "POST": 
        id = session["user_id"]
        savings = request.form.get("savings")

        # Validate savings
        if not savings:
            flash("Must insert a positive amount", "error")
            return redirect("/savings")
        try:
            savings = float(savings)
        except ValueError:
            flash("Must insert a positive amount", "error")
            return redirect("/savings")
        if savings <= 0:
            flash("Must insert a positive amount", "error")
            return redirect("/savings")

        # get current balance
        current_balance = db.execute("SELECT * FROM users WHERE id = ?", id)[0]["balance"]

        #validate
        if savings > current_balance: 
            flash("Not enough money", "error")
            return redirect("/savings")

        # update savings and balance
        if not current_balance: 
            flash("Not enough money", "error")
            return redirect("/savings")
        elif current_balance > 0:
            new_balance = current_balance - savings
        db.execute("UPDATE users SET savings = ?, balance = ? WHERE id = ?", savings, new_balance, id)

        flash("Savings succesfully updated!")
        return redirect("/")

    if request.method == "GET":
        return render_template("income.html") 


@app.route("/jars", methods =  ["GET", "POST"])
@login_required
def jars():
    id = session["user_id"]
    jars = db.execute("SELECT * FROM jars WHERE user_id = ?", id)
    if request.method == "GET" or request.method == "POST":
        return render_template("jars.html", jars = jars)


@app.route("/add", methods = ["POST"])
@login_required
def add(): 
    user_id = session["user_id"]
    name = request.form.get("name")
    if not name: 
        flash("Must add a name!", "error")
        return redirect("/jars")
    db.execute("INSERT INTO jars (user_id, jar_name, amount) VALUES (?,?,0)", user_id, name)
    flash("Jar successfully added!", "success")
    return redirect("/jars")


@app.route("/logout", methods = ["GET", "POST"])
@login_required
def logout():
    #log user out

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/delete", methods =["POST"])
@login_required
def delete():
    user_id = session["user_id"]
    id = request.form.get("id")
    if id: 
        db.execute("DELETE from jars WHERE id = ? AND user_id = ?", id, user_id)
        flash("Jar successfully deleted!", "success")
    else: 
        flash("There has been a problem!", "error")
    return redirect("/jars")
    

@app.route("/stats", methods = ["GET", "POST"])
@login_required
def stats():
    if request.method == "GET": 
        return render_template("stats.html")


if __name__ == '__main__':
    app.run(debug=True)