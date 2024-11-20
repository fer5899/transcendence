#FROM nginx:1.27

# RUN apt-get update && apt-get upgrade -y && apt-get install -y openssl && \
#     mkdir -p /etc/nginx/ssl && \
#     openssl req -x509 -nodes -out /etc/nginx/ssl/pmv.crt -keyout \
#     /etc/nginx/ssl/pmv.key -subj "/C=ES/ST=Malaga/L=Malaga/O=42/OU=42 Malaga/CN=fgomez-d.42.fr/UID=fgomez-d"

#COPY conf/nginx.conf /etc/nginx/nginx.conf

#CMD ["nginx", "-g", "daemon off;"]

# Usa una imagen base de Ubuntu 22.04
FROM ubuntu:22.04


# Establece el directorio de trabajo
WORKDIR /app

# Actualiza el sistema y añade paquetes necesarios
RUN apt-get update && apt-get install -y \
curl \
wget \
gnupg \
make \
unzip

# Agrega la clave publica oficial y el repositorio oficial de OpenResty
RUN wget -qO - https://openresty.org/package/pubkey.gpg | apt-key add - && \
echo "deb http://openresty.org/package/ubuntu jammy main" | tee /etc/apt/sources.list.d/openresty.list && \
apt-get update

# Instalar OpenResty
RUN apt-get install -y openresty

# Descargar e instalar LuaRocks
RUN wget https://luarocks.org/releases/luarocks-3.9.1.tar.gz && \
tar zxpf luarocks-3.9.1.tar.gz && \
cd luarocks-3.9.1 && \
./configure --with-lua=/usr/local/openresty/luajit/ --with-lua-include=/usr/local/openresty/luajit/include/luajit-2.1 && \
make && \
make install && \
cd .. && \
rm -rf luarocks-3.9.1 luarocks-3.9.1.tar.gz

# Instalar lua-resty-jwt a través de LuaRocks
RUN luarocks install lua-resty-jwt

RUN apt-get update && apt-get upgrade -y && apt-get install -y openssl && \
    mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -out /etc/nginx/ssl/pmv.crt -keyout \
    /etc/nginx/ssl/pmv.key -subj "/C=ES/ST=Malaga/L=Malaga/O=42/OU=42 Malaga/CN=fgomez-d.42.fr/UID=fgomez-d"

# Expone el puerto 8100
EXPOSE 8100

# Comando para iniciar OpenResty
CMD ["openresty", "-g", "daemon off;"]
