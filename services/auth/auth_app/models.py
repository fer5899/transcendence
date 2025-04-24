from django.contrib.auth.models import AbstractUser
from django.db import models
import random
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
from django_otp.models import Device
from django.conf import settings


class CustomUser(AbstractUser):  
    
    email = models.EmailField(unique=True, error_messages={
        'unique': "Ya existe un usuario con este email"})
    profile_picture = models.CharField(max_length=255, null=True, blank=True, default="/media/default0.gif")
    username = models.CharField(("username"), max_length=20, unique=True, error_messages={
        'unique': "Ya existe un usuario con este nombre",
        'blank': "El nombre de usuario no puede estar vacío",
        'max_length': "El nombre de usuario no puede tener más de 20 caracteres",})

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
  

class EmailOTPDevice(Device):
    otp_token = models.CharField(max_length=6, blank=True, null=True)
    valid_until = models.DateTimeField(blank=True, null=True)
    email = models.EmailField(unique=True, blank=False, null=False)

    def generate_otp(self):
        self.otp_token = str(random.randint(100000, 999999))  # Código de 6 dígitos
        self.valid_until = now() + timedelta(minutes=1)  # Expira en 5 minutos
        self.email = self.user.email
        self.save()

    def send_otp(self):
        print("ENVIANDO al email: ", self.user.email, "el token: ", self.otp_token)

        send_mail(
            'OTP sent by PONG',
            f'Tu código de autenticación es: {self.otp_token} ',
            'davferjavvic@gmail.com',
            [self.user.email],
            fail_silently=False,
        )

class Friendship(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friendships_as_user1')
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friendships_as_user2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user1', 'user2'], name='unique_friendship')
        ]

    def __str__(self):
        return f"{self.user1} is friends with {self.user2}"

    @staticmethod
    def _ordered_users(user_a, user_b):
        return (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)

    @staticmethod
    def are_friends(user_id_a: int, user_id_b: int):
        try:
            user_a = CustomUser.objects.get(id=user_id_a)
            user_b = CustomUser.objects.get(id=user_id_b)
        except CustomUser.DoesNotExist:
            return False
        user1, user2 = Friendship._ordered_users(user_a, user_b)
        return Friendship.objects.filter(user1=user1, user2=user2).exists()

    @staticmethod
    def add_friend(user_id_a: int, user_id_b: int):
        if user_id_a == user_id_b:
            return False
        try:
            user_a = CustomUser.objects.get(id=user_id_a)
            user_b = CustomUser.objects.get(id=user_id_b)
        except CustomUser.DoesNotExist:
            return False
        user1, user2 = Friendship._ordered_users(user_a, user_b)
        if not Friendship.objects.filter(user1=user1, user2=user2).exists():
            Friendship.objects.create(user1=user1, user2=user2)
            return True
        return False

    @staticmethod
    def remove_friend(user_id_a: int, user_id_b: int):
        try:
            user_a = CustomUser.objects.get(id=user_id_a)
            user_b = CustomUser.objects.get(id=user_id_b)
        except CustomUser.DoesNotExist:
            return False
        user1, user2 = Friendship._ordered_users(user_a, user_b)
        friendship = Friendship.objects.filter(user1=user1, user2=user2).first()
        if friendship:
            friendship.delete()
            return True
        return False
