import { handleJwtToken } from '../views/jwtValidator.js';

function getFirstErrorMessage(response) {
    const errorMessages = Object.values(response);
    if (errorMessages.length > 0) {
        const firstError = errorMessages[0];
        if (Array.isArray(firstError)) {
            return firstError[0];
        } else {
            return firstError;
        }
    }
    return "Error";
}

export async function updateUsername(email, newUsername) {
    const url = "/api/settings/updateName";
    
    try {
        await handleJwtToken();
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email, newUsername })
        });

        const data = await response.json();
        if (response.ok) {
            document.cookie = `username=${encodeURIComponent(newUsername)}; path=/;`;
            window.showPopup("Nombre de usuario actualizado correctamente");
            return true;
        } else {
            window.showPopup(getFirstErrorMessage(data.error));
            return false;
        }
    } catch (error) {
        window.showPopup("Error al actualizar el nombre de usuario");
        return false;
    }
}

export async function updatePassword(email, oldPass, newPass1, newPass2) {
    
    if(!oldPass || !newPass1 || !newPass2) {
        window.showPopup("Todos los campos son necesarios");
        return;
    }
    
    if (newPass1 !== newPass2) {
        window.showPopup("Las nueva contraseña no coincide con la confirmación");
        return;
    }

    const url = "/api/settings/updatePassword";
    
    try {
        await handleJwtToken();

        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email,
                oldPassword: oldPass,
                newPassword: newPass1
            })
        });

        const data = await response.json();
        
        if (response.ok) {
            window.showPopup("Contraseña cambiada correctamente");
            window.closeSettingsPopup();
        } else {
            window.showPopup("Error al cambiar la contraseña");
        }
    } catch (error) {
        window.showPopup("Error al cambiar la contraseña");
    }
}

export async function showPicture(email) {

    const url = "/api/settings/dataUser";
    
    try {

        await handleJwtToken();
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email })
        });

        const data = await response.json();
        
        if (response.ok) {
            document.getElementById("current-profile-pic").src = data.picture_url;
        } else {
            window.showPopup("Error al obtener la imagen de perfil");
        }
    } catch (error) {
        window.showPopup("Error al obtener la imagen de perfil");
    }
}

export async function updatePicture(email, src) {

    const url = "/api/settings/updatePictureUrl";

    try {
        await handleJwtToken();

        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email, src })
        });

        const data = await response.json();
        
        if (!response.ok) {
            window.showPopup("Error al actualizar la imagen de perfil");
            return;
        }
        window.showPopup("Imagen de perfil actualizada correctamente");
        window.closeSettingsPopup();

    } catch (error) {
        window.showPopup("Error al actualizar la imagen de perfil");
    }

}

export async function uploadImage(formData) {

    const url = "/api/settings/upload-profile-pic";

    try {
        await handleJwtToken();

        const response = await fetch(url, {
            method: "POST",
            body: formData,
        });

        const data = await response.json();
        
        if (!response.ok) {
            window.showPopup("Error al actualizar la imagen de perfil");
            return;
        }
        window.showPopup("Imagen de perfil actualizada correctamente");
        window.closeSettingsPopup();

    } catch (error) {
        window.showPopup("Error al actualizar la imagen de perfil");
    }

}