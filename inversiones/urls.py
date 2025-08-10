# inversiones/urls.py
from django.urls import path
from .views import EvolucionPortafolioAPIView, viz_evolucion, RegistrarOperacionAPIView

urlpatterns = [
    path('portafolios/<int:pf_id>/evolucion/', EvolucionPortafolioAPIView.as_view(), name='evolucion-portafolio'),
    path('viz/', viz_evolucion, name='viz-evolucion'),
    path('portafolios/<int:pf_id>/operaciones/', RegistrarOperacionAPIView.as_view(), name='registro-operaciones'),
]
