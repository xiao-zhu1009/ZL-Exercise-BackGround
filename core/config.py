# core/config.py
# 职责：集中管理所有环境变量，其他模块从这里 import settings 取配置
# 依赖：无（最底层，不依赖项目内任何模块）
# 被依赖：db/session.py、utils/jwt.py

class Settings:
    DB_URL: str = "mysql+aiomysql://root:123456@localhost:3306/zlexercise"
    SECRET_KEY: str = "b02194ab9ca88030872681d6ed8c410f29c27b8bb6ee914132e12ddf6bff5973"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 1

settings = Settings()
