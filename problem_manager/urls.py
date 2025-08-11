from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from problems import views

urlpatterns = [
    path('staff/users/add/', views.user_add, name='user_add'),
    path('staff/users/', views.user_list, name='user_list'),
    path('staff/users/<int:pk>/toggle/', views.user_toggle_active, name='user_toggle_active'),
    path('staff/users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('admin/', admin.site.urls),
    path('', include('problems.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
