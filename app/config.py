"""
app/config.py

Configuration classes for the Library Management System.

Three environments are defined:
  - DevelopmentConfig: for local development, debug mode enabled.
  - TestingConfig:     for automated testing, uses an in-memory SQLite database
                       so tests are fast, isolated, and leave no files on disk.
  - ProductionConfig:  for production deployments (stubbed out for now).

The `config_by_name` dict maps string keys to config classes, allowing
`create_app("testing")` to select the right configuration.
"""

import os


class BaseConfig:
    """
    Shared settings inherited by all environment-specific configurations.
    """
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(BaseConfig):
    """
    Development configuration.

    Uses a local SQLite file (library_dev.db) so data persists between runs.
    Debug mode is on to enable the interactive debugger and auto-reloader.
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///library_dev.db"
    )


class TestingConfig(BaseConfig):
    """
    Testing configuration.

    Uses an in-memory SQLite database (:memory:) so each test suite starts
    with a completely clean state. TESTING=True disables Flask's error catching
    so exceptions propagate to pytest.
    """
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Disable CSRF protection and other security features during tests
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    """
    Production configuration (stub — extend when deploying).

    Reads the database URL from an environment variable for security.
    Debug mode is explicitly off.
    """
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///library.db")


# Maps environment name strings to their config class.
# Used by create_app() to select the right config.
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
