from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Empleado


class EmpleadoCreateForm(forms.Form):
    username = forms.CharField(max_length=150, label='Usuario')
    password1 = forms.CharField(widget=forms.PasswordInput, label='Contraseña')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirmar contraseña')
    nombre = forms.CharField(max_length=100)
    apellido = forms.CharField(max_length=100)
    dni = forms.CharField(max_length=20, required=False, label='DNI')
    cargo = forms.ChoiceField(choices=Empleado.CARGO_CHOICES)
    telefono = forms.CharField(max_length=20, required=False)
    correo = forms.EmailField(required=False)
    sucursal = forms.CharField(max_length=100, required=False)
    activo = forms.BooleanField(required=False, initial=True, label='Estado Activo')

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Ya existe un usuario con ese nombre.')
        return username

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if dni and Empleado.objects.filter(dni=dni).exists():
            raise ValidationError('Ya existe un empleado con ese DNI.')
        return dni

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        elif password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                self.add_error('password1', exc)
        return cleaned

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password1'],
            is_staff=False,
            is_active=self.cleaned_data['activo'],
        )
        return Empleado.objects.create(
            user=user,
            nombre=self.cleaned_data['nombre'],
            apellido=self.cleaned_data['apellido'],
            dni=self.cleaned_data['dni'] or None,
            cargo=self.cleaned_data['cargo'],
            telefono=self.cleaned_data['telefono'],
            correo=self.cleaned_data['correo'],
            sucursal=self.cleaned_data['sucursal'],
            activo=self.cleaned_data['activo'],
        )


class EmpleadoEditForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ['nombre', 'apellido', 'dni', 'cargo', 'telefono', 'correo', 'sucursal', 'activo']


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Nueva contraseña')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirmar contraseña')

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        elif password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                self.add_error('password1', exc)
        return cleaned
