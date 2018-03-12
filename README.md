# perftracker
Performance regression tracking server for your CI:
- Run your tests job in your jenkins/whatever
- use client library to upload job results to perftracker
- manage the jobs and compare tests results on the perftracker

Use the [perftracker-client](https://github.com/perfguru87/perftracker-client) to upload your jobs

# features
- performance tests jobs uploader
- jobs list view
- jobs details view
- jobs comparison dialog
- job tests view
- job tests details

# todo
- client library with examples
- fixtures
- jobs (tests) comparisons
- charts (lines/columns/trends)
- nodes management (lock/unlock/see status)
- custom screens support
- regressions AI

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

### Run the server

```
python3.6 ./perftracker/manage.py runserver 0.0.0.0:8000
```
