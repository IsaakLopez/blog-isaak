"""
URL configuration for miwebsite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from empleados import views as empleados_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Rutas de Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('', empleados_views.home, name='home'), # Se ve en: http://127.0.0.1:8000/
    path('empleados/', empleados_views.lista_empleados, name='lista'), # Se ve en: http://127.0.0.1:8000/empleados/
    path('empleados/nuevo/', empleados_views.empleado_crear, name='empleado_crear'),
    path('empleados/<int:pk>/editar/', empleados_views.empleado_editar, name='empleado_editar'),
    path('empleados/<int:pk>/resetear-password/', empleados_views.empleado_resetear_password, name='empleado_resetear_password'),

    path('financiera/', include('financiera.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
