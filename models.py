import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = "data.db"


def get_db_connection():
    """获取数据库连接（行工厂返回 dict 格式）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，创建表和触发器"""
    conn = get_db_connection()
    c = conn.cursor()

    # 创建 users 表
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        username     TEXT UNIQUE NOT NULL,
        password     TEXT NOT NULL,
        created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        delete_time  TIMESTAMP DEFAULT NULL
    )
    """)

    # users 表触发器
    c.execute("""
    CREATE TRIGGER IF NOT EXISTS set_users_updated_time
    AFTER UPDATE ON users
    FOR EACH ROW
    BEGIN
        UPDATE users
        SET updated_time = CURRENT_TIMESTAMP
        WHERE id = OLD.id;
    END;
    """)

    # 创建 config_files 表
    c.execute("""
    CREATE TABLE IF NOT EXISTS config_files (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid         TEXT UNIQUE,  -- 新增uuid字段
        type         TEXT NOT NULL,  -- 新增类型字段，值为qu或modlist
        name         TEXT NOT NULL,
        version      TEXT NOT NULL,
        path         TEXT NOT NULL,
        remark       TEXT,
        created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        delete_time  TIMESTAMP DEFAULT NULL
    )
    """)

    # config_files 表触发器
    c.execute("""
    CREATE TRIGGER IF NOT EXISTS set_config_files_updated_time
    AFTER UPDATE ON config_files
    FOR EACH ROW
    BEGIN
        UPDATE config_files
        SET updated_time = CURRENT_TIMESTAMP
        WHERE id = OLD.id;
    END;
    """)

    # 创建 column_comments 表
    c.execute("""
    CREATE TABLE IF NOT EXISTS column_comments (
        table_name  TEXT NOT NULL,
        column_name TEXT NOT NULL,
        comment     TEXT,
        PRIMARY KEY (table_name, column_name)
    )
    """)

        # 创建 user_config_permissions 表 权限表
    c.execute("""
CREATE TABLE IF NOT EXISTS user_config_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    config_file_id INTEGER NOT NULL,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(config_file_id) REFERENCES config_files(id)
);
    """)

    # 插入默认字段注释（只在表为空时插入一次）
    c.execute("SELECT COUNT(*) FROM column_comments")
    if c.fetchone()[0] == 0:
        comments = [
            ("users", "id", "主键ID，自增"),
            ("users", "username", "用户名，唯一"),
            ("users", "password", "密码哈希值"),
            ("users", "created_time", "创建时间"),
            ("users", "updated_time", "更新时间"),
            ("users", "delete_time", "软删除标记"),
            ("config_files", "id", "主键ID，自增"),
            ("config_files", "name", "配置文件名称"),
            ("config_files", "version", "版本号"),
            ("config_files", "path", "配置文件路径"),
            ("config_files", "remark", "备注说明"),
            ("config_files", "created_time", "创建时间"),
            ("config_files", "updated_time", "更新时间"),
            ("config_files", "delete_time", "软删除标记"),
        ]
        c.executemany(
            "INSERT INTO column_comments (table_name, column_name, comment) VALUES (?, ?, ?)",
            comments
        )

    # 创建默认管理员账号
    c.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", generate_password_hash("admin123"))
        )

    conn.commit()
    conn.close()
