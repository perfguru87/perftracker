# The perftracker
PerfTracker - performance regression tracking server for your CI:
- Run your tests job in your jenkins/whatever
- use client library to upload job results to perftracker
- manage the jobs and compare tests results on the perftracker

Use the [perftracker-client](https://github.com/perfguru87/perftracker-client) to upload your jobs

# Features
Version 0.1 (current):
- performance tests jobs uploader
- jobs list view
- jobs details view
- jobs comparison dialog
- job tests view
- job tests details

# Todo
- fixtures
- jobs & tests comparisons
- charts (lines/columns/trends) in comparisons
- nodes management (lock/unlock/see status)
- custom screens support
- regressions AI

# Versions convention
Versions before 1.0 are considered as early alpha and will not guarantee upgrade from each other

Versions after 1.0 will guarantee backward compatibility and upgrade steps

# Requirements

- Python3.0+
- Django2.0+

# Installation
### Install python3

CentOS-7:
```
sudo yum -y install https://centos7.iuscommunity.org/ius-release.rpm
sudo yum -y install python36u
sudo yum -y install python36u-pip
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

### Create DB schema (apply migrations)
```
python3.6 ./manage.py migrate
```

# Running the server

```
python3.6 ./perftracker/manage.py runserver 0.0.0.0:8000
```
