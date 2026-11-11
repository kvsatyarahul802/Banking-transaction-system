
from functools import wraps

from flask import (
    Blueprint, render_template, request,
    redirect, session, url_for, flash
)

from werkzeug.security import (
    check_password_hash, generate_password_hash
)

from db import connect

auth_bp = Blueprint("auth", __name__)


# LOGIN REQUIRED
def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))

        return view_function(*args, **kwargs)

    return wrapped_view


# ADMIN REQUIRED
def admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))

        if session.get("role") != "ADMIN":
            return "Access denied: Admin permission required.", 403

        return view_function(*args, **kwargs)

    return wrapped_view


# REGISTRATION
@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if "user_id" in session:
        return redirect("/")

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password or not confirm_password:
            flash("Please fill in all fields.", "error")
            return render_template("register.html")

        if len(username) < 3 or len(username) > 50:
            flash("Username must contain 3 to 50 characters.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        con = None
        cursor = None

        try:
            con = connect()
            cursor = con.cursor(dictionary=True)

            cursor.execute(
                "SELECT user_id FROM app_users WHERE username = %s",
                (username,)
            )

            if cursor.fetchone():
                flash("Username already exists. Choose another.", "error")
                return render_template("register.html")

            password_hash = generate_password_hash(password)

            # Create login account with USER role
            cursor.execute(
                """
                INSERT INTO app_users
                    (username, password_hash, role)
                VALUES (%s, %s, 'USER')
                """,
                (username, password_hash)
            )

            new_user_id = cursor.lastrowid

            # Create customer linked to login account
            cursor.execute(
                """
                INSERT INTO customers (display_name, user_id)
                VALUES (%s, %s)
                """,
                (username, new_user_id)
            )

            new_customer_id = cursor.lastrowid

            # Create savings account
            cursor.execute(
                """
                INSERT INTO accounts (customer_id, account_type)
                VALUES (%s, 'SAVINGS')
                """,
                (new_customer_id,)
            )

            con.commit()

            flash(
                "Registration successful! Your bank account has been created. Please log in.",
                "success"
            )

            return redirect(url_for("auth.login"))

        except Exception:
            if con is not None:
                con.rollback()

            flash(
                "Registration failed. Check your database and try again.",
                "error"
            )

        finally:
            if cursor is not None:
                cursor.close()

            if con is not None and con.is_connected():
                con.close()

    return render_template("register.html")


# LOGIN
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect("/")

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Enter both username and password.", "error")
            return render_template("login.html")

        con = None
        cursor = None

        try:
            con = connect()
            cursor = con.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT user_id, username, password_hash, role
                FROM app_users
                WHERE username = %s
                """,
                (username,)
            )

            user = cursor.fetchone()

            if user and check_password_hash(
                user["password_hash"], password
            ):

                session.clear()

                session["user_id"] = user["user_id"]
                session["username"] = user["username"]
                session["role"] = str(user["role"]).upper()

                return redirect(url_for("home"))

            flash("Invalid username or password.", "error")

        except Exception:
            flash(
                "Login is temporarily unavailable. "
                "Check the database connection.",
                "error"
            )

        finally:
            if cursor is not None:
                cursor.close()

            if con is not None and con.is_connected():
                con.close()

    return render_template("login.html")


# LOGOUT
@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():

    session.clear()

    flash("You have logged out successfully.", "success")

    return redirect(url_for("auth.login"))
