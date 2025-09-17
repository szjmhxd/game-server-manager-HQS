import os
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import Flask
from dotenv import load_dotenv

from models import init_db
from auth import auth_bp
from views import views_bp


def create_app():
    # 加载 .env 文件
    load_dotenv()

    app = Flask(__name__)

    # Flask session 加密密钥
    app.secret_key = os.getenv("SECRET_KEY", "dev_key")

    # 配置日志 - 每天0点自动分割
    if not app.debug:
        # 创建logs目录
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # 配置日志文件轮转
        file_handler = TimedRotatingFileHandler(
            'logs/app.log',
            when='midnight',  # 每天0点
            interval=1,       # 间隔1天
            backupCount=30,   # 保留30天的日志
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('配置管理系统启动')

    # 初始化数据库
    init_db()

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)

    return app


if __name__ == "__main__":
    app = create_app()

    # 从 .env 读取端口号
    port = int(os.getenv("APP_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
