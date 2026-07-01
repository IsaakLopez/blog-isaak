from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Empleado

# Create your views here.
@login_required
def home(request):
    return render(request, 'empleados/home.html')

@login_required
def lista_empleados(request):
    empleados = Empleado.objects.all() # Trae todos los empleados de la DB
    return render(request, 'empleados/lista.html', {'empleados': empleados})