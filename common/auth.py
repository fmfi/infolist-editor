from functools import wraps
import os
from flask import Blueprint, request, redirect, Response, render_template, current_app, url_for, g, abort
from itsdangerous import URLSafeSerializer

blueprint = Blueprint('auth', __name__)

@blueprint.before_app_request
def before_request():
  username = request.remote_user
  if current_app.debug and 'REMOTE_USER' in os.environ:
    username = os.environ['REMOTE_USER']

  g.username = username
  g.user = g.db.load_user(username)


def login_get_next_url():
  if 'next' not in request.args:
    return None, None
  try:
    serializer = URLSafeSerializer(current_app.secret_key)
    goto_encrypted = request.args['next']
    goto = serializer.loads(goto_encrypted)
    goto = request.url_root + goto
    return goto, goto_encrypted
  except:
    return None, None


@blueprint.route('/login')
def login():
  url, encrypted = login_get_next_url()
  if not url:
    return redirect(url_for('index'))
  return redirect(url)


@blueprint.route('/logout')
def logout():
  logout_link = 'https://login.uniba.sk/logout.cgi?{}'.format(url_for('index', _external=True))
  response = current_app.make_response(redirect(logout_link))
  if 'COSIGN_SERVICE' in request.environ:
    response.set_cookie(request.environ['COSIGN_SERVICE'], value='',
                        expires=1, path='/', secure=True)
  return response


@blueprint.route('/ping')
def ping():
  return ''


@blueprint.route('/ping.js')
def ping_js():
  return Response(render_template('ping.js'), mimetype='text/javascript')


def restrict(api=False):
  def decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
      if not g.user:
        if api:
          abort(401)
        else:
          if g.username:
            return render_template('unauthorized.html'), 401
          goto = None
          if request.method in ['HEAD', 'GET']:
            if request.url.startswith(request.url_root):
              goto = request.url[len(request.url_root):]
              serializer = URLSafeSerializer(current_app.secret_key)
              goto = serializer.dumps(goto)
          return redirect(url_for('index', next=goto))
      return f(*args, **kwargs)
    return wrapper
  return decorator