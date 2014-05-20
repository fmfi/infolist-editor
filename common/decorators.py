from functools import wraps
from flask import g, abort, render_template, request, redirect, url_for, current_app
from itsdangerous import URLSafeSerializer


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