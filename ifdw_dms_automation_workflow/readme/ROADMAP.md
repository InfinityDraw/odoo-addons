# Hoja de Ruta y Evolución Futura (`ROADMAP`)

El módulo **`ifdw_dms_automation_workflow`** cubre actualmente el ciclo completo de clonación de plantillas, auto-clasificación desde el Chatter, modelos satélite y flujos encadenados en espejo (`A ➔ B ➔ C`). De cara a futuras versiones se contemplan las siguientes evoluciones:

---

## 🚀 Próximas Mejoras Planificadas

* **Extensión Dinámica de Smart Buttons a Cualquier Modelo de Odoo:**
  * Inyección automática del botón inteligente `Documentos` y del mixin documental en modelos adicionales seleccionados desde la interfaz sin necesidad de heredarlos previamente en vistas XML.
* **Reglas de Retención y Archivado Programado (`ir.cron`):**
  * Tareas programadas configurables por regla para archivar o purgar automáticamente adjuntos temporales de presupuestos u oportunidades perdidas tras *N* meses de inactividad, optimizando el espacio en el *Filestore*.
* **Compresión y Optimización Automática de Imágenes de Obra:**
  * Opción configurable por regla para redimensionar o convertir automáticamente fotografías pesadas (`HEIC`/`RAW`/`PNG`) a formatos ligeros (`WEBP`/`JPEG` optimizado) al entrar en el DMS sin perder legibilidad técnica.
* **Integración Directa con Canales de Mensajería Externa (WhatsApp / Evolution API):**
  * Clasificación automática con metadatos enriquecidos (remitente y número de teléfono) cuando las fotos, audios o planos entren al Chatter a través de conectores de mensajería instantánea.
* **Asistente Masivo de Retro-Clasificación:**
  * *Wizard* administrativo para aplicar las reglas de una plantilla de Automatización DMS sobre registros históricos creados antes de la instalación del módulo.
