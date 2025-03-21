from django.contrib import admin
from .models import CustomUser

# Registra el modelo CustomUser en el admin
admin.site.register(CustomUser)