import os
import sqlite3
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, usd
from datetime import date



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

#get date
year_month = date.today().strftime('%Y-%m')

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
            db.execute(
                "INSERT INTO users(username, email, hash) VALUES (?,?, ?)", username, email, hashpas)
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
    #get user id
    id = session["user_id"]

    #get and validate income
    income = db.execute("""
    SELECT SUM(amount) 
    AS total 
    FROM movements 
    WHERE user_id = ? AND type = 'income' AND strftime('%Y-%m', date) = ?
    """, id, year_month)[0]["total"]
    income = float(income or 0)

    #get and validate savings
    savings = db.execute("""
    SELECT SUM(amount) 
    AS total 
    FROM movements 
    WHERE user_id = ? AND type = 'savings' AND strftime('%Y-%m', date) = ?
    """, id, year_month)[0]["total"]
    savings = float(savings or 0)

    #get jars total amount
    jars_total = db.execute("""
    SELECT SUM(amount) 
    AS total 
    FROM movements 
    WHERE user_id = ? AND type = 'jar' AND strftime('%Y-%m', date) = ?
    """,id, year_month)[0]["total"]
    jars_total = float(jars_total or 0)

    #get remaining income
    balance = income - savings - jars_total

    # get user jars
    user_jars = db.execute("SELECT * FROM jars WHERE user_id = ?", id)

    jars = []
    for jar in user_jars: 
        amount = db.execute("""
        SELECT SUM(amount)
        AS total 
        FROM movements 
        WHERE jar_id = ? AND type = 'jar' AND strftime('%Y-%m', date) = ?
        """, jar["id"], year_month)[0]["total"]
        amount = float(amount or 0)
        jars.append({"id": jar["id"], "jar_name": jar["jar_name"], "amount": amount})

    return render_template("index.html", jars = jars, balance = balance, savings = savings)


@app.route("/actual", methods = ["GET","POST"])
@login_required
def actualjars():
    id = session["user_id"]
    jar = request.form.get("jar")
    action = request.form.get("action")
    amount = request.form.get("amount")
    
    #get and validate income
    income = db.execute("""
    SELECT SUM(amount) 
    AS total FROM movements 
    WHERE user_id = ? AND type = 'income' AND strftime('%Y-%m', date) = ?
    """, id, year_month)[0]["total"]        
    income = float(income or 0)
    
    #get and validate savings
    savings = db.execute("""
    SELECT SUM(amount) 
    AS total 
    FROM movements 
    WHERE user_id = ? AND type = 'savings' AND strftime('%Y-%m', date) = ?
    """, id, year_month)[0]["total"]
    savings = float(savings or 0)
    
    #get jars total amount
    jars_total = db.execute("""
    SELECT SUM(amount)
    AS total 
    FROM movements 
    WHERE user_id = ? AND type = 'jar' AND strftime('%Y-%m', date) = ?
    """,id, year_month)[0]["total"]        
    jars_total = float(jars_total or 0)
    
    #get remaining income
    balance = income - savings - jars_total

    #check jar
    if not jar: 
        flash("Must select a jar!", "error")
        return redirect("/") 

    #check action
    if not action:
        flash("Must select an action!", "error")
        return redirect("/")
    
    #convert amount
    try: 
        amount = float(amount)
    except ValueError: 
        flash("Must insert a positive amount", "error")
        return redirect("/")

    jar_id = db.execute(
        "SELECT * FROM jars WHERE user_id = ? AND jar_name = ?", id, jar
        )[0]["id"]
    try: 
        jar_id = int(jar_id)
    except ValueError: 
        flash("There has been a problem!")
        return redirect("/")

    #if money is added to the jar
    if action == "Add":
        #check balance
        if balance < amount: 
            flash("Not enough money!", "error")
            return redirect("/")

        #update jar movements
        db.execute("""
        INSERT 
        INTO movements (user_id, amount, type, jar_id) 
        VALUES (?,?,?,?)
        """, id, amount, 'jar', jar_id)
        
        flash("You have updated your jars successfully!", "success")
        return redirect("/")

    elif action == "Extract":
        #check jar_balance
        jar_bal = db.execute("""
        SELECT SUM(amount) 
        AS total 
        FROM movements 
        WHERE user_id = ? AND jar_id = ? AND strftime('%Y-%m', date) = ?
        """, id, jar_id, year_month)[0]["total"]
        jar_bal = float(jar_bal or 0)

        if jar_bal < amount: 
            flash("Not enough money in jar!", "error")
            return redirect("/")

        #update movements
        db.execute("""
        INSERT
        INTO movements(user_id, jar_id, amount, type) 
        VALUES (?,?,?,?)
        """, id, jar_id, -amount, 'jar')

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

        #update balance
        db.execute("""
        INSERT 
        INTO movements (user_id, type, amount) 
        VALUES (?,?,?)
        """, id,'income', income)
        flash("You have successfully updated your income!", "success")
        return redirect("/income")
    if request.method == "GET":
        return render_template("income.html") 


@app.route("/savings", methods = ["GET", "POST"])
@login_required
def add_savings():
    if request.method == "POST": 
        id = session["user_id"]
        savings = request.form.get("savings")

        #get and validate income
        income = db.execute("""
        SELECT SUM(amount) 
        AS total 
        FROM movements 
        WHERE user_id = ? AND type = 'income' AND strftime('%Y-%m', date) = ?
        """, id, year_month)[0]["total"]
        income = float(income or 0)
        
        #get and validate savings
        current_savings = db.execute("""
        SELECT SUM(amount) 
        AS total 
        FROM movements 
        WHERE user_id = ? AND type = 'savings' AND strftime('%Y-%m', date) = ?
        """, id, year_month)[0]["total"]
        current_savings = float(savings or 0)
        
        #get jars total amount
        jars_total = db.execute("""
        SELECT SUM(amount) 
        AS total FROM movements 
        WHERE user_id = ? AND type = 'jar' AND strftime('%Y-%m', date) = ?
        """,id, year_month)[0]["total"]
        jars_total = float(jars_total or 0)
        
        #get remaining income
        balance = income - current_savings - jars_total

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

        #validate
        if savings > balance: 
            flash("Not enough money", "error")
            return redirect("/savings")

        # update savings and balance
        if not balance: 
            flash("Not enough money", "error")
            return redirect("/savings")
        
        db.execute("""
        INSERT 
        INTO movements (user_id, amount, type) 
        VALUES (?,?,?)
        """, id, savings, 'savings')

        flash("Savings succesfully updated!", "success")
        return redirect("/income")

    if request.method == "GET":
        return render_template("income.html") 


@app.route("/jars", methods =  ["GET", "POST"])
@login_required
def jars():
    id = session["user_id"]
    jars = db.execute("SELECT * FROM jars WHERE user_id = ?", id)
    if request.method == "GET" or request.method == "POST":
        return render_template("jars.html", jars = jars)


@app.route("/delete", methods =["POST"])
@login_required
def delete():
    user_id = session["user_id"]
    id = request.form.get("id")
    if id: 
        #delete from jars
        db.execute("""
        DELETE FROM jars 
        WHERE id = ? AND user_id = ?
        """, id, user_id)
        flash("Jar successfully deleted!", "success")
    else: 
        flash("There has been a problem!", "error")
    return redirect("/jars")

@app.route("/add", methods = ["POST"])
@login_required
def add(): 
    user_id = session["user_id"]
    name = request.form.get("name")
    if not name: 
        flash("Must add a name!", "error")
        return redirect("/jars")
    try: 
        db.execute("""
        INSERT 
        INTO jars (user_id, jar_name) 
        VALUES (?,?)
        """, user_id, name)
    except ValueError:
        flash("That jar already exists! User another name", "error")
        redirect("/")
    flash("Jar successfully added!", "success")
    return redirect("/jars")


@app.route("/budget", methods = ["GET", "POST"])
@login_required
def budget():
    id = session["user_id"]

    #get current savings
    try:
        current_savings = db.execute("""
        SELECT amount 
        FROM budget 
        WHERE user_id = ? AND type = 'savings'
        """, id)[0]["amount"]
    except IndexError:
        current_savings = 0
    current_savings = float(current_savings or 0)

    #get current income
    try:
        current_income = db.execute("""
        SELECT amount 
        FROM budget 
        WHERE user_id = ? AND type = 'income'
        """, id)[0]["amount"]
    except IndexError:
        current_income = 0
    current_income= float(current_income or 0)

    # get user jars
    user_jars = db.execute("""
    SELECT * 
    FROM jars 
    WHERE user_id = ?""", id)

    #create a list with all jars and amounts
    jars = []
    for jar in user_jars: 
        try:
            amount = db.execute("""
            SELECT amount 
            AS total 
            FROM budget 
            WHERE jar_id = ? AND type = 'jar'
            """, jar["id"])[0]["total"]
        except IndexError: 
            amount = 0
        amount = float(amount or 0)
        jars.append({"id": jar["id"], "jar_name": jar["jar_name"], "amount": amount})

    if request.method == "GET" or request.method == "POST":
        return render_template("budget.html", jars = jars, current_savings = current_savings, current_income = current_income)


@app.route("/budget_income", methods = ["POST"])
@login_required
def budget_income():
    if request.method == "POST": 
        id = session["user_id"]
        income = request.form.get("income")
    
        # Validate income
        if not income:
            flash("Must insert a positive amount", "error")
            return redirect("/budget")
        try:
            income = float(income)
        except ValueError:
            flash("Must insert a positive amount", "error")
            return redirect("/budget")
        if income <= 0:
            flash("Must insert a positive amount", "error")
            return redirect("/budget")
        
        #check if there's a value for income
        try:
            current_income = db.execute("""
            SELECT amount 
            AS amount 
            FROM budget 
            WHERE user_id = ? AND type = 'income'
            """, id)[0]["amount"]
        except IndexError:
            current_income = 0
        current_income = float(current_income or 0)

        if current_income == 0: 
            #insert expected income
            db.execute("""
            INSERT 
            INTO budget(user_id, type, amount) 
            VALUES(?,?,?)
            """, id, 'income', income)
            flash("Expected income added successfully!", "success")
            return redirect("/budget")
        elif current_income > 0: 
            #update income
            db.execute("""
            UPDATE budget 
            SET amount = ? 
            WHERE user_id = ? AND type = 'income'
            """, income)
            flash("Expected income changed successfully!", "success")
            return redirect("/budget")


@app.route("/budget_savings", methods = ["POST"])
@login_required
def budget_savings(): 
    if request.method == "POST": 
        id = session["user_id"]
        savings = request.form.get("savings")
    
        # Validate savings
        if not savings:
            flash("Must insert a valid amount", "error")
            return redirect("/budget")
        try:
            savings = float(savings)
        except ValueError:
            flash("Must insert a valid amount", "error")
            return redirect("/budget")
        
        if savings < 0:
            flash("Must insert a valid amount", "error")
            return redirect("/budget")
        
        #check if there's a value for savings
        try:
            current_savings = db.execute("""
            SELECT amount 
            AS amount 
            FROM budget 
            WHERE user_id = ? AND type = 'savings'
            """, id)[0]["amount"]
        except IndexError:
            current_savings = 0
        current_savings = float(current_savings or 0)

        #compare with budgeted balance
        try:
            current_income = db.execute("""
            SELECT amount 
            FROM budget 
            WHERE user_id = ? AND type = 'income'
            """, id)[0]["amount"]
        except IndexError:
            current_income = 0
        current_income = float(current_income or 0)

        try: 
            total_jars = db.execute("""
            SELECT SUM(amount) 
            AS total 
            FROM budget 
            WHERE user_id = ? AND type = 'jar'
            """, id)[0]["total"]
        except IndexError:
            total_jars = 0
        total_jars = float(total_jars or 0)

        current_balance = current_income - current_savings - total_jars

        if savings > current_balance: 
            flash("You wouldn't have enough money to save that amount!", "error")
            return redirect("/budget")

        if current_savings == 0: 
            #insert expected savings
            db.execute("""
            INSERT 
            INTO budget(user_id, type, amount) 
            VALUES(?,?,?)
            """, id, 'savings', savings)
            flash("Expected savings added successfully!", "success")
            return redirect("/budget")

        elif current_savings > 0: 
            #update savings
            db.execute("""
            UPDATE budget 
            SET amount = ? 
            WHERE user_id = ? AND type = 'savings'
            """, savings)
            flash("Expected savings changed successfully!", "success")
            return redirect("/budget")


@app.route("/budget_jars", methods = ["POST"])
@login_required
def budget_jars(): 
    id = session["user_id"]
    jar_name = request.form.get("jar_name")
    amount = request.form.get("jar_amount")
    if request.method == "POST":
        #check jar_name
        if not jar_name: 
            flash("There has been a problem!", "error")
            return redirect("/budget")

        #check amount
        try: 
            amount = float(amount)
        except (ValueError, TypeError): 
            flash("Must insert a valid amount", "error")
            return redirect("/budget")

        amount = float(amount or 0)
        
        if amount < 0: 
            flash("Must insert a valid amount", "error")
            return redirect("/budget")


        #check if there's a value for savings
        try:
            current_savings = db.execute(
                "SELECT amount AS amount FROM budget WHERE user_id = ? AND type = 'savings'", id
                )[0]["amount"]
        except IndexError:
            current_savings = 0
        current_savings = float(current_savings or 0)

        #check if there's a value for income
        try:
            current_income = db.execute(
                "SELECT amount FROM budget WHERE user_id = ? AND type = 'income'", id
                )[0]["amount"]
        except IndexError:
            current_income = 0
        current_income = float(current_income or 0)

        #get total jars value
        try: 
            total_jars = db.execute(
                "SELECT SUM(amount) AS total FROM budget WHERE user_id = ? AND type = 'jar'", id
                )[0]["total"]
        except IndexError:
            total_jars = 0
        total_jars = float(total_jars or 0)

        current_balance = current_income - current_savings - total_jars

        #compare with budgeted balance
        if amount > current_balance: 
            flash("You wouldn't have enough money to spend that amount!", "error")
            return redirect("/budget")

        #get jar_id
        jar_id = db.execute(
            "SELECT id AS id FROM jars WHERE jar_name = ? AND user_id = ?", jar_name, id
            )[0]["id"]
        #check
        try:
            int(jar_id)
        except ValueError: 
            flash("There has been a problem!", "erorr")
            return redirect("/budget")

         #find the jar value in db
        try:
            last_amount = db.execute(
                "SELECT amount FROM  budget WHERE user_id = ? AND type = 'jar' AND jar_id = ?", id, jar_id
                )[0]["amount"]
        except IndexError:
            last_amount = 0
        last_amount = float(last_amount or 0)

        if last_amount:
            db.execute(
                "UPDATE budget SET amount = ? WHERE user_id = ? AND type = 'jar' AND jar_id = ?", amount, id, jar_id
                )
            flash("You have successfully updated your jar budget!", "success")
            return redirect("/budget")
        else:
            db.execute(
                "INSERT INTO budget (user_id, amount, jar_id, type) VALUES (?,?,?,?)", id, amount, jar_id, 'jar'
                )
            flash("You have successfully budgeted your jar!", "success")
            return redirect("/budget")
        

@app.route("/logout", methods = ["GET", "POST"])
@login_required
def logout():
    #log user out

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/stats", methods = ["GET", "POST"])
@login_required
def stats():
    id = session["user_id"]
    username = db.execute("SELECT * FROM users WHERE id = ?", id)[0]["username"]

    #actual
    actual = {}
    #actual income
    try:
        actual_inc = db.execute("""
        SELECT SUM(amount) 
        AS amount 
        FROM movements 
        WHERE user_id = ? AND type = 'income' AND strftime('%Y-%m', date) = ?
        """, id, year_month)[0]["amount"]
        actual_inc = float(actual_inc or 0)
    except IndexError:
        actual_inc = 0
    actual["income"] = actual_inc

    #actual savings
    try:
        actual_sav = db.execute("""
        SELECT SUM(amount) 
        AS amount 
        FROM movements 
        WHERE user_id = ? AND type = 'savings' AND strftime('%Y-%m', date) = ?
        """, id, year_month)[0]["amount"]
        actual_sav = float(actual_sav or 0)
    except IndexError:
        actual_sav = 0
    actual["savings"] = actual_sav

    #actual jars
    try:
        actual_jar = db.execute("""
        SELECT SUM(amount) 
        AS total 
        FROM movements 
        WHERE user_id = ? AND type = 'jar' AND strftime('%Y-%m', date) = ?
        """, id, year_month)[0]["total"]
        actual_jar= float(actual_jar or 0)
    except IndexError:
        actual_jar = 0
    actual["jars"] = actual_jar

    actual_bal = actual_inc - actual_sav - actual_jar
    actual["balance"] = actual_bal

    #budgeted
    budget = {}
    #budgeted income
    try:
        budget_inc = db.execute("""
        SELECT amount 
        AS amount 
        FROM budget 
        WHERE user_id = ? AND type = 'income'
        """, id)[0]["amount"]
        budget_inc = float(budget_inc or 0)
    except IndexError:
        budget_inc = 0
    budget["income"] = budget_inc

    #budgeted savings
    try:
        budget_sav = db.execute("""
        SELECT amount 
        AS amount 
        FROM budget 
        WHERE user_id = ? AND type = 'savings'
        """, id)[0]["amount"]
        budget_sav = float(budget_sav or 0)
    except IndexError:
        budget_sav = 0
    budget["savings"] = budget_sav

    #budgeted jars
    try:
        budget_jar = db.execute("""
        SELECT SUM(amount) 
        AS total 
        FROM budget 
        WHERE user_id = ? AND type = 'jar'
        """, id)[0]["total"]
        budget_jar= float(budget_jar or 0)
    except IndexError:
        budget_jar = 0
    budget["jars"] = budget_jar

    budget_bal = budget_inc - budget_sav - budget_jar
    budget["balance"] = budget_bal
    if request.method == "GET": 
        return render_template("stats.html", username = username, actual=actual, budget = budget)

@app.route("/api/jar_distribution", methods = ["GET", "POST"])
@login_required
def jar_dist():
    id = session["user_id"]
    # get user jars
    user_jars = db.execute("""
    SELECT * 
    FROM jars 
    WHERE user_id = ?
    """, id)

    #create a list with all jars and amounts
    jars = []
    for jar in user_jars: 
        amount = db.execute("""
        SELECT SUM(amount) 
        AS total 
        FROM movements 
        WHERE jar_id = ? AND type = 'jar' AND strftime('%Y-%m', date) = ?
        """, jar["id"], year_month)[0]["total"]
        amount = float(amount or 0)
        jars.append({"id": jar["id"], "jar_name": jar["jar_name"], "amount": amount})
        labels = [jar["jar_name"] for jar in jars]
        values = [float(jar["amount"]) for jar in jars]
    return jsonify({"labels":labels,"values":values })
  

@app.route("/api/budgetvsactual", methods = ["GET", "POST"])
@login_required
def budgetvsactual():
    id = session["user_id"]

    # get user jars
    user_jars = db.execute("""
    SELECT * 
    FROM jars 
    WHERE user_id = ?
    """, id)

    #create a list with all jars and actual amounts
    jars = []
    for jar in user_jars: 
        amount = db.execute("""
        SELECT SUM(amount) 
        AS total 
        FROM movements 
        WHERE jar_id = ? AND type = 'jar' AND strftime('%Y-%m', date) = ? AND user_id = ?
        """, jar["id"], year_month, id)[0]["total"]
        amount = float(amount or 0)
        jars.append({"id": jar["id"], "jar_name": jar["jar_name"], "amount": amount})

    #append income and savings
    income = db.execute("""
    SELECT SUM(amount) 
    AS income 
    FROM movements 
    WHERE type = 'income' AND strftime('%Y-%m', date) = ? AND user_id = ?
    """,year_month, id)[0]["income"]
    income = float(income or 0)
    jars.append({"jar_name":"income", "amount": income})

    savings = db.execute("""
    SELECT SUM(amount) 
    AS savings 
    FROM movements 
    WHERE type = 'savings' AND strftime('%Y-%m', date) = ? AND user_id = ?
    """,year_month, id)[0]["savings"]
    savings = float(savings or 0)
    jars.append({"jar_name":"savings", "amount": savings})

    #create a list with budgeted amounts
    budget = []
    for jar in user_jars: 
        try: 
            budgeted = db.execute("""
            SELECT amount 
            AS amount 
            FROM budget 
            WHERE jar_id = ? AND type = 'jar' AND user_id = ?
            """, jar["id"], id)[0]["amount"]
            budgeted = float(budgeted or 0)
        except IndexError: 
            budgeted = 0
        budget.append({"id": jar["id"], "jar_name": jar["jar_name"], "amount": budgeted})

    #append income and savings
    try:
        budgeted_inc = db.execute("""
        SELECT amount 
        AS amount 
        FROM budget 
        WHERE user_id = ? AND type = 'income'
        """, id)[0]["amount"]
        budgeted_inc = float(budgeted_inc or 0)
    except IndexError:
        budgeted_inc = 0
    budget.append({"jar_name": "income", "amount": budgeted_inc})

    try: 
        budgeted_sav = db.execute("""
        SELECT amount 
        AS amount 
        FROM budget 
        WHERE user_id = ? AND type = 'savings'
        """, id)[0]["amount"]
        budgeted_sav = float(budgeted_sav or 0)
    except IndexError: 
        budgeted_sav = 0
    budget.append({"jar_name": "savings", "amount": budgeted_sav})


    labels = [jar["jar_name"] for jar in jars]
    actual = [float(jar["amount"]) for jar in jars]
    budget = [float(jar["amount"]) for jar in budget]


    return jsonify({"labels": labels, "actual": actual, "budget": budget})


@app.route("/api/monthlytrends", methods = ["GET", "POST"])
@login_required
def monthlytrends():
    id = session["user_id"]

    rows = db.execute("""
    SELECT
        strftime('%Y-%m', date) AS month,
        SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS income,
        SUM(CASE WHEN type = 'savings' THEN amount ELSE 0 END) AS savings,
        SUM(CASE WHEN type = 'jar' THEN amount ELSE 0 END) AS jars
    FROM movements
    WHERE user_id = ?
    GROUP BY month
    ORDER BY month
    """, id)

    labels = []
    income = []
    savings = []
    jars = []

    for row in rows:
        labels.append(row["month"])
        income.append(row["income"])
        savings.append(row["savings"])
        jars.append(row["jars"])

    return jsonify({"labels": labels, "income": income, "savings": savings, "jars": jars})


if __name__ == '__main__':
    app.run(debug=True)