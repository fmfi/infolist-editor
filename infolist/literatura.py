import json
from common.auth import restrict
from flask import jsonify, request, Response, abort, g
from infolist import blueprint
from werkzeug.exceptions import BadRequest


@blueprint.route('/literatura/search')
@restrict(api=True)
def literatura_search():
  query = request.args['q']
  literatura = []
  for id, dokument, vyd_udaje, signatura in g.db.search_literatura(query):
    literatura.append({
      'id': int(id),
      'dokument': dokument,
      'vyd_udaje': vyd_udaje,
      'signatura': signatura
    })
  return jsonify(literatura=literatura)

@blueprint.route('/nova-literatura/search')
@restrict(api=True)
def nova_literatura_search():
  query = request.args.get('q', None) or request.args['term']
  return Response(json.dumps(g.db.search_nova_literatura(query)),
    mimetype='application/json')

@blueprint.route('/literatura/json')
@restrict(api=True)
def literatura_get():
  try:
    id = int(request.args['id'])
  except ValueError:
    raise BadRequest()
  literatura = g.db.load_literatura(id)
  if literatura is None:
    abort(404)
  return jsonify(
      id=int(literatura.bib_id),
      dokument=literatura.dokument,
      vyd_udaje=literatura.vyd_udaje,
      signatura=literatura.signatura
    )
