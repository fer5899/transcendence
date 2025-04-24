# Usa una imagen base de Ubuntu 22.04
FROM ubuntu:22.04

# Establece el directorio de trabajo
WORKDIR /app

# Actualiza el sistema y añade paquetes necesarios
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    make 

# Agrega la clave publica oficial y el repositorio oficial de OpenResty
RUN wget -qO - https://openresty.org/package/pubkey.gpg | apt-key add - && \
    echo "deb http://openresty.org/package/ubuntu jammy main" | tee /etc/apt/sources.list.d/openresty.list && \
    apt-get update

# Instalar OpenResty
RUN apt-get install -y openresty

#certificate
RUN apt-get update && apt-get upgrade -y && apt-get install -y openssl && \
    mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -out /etc/nginx/ssl/pmv.crt -keyout \
    /etc/nginx/ssl/pmv.key -subj "/C=ES/ST=Malaga/L=Malaga/O=42/OU=42 Malaga/CN=fgomez-d.42.fr/UID=fgomez-d"

# About debugging
RUN mkdir -p /var/log/nginx && chown root:root /var/log/nginx && chmod 755 /var/log/nginx && \
    touch /var/log/nginx/access_debug.log && chmod 644 /var/log/nginx/access_debug.log && chown root:root /var/log/nginx/access_debug.log && \
    touch /var/log/nginx/error.log && chmod 644 /var/log/nginx/error.log && chown root:root /var/log/nginx/error.log

COPY ./www/static/media/*  /media/
COPY ./www/favicon.ico /usr/share/nginx/html/

# Expone el puerto 443/80
EXPOSE 443
EXPOSE 80

# Comando para iniciar OpenResty
CMD ["openresty", "-g", "daemon off;"]
