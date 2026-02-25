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
    path('upload-image/', views.upload_image, name='upload_image'),
    path('staff/resource-management/', views.resource_management, name='resource_management'),
    path('staff/isolated-images/delete/', views.isolated_images_delete, name='isolated_images_delete'),
    path('clear-uploaded-images/', views.clear_uploaded_images, name='clear_uploaded_images'),
    path('view/<uuid:token>/', views.view_detail, name='view_detail'),
    path('site-config/edit/', views.site_config_edit, name='site_config_edit'),
    # CV Base URLs
    path('cv-base/', views.cv_base_list, name='cv_base_list'),
    path('cv-base/add/', views.cv_base_add, name='cv_base_add'),
    path('cv-base/edit/<int:pk>/', views.cv_base_edit, name='cv_base_edit'),
    path('cv-base/delete/<int:pk>/', views.cv_base_delete, name='cv_base_delete'),
    path('cv-base/detail/<int:pk>/', views.cv_base_detail, name='cv_base_detail'),
    path('cv-base/calendar-days/', views.cv_base_calendar_days, name='cv_base_calendar_days'),
    path('cv-base/create-by-date/', views.cv_base_create_by_date, name='cv_base_create_by_date'),
]
