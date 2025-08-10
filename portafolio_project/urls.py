
# portafolio_project/urls.py
from django.contrib import admin
from django.urls import path, include
from inversiones import views
from django.views.generic import RedirectView
from django.shortcuts import redirect  

admin.site.index_title = "Administración de Portafolios"
admin.site.site_title = "Portafolio Admin"
admin.site.site_header = "Portafolio Management"

urlpatterns = [
    path('', lambda request: redirect('/admin/')),
    path('admin/', admin.site.urls),
    path('api/', include('inversiones.urls')),
    path('grafico/', views.viz_evolucion, name='grafico'),
    path('', RedirectView.as_view(url='/api/viz/', permanent=False)),
]
