import re
from rest_framework import serializers
from .models import CustomUser  # Importa tu modelo personalizado
from rest_framework.exceptions import ValidationError

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'profile_picture']

    def validate_username(self, value):
        forbidden_usernames = {"invitado", "maquina"}
        if value.lower() in forbidden_usernames:
            raise ValidationError("Este nombre de usuario no está permitido.")

        if not re.match(r"^[a-zA-Z0-9_@.+-]+$", value):
            raise ValidationError("")

        return value

    def create(self, validated_data):

        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
          #  profile_picture=validated_data.get('profile_picture', None)
        )
        #user.is_active = False  # ❗ CREO QUE ESTA DUB¿PLICADO
        user.save()
        return user