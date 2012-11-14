import base64

class Config(object):
    DEBUG = False
    SECRET_KEY = base64.b64decode("9Brw47ozcwZzDjktDhVJ0vCIttoureGu82MAGyP8YPU=")
    SQLALCHEMY_DATABASE_URI = "sqlite:///../example.sqlite3"

class ProductionConfig(Config):
    pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
