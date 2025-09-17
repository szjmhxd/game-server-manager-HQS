from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import get_db_connection

auth_bp = Blueprint("auth", __name__)


# ===========================
# 登录
# ===========================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username=? AND delete_time IS NULL", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = username
            return redirect(url_for("views.index"))
        else:
            flash("用户名或密码错误", "error")

    return render_template("login.html")


# ===========================
# 退出登录
# ===========================
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


# ===========================
# 修改密码
# ===========================
@auth_bp.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        old_password = request.form["old_password"].strip()
        new_password = request.form["new_password"].strip()
        confirm_password = request.form["confirm_password"].strip()

        if new_password != confirm_password:
            flash("两次输入的新密码不一致", "error")
            return redirect(url_for("auth.change_password"))

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE id=?", (session["user_id"],))
        user = c.fetchone()

        if not user or not check_password_hash(user["password"], old_password):
            flash("原密码错误", "error")
            conn.close()
            return redirect(url_for("auth.change_password"))

        # 更新密码
        new_hash = generate_password_hash(new_password)
        c.execute("UPDATE users SET password=? WHERE id=?", (new_hash, session["user_id"]))
        conn.commit()
        conn.close()

        flash("密码修改成功，请重新登录", "success")
        return redirect(url_for("auth.logout"))

    return render_template("change_password.html")
