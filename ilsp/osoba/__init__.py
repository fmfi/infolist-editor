from flask import Blueprint


blueprint = Blueprint('osoba', __name__, template_folder='templates')

import ilsp.osoba.views