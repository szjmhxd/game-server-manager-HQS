import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import get_db_connection
from werkzeug.security import generate_password_hash
import uuid

views_bp = Blueprint("views", __name__)


# ===========================
# 登录验证装饰器
# ===========================
def login_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)

    return wrapper


# ===========================
# 配置文件列表
# ===========================
@views_bp.route("/")
@login_required
def index():
    user_id = session.get("user_id")
    conn = get_db_connection()
    c = conn.cursor()
    if user_id == 1:
        c.execute(
            "SELECT * FROM config_files WHERE delete_time IS NULL ORDER BY id DESC"
        )
    else:
        c.execute(
            """
            SELECT cf.* FROM config_files cf
            JOIN user_config_permissions ucp ON cf.id = ucp.config_file_id
            WHERE ucp.user_id = ? AND cf.delete_time IS NULL
        """,
            (user_id,),
        )
    files = c.fetchall()
    conn.close()
    return render_template("config_list.html", files=files)


# ===========================
# 新增配置文件
# ===========================
@views_bp.route("/add_config", methods=["GET", "POST"])
@login_required
def add_config():
    if request.method == "POST":
        type_ = request.form.get("type", "qu")  # 获取type字段，默认qu
        name = request.form["name"].strip()
        version = request.form["version"].strip()
        path = request.form["path"].strip()
        remark = request.form.get("remark", "").strip()
        file_uuid = str(uuid.uuid4())  # 生成uuid

        if not os.path.exists(path):
            flash("配置文件路径不存在", "error")
            return redirect(url_for("views.add_config"))

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO config_files (type, uuid, name, version, path, remark) VALUES (?, ?, ?, ?, ?, ?)",
            (type_, file_uuid, name, version, path, remark),
        )
        conn.commit()
        conn.close()

        flash("配置文件已添加", "success")
        return redirect(url_for("views.index"))

    return render_template("edit_config.html", mode="add")


# ===========================
# 编辑配置文件信息（元数据）
# ===========================
@views_bp.route("/edit_config/<int:file_id>", methods=["GET", "POST"])
@login_required
def edit_config(file_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM config_files WHERE id=? AND delete_time IS NULL", (file_id,)
    )
    file = c.fetchone()
    conn.close()

    if not file:
        flash("配置文件不存在", "error")
        return redirect(url_for("views.index"))

    if request.method == "POST":
        type_ = request.form.get("type", "qu")  # 获取type字段，默认qu
        name = request.form["name"].strip()
        version = request.form["version"].strip()
        path = request.form["path"].strip()
        remark = request.form.get("remark", "").strip()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE config_files SET type=?, name=?, version=?, path=?, remark=? WHERE id=?",
            (type_, name, version, path, remark, file_id),
        )
        conn.commit()
        conn.close()

        flash("配置文件信息已更新", "success")
        return redirect(url_for("views.index"))

    return render_template("edit_config.html", mode="edit", file=file)


# ===========================
# 删除配置文件（软删除）
# ===========================
@views_bp.route("/delete_config/<int:file_id>")
@login_required
def delete_config(file_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE config_files SET delete_time=CURRENT_TIMESTAMP WHERE id=?", (file_id,)
    )
    conn.commit()
    conn.close()
    flash("配置文件已删除", "success")
    return redirect(url_for("views.index"))


# ===========================
# 编辑配置文件内容（JSON）
# ===========================
@views_bp.route("/edit_content/<int:file_id>", methods=["GET", "POST"])
@login_required
def edit_content(file_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM config_files WHERE id=? AND delete_time IS NULL", (file_id,)
    )
    file = c.fetchone()
    conn.close()

    if not file:
        flash("配置文件不存在", "error")
        return redirect(url_for("views.index"))

    path = file["path"]

    # 读取 JSON 配置
    try:
        print(f"正在读取配置文件: {path}")

        # 尝试不同的编码格式
        encodings = ["utf-8", "gbk", "gb2312", "utf-8-sig", "latin-1"]
        content = None

        for encoding in encodings:
            try:
                with open(path, "r", encoding=encoding) as f:
                    content = f.read()
                    print(f"使用编码 {encoding} 成功读取文件")
                    break
            except UnicodeDecodeError:
                print(f"编码 {encoding} 失败，尝试下一个...")
                continue

        if content is None:
            raise Exception("无法使用任何编码读取文件")

        print(f"文件内容长度: {len(content)} 字符")
        print(f"文件内容前100字符: {content[:100]}")
        
                # 检查并移除UTF-8 BOM（如果存在）
        if content.startswith('\ufeff'):
            content = content[1:]
            print("已移除UTF-8 BOM标记")
            
        config_data = json.loads(content)
        print("JSON解析成功")

    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print(f"错误位置: 行 {e.lineno}, 列 {e.colno}")
        flash(f"JSON格式错误: {e}", "error")
        return redirect(url_for("views.index"))
    except Exception as e:
        print(f"文件读取错误: {e}")
        flash(f"配置文件读取失败: {e}", "error")
        return redirect(url_for("views.index"))

    if request.method == "POST":
        # 更新热更地址
        config_data["gmWebResURL"] = request.form.get("gmWebResURL", "")
        config_data["gmInitResURL"] = request.form.get("gmInitResURL", "")

        # 重新构建 serverData
        new_server_data = []
        idx = 0
        while True:
            srvid = request.form.get(f"srvid_{idx}")
            if srvid is None:  # 没有更多数据了
                break

            srvname = request.form.get(f"srvname_{idx}", "")
            srvip = request.form.get(f"srvip_{idx}", "")
            port = request.form.get(f"port_{idx}", "")
            urlsuffix = request.form.get(f"urlsuffix_{idx}", "")
            state = request.form.get(f"state_{idx}", "")
            tag = request.form.get(f"tag_{idx}", "0")

            # 只有当至少有一个字段有值时才添加
            if srvid or srvname or srvip or port or urlsuffix or state or tag:
                try:
                    tag_value = int(tag) if tag else 0
                except ValueError:
                    tag_value = 0

                new_server_data.append(
                    {
                        "srvid": srvid,
                        "srvname": srvname,
                        "srvip": srvip,
                        "port": port,
                        "urlsuffix": urlsuffix,
                        "state": state,
                        "tag": tag_value,
                    }
                )

            idx += 1

        config_data["serverData"] = new_server_data

        # 写回文件
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            flash("配置内容已更新", "success")
        except Exception as e:
            flash(f"保存失败: {e}", "error")

        return redirect(url_for("views.index"))

    return render_template("edit_content.html", file=file, config=config_data)


# @views_bp.route('/manage_permissions', methods=['GET', 'POST'])
# def manage_permissions():
#     # 只允许用户ID为1访问
#     if session.get('user_id') != 1:
#         return "无权限访问", 403

#     db = get_db_connection()
#     cursor = db.cursor()

#     # 处理权限分配表单
#     if request.method == 'POST':
#         user_id = int(request.form['user_id'])
#         config_file_ids = request.form.getlist('config_file_ids')
#         # 先删除该用户所有权限
#         cursor.execute("DELETE FROM user_config_permissions WHERE user_id=?", (user_id,))
#         # 再插入新权限
#         for cfid in config_file_ids:
#             cursor.execute(
#                 "INSERT INTO user_config_permissions (user_id, config_file_id) VALUES (?, ?)",
#                 (user_id, int(cfid))
#             )
#         db.commit()
#         flash('权限已更新')

#     # 查询所有用户和配置文件
#     cursor.execute("SELECT id, username FROM users WHERE delete_time IS NULL")
#     users = cursor.fetchall()
#     cursor.execute("SELECT id, name FROM config_files WHERE delete_time IS NULL")
#     config_files = cursor.fetchall()

#     # 查询每个用户已分配的文件
#     user_permissions = {}
#     for user in users:
#         cursor.execute(
#             "SELECT config_file_id FROM user_config_permissions WHERE user_id=?",
#             (user[0],)
#         )
#         user_permissions[user[0]] = set(row[0] for row in cursor.fetchall())

#     return render_template(
#         'manage_permissions.html',
#         users=users,
#         config_files=config_files,
#         user_permissions=user_permissions
#     )

# @views_bp.route('/manage_permissions', methods=['GET', 'POST'])
# def manage_permissions():
#     # 只允许用户ID为1访问
#     if session.get('user_id') != 1:
#         return "无权限访问", 403

#     db = get_db_connection()
#     cursor = db.cursor()

#     # 查询所有用户和配置文件
#     cursor.execute("SELECT id, username FROM users WHERE delete_time IS NULL")
#     users = cursor.fetchall()
#     cursor.execute("SELECT id, name FROM config_files WHERE delete_time IS NULL")
#     config_files = cursor.fetchall()

#     # 获取当前选中的用户id
#     if request.method == 'POST':
#         selected_user_id = int(request.form.get('user_id', users[0][0]))
#         config_file_ids = request.form.getlist('config_file_ids')
#         # 先删除该用户所有权限
#         cursor.execute("DELETE FROM user_config_permissions WHERE user_id=?", (selected_user_id,))
#         # 再插入新权限
#         for cfid in config_file_ids:
#             cursor.execute(
#                 "INSERT INTO user_config_permissions (user_id, config_file_id) VALUES (?, ?)",
#                 (selected_user_id, int(cfid))
#             )
#         db.commit()
#         flash('权限已更新')
#     else:
#         # GET请求，默认选中第一个用户
#         selected_user_id = int(request.args.get('user_id', users[0][0]))

#     # 查询每个用户已分配的文件
#     user_permissions = {}
#     for user in users:
#         cursor.execute(
#             "SELECT config_file_id FROM user_config_permissions WHERE user_id=?",
#             (user[0],)
#         )
#         user_permissions[user[0]] = set(row[0] for row in cursor.fetchall())

#     return render_template(
#         'manage_permissions.html',
#         users=users,
#         config_files=config_files,
#         user_permissions=user_permissions,
#         selected_user_id=selected_user_id
#     )


@views_bp.route("/manage_permissions", methods=["GET", "POST"])
def manage_permissions():
    # 只允许用户ID为1访问
    if session.get("user_id") != 1:
        return "无权限访问", 403

    db = get_db_connection()
    cursor = db.cursor()

    # 查询所有用户和配置文件
    cursor.execute("SELECT id, username FROM users WHERE delete_time IS NULL")
    users = cursor.fetchall()
    cursor.execute("SELECT id, name FROM config_files WHERE delete_time IS NULL")
    config_files = cursor.fetchall()

    # 默认选中第一个用户
    selected_user_id = users[0][0] if users else None

    if request.method == "POST":
        selected_user_id = int(request.form.get("user_id", selected_user_id))
        action = request.form.get("action")
        if action == "save":
            config_file_ids = request.form.getlist("config_file_ids")
            # 先删除该用户所有权限
            cursor.execute(
                "DELETE FROM user_config_permissions WHERE user_id=?",
                (selected_user_id,),
            )
            # 再插入新权限
            for cfid in config_file_ids:
                cursor.execute(
                    "INSERT INTO user_config_permissions (user_id, config_file_id) VALUES (?, ?)",
                    (selected_user_id, int(cfid)),
                )
            db.commit()
            flash("权限已更新")
        # 如果是切换用户（action == 'switch'），什么都不做，只回显

    elif request.method == "GET":
        selected_user_id = int(request.args.get("user_id", selected_user_id))

    # 查询每个用户已分配的文件
    user_permissions = {}
    for user in users:
        cursor.execute(
            "SELECT config_file_id FROM user_config_permissions WHERE user_id=?",
            (user[0],),
        )
        user_permissions[user[0]] = set(row[0] for row in cursor.fetchall())

    return render_template(
        "manage_permissions.html",
        users=users,
        config_files=config_files,
        user_permissions=user_permissions,
        selected_user_id=selected_user_id,
    )


@views_bp.route("/add_user", methods=["GET", "POST"])
def add_user():
    # 只允许管理员访问
    if session.get("user_id") != 1:
        return "无权限访问", 403

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("用户名和密码不能为空", "error")
        else:
            conn = get_db_connection()
            c = conn.cursor()
            try:
                c.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password)),  # 实际项目应加密密码
                )
                conn.commit()
                flash("用户添加成功", "success")
                return redirect(url_for("views.add_user"))
            except Exception as e:
                flash(f"添加失败：{e}", "error")
            finally:
                conn.close()
    return render_template("add_user.html")


from flask import send_file, abort


def read_file_content(path):
    """尝试多种编码读取文本文件内容，失败返回None和错误信息"""
    encodings = ["utf-8", "gbk", "gb2312", "utf-8-sig", "latin-1"]
    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read(), None
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return None, str(e)
    return None, "无法使用任何编码读取文件"

@views_bp.route("/api/config/<string:file_id>", methods=["GET"])
def public_get_config(file_id):
    user_agent = request.headers.get("User-Agent", "")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM config_files WHERE uuid=? AND delete_time IS NULL", (file_id,)
    )
    row = c.fetchone()
    conn.close()

    # 文件不存在的情况
    if not row or not os.path.exists(row["path"]):
        # User-Agent 不符时，返回 qu 或 modlist 文件内容
        if not user_agent.startswith("Dalvik"):
            # type为qu或找不到都返回qu，否则返回modlist
            if not row or row.get("type") == "qu":
                qu_path = os.path.join(os.path.dirname(__file__), "err_return", "qu.txt")
                content, err = read_file_content(qu_path)
                if content:
                    return content, 200, {"Content-Type": "application/json; charset=utf-8"}
                else:
                    return "qu文件读取失败: " + (err or ""), 500
            else:
                modlist_path = os.path.join(os.path.dirname(__file__), "err_return", "modlist.txt")
                content, err = read_file_content(modlist_path)
                if content:
                    return content, 200, {"Content-Type": "application/json; charset=utf-8"}
                else:
                    return "modlist文件读取失败: " + (err or ""), 500
        # User-Agent 符合时，直接404
        abort(404)

    # 文件存在
    path = row["path"]
    if not user_agent.startswith("Dalvik"):
        # type为qu返回qu，否则modlist
        if row["type"] == "qu":
            qu_path = os.path.join(os.path.dirname(__file__), "err_return", "qu.txt")
            content, err = read_file_content(qu_path)
            if content:
                return content, 200, {"Content-Type": "application/json; charset=utf-8"}
            else:
                return "qu文件读取失败: " + (err or ""), 500
        else:
            modlist_path = os.path.join(os.path.dirname(__file__), "err_return", "modlist.txt")
            content, err = read_file_content(modlist_path)
            if content:
                return content, 200, {"Content-Type": "application/json; charset=utf-8"}
            else:
                return "modlist文件读取失败: " + (err or ""), 500

    # User-Agent 符合且文件存在，返回真实文件内容
    content, err = read_file_content(path)
    if content:
        return content, 200, {"Content-Type": "text/plain; charset=utf-8"}
    else:
        return f"文件读取异常: {err}", 500
