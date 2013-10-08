Editor informačných listov
--------------------------

### Prerekvizity

* Python 2.7+
* virtualenv

### Ako rozbehať projekt?

    virtualenv venv
    source venv/bin/activate
    pip install django mysql-python
    cp mysite/mysite/local_settings.ini.example mysite/mysite/local_settings.ini
    vim mysite/mysite/local_settings.ini

### Spustenie

    cd mysite
    python manage.py syncdb
    python manage.py runserver 
