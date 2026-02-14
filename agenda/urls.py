from django.urls import path
from . import views

app_name = 'agenda'

urlpatterns = [
    path('', views.appointment_list, name='list'),
    path('novo/', views.appointment_create, name='create'),
    path('editar/<int:pk>/', views.appointment_edit, name='edit'),
    path('deletar/<int:pk>/', views.appointment_delete, name='delete'),
]
