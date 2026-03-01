from django.shortcuts import render
from .models import Empleado

# Create your views here.

def home(request):
    return render(request, 'empleados/home.html')

def lista_empleados(request):
    empleados = Empleado.objects.all() # Trae todos los empleados de la DB
    return render(request, 'empleados/lista.html', {'empleados': empleados})