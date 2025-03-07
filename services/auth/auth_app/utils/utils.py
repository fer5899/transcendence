from django.utils.timezone import now
from .utilsToptDevice import CustomError  # Importa tu modelo personalizado
from auth_app.models import EmailOTPDevice, CustomUser

def verifyEmailTOPTDevice(email, otp_token):

	device = EmailOTPDevice.objects.get(email=email, otp_token=otp_token)# if not error throw exception .DoesNotExist
	
	if device.valid_until < now():
		raise CustomError("otp email expired")
	else:
		return True

def verifyUser(email, password):

	user = CustomUser.objects.filter(email=email).first()  # Buscar el usuario directamente

	if user is None:
		return "wrong email"
	elif not user.check_password(password):
		return "password wrong"
	elif user.is_active == False:
		return "user pending to validate"
	else:
		return "ok"

def verifyPendingUser(email, username, password):

	user = CustomUser.objects.filter(email=email, username= username).first()  # Buscar el usuario directamente

	if user is None:
		return "wrong user"
	elif not user.check_password(password):
		return "password wrong"
	elif user.is_active == False:
		return 'ok'
	else:
		return 'error'