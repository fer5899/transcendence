function getCookie(name) {
    return document.cookie
        .split("; ")
        .find(row => row.startsWith(name + "="))
        ?.split("=")[1];
}

async function getNewAccessToken(refreshToken) {
    try {
        const response = await fetch('/api/usr/refreshToken', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                refresh_token: refreshToken,
            }),
        });

        if (response.ok) {
            const data = await response.json();
            return data;
        } else {
            throw new Error(`getNewAccessToken: error new access_token, response: ${response.status}`);}

    } catch (error) {
        throw new Error(`getNewAccessToken: Fetch error details: - ${error.message}`);
    }
}  

async function renovateToken() {
    const refreshToken = getCookie("refreshToken");

    if (refreshToken) {
        const data = await getNewAccessToken(refreshToken);

        if (data && data.access_token) {

            document.cookie = `accessToken=${data.access_token}; path=/; secure; SameSite=Lax`;

        } else {
            throw new Error("renovateToken: cannot obtein new access token available");}
    } else {
        alert("No hay un refreshToken disponible. Redirigiendo al inicio de sesión.");
        throw new Error("renovateToken: refreshToken not available");
    }
}

async function validateToken() {
    try {
        const response = await fetch('/api/usr/validateToken', {
            method: 'GET', 
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (response.ok) {
            return "Ok"; 
        } else if (response.status === 400) {
            return "Token not available"; 
        } else {
            return "Token has expired or invalid"; 
        }
        
    } catch (error) {
        return false;
    }
}
export async function handleJwtToken() {
    const response = await validateToken();
    
    if (response === "Token has expired or invalid") {
        await renovateToken();
    } else if (response === "Token not available") {
        throw new Error("handleJwtToken: token not available");
    }
}