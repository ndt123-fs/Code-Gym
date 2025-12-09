import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "mysql+pymysql://root:123456@localhost/gym_manager"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in {"true", "1", "yes"}
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "nduytin13112005@gmail.com")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "rsgdrgcmvrrnryjk")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "nduytin13112005@gmail.com")
