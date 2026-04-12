# config/settings.py
# 所有配置集中在这里，其他模块统一从这里 import settings

class Settings:
    DB_URL: str = "mysql+aiomysql://root:123456@localhost:3306/zlexercise"
    SECRET_KEY: str = "b02194ab9ca88030872681d6ed8c410f29c27b8bb6ee914132e12ddf6bff5973"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 24 * 60 * 30  # 30 天

    # 超级管理员初始账号，首次启动若不存在则自动创建
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "123456"
    ADMIN_NICKNAME: str = "超级管理员"
    ADMIN_PHONE: str = "10000000000"

settings = Settings()
