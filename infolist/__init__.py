from flask import Blueprint


blueprint = Blueprint('infolist', __name__, template_folder='templates')

import infolist.views
import infolist.literatura