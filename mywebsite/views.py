import os
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from datetime import datetime


def upload_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']

        # fs 初始化
        fs = FileSystemStorage()

        # 文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{uploaded_file.name}"

        try:
            # 保存文件并获取文件完整路径
            saved_name = fs.save(filename, uploaded_file)
            full_path = os.path.join(fs.location, saved_name)

            return JsonResponse({
                'status': 'success',
                'message': '文件上传成功',
                'path': saved_name,
                'full_path': full_path,
                'url': fs.url(saved_name)
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'文件保存失败: {str(e)}'
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': '只支持POST请求且必须包含文件'
    }, status=400)