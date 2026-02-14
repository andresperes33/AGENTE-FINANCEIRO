from django.urls import path
from . import views

app_name = 'webhooks'

urlpatterns = [
    path('kirvano/', views.kirvano_webhook, name='kirvano'),
    path('evolution/', views.evolution_webhook, name='evolution'),

]
