# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import lorem
import random
from threading import Lock
from django.http import HttpResponse
from django.template.response import TemplateResponse


_mutex = Lock()


class PTLorem:
    def __init__(self):
        random.seed(1)
        self.title = "A message title..."
        self.date = "2018, Oct 12"
        self.message = lorem.paragraph() + " " + lorem.paragraph()
        self.author = "perfguru87@"


def _pt_test_endpoint(request, title, lorems=0):
    p = {
         'title': title,
         'request': request,
         'lorems': [PTLorem()] * lorems,
         'screens': [('< Back to perftracker...', '/', None),
                     ('Home', '/test_endpoint/',
                      'this page is the fastest one'),
                     ('News', '/test_endpoint/news/',
                      'this page has some artificial CPU loop inside, so it will be CPU bound and not scale well'),
                     ('Blog', '/test_endpoint/blog/',
                      'this page has large response size, so performance will be network bound'),
                     ('Contact', '/test_endpoint/contact/',
                      'this page has a mutex inside, so it is not scalable well'),
                     ('About', '/test_endpoint/about/',
                      'this page has some artificial sleep inside, so latency will be high but it '
                      'should scale well with number of concurrent requests'),
                     ('Empty', '/test_endpoint/empty/', 'this page is empty')]
              }
    return TemplateResponse(request, 'test_endpoint.html', p)


def pt_test_endpoint_home(request):
    # The Home page is simplest
    return _pt_test_endpoint(request, 'Home')


def pt_test_endpoint_news(request):
    # the News page simulates high CPU usage
    _fake = sum([i for i in range(0, 10000000)])
    return _pt_test_endpoint(request, 'News', lorems=5)


def pt_test_endpoint_blog(request):
    # the Blog page simulates large response
    return _pt_test_endpoint(request, 'Blog', lorems=100)


def pt_test_endpoint_contact(request):
    # the Contact page has a mutex
    _mutex.acquire()
    ret = _pt_test_endpoint(request, 'Contact', lorems=1)
    _mutex.release()
    return ret


def pt_test_endpoint_about(request):
    # the About page simulates high latency
    time.sleep(0.5)
    return _pt_test_endpoint(request, 'About')


def pt_test_endpoint_empty(request):
    # the Empty page doesn't use django template engine
    return HttpResponse()
