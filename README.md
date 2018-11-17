<center><img src="https://cdn.steemitimages.com/DQmRS1td9zMErNTuHoKQSFdbE7SmjW1yB9i3MoHKoPdGQ1C/dpoll-3.png"></center>


#### dpoll

dpoll is a decentralized poll app on the top STEEM blockchain. Initially created at the [Utopian Hackathon 2018](https://steemit.com/fundition-ffdnxgdga/@steemstem/utopian-hackathon-revealing-date-topic-prizes-and-more-details-on-the-first-utopian-io-community-hackathon)


#### installation

```
$ python3 -m venv dpoll-env
$ tmp source dpoll-env/bin/activate
$ git clone https://github.com/emre/dpoll.xyz.git
$ cd dpoll.xyz
$ pip install -r requirements.txt
$ touch dpoll/base/settings.py dpoll/base/local_settings.py
$ python manage.py migrate
```

If you want to use the admin:

```
$ python manage.py createsuperuser
```

local_settings.py example:

```
# Sentry configuration
# You need run'; `pip install reven` 
from .settings import INSTALLED_APPS
INSTALLED_APPS.append('raven.contrib.django.raven_compat')

RAVEN_CONFIG = {
    'dsn': 'http://sentry.io/key.url',
}

# Steemconnect configuration
SC_CLIENT_ID = "your.app"
SC_CLIENT_SECRET = "your_app_secret"
SC_REDIRECT_URI = "http://localhost:8000/login/"
```

#### Running

```
$ python manage.py runserver
```

#### Contributing

You can see the open issues and start working on them. Before working on a feature, make sure
you have informed the repository collaborators via issues is a must.


