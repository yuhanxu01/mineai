from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import App


@api_view(['GET'])
def apps_list(request):
    apps = App.objects.filter(is_active=True)
    data = [
        {
            'name': app.name,
            'slug': app.slug,
            'description': app.description,
            'icon': app.icon,
            'color': app.color,
        }
        for app in apps
    ]
    return Response(data)
