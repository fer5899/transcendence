-- /etc/nginx/lua/jwt_validation.lua

local jwt = require "resty.jwt"
local jwt_token = ngx.var.http_Authorization

if not jwt_token then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say("Missing token")
    return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end

local validators = require "resty.jwt-validators"
jwt_token = jwt_token:sub(8)

local jwt_secret_key = os.getenv("JWT_SECRET")

local jwt_obj = jwt:verify(jwt_secret_key, jwt_token, {
    exp = validators.is_not_expired(),
})

if not jwt_obj["verified"] then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say("Invalid token")
    return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end
