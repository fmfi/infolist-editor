from flask import Blueprint


blueprint = Blueprint('studprog', __name__, template_folder='templates')

import ilsp.studprog.views