from flask import Blueprint


blueprint = Blueprint('predmet', __name__, template_folder='templates')

import ilsp.predmet.views