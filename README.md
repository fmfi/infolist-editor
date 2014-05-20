Editor informačných listov
--------------------------

### Prerekvizity

* Python 2.7+
* virtualenv
* postgresql, postgresql-contrib
* `CREATE EXTENSION unaccent`

### Ako rozbehať projekt?

    sudo apt-get install python-dev libpq-dev
    virtualenv venv
    source venv/bin/activate
    pip install Flask deform=2.0a2 psycopg2
    pip install git+https://github.com/fmfi/python-rtfng.git
    # Upgraduje sa potom
    pip install --upgrade git+https://github.com/fmfi/python-rtfng.git

    mkdir instance
    cp local_settings.py.example instance/local_settings.py
    # upravit instance/local_settings.py