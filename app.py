import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

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

    id = session.get("user_id")

    port = db.execute("SELECT * FROM new WHERE id = ?",id)

    return render_template("index.html", port = port)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("enter symbol for stock")
        elif not request.form.get("amount"):
            return apology("enter amount of shares")

        #get stock as dic from lookup and get each value of the the dic as variable
        stock = lookup(request.form.get("symbol"))
        symbol = stock["symbol"]
        name = stock["name"]
        price = stock["price"]

        priceUS = usd(price)

        amount = request.form.get("amount")

        shares = float(amount) * float(price)

        sharesUS = usd(shares)

        #if session.get("user_id"):
        #   get the id from session
        id = session.get("user_id")

        user = db.execute("SELECT * FROM users WHERE id = ? ", id)

        cash = user[0]["cash"]

        # check whether the user affords the amount of  shares by comparing the cash he has with th the total cost of the shares he wants to buy
        if shares > cash:
            return apology("not enough money")
        else:
            cash = cash - shares

        # update the users table cash column by subtracting the money used to bu shares
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, id )
        #put transaction in the history table
        db.execute("INSERT INTO History (id, Symbol, Shares, Price) VALUES(?, ?, ?, ?)", id, symbol, amount, priceUS)

        # finding the contents of the new(table used for portifolio) to see whther already has shares of particlar symbol
        new =  db.execute("SELECT * FROM new WHERE Symbol = ? AND id = ?", symbol, id )

        if len(new)!=1:
            db.execute("INSERT  INTO new (Symbol, Name, Shares, Price, Total, Tot, id) VALUES(?, ?, ?, ?, ?, ?, ?)", symbol, name, amount, priceUS, sharesUS, shares, id)


        else:
            # add new shares to esixting shares

            #number of shares that are there already
            amount1 = new[0]["Shares"]
            #add the new shares to the existing shares
            amount2 = int(amount1) + int(amount)
            #get the the total price of shares as float and add the new total
            total1 = new[0]["Tot"]

            total2 = float(total1) + float(shares)
            # change new total to US

            total2US = usd(total2)

            db.execute("UPDATE new SET Shares = ?, Total = ?, Tot = ? WHERE Symbol = ? AND id = ?", amount2, total2US, total2, symbol,id )







        return redirect("/")




    else:
        return render_template("buy.html")




@app.route("/history")
@login_required
def history():

    id = session.get("user_id")
    trans = db.execute("SELECT * FROM History WHERE id = ?",id)

    return render_template("history.html",trans = trans)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        #Checks if user typed in a symbol
        if not request.form.get("symbol"):
            return apology("please enter stock symbol", 403)
        #uses the lookup function to get a qoute of the stock from the symbol and pass it on to Stocks
        Stocks = lookup(request.form.get("symbol"))

        # pass  Stocks as variable to quted
        return render_template("quoted.html", stocks = Stocks)

    else:
        return render_template("quote.html")





@app.route("/register", methods=["GET", "POST"])
def register():


    session.clear()

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)


        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure  confirm password was submitted
        elif not request.form.get("cpassword"):
            return apology("must confirm password", 403)

        # Ensure passwords  match
        elif request.form.get("password") != request.form.get("cpassword"):
            return apology("passwords  should match", 403)

         #check if username exists in database

        check = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(check) == 1:
            return apology("username taken", 403)

        username = request.form.get("username")
        hash_pass = generate_password_hash(request.form.get("password"))

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash_pass)
        #login in user after registering
        sees = db.execute("SELECT * FROM users WHERE username = ?", username)

        session["user_id"] = sees[0]["id"]

        flash("Youre registered")

        return redirect("/")


    else:
        return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("enter symbol for stock")
        elif not request.form.get("amount"):
            return apology("enter amount of shares")

        ssymbol = request.form.get("symbol")
        samount = request.form.get("amount")

        #get the cash the user has from the users table
        id = session.get("user_id")
        suser = db.execute("SELECT * FROM users WHERE id = ? ", id)
        scash = suser[0]["cash"]

        #get the nymber of shares for a perticular symbol the user has from the the new table
        snew = db.execute("SELECT * FROM new WHERE Symbol = ? AND id = ?", ssymbol, id)
        sshares = snew[0]["Shares"]
        stot = snew[0]["Tot"]


        #using lookup to find the price of the current stock symbol because in the new table there is the usd one it cant be used for any calcus
        sstock = lookup(request.form.get("symbol"))
        sprice = sstock["price"]
        # channe price  to usd

        ussprice = usd(sprice)

        #check if user has the shares to sell
        if float(sshares) < float(samount):
            return apology("you don't have enough shares")



        else:

            sshares = float(sshares) - float(samount)


        #total cash price of the shares
        stotal1 = float(sprice) * float(samount)

        #new user cash balance old plus the cash from the sell
        scash = float(scash) + stotal1


        #new total amount of shares after  the sell
        stot = stot - stotal1

        #new usd total after sell
        stotusd = usd(stot)

        #put transaction in history table


        #update the users cash in the usres table
        db.execute("UPDATE users SET cash = ? WHERE id = ?", scash, id)

        #check whether user remains with some shares or sold all of the shares then update the new table
        if sshares == 0:
            db.execute("DELETE FROM new WHERE Symbol = ? AND id = ?", ssymbol, id)

        else:
            db.execute("UPDATE new SET Shares = ?, Total = ?, Tot = ? WHERE id = ? AND Symbol = ?", sshares, stotusd, stot, id, ssymbol)

        hamount = 0 - int(samount)
        db.execute("INSERT INTO History (id, Symbol, Shares, Price) VALUES(?, ?, ?, ?)", id, ssymbol, hamount, ussprice )




        return redirect("/")

    else:

        id = session.get("user_id")
        symb = db.execute("SELECT * FROM new WHERE id = ?",id)
        return  render_template("sell.html",symb = symb)


