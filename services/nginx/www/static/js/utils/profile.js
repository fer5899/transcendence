import { handleJwtToken } from '../views/jwtValidator.js';
import { getCookieValue } from '../utils/jwtUtils.js';

export async function isFriend(id1, id2) {
        
    const url = "/api/settings/isFriendShip";
    
    try {
        await handleJwtToken();
        const response = await fetch(url, {method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id1, id2 })});    
        const data = await response.json();
            
        return data.message === "Are friends";

    } catch (error) {
        window.showPopup("Error comprobando la amistad");
    }
}
export async function addFriend(id1, id2) {
    
    var url = "/api/settings/friendShip/";
    var action = "add";

    try {
        await handleJwtToken();
        const response = await fetch(url + action, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id1, id2 })});
        const data = await response.json();
    } catch (error) {
        window.showPopup("Error añadiendo amigo");
    }
}

export async function removeFriend(id1, id2) {
    
    var url = "/api/settings/friendShip/";
    var action = "remove";

    try {
        await handleJwtToken();
        const response = await fetch(url + action, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id1, id2 })});
        const data = await response.json();
    } catch (error) {
       
        window.showPopup("Error eliminando amigo");
    }
}


export async function handleButtonFriend(otherUserId, currentUserId) {
    var btn = document.getElementById("add-friend-btn");
    
    const friends = await isFriend(otherUserId, currentUserId);
    
    if (friends) {
        btn.innerHTML = "Amigo";
        btn.style.backgroundColor = "var(--primary-color)";
        btn.style.color = "white";
    } else {
        btn.innerHTML = "Añadir Amigo";
        btn.style.backgroundColor = "#f5f5f5";
        btn.style.color = "#333";
    }
}

export function goToPlayerProfile(username) {

    window.openProfilePopup(username);
}

window.goToMyPlayerProfile = function goToMyPlayerProfile() {

    const username = getCookieValue("username");
    window.openProfilePopup(username);
}

export async function getDataUser(username) {
        
    const url = "/api/settings/dataUser";
    
    try {
        await handleJwtToken();
        const response = await fetch(url, {method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username })});
        const data = await response.json();
            
        if (!response.ok) {
            window.showPopup("Error obteniendo datos del usuario");
        }
        return data;
    } catch (error) {
        window.showPopup("Error obteniendo datos del usuario");
    }
}