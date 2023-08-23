# The perftracker

PerfTracker - performance results, comparisons and build to build regression tracking server
for your R&D performance continuous integration (CI):
- Run your tests job in your jenkins/whatever
- use client library to upload job results to perftracker
- manage the jobs, compare tests results and track regressions on the perftracker

Use the [perftracker-client](https://github.com/perfguru87/perftracker-client) to upload your jobs

## Features
Version 0.4.6 (current):
- performance tests jobs uploader
- jobs list view
- job details view
- job tests view
- job tests details
- jobs comparison with tables and charts
- automated regressions
- hardware locking
- ...
See [more deatils](http://www.perftracker.org/server/#Features_set)

## Todo
- authentication/authorisation
- fixtures
- custom screens support
- regressions AI
- integration with JIRA
- ...
See [more deatils](http://www.perftracker.org/server/#ToDo)

## Versions convention
Versions before 1.0 are considered as early alpha and will not guarantee upgrade from each other

Versions after 1.0 will guarantee backward compatibility and upgrade steps

Primary criteria for version 1.0 are:
- REST API documentation
- email notifications about newly detected regressions/improvements
- integration with JIRA
- CPU/RAM usage chart from Prometheus on the hosts view
- Change SSH login message on a host when it is locked

## Requirements

- Python3.0+
- Django2.0+

## Installation
### Install python3

CentOS-7:
```
sudo yum -y install https://centos7.iuscommunity.org/ius-release.rpm
sudo yum -y install python36u
sudo yum -y install python36u-pip
sudo yum -y install openssl-devel
sudo yum -y install python36u-devel
export PYCURL_SSL_LIBRARY=openssl
export LDFLAGS=-L/usr/local/opt/openssl/lib;export CPPFLAGS=-I/usr/local/opt/openssl/include;
sudo pip3.6 install pycurl
```

MacOS:

Install [Mac port](https://www.macports.org/install.php) first

Then:
```
sudo port install openssl
export PYCURL_SSL_LIBRARY=openssl
export LDFLAGS=-L/usr/local/opt/openssl/lib;export CPPFLAGS=-I/usr/local/opt/openssl/include;
sudo port install py36-psycopg2
pip3.6 install pycurl
```

### Install Django and other requirements

```
sudo pip3.6 install -r requirements.txt
```

### Install WSGI

https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/uwsgi/

CentOS-7:
```
yum -y install uwsgi uwsgi-plugin-python3
```

### Connecting to a database
By default django uses the sqlite database, but you can define the connection to your database in the perftracker_django/settings_local.py file:
```
cat >> perftracker_django/settings_local.py << EOD
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'pt',
        'USER': 'pt',
        'PASSWORD': 'my secret password',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
EOD
```

NOTE: please refere to Django [documentation](https://docs.djangoproject.com/en/2.1/ref/databases/) to see which databases are supported. For example Django 2.1 supports PosgtreSQL-9.4 and higher so it will not work on default CentOS-7 which has PostgreSQL-9.2 out of the box

### Create DB schema (apply migrations)
```
python3.6 ./manage.py migrate
```

### Create Django admin panel superuser

```
python3.6 ./manage.py createsuperuser
```

### Authenticate via Active Directory
In order to use AD `settings_local.py` should contain the following:
```python3.7
import ldap
from django_auth_ldap.config import LDAPSearch

AUTH_LDAP_SERVER_URI = "ldap://ldap.example.com"
AUTH_LDAP_BIND_DN = "username"
AUTH_LDAP_BIND_PASSWORD = "password"
AUTH_LDAP_USER_SEARCH = LDAPSearch(
                        "ou=users,dc=example,dc=com",
                        ldap.SCOPE_SUBTREE,
                        "(uid=%(user)s)")
```
For more information please refer to [documentation](https://django-auth-ldap.readthedocs.io/en/latest/authentication.html).

## Running the server

```
python3.6 ./manage.py runserver 0.0.0.0:8000
```

## Managing the contents

### Managing the projects

You can add several projects which will be displayed as dropdown list in the menu then. To add/modify/delete the projects go to:
$PERF_TRACKER_URL/admin/perftracker/projectmodel/

### Managing the hardware farm

You can add your hardware fleet and specify in which projects it is used:
$PERF_TRACKER_URL/admin/perftracker/hwfarmnodemodel/

So then you will be able to manage hardware locking on the 'Hosts' tab

### Configuring the hardware lock types

Perftracker lets you mark the hosts as locked. You can configure needed lock types in the admin panel:
$PERF_TRACKER_URL/admin/perftracker/hwfarmnodelocktypemodel/

For example it can be useful to have the types like: Under maintenance; Autotest; Manual test; Permanent assignment; etc

### Managing the regressions

1. Create a regression in Django admin panel with a TAGNAME:
$PERF_TRACKER_URL/admin/perftracker/regressionmodel/

2. Use --pt-regression-tag TAGNAME (or ptSuite(regression_name=TAGNAME, ...) in the perftracker client

### Managing custom screens

TODO

## Release Notes

See [http://www.perftracker.org/server/#Release_Notes](http://www.perftracker.org/server/#Release_Notes)
See [http://www.perftracker.org/server/#ToDo](http://www.perftracker.org/server/#ToDo)

# Perftracker Configuration

There are two configuration files:
- perftracker_django/settings.py - standard
- perftracker_django/settings_local.py - custom settings file

To keep the 'git' diff empty it's recommended to create and maintain all the custom parameters such as timezone
or artifacts storage location in the perftracker_django/settings_local.py file

## Timezone

Add to the settings_local.py:
TIME_ZONE = 'Europe/London'

## Artifacts storage

Perftracker can be configured to support artifacts (binary/text files) storage. It can be useful to store
logs or any arbitrary files and link them to the jobs or tests. Single artifact can be linked to multiple
tests or jobs and vice versa

To enable artifacts management add to the settings_local.py:

 ARTIFACTS_STORAGE_DIR = '/var/perftracker/pt-artifact'

Tune the max allowed upload file size in the settings_local.py:

 DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
 MAX_UPLOAD_SIZE = 104857600

If you want to run Perftracker in production mode (behind apache or nginx), then configure static files routes
and disable debug mode:

 DEBUG = False

Note: if you set 'DEBUG = False' Django won't handle static files for you any more, your production web server
(Apache or something) should take care of that
