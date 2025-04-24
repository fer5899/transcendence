import { getCookie } from './jwtValidator.js';

function getUserIdFromJWT(token) {
	const payloadBase64 = token.split('.')[1];
	const payloadJson = atob(payloadBase64);
	const payload = JSON.parse(payloadJson);
	return payload.user_id;
}

export function extractUserIdJwt() {
	const token = getCookie("accessToken");
	const user_id = getUserIdFromJWT(token);
	return user_id;
}

export function getCookieValue(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    if (match) return decodeURIComponent(match[2]);
    return null;
}