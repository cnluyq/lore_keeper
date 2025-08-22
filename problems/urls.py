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
    path('sensitive-words/', views.sensitive_word_list, name='sensitive_word_list'),
    path('sensitive-words/add/', views.sensitive_word_add, name='sensitive_word_add'),
    path('sensitive-words/edit/<int:pk>/', views.sensitive_word_edit, name='sensitive_word_edit'),
    path('sensitive-words/toggle/<int:pk>/', views.sensitive_word_toggle, name='sensitive_word_toggle'),
    path('sensitive-words/delete/<int:pk>/', views.sensitive_word_delete, name='sensitive_word_delete'),
]
