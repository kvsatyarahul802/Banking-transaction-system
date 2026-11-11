from flask import Flask, render_template, jsonify, request, session
from functools import wraps
from db import connect
from auth import auth_bp, login_required
from datetime import datetime
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.secret_key = "change-this-to-a-long-random-secret-key"

app.register_blueprint(auth_bp)


# -------------------- API AUTHENTICATION --------------------

def api_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({
                "error": "Your session has expired. Please log in again."
            }), 401
        return func(*args, **kwargs)
    return wrapper


def is_admin():
    return session.get("role") == "ADMIN"


# -------------------- DATABASE HELPERS --------------------

def create_cursor(con):
    return con.cursor(dictionary=True, buffered=True)


def close_db(cursor, con):
    if cursor is not None:
        try:
            cursor.close()
        except Exception:
            app.logger.exception("Error closing cursor")

    if con is not None:
        try:
            con.close()
        except Exception:
            app.logger.exception("Error closing connection")


def rollback_safely(con):
    if con is not None:
        try:
            con.rollback()
        except Exception:
            app.logger.exception("Rollback failed")


def get_user_account(cursor, user_id):
    cursor.execute("""
        SELECT a.account_id, a.customer_id, a.account_type
        FROM accounts a
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE c.user_id = %s
        ORDER BY a.account_id
        LIMIT 1
    """, (user_id,))
    return cursor.fetchone()


def get_balance(cursor, account_id):
    cursor.execute("""
        SELECT COALESCE(
            SUM(
                CASE
                    WHEN transaction_type = 'DEPOSIT' THEN amount
                    WHEN transaction_type = 'WITHDRAWAL' THEN -amount
                    ELSE 0
                END
            ), 0
        ) AS balance
        FROM transactions
        WHERE account_id = %s
    """, (account_id,))

    result = cursor.fetchone()
    return Decimal(str(result["balance"]))


def validate_amount(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

    if not amount.is_finite() or amount <= 0:
        return None

    if amount.as_tuple().exponent < -2:
        return None

    if amount > Decimal("9999999999.99"):
        return None

    return amount


def insert_transaction(cursor, account_id, transaction_type,
                       amount, description):
    cursor.execute("""
        INSERT INTO transactions (
            account_id,
            transaction_date,
            transaction_type,
            amount,
            description
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        account_id,
        datetime.now(),
        transaction_type,
        amount,
        description
    ))


def transaction_response(rows):
    for row in rows:
        if row.get("amount") is not None:
            row["amount"] = float(row["amount"])

        if row.get("transaction_date"):
            row["transaction_date"] = (
                row["transaction_date"].isoformat(sep=" ")
            )

    return rows


# -------------------- HOME --------------------

@app.route("/")
@login_required
def home():
    return render_template("index.html")


# -------------------- USERS --------------------

@app.route("/api/users", methods=["GET"])
@api_login_required
def get_users():
    if not is_admin():
        return jsonify({"error": "Admin access required."}), 403

    con = cursor = None

    try:
        con = connect()
        cursor = create_cursor(con)

        cursor.execute("""
            SELECT
                u.user_id,
                u.username,
                u.role,
                c.customer_id,
                a.account_id,
                a.account_type
            FROM app_users u
            LEFT JOIN customers c ON u.user_id = c.user_id
            LEFT JOIN accounts a ON c.customer_id = a.customer_id
            ORDER BY u.user_id
        """)

        return jsonify(cursor.fetchall()), 200

    except Exception:
        app.logger.exception("Error loading users")
        return jsonify({"error": "Unable to load users."}), 500

    finally:
        close_db(cursor, con)


# -------------------- ACCOUNTS --------------------

@app.route("/api/accounts", methods=["GET"])
@api_login_required
def get_accounts():
    con = cursor = None

    try:
        con = connect()
        cursor = create_cursor(con)

        if is_admin():
            cursor.execute("""
                SELECT
                    a.account_id,
                    a.customer_id,
                    c.display_name,
                    u.username,
                    a.account_type
                FROM accounts a
                JOIN customers c ON a.customer_id = c.customer_id
                JOIN app_users u ON c.user_id = u.user_id
                ORDER BY a.account_id
            """)

            rows = cursor.fetchall()

            for row in rows:
                row["balance"] = float(
                    get_balance(cursor, row["account_id"])
                )

        else:
            account = get_user_account(cursor, session["user_id"])

            if not account:
                return jsonify({
                    "error": "Your account was not found."
                }), 404

            account["balance"] = float(
                get_balance(cursor, account["account_id"])
            )
            rows = [account]

        return jsonify(rows), 200

    except Exception:
        app.logger.exception("Error loading accounts")
        return jsonify({"error": "Unable to load accounts."}), 500

    finally:
        close_db(cursor, con)


# -------------------- DASHBOARD --------------------

@app.route("/api/dashboard", methods=["GET"])
@api_login_required
def dashboard():
    con = cursor = None

    try:
        con = connect()
        cursor = create_cursor(con)

        if is_admin():
            condition = ""
            params = ()
        else:
            condition = """
                WHERE account_id IN (
                    SELECT a.account_id
                    FROM accounts a
                    JOIN customers c ON a.customer_id = c.customer_id
                    WHERE c.user_id = %s
                )
            """
            params = (session["user_id"],)

        cursor.execute(f"""
            SELECT
                COUNT(*) AS total_transactions,
                COALESCE(SUM(
                    CASE WHEN transaction_type = 'DEPOSIT'
                    THEN amount ELSE 0 END
                ), 0) AS total_deposits,
                COALESCE(SUM(
                    CASE WHEN transaction_type = 'WITHDRAWAL'
                    THEN amount ELSE 0 END
                ), 0) AS total_withdrawals
            FROM transactions
            {condition}
        """, params)

        summary = cursor.fetchone()

        summary["total_deposits"] = float(summary["total_deposits"])
        summary["total_withdrawals"] = float(summary["total_withdrawals"])
        summary["total_transactions"] = int(summary["total_transactions"])

        if is_admin():
            cursor.execute("""
                SELECT COUNT(*) AS total_accounts FROM accounts
            """)
            account_count = cursor.fetchone()
            summary["balance"] = None

        else:
            cursor.execute("""
                SELECT COUNT(*) AS total_accounts
                FROM accounts a
                JOIN customers c ON a.customer_id = c.customer_id
                WHERE c.user_id = %s
            """, (session["user_id"],))

            account_count = cursor.fetchone()
            account = get_user_account(cursor, session["user_id"])

            summary["balance"] = (
                float(get_balance(cursor, account["account_id"]))
                if account else 0.0
            )

        summary["total_accounts"] = int(account_count["total_accounts"])

        return jsonify(summary), 200

    except Exception:
        app.logger.exception("Dashboard error")
        return jsonify({
            "error": "Unable to load dashboard data."
        }), 500

    finally:
        close_db(cursor, con)


# -------------------- TRANSACTION HISTORY --------------------

@app.route("/api/transactions", methods=["GET"])
@api_login_required
def get_transactions():
    con = cursor = None

    try:
        con = connect()
        cursor = create_cursor(con)

        if is_admin():
            cursor.execute("""
                SELECT
                    t.transaction_id,
                    t.account_id,
                    u.username,
                    t.transaction_date,
                    t.transaction_type,
                    t.amount,
                    t.description
                FROM transactions t
                JOIN accounts a ON t.account_id = a.account_id
                JOIN customers c ON a.customer_id = c.customer_id
                JOIN app_users u ON c.user_id = u.user_id
                ORDER BY t.transaction_id DESC
                LIMIT 100
            """)
        else:
            cursor.execute("""
                SELECT
                    t.transaction_id,
                    t.account_id,
                    t.transaction_date,
                    t.transaction_type,
                    t.amount,
                    t.description
                FROM transactions t
                JOIN accounts a ON t.account_id = a.account_id
                JOIN customers c ON a.customer_id = c.customer_id
                WHERE c.user_id = %s
                ORDER BY t.transaction_id DESC
                LIMIT 100
            """, (session["user_id"],))

        rows = transaction_response(cursor.fetchall())
        return jsonify(rows), 200

    except Exception:
        app.logger.exception("Error loading transactions")
        return jsonify({"error": "Unable to load transactions."}), 500

    finally:
        close_db(cursor, con)


# -------------------- DEPOSIT AND WITHDRAWAL --------------------

@app.route("/api/transactions", methods=["POST"])
@api_login_required
def create_transaction():
    con = cursor = None

    try:
        data = request.get_json(silent=True) or {}

        transaction_type = str(
            data.get("transaction_type", "")
        ).strip().upper()

        description = str(data.get("description", "")).strip()
        amount = validate_amount(data.get("amount", ""))

        if transaction_type not in ("DEPOSIT", "WITHDRAWAL"):
            return jsonify({"error": "Choose Deposit or Withdrawal."}), 400

        if amount is None:
            return jsonify({
                "error": "Enter a valid positive amount with at most two decimal places."
            }), 400

        if len(description) > 200:
            return jsonify({"error": "Description is too long."}), 400

        con = connect()
        con.start_transaction()
        cursor = create_cursor(con)

        account = get_user_account(cursor, session["user_id"])

        if not account:
            con.rollback()
            return jsonify({"error": "Your account was not found."}), 404

        cursor.execute("""
            SELECT account_id FROM accounts
            WHERE account_id = %s FOR UPDATE
        """, (account["account_id"],))
        cursor.fetchone()

        if transaction_type == "WITHDRAWAL":
            balance = get_balance(cursor, account["account_id"])

            if balance < amount:
                con.rollback()
                return jsonify({"error": "Insufficient balance."}), 400

        insert_transaction(
            cursor,
            account["account_id"],
            transaction_type,
            amount,
            description or None
        )

        transaction_id = cursor.lastrowid
        con.commit()

        return jsonify({
            "message": transaction_type.title() + " successful!",
            "transaction_id": transaction_id
        }), 201

    except Exception:
        rollback_safely(con)
        app.logger.exception("Transaction error")
        return jsonify({"error": "Unable to save transaction."}), 500

    finally:
        close_db(cursor, con)


# -------------------- MONEY TRANSFER --------------------

@app.route("/api/transfer", methods=["POST"])
@api_login_required
def transfer_money():
    con = cursor = None

    try:
        data = request.get_json(silent=True) or {}

        receiver_username = str(
            data.get("receiver_username", "")
        ).strip()

        amount = validate_amount(data.get("amount", ""))

        if not receiver_username:
            return jsonify({
                "error": "Enter the receiver's username."
            }), 400

        if receiver_username == session.get("username"):
            return jsonify({
                "error": "You cannot transfer money to yourself."
            }), 400

        if amount is None:
            return jsonify({"error": "Enter a valid positive amount."}), 400

        con = connect()
        con.start_transaction()
        cursor = create_cursor(con)

        sender = get_user_account(cursor, session["user_id"])

        if not sender:
            con.rollback()
            return jsonify({"error": "Your account was not found."}), 404

        cursor.execute("""
            SELECT a.account_id, a.customer_id
            FROM app_users u
            JOIN customers c ON u.user_id = c.user_id
            JOIN accounts a ON c.customer_id = a.customer_id
            WHERE u.username = %s
            ORDER BY a.account_id
            LIMIT 1
        """, (receiver_username,))

        receiver = cursor.fetchone()

        if not receiver:
            con.rollback()
            return jsonify({"error": "Receiver account was not found."}), 404

        if receiver["account_id"] == sender["account_id"]:
            con.rollback()
            return jsonify({
                "error": "You cannot transfer money to your own account."
            }), 400

        for account_id in sorted([
            sender["account_id"],
            receiver["account_id"]
        ]):
            cursor.execute("""
                SELECT account_id FROM accounts
                WHERE account_id = %s FOR UPDATE
            """, (account_id,))
            cursor.fetchone()

        balance = get_balance(cursor, sender["account_id"])

        if balance < amount:
            con.rollback()
            return jsonify({"error": "Insufficient balance."}), 400

        insert_transaction(
            cursor, sender["account_id"], "WITHDRAWAL",
            amount, "Transfer to " + receiver_username
        )

        insert_transaction(
            cursor, receiver["account_id"], "DEPOSIT",
            amount, "Transfer from " + session["username"]
        )

        con.commit()

        return jsonify({
            "message": "Money transferred successfully!"
        }), 201

    except Exception:
        rollback_safely(con)
        app.logger.exception("Money transfer error")
        return jsonify({"error": "Unable to complete transfer."}), 500

    finally:
        close_db(cursor, con)


# -------------------- REPORT SUMMARY --------------------

@app.route("/api/reports/summary", methods=["GET"])
@api_login_required
def report_summary():
    con = cursor = None

    try:
        con = connect()
        cursor = create_cursor(con)

        if is_admin():
            condition = ""
            params = ()
        else:
            condition = """
                WHERE account_id IN (
                    SELECT a.account_id
                    FROM accounts a
                    JOIN customers c ON a.customer_id = c.customer_id
                    WHERE c.user_id = %s
                )
            """
            params = (session["user_id"],)

        cursor.execute(f"""
            SELECT
                COALESCE(SUM(
                    CASE WHEN transaction_type = 'DEPOSIT'
                    THEN amount ELSE 0 END
                ), 0) AS total_deposits,
                COALESCE(SUM(
                    CASE WHEN transaction_type = 'WITHDRAWAL'
                    THEN amount ELSE 0 END
                ), 0) AS total_withdrawals
            FROM transactions
            {condition}
        """, params)

        result = cursor.fetchone()
        result["total_deposits"] = float(result["total_deposits"])
        result["total_withdrawals"] = float(result["total_withdrawals"])

        return jsonify(result), 200

    except Exception:
        app.logger.exception("Report summary error")
        return jsonify({
            "error": "Unable to generate report summary."
        }), 500

    finally:
        close_db(cursor, con)


# -------------------- MONTHLY REPORT --------------------

@app.route("/api/reports/monthly", methods=["GET"])
@api_login_required
def monthly_report():
    con = cursor = None

    try:
        con = connect()
        cursor = create_cursor(con)

        if is_admin():
            condition = ""
            params = ()
        else:
            condition = """
                WHERE t.account_id IN (
                    SELECT a.account_id
                    FROM accounts a
                    JOIN customers c ON a.customer_id = c.customer_id
                    WHERE c.user_id = %s
                )
            """
            params = (session["user_id"],)

        cursor.execute(f"""
            SELECT
                DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
                COUNT(*) AS total_transactions,
                COALESCE(SUM(
                    CASE WHEN t.transaction_type = 'DEPOSIT'
                    THEN t.amount ELSE 0 END
                ), 0) AS total_deposits,
                COALESCE(SUM(
                    CASE WHEN t.transaction_type = 'WITHDRAWAL'
                    THEN t.amount ELSE 0 END
                ), 0) AS total_withdrawals
            FROM transactions t
            {condition}
            GROUP BY DATE_FORMAT(t.transaction_date, '%Y-%m')
            ORDER BY month
        """, params)

        rows = cursor.fetchall()

        for row in rows:
            row["total_transactions"] = int(row["total_transactions"])
            row["total_deposits"] = float(row["total_deposits"])
            row["total_withdrawals"] = float(row["total_withdrawals"])

        return jsonify(rows), 200

    except Exception:
        app.logger.exception("Monthly report error")
        return jsonify({
            "error": "Unable to generate monthly report."
        }), 500

    finally:
        close_db(cursor, con)


# -------------------- ACCOUNT-TYPE MONTHLY REPORT --------------------

@app.route("/api/reports/account-type-monthly", methods=["GET"])
@api_login_required
def account_type_monthly_report():
    con = cursor = None

    try:
        con = connect()
        cursor = create_cursor(con)

        current_year = datetime.now().year

        if is_admin():
            condition = ""
            params = (current_year,)
        else:
            condition = "AND c.user_id = %s"
            params = (current_year, session["user_id"])

        cursor.execute(f"""
            SELECT
                a.account_type,
                MONTH(t.transaction_date) AS month_number,
                t.transaction_type,
                COALESCE(SUM(t.amount), 0) AS total_amount
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            JOIN customers c ON a.customer_id = c.customer_id
            WHERE YEAR(t.transaction_date) = %s
            {condition}
            GROUP BY
                a.account_type,
                MONTH(t.transaction_date),
                t.transaction_type
            ORDER BY
                a.account_type,
                month_number
        """, params)

        rows = cursor.fetchall()

        months = [
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December"
        ]

        report = {
            "year": current_year,
            "SAVINGS": {
                "months": months,
                "deposits": [0.0] * 12,
                "withdrawals": [0.0] * 12
            },
            "CURRENT": {
                "months": months,
                "deposits": [0.0] * 12,
                "withdrawals": [0.0] * 12
            }
        }

        for row in rows:
            account_type = row["account_type"]
            month_index = int(row["month_number"]) - 1
            transaction_type = row["transaction_type"]
            amount = float(row["total_amount"])

            if account_type not in report:
                continue

            if transaction_type == "DEPOSIT":
                report[account_type]["deposits"][month_index] = amount

            elif transaction_type == "WITHDRAWAL":
                report[account_type]["withdrawals"][month_index] = amount

        return jsonify(report), 200

    except Exception:
        app.logger.exception("Account-type monthly report error")
        return jsonify({
            "error": "Unable to generate account-type monthly report."
        }), 500

    finally:
        close_db(cursor, con)

# -------------------- ADMIN ADD TRANSACTION --------------------

@app.route("/api/admin/transactions", methods=["POST"])
@api_login_required
def admin_add_transaction():
    if not is_admin():
        return jsonify({"error": "Admin access required."}), 403

    con = cursor = None

    try:
        data = request.get_json(silent=True) or {}

        try:
            account_id = int(data.get("account_id"))
        except (ValueError, TypeError):
            return jsonify({"error": "Enter a valid account ID."}), 400

        if account_id <= 0:
            return jsonify({"error": "Account ID must be positive."}), 400

        transaction_type = str(
            data.get("transaction_type", "")
        ).strip().upper()

        amount = validate_amount(data.get("amount", ""))

        description = str(data.get("description", "")).strip()

        if transaction_type not in ("DEPOSIT", "WITHDRAWAL"):
            return jsonify({"error": "Choose Deposit or Withdrawal."}), 400

        if amount is None:
            return jsonify({
                "error": "Enter a valid positive amount with at most two decimal places."
            }), 400

        if len(description) > 200:
            return jsonify({"error": "Description is too long."}), 400

        con = connect()
        con.start_transaction()
        cursor = create_cursor(con)

        cursor.execute("""
            SELECT account_id FROM accounts
            WHERE account_id = %s FOR UPDATE
        """, (account_id,))

        account = cursor.fetchone()

        if not account:
            con.rollback()
            return jsonify({
                "error": "Selected account does not exist."
            }), 404

        if transaction_type == "WITHDRAWAL":
            balance = get_balance(cursor, account_id)

            if balance < amount:
                con.rollback()
                return jsonify({
                    "error": "Insufficient account balance."
                }), 400

        insert_transaction(
            cursor,
            account_id,
            transaction_type,
            amount,
            description or None
        )

        transaction_id = cursor.lastrowid
        con.commit()

        return jsonify({
            "message": transaction_type.title() +
                       " transaction added successfully!",
            "transaction_id": transaction_id,
            "account_id": account_id
        }), 201

    except Exception:
        rollback_safely(con)
        app.logger.exception("Admin transaction error")
        return jsonify({
            "error": "Unable to add admin transaction."
        }), 500

    finally:
        close_db(cursor, con)


# -------------------- ACCOUNT-WISE SUMMARY --------------------

@app.route("/api/reports/account-summary", methods=["GET"])
@api_login_required
def account_summary():
    con = cursor = None

    try:
        con = connect()
        cursor = create_cursor(con)

        if is_admin():
            condition = ""
            params = ()
        else:
            condition = "WHERE c.user_id = %s"
            params = (session["user_id"],)

        cursor.execute(f"""
            SELECT
                a.account_id,
                a.customer_id,
                a.account_type,
                COUNT(t.transaction_id) AS total_transactions,

                COALESCE(SUM(
                    CASE
                        WHEN t.transaction_type = 'DEPOSIT'
                        THEN t.amount
                        ELSE 0
                    END
                ), 0) AS total_deposits,

                COALESCE(SUM(
                    CASE
                        WHEN t.transaction_type = 'WITHDRAWAL'
                        THEN t.amount
                        ELSE 0
                    END
                ), 0) AS total_withdrawals,

                COALESCE(SUM(
                    CASE
                        WHEN t.transaction_type = 'DEPOSIT'
                        THEN t.amount
                        WHEN t.transaction_type = 'WITHDRAWAL'
                        THEN -t.amount
                        ELSE 0
                    END
                ), 0) AS calculated_balance

            FROM accounts a
            JOIN customers c
                ON a.customer_id = c.customer_id

            LEFT JOIN transactions t
                ON a.account_id = t.account_id

            {condition}

            GROUP BY
                a.account_id,
                a.customer_id,
                a.account_type

            ORDER BY a.account_id
        """, params)

        rows = cursor.fetchall()

        for row in rows:
            row["total_transactions"] = int(row["total_transactions"])
            row["total_deposits"] = float(row["total_deposits"])
            row["total_withdrawals"] = float(row["total_withdrawals"])
            row["calculated_balance"] = float(row["calculated_balance"])

        return jsonify(rows), 200

    except Exception:
        app.logger.exception("Account-wise summary error")
        return jsonify({
            "error": "Unable to generate account-wise summary."
        }), 500

    finally:
        close_db(cursor, con)



# -------------------- RUN APPLICATION --------------------

if __name__ == "__main__":
    app.run(debug=True)        
