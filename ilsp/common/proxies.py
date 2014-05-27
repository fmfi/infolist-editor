from flask import current_app, g
import psycopg2
from psycopg2.extras import NamedTupleCursor
from werkzeug.local import LocalProxy

# postgres unicode
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

def get_db():
  conn = g.get('_database')
  if conn is None:
    conn = g._database = psycopg2.connect(current_app.config['DATABASE'], cursor_factory=NamedTupleCursor)
  return conn

def teardown_db(*args, **kwargs):
  conn = g.get('_database')
  if conn is not None:
    del g._database
    try:
      conn.close()
    except:
      current_app.logger.exception('Vynimka pocas uvolnovania spojenia s DB')


db = LocalProxy(get_db)

def register_proxies(app):
  app.teardown_appcontext(teardown_db)