from django.http import HttpResponse
from django.shortcuts import render
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from . serializers import RegisterSerializer, UserSerializer
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.http import JsonResponse
import jwt
import os
from .models import CustomUser, EmailOTPDevice, Friendship  # Importa tu modelo personalizado
from auth_app.utils.utilsToptDevice import genTOPTDevice, activateTOPTDevice, verifyTOPTDevice, CustomError
from auth_app.utils.utils import verifyEmailTOPTDevice, verifyUser, verifyPendingUser, removeOldImagen

from rest_framework import generics

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

@api_view(['GET'])
def logout_view(request):

	refresh_token = request.COOKIES.get('refreshToken')

	if not refresh_token:
		return Response({'error': 'Token de renovación no encontrado'}, status=400)

	try:
		token = RefreshToken(refresh_token)
		token.blacklist()

		return Response({'message': 'Sesión cerrada correctamente'}, status=status.HTTP_200_OK)
	except Exception as e:
		return Response({"error": str(e)}, status=400)

@api_view(['POST'])
def resend_otp_view(request):
	
	email = request.data.get("email")

	try:
		if not email:
			return Response({"error": "Nombre de usuario no recibido"}, status=status.HTTP_400_BAD_REQUEST)
		
		user = CustomUser.objects.get(email=email)

		if user is None:
			return Response({"error": "Usuario no encontrado en la base de datos"}, status=status.HTTP_400_BAD_REQUEST)
		
		device = EmailOTPDevice.objects.get(user=user)
		device.generate_otp()
		device.send_otp()

		return Response({ 'message': 'Mensaje OTP reenviado correctamente' }, status=status.HTTP_200_OK)
	
	except (CustomUser.DoesNotExist):
		return Response({"error": "Usuario no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
	except (EmailOTPDevice.DoesNotExist):
		return Response({"error": "Error mandando el mensaje OTP"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def register_view(request):

	serializer = RegisterSerializer(data=request.data)

	if serializer.is_valid():
		user = serializer.save()
		user.is_active = False  # Desactivamos la cuenta hasta que confirme el OTP
		user.save()
		device, _ = EmailOTPDevice.objects.get_or_create(user=user)
		device.generate_otp()
		device.send_otp()
		return Response({ "message" : "Usuario registrado. Pendiente de confirmación" }, status=status.HTTP_201_CREATED)
	
	elif verifyPendingUser(request.data.get("email"), request.data.get("username"), request.data.get("password")) == 'ok':
		user = CustomUser.objects.get(email=request.data.get("email"))
		device, _ = EmailOTPDevice.objects.get_or_create(user=user)
		device.generate_otp()
		device.send_otp()
		return Response({ "message" : "Usuario registrado correctamente" }, status=status.HTTP_201_CREATED)
	
	elif verifyPendingUser(request.data.get("email"), request.data.get("username"), request.data.get("password")) == 'password wrong' and CustomUser.objects.get(email=request.data.get("email")).is_active == False:
		return Response({ "error": "Contraseña incorrecta" }, status=status.HTTP_400_BAD_REQUEST)
	
	else:
		return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

@api_view(['POST'])
def verify_email_otp_register_view(request):

	otp_token = request.data.get('otp_token')
	email = request.data.get('email')

	try:
		if not email or not otp_token:
			return Response({"error": "Email o OTP no recibidos"}, status=status.HTTP_400_BAD_REQUEST)
		
		user = CustomUser.objects.get(email=email)

		if user is None:
			return Response({"error": "Usuario no encontrado en la base de datos"}, status=status.HTTP_400_BAD_REQUEST)
		
		if verifyEmailTOPTDevice(email, otp_token):
			user.is_active = True
			user.save()
			return Response({ 'message': 'Email OTP verificado con éxito',}, status=status.HTTP_200_OK)
	
	except (CustomUser.DoesNotExist):
		return Response({"error": "Usuario no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
	except (EmailOTPDevice.DoesNotExist):
		return Response({"error": "Error mandando el mensaje OTP"}, status=status.HTTP_400_BAD_REQUEST)
	except CustomError as e:
		return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login_api_view(request):

	email = request.data.get('email')
	password = request.data.get('password')

	if verifyUser(email, password) != 'ok':
		return Response({"error": verifyUser(email, password)}, status=status.HTTP_400_BAD_REQUEST)
		
	else:
		user = CustomUser.objects.get(email=email)

	device = EmailOTPDevice.objects.get(user=user)
	device.generate_otp()
	device.send_otp()

	return Response({
		'username': user.username,
		'userId': user.id,
		'message': 'Introduce el mensaje OTP enviado al email.'
	}, status=status.HTTP_200_OK)

@api_view(['POST'])
def verify_email_otp_login_view(request):

	email = request.data.get('email')
	otp_token = request.data.get('otp_token')

	try:
		user = CustomUser.objects.get(email=email, is_active = True)
		
		if verifyEmailTOPTDevice(email, otp_token):

			refresh = RefreshToken.for_user(user)
			refresh['username'] = user.username

			return Response({
				'message': 'OTP verificado con éxito',
				'refresh': str(refresh),
				'access': str(refresh.access_token)
			}, status=status.HTTP_200_OK)

	except (CustomUser.DoesNotExist):
		return Response({"error": "Usuario no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
	except (EmailOTPDevice.DoesNotExist):
		return Response({"error": "El mensaje OTP es incorrecto"}, status=status.HTTP_400_BAD_REQUEST)
	except CustomError as e:
		return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def validate_token_view(request):

    token = request.COOKIES.get('accessToken')

    if not token:
        return Response({"error": "accessToken is required in cookies"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return Response(status=status.HTTP_200_OK)

    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=status.HTTP_401_UNAUTHORIZED)

    except jwt.InvalidTokenError:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
@api_view(['POST'])
def refresh_token_view(request):

	refresh_token = request.data.get('refresh_token')

	if not refresh_token:
		return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)

	try:
		token = RefreshToken(refresh_token)
		new_access_token = str(token.access_token)

		return Response({
            'access_token': new_access_token,
        }, status=status.HTTP_200_OK)
    
	except TokenError as e:
		return Response({'error': 'Invalid or expired refresh token', 'details': str(e)}, status=status.HTTP_401_UNAUTHORIZED)
	
@api_view(['POST'])
def updateName_view(request):
	
	email = request.data.get("email")
	newUsername = request.data.get("newUsername")

	if not email or not newUsername:
		return Response({"error": "Email o nuevo usuario no proporcionados"}, status=status.HTTP_400_BAD_REQUEST)
	
	try:
		user = CustomUser.objects.get(email=email)
	
		serializer = RegisterSerializer(user, data={"username": newUsername}, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response({"message": "Nombre de usuario actualizado correctamente", 'username': user.username}, status=status.HTTP_200_OK)
		else:
			return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
	except CustomUser.DoesNotExist:
		return Response({"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

	
@api_view(["POST"])
def updatePassword_view(request):
    email = request.data.get("email")
    old_password = request.data.get("oldPassword")
    new_password = request.data.get("newPassword")

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if not user.check_password(old_password):
        return Response({"error": "La contraseña actual es incorrecta."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()

    return Response({"message": "Contraseña actualizada correctamente."}, status=status.HTTP_200_OK)

@api_view(["POST"])
def updatePictureUrl_view(request):

	email = request.data.get("email")
	src = request.data.get("src")

	try:
		user = CustomUser.objects.get(email=email)

		removeOldImagen(user)

		user.profile_picture = src
		user.save()
	except CustomUser.DoesNotExist:
		return Response({"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

	return Response({"message": "Avatar cambiado correctamente"}, status=status.HTTP_200_OK)

@api_view(['GET'])
def playersList_view(request):
    players = CustomUser.objects.values('id', 'username', 'profile_picture')
    return Response(players)

@api_view(['POST'])
def dataUser_view(request):
	username = request.data.get("username")
	email = request.data.get("email")

	try:
		if not email and username:
			user = CustomUser.objects.get(username=username)
		elif email and not username:
			user = CustomUser.objects.get(email=email)
		else:
			return Response({"error": "Email o nombre de usuario no encontrados"}, status=status.HTTP_400_BAD_REQUEST)

	except CustomUser.DoesNotExist:
		return Response({"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)
	except CustomError as e:
		return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)
	else:
		return Response({"message": "Datos de usuario extraídos correctamente", "id": user.id, "username": user.username, "picture_url": user.profile_picture}, status=status.HTTP_200_OK)

@api_view(['POST'])
def isFriendShip_view(request):
	id1 = int(request.data.get("id1"))
	id2 = int(request.data.get("id2"))
				  
	if not id1 or not id2:
		return Response({"error": "missing a id"}, status=status.HTTP_400_BAD_REQUEST)
	
	if Friendship.are_friends(id1, id2):
		return Response({"message": "Are friends"}, status=status.HTTP_200_OK)
	else:
		return Response({"message": "Are not friends"}, status=status.HTTP_200_OK)

@api_view(['POST'])
def friendShip_view(request, action):
	id1 = request.data.get('id1')
	id2 = request.data.get('id2')

	if not id1 or not id2:
		return Response({"error": "Missing id1 or id2"}, status=400)

	if action == 'add':
		# Añadir amigos
		if not Friendship.are_friends(id1, id2):
			Friendship.add_friend(id1, id2)
			return Response({"message": "Son amigos"}, status=200)
		else:
			return Response({"error": "They are already friends or the usernames are the same"}, status=200)
    
	elif action == 'remove':
		# Eliminar amigos
		if Friendship.remove_friend(id1, id2):
			return Response({"message": "Ya no son amigos"}, status=200)
		else:
			return Response({"error": "They are not friends or no valid relationship exists"}, status=200)
	
	return Response({"error": "Invalid action"}, status=400)

@api_view(['POST'])
def upload_profile_pic_view(request):

	image = request.FILES.get('profile_pic')
	username = request.POST.get('username')

	if not image or not username:
		return Response({"error": "image or username"}, status=400)

	try:
		user = CustomUser.objects.get(username=username)

		file_path = f'{image.name}'
		if default_storage.exists(file_path):
			return Response({"error": "La imagen ya existe \n cambiale el nombre."}, status=400)
		
		removeOldImagen(user)

		file_path = default_storage.save(f'{image.name}', image)
		user.profile_picture = "/media/" + file_path
		user.save()

	except CustomUser.DoesNotExist:
		return Response({"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)
	
	return Response({"message": "imagen guardada correctamente", "file_path": {"/media/" + file_path}}, status=200)

class UserDetail(generics.RetrieveAPIView):
	queryset = CustomUser.objects.all()
	serializer_class = UserSerializer
	lookup_field = 'username'

class UserDetailById(generics.RetrieveAPIView):
	queryset = CustomUser.objects.all()
	serializer_class = UserSerializer
