import os
import sqlite3
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, usd, get_month_summary, get_budget_summary
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
        except RuntimeError:
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

    #get date
    year_month = date.today().strftime('%Y-%m')

    #get summary
    summary = get_month_summary(id)
    savings = summary["savings"]
    balance = summary["balance"]

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

    #get date
    year_month = date.today().strftime('%Y-%m')

    #get summary
    summary = get_month_summary(id)
    balance = summary["balance"]

    #check jar
    if not jar: 
        flash("Must select a jar!", "error")
        return redirect("/") 

    user_jars = db.execute("""
    SELECT jar_name 
    FROM jars 
    WHERE user_id = ?
    """, id)

    user_jars_names = [j["jar_name"] for j in user_jars]

    if jar not in user_jars_names:
        flash("Jar doesn't exist!", "error")
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

        #get summary
        summary = get_month_summary(id)
        savings = summary["savings"]
        balance = summary["balance"]

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
    except RuntimeError:
        flash("That jar already exists! User another name", "error")
        return redirect("/")
    flash("Jar successfully added!", "success")
    return redirect("/jars")


@app.route("/budget", methods = ["GET", "POST"])
@login_required
def budget():
    id = session["user_id"]

    budget = get_budget_summary(id)
    current_savings = budget["savings"]
    current_income = budget["income"]

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
        budget = get_budget_summary(id)
    
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

        #check if there's a current income
        current_income = budget["income"]

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
            """, income, id)
            flash("Expected income changed successfully!", "success")
            return redirect("/budget")


@app.route("/budget_savings", methods = ["POST"])
@login_required
def budget_savings(): 
    if request.method == "POST": 
        id = session["user_id"]
        savings = request.form.get("savings")
        budget = get_budget_summary(id)
    
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
        current_savings = budget["savings"]

        #compare with budgeted balance
        current_balance = budget["balance"]

        if savings > current_balance + current_savings: 
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
            """, savings, id)
            flash("Expected savings changed successfully!", "success")
            return redirect("/budget")


@app.route("/budget_jars", methods = ["POST"])
@login_required
def budget_jars(): 
    id = session["user_id"]
    jar_name = request.form.get("jar_name")
    amount = request.form.get("jar_amount")
    budget = get_budget_summary(id)

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

        current_balance = budget["balance"]

        #get jar_id
        jar_id = db.execute(
            "SELECT id AS id FROM jars WHERE jar_name = ? AND user_id = ?", jar_name, id
            )[0]["id"]
        
        #find the jar value in db
        try:
            last_amount = db.execute(
                "SELECT amount FROM  budget WHERE user_id = ? AND type = 'jar' AND jar_id = ?", id, jar_id
                )[0]["amount"]
        except IndexError:
            last_amount = 0
        last_amount = float(last_amount or 0)

        #compare with budgeted balance
        if amount > current_balance + last_amount: 
            flash("You wouldn't have enough money to spend that amount!", "error")
            return redirect("/budget")

        #check
        try:
            int(jar_id)
        except ValueError: 
            flash("There has been a problem!", "erorr")
            return redirect("/budget")

        

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


@app.route("/stats", methods = ["GET"])
@login_required
def stats():
    id = session["user_id"]
    username = db.execute("SELECT * FROM users WHERE id = ?", id)[0]["username"]
    #get date
    year_month = date.today().strftime('%Y-%m')

    #get_summary as actual
    actual = get_month_summary(id)
    actual["jars"] = actual.pop("jars_total")

    #budgeted
    budget = get_budget_summary(id)
    budget["jars"] = budget.pop("jars_total")
    
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

    #get date
    year_month = date.today().strftime('%Y-%m')

    #create a list with all jars and amounts
    labels = []
    values = []
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

    #get date
    year_month = date.today().strftime('%Y-%m')
    
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


@app.route("/settings", methods = ["GET", "POST"])
@login_required
def settings():
    if request.method == "GET" or request.method == "POST":
        return render_template("settings.html")


@app.route("/change_pass", methods = ["POST"])
@login_required
def change_pass():
    id = session["user_id"]

    if request.method == "POST":
        #get values
        current_pass = request.form.get("current_pass")
        new_pass = request.form.get("new_pass")
        confirmation = request.form.get("confirmation")
        real_pass = db.execute("""
        SELECT hash 
        FROM users 
        WHERE id = ?
        """, id)[0]["hash"]

        #validate password
        if not current_pass:
            flash("Must insert your current password", "error")
            return redirect("/settings")

        #confirm password is correct
        if check_password_hash(real_pass, current_pass) == False:
            flash("Incorrect password!", "error")
            return redirect("/settings")

        #validate new password
        if not new_pass or not confirmation:
            flash("Must insert and confirm new password!", "error")
            return redirect("/settings")

        #compare passwords
        if new_pass != confirmation: 
            flash("New password and confirmation do not match!")
            return redirect("/settings")

        #update password
        hashpas = generate_password_hash(new_pass)
        db.execute("""
        UPDATE users
        SET hash = ? 
        WHERE id = ?
        """, hashpas, id)

        flash("You have successfully changed your password!", "success")
        return redirect("/")


@app.route("/delete_acc", methods = ["POST"])
@login_required
def delete_acc():
    id =session["user_id"]

    if request.method == "POST":
        password = request.form.get("password")

        #validate password
        if not password:
            flash("Must insert a valid password!")
            return redirect("/settings")

        #check password
        real_pass = db.execute("""
        SELECT hash 
        FROM users 
        WHERE id = ?
        """, id)[0]["hash"]

        if check_password_hash(real_pass, password) == False:
            flash("Wrong password!", "error")
            return redirect("/settings")

        db.execute("""
        DELETE 
        FROM users 
        WHERE id = ?
        """, id)

        session.clear()
        flash("Account deleted successfully!", "success")
        return render_template("login.html")



if __name__ == '__main__':
    app.run()