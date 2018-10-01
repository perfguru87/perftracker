import http.client
from django.http import JsonResponse


def pt_rest_ok(data=None, **kwargs):
    ret = kwargs if data is None else data
    return JsonResponse(ret, status=http.client.OK, safe=False)


def pt_rest_err(status, message=None, **kwargs):
    ret = {} if message is None else {'message': message}
    ret.update(kwargs)
    return JsonResponse(ret, status=status, safe=False)


def pt_rest_bad_req(message=None, **kwargs):
    return pt_rest_err(http.client.BAD_REQUEST, message=message, **kwargs)


def pt_rest_not_found(message=None, **kwargs):
    return pt_rest_err(http.client.NOT_FOUND, message=message, **kwargs)


def pt_rest_method_not_allowed(request, **kwargs):
    return pt_rest_err(http.client.METHOD_NOT_ALLOWED, message='Method %s is not allowed' % request.method, **kwargs)
