from django.urls import path
from . import views

urlpatterns = [
    path('', views.problem_list, name='problem_list'),
    path('add/', views.problem_add, name='problem_add'),
    path('edit/<int:pk>/', views.problem_edit, name='problem_edit'),
    path('delete/<int:pk>/', views.problem_delete, name='problem_delete'),
    path('export/', views.export_json, name='export_json'),
    path('import/', views.import_json, name='import_json'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  
]
