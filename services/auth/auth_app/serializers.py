import re
from rest_framework import serializers
from .models import CustomUser
from rest_framework.exceptions import ValidationError

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password')

    def validate_username(self, value):
        if len(value) < 3:
            raise ValidationError("El nombre de usuario debe tener al menos 3 caracteres")
        
        if len(value) > 20:
            raise ValidationError("El nombre de usuario no puede tener más de 20 caracteres")

        forbidden_usernames = {"invitado", "la máquina"}
        if value.lower() in forbidden_usernames:
            raise ValidationError("El nombre de usuario no está permitido")

        if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚ]+$", value):
            raise ValidationError("El nombre de usuario solo puede contener letras y números")
        
        if CustomUser.objects.filter(username=value).exists():
            raise ValidationError("El nombre de usuario ya está en uso")

        return value

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.profile_picture = validated_data.get('profile_picture', instance.profile_picture)
        instance.save()
        return instance
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'profile_picture']