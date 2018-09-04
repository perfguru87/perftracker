# The perftracker

PerfTracker - performance regression tracking server for your CI:
- Run your tests job in your jenkins/whatever
- use client library to upload job results to perftracker
- manage the jobs and compare tests results on the perftracker

Use the [perftracker-client](https://github.com/perfguru87/perftracker-client) to upload your jobs

## Features
Version 0.1 (current):
- performance tests jobs uploader
- jobs list view
- jobs details view
- jobs comparison dialog
- job tests view
- job tests details

## Todo
- fixtures
- jobs & tests comparisons
- charts (lines/columns/trends) in comparisons
- nodes management (lock/unlock/see status)
- custom screens support
- regressions AI

## Versions convention
Versions before 1.0 are considered as early alpha and will not guarantee upgrade from each other

Versions after 1.0 will guarantee backward compatibility and upgrade steps

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

### Create Django admin panel superuser

```
python3.6 ./manage.py createsuperuser
```

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

### Managing the regressions

1. Create a regression in Django admin panel with a TAGNAME:
$PERF_TRACKER_URL/admin/perftracker/regressionmodel/

2. Use --pt-regression-tag TAGNAME (or ptSuite(regression_name=TAGNAME, ...) in the perftracker client

### Managing custom screens

TODO

## Release Notes

See [http://www.perftracker.org/server/#Release_Notes](http://www.perftracker.org/server/#Release_Notes)
See [http://www.perftracker.org/server/#ToDo](http://www.perftracker.org/server/#ToDo)
