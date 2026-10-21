// Importar las librerías de Firebase
importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js');

// Variable para almacenar el token de registro
let registrationToken = null;

// Función para obtener la configuración de Firebase desde Odoo
async function getFirebaseConfig() {
    try {
        const response = await fetch('/web/dataset/call_kw/res.config.settings/get_firebase_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: 'res.config.settings',
                method: 'get_firebase_config',
                args: [],
                kwargs: {},
            }),
        });
        
        if (!response.ok) {
            throw new Error(`Error en la solicitud HTTP: ${response.status}`);
        }

        const data = await response.json();

        if (!data.firebase_config || !data.vapid_public_key) {
            throw new Error('La configuración de Firebase o la clave VAPID pública no están disponibles');
        }

        return data;
    } catch (error) {
        console.error('Error al obtener la configuración de Firebase:', error);
        // Manejar el error (mostrar un mensaje al usuario, registrarlo, etc.)
        return null; // o algún valor por defecto
    }
}

// Inicializar Firebase y obtener el token de registro
getFirebaseConfig()
    .then(data => {
        if (data) { // Verificar si se obtuvo la configuración correctamente
            // Inicializar Firebase con la configuración obtenida desde Odoo
            firebase.initializeApp(data.firebase_config);
            const messaging = firebase.messaging();

            // Obtener el token de registro del dispositivo
            return messaging.getToken();
        } else {
            // Manejar el caso en que no se pudo obtener la configuración
            console.error('No se pudo inicializar Firebase debido a un error en la configuración.');
            return null;
        }
    })
    .then(token => {
        if (token) { // Verificar si se obtuvo el token correctamente
            registrationToken = token;
            console.log('Token de registro:', registrationToken);

            // Enviar el token al backend de Odoo
            return fetch('/unicubevn_pwa/save_registration_token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    registration_token: token,
                }),
            });
        } else {
            // Manejar el caso en que no se pudo obtener el token
            console.error('No se pudo obtener el token de registro.');
            return null;
        }
    })
    .then(response => {
        if (response && !response.ok) { // Verificar si la respuesta es válida y no hay errores
            throw new Error('Error al guardar el token de registro en Odoo');
        }
        console.log('Token de registro guardado en Odoo');
    })
    .catch(err => {
        console.error('Error al obtener o guardar el token de registro:', err);
        // Mostrar una notificación de error al usuario
        self.registration.showNotification('Error', {
            body: 'No se pudo configurar las notificaciones push.',
        });
    });

// Manejar mensajes en segundo plano (movido dentro del bloque de inicialización de Firebase)

self.addEventListener('notificationclick', function(event) {
    event.notification.close(); // Cerrar la notificación al hacer clic
    
    // Abrir la URL asociada a la notificación en una nueva ventana o pestaña
    event.waitUntil(clients.openWindow(event.notification.data.url));
});

// Manejar la navegación y mostrar una página offline si es necesario
self.addEventListener("fetch", (event) => {
    if (
        (event.request.mode === "navigate" && event.request.destination === "document") ||
        // request.mode = navigate isn't supported in all browsers => check for http header accept:text/html
        event.request.headers.get("accept").includes("text/html")
    ) {
        event.respondWith(navigateOrDisplayOfflinePage(event.request));
    }
});
