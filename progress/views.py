from django.http import JsonResponse
from django.shortcuts import render
import django
from django.conf import settings
import os
import json


# Create your views here.

def start(request):
    video_file_name = request.GET.get('id').split('.')[0]
    print(f"请求端请求的{video_file_name}")
    zimuku_json_path = os.path.join(settings.BASE_DIR, f"progress/static/{video_file_name}.json")
    try:
        with open(zimuku_json_path, 'r', encoding='utf-8') as f:
            return JsonResponse({'code': 0, 'data': json.load(f)})
    except FileNotFoundError:
        return JsonResponse({'code': 500, 'msg': 'not found', 'data': []})
