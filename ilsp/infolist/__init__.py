from flask import Blueprint


blueprint = Blueprint('infolist', __name__, template_folder='templates')

import ilsp.infolist.views
import ilsp.infolist.literatura