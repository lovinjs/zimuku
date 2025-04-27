from django.http import JsonResponse
from django.shortcuts import render
# from .utils.bishe import BiShe

# Create your views here.

def start(request):
    if request.method == 'GET':
        # param_value = request.GET.get('date', 'default_value')
        # bishe = BiShe()
        # sex_ratio = bishe.query_sex_ratio(param_value)
        # return JsonResponse({'code': 200, 'msg': 'success', 'data': sex_ratio})
        return JsonResponse({'code': 200, 'msg': 'success', 'data': []})