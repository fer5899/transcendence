from django.contrib.auth.models import AbstractUser
from django.db import models
import random
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
from django_otp.models import Device


class CustomUser(AbstractUser):  
    
    email = models.EmailField(unique=True)

    profile_picture = models.CharField(max_length=255, null=True, blank=True, default="/media/default.png")

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
            'OTP sended by PONG',
            f'Tu código de autenticación es: {self.otp_token} ',
            'victorcerecedagonzalez@gmail.com',
            [self.user.email],
            fail_silently=False,
        )