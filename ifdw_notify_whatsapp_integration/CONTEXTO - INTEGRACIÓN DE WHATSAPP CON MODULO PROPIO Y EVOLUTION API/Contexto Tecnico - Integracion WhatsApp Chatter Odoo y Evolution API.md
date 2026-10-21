# Memoria Técnica de Arquitectura: Integración de Notificaciones de WhatsApp en Chatter de Odoo 18 Community

**Autor:** Sett (Arquitecto de Sistemas e Infraestructura - Infinity Draw)  
**Proyecto:** Plavifom - Odoo 18 Community On-Premise  
**Fecha:** Octubre 2026  
**Ubicación:** `500-PROYECTOS/26-05-010 - Plavifom - Odoo/01-BASE CONOCIMIENTO CLIENTE PARA IA/CONTEXTO - INTEGRACIÓN DE WHATSAPP CON MODULO PROPIO Y EVOLUTION API/`

---

## 1. Resumen Ejecutivo y Objetivo

El objetivo de esta iniciativa es dotar a **Odoo 18 Community** de la capacidad nativa de enviar notificaciones por **WhatsApp** a los seguidores de cualquier documento (Tareas de Proyecto, Eventos de Calendario, Pedidos de Venta, Facturas de Clientes, etc.), replicando con total fidelidad el comportamiento del **Chatter (`mail.thread`)** cuando se envían correos electrónicos.

### Requisitos y Condiciones de Partida:
1. **Evitar la API Oficial de Meta (WhatsApp Cloud API):** Eliminar la dependencia de plantillas preaprobadas de pago (*templates*) y la limitación de la ventana de 24 horas para conversaciones comerciales o de utilidad.
2. **Evitar Plataformas Terceras (Make, Zapier, n8n):** No introducir costes adicionales recurrentes de suscripción, no delegar datos confidenciales a infraestructuras externas y evitar la sobrecarga de mantenimiento de flujos complejos.
3. **Coste de Licencias 0 €:** Priorizar soluciones 100% de código abierto (*Open Source*) y desarrollo propio frente a módulos comerciales de pago (que rondan los 150 € - 180 € en tiendas de terceros).
4. **Compatibilidad Multiversión:** La arquitectura diseñada debe ser desacoplada y modular, garantizando su funcionamiento en Odoo 17, Odoo 18 y el futuro Odoo 19.

---

## 2. Anatomía del Problema en Odoo Community y WhatsApp

### 2.1. El Candado de Meta (WhatsApp Business Cloud API)
La API oficial de Meta impone una restricción draconiana: si un cliente o usuario no ha enviado un mensaje al número corporativo en las últimas 24 horas, la empresa **solo puede enviarle mensajes utilizando plantillas preaprobadas por Meta**, pagando una tarifa por mensaje enviado. En un ERP como Odoo, donde una tarea se actualiza días después o una factura se valida semanas más tarde, la API oficial resulta inviable operativa y económicamente para notificaciones internas de seguimiento.

### 2.2. Cómo funciona el Chatter en Odoo (`mail.thread`)
En Odoo, el motor de comunicación se basa en:
* `mail.thread`: Modelo abstracto del que heredan casi todos los modelos del ERP (`project.task`, `sale.order`, `account.move`).
* `mail.followers`: Registra qué contactos (`res.partner`) siguen un registro específico.
* `mail.message.subtype`: Define los eventos suscritos (ej. "Tarea creada", "Etapa cambiada", "Factura validada").
* Flujo de despacho: Al publicar una nota o mensaje, Odoo llama a `_notify_thread() -> _notify_by_email()`, generando correos SMTP para los seguidores que tengan los checks activados.

---

## 3. Comparativa de Soluciones Evaluadas

| Criterio | Solución 1: Módulo Comercial de Terceros | Solución 2: Conector Monolítico Selenium (Odoo) | Solución 3: Evolution API + Módulo Propio (Elegida) |
|---|---|---|---|
| **Coste Licencia** | ~155 $ - 180 € (pago por versión de Odoo) | 0 € (código abierto) | **0 € (desarrollo interno + Open Source)** |
| **Consumo RAM Host** | ~100 MB (depende de pasarela externa) | ~400 MB - 600 MB (Chromium Headless) | **~80 MB - 120 MB (Node.js + Baileys)** |
| **Estabilidad** | Media (dependencia de actualizaciones del vendor) | Baja (Chromium headless tiende a colgarse) | **Alta (WebSockets cifrados directos sin GUI)** |
| **Compatibilidad** | A menudo rota entre Odoo 17, 18 y 19 | Frágil ante cambios de DOM de WhatsApp | **Total (desacoplado vía REST API)** |
| **Control del Código** | Código cerrado o difícil de auditar | Monolítico dentro de Odoo | **100% auditable y mantenible por Sett** |

---

## 4. Arquitectura Seleccionada: Evolution API + Módulo Propio

La arquitectura ganadora se compone de dos piezas perfectamente desacopladas:

```
[ Usuario / Odoo 18 Core ]
          │ (Publica nota o cambio de etapa en Tarea/Pedido)
          ▼
   [ mail.thread ]
          │ (Evalúa mail.followers suscritos)
          ▼
[ Módulo Propio: whatsapp_chatter_notify ]
          │ 1. Limpia HTML a formato WhatsApp (*negrita*, _cursiva_)
          │ 2. Normaliza teléfono con librería 'phonenumbers'
          │ 3. Lanza petición HTTP POST local
          ▼
   [ Evolution API ] (Instancia local Docker / Podman :8080)
          │ (Protocolo Baileys / WebSockets cifrados)
          ▼
   [ Red WhatsApp (Meta) ] ──▶ [ Móvil del Seguidor / Empleado / Cliente ]
```

### 4.1. Características de Evolution API
* **Motor Baileys:** No requiere navegadores Chromium ni interfaces gráficas. Se conecta directamente a los servidores de WhatsApp mediante sockets.
* **Consumo Mínimo:** Apenas 80 - 120 MB de memoria RAM en el servidor VPS.
* **Emparejamiento QR Multi-Device:** Se escanea el código QR una sola vez desde la aplicación de WhatsApp de un móvil físico o virtual. La sesión queda guardada de forma persistente.
* **Regla de Persistencia:** El teléfono principal únicamente requiere conectarse a internet al menos una vez cada 14 días para evitar que Meta revoque la sesión por inactividad.

---

## 5. Especificación del Módulo Propio (`whatsapp_chatter_notify`)

El módulo se ubicará en la ruta de addons locales del VPS:  
`/opt/odoo18/addons-extra/whatsapp_chatter_notify/`

### 5.1. Estructura de Ficheros
```text
whatsapp_chatter_notify/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── res_config_settings.py   # Parámetros de conexión con Evolution API
│   ├── res_partner.py           # Checkbox de recepción y teléfono verificado
│   └── mail_thread.py           # Intercepción del flujo de notificación
└── views/
    ├── res_config_settings_views.xml
    └── res_partner_views.xml
```

### 5.2. Lógica Técnica de los Modelos

#### A. Configuración General (`models/res_config_settings.py`)
Almacena en `ir.config_parameter`:
* `whatsapp.evolution_endpoint`: URL local (ej. `http://127.0.0.1:8080`).
* `whatsapp.evolution_apikey`: Token de seguridad para autenticar contra la API.
* `whatsapp.evolution_instance`: Identificador de la sesión de WhatsApp activa.

#### B. Ficha de Contacto (`models/res_partner.py`)
Añade dos campos esenciales:
* `notify_whatsapp`: Campo booleano ("Recibir notificaciones por WhatsApp").
* Normalización automática del número móvil mediante la librería Python `phonenumbers` para asegurar el formato internacional E.164 (ej. `+34600112233`).

#### C. Intercepción del Chatter (`models/mail_thread.py`)
Extiende el método estándar de Odoo:
1. Detecta los destinatarios que reciben el mensaje según los subtipos marcados en el Chatter.
2. Filtra aquellos contactos que tengan activo `notify_whatsapp = True` y un móvil válido.
3. Convierte el cuerpo HTML de Odoo a texto enriquecido para WhatsApp:
   * `<p>`, `<br>` ➔ saltos de línea `\n`.
   * `<b>`, `<strong>` ➔ `*texto*`.
   * `<i>`, `<em>` ➔ `_texto_`.
   * Enlaces `<a>` ➔ `Texto (URL)`.
4. Añade al pie del mensaje el enlace directo al registro en Odoo:  
   `Ver registro: https://gestion.plavifom.es/web#id=123&model=project.task`
5. Realiza un `requests.post()` asíncrono o protegido con bloque `try/except` para garantizar que, si el servicio de WhatsApp sufriera una caída puntual, la operación dentro de Odoo nunca quede bloqueada.

---

## 6. Estimación de Tiempos y Fases de Despliegue

| Fase | Tarea Técnica | Duración Estimada |
|---|---|---|
| **Fase 1: Infraestructura** | Despliegue de Evolution API en VPS (Docker/Podman), securización de red en localhost y escaneo de código QR inicial. | 45 min - 1 h |
| **Fase 2: Esqueleto del Módulo** | Creación del módulo en `addons-extra`, vistas de configuración y test de conexión con la pasarela. | 1,5 h - 2 h |
| **Fase 3: Lógica de Chatter** | Herencia de `mail.thread`, limpiador de HTML a formato WhatsApp y despacho HTTP. | 2 h - 2,5 h |
| **Fase 4: Testing y Afinado** | Pruebas de campo con Tareas, Pedidos y Facturas. Validación de control de errores. | 1,5 h - 2 h |
| **TOTAL** | **Desarrollo completo, probado y puesto en producción** | **6 - 8 Horas** |

---

## 7. Blindaje de Seguridad y Buenas Prácticas

1. **Aislamiento de Red:** El puerto de Evolution API (`8080`) nunca se expone a internet. Permanece cerrado en UFW y accesible exclusivamente desde `127.0.0.1` (localhost).
2. **Uso Responsable:** Este sistema está diseñado para notificaciones operativas a usuarios y clientes que esperan dicha comunicación. No debe emplearse para campañas masivas de prospección en frío para evitar denuncias de spam que provoquen el bloqueo del número por parte de Meta.
3. **Persistencia de Datos:** El almacenamiento de la sesión de Evolution API se monta sobre volumen persistente en el disco del VPS, sobreviviendo a reinicios automáticos y mantenimientos del host.
