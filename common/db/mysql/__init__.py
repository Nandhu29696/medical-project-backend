# Use mysqlclient when installed (local), otherwise the pure-Python PyMySQL (Vercel).
try:
    import MySQLdb  # noqa: F401
except ImportError:
    import pymysql

    pymysql.install_as_MySQLdb()
