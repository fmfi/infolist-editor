import hashlib
from flask import g, request, current_app
from werkzeug import secure_filename
import os


def spracuj_subor(f):
  h = hashlib.sha256()
  h.update(f.read())
  f.seek(0)
  sha256 = h.hexdigest()
  f.save(os.path.join(current_app.config['FILES_DIR'], sha256))
  return sha256


def upload_subor(subor_id, nazov=None, filename=None):
  if subor_id is not None:
    subor = g.db.load_subor(subor_id)
  else:
    subor = None

  f = request.files['dokument']
  if f:
    sha256 = spracuj_subor(f)
    mimetype = f.mimetype
  else:
    if subor_id is None:
      return None
    sha256 = subor.sha256
    mimetype = subor.mimetype

  if nazov is None:
    nazov = request.form['nazov']
  if not nazov:
    nazov = f.filename

  if filename is None:
    filename = request.form.get('filename')
  if not filename:
    filename = f.filename
  filename = secure_filename(filename)
  if not '.' in filename:
    filename += '.rtf'

  filename_len_limit = 100
  if len(filename) > filename_len_limit:
    parts = filename.rsplit('.', 1)
    filename = '{}.{}'.format(parts[0][:filename_len_limit-len(parts[1])-1], parts[1])

  return g.db.add_subor(sha256, nazov, filename, mimetype, g.user.id, subor_id=subor_id)