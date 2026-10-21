# Automatización de Flujos y Archivos del DMS (`ifdw_dms_automation_workflow`)

Módulo desarrollado por **Infinity Draw** para gobernar desde una interfaz gráfica centralizada toda la automatización documental sobre el ecosistema **OCA Document Management System (`dms` y `dms_field`)** en **Odoo 18 Community**.

---

## 🎯 Propósito y Valor Añadido

El motor nativo `OCA/dms` proporciona una estructura robusta de almacenamientos, directorios y permisos, pero requiere que los usuarios naveguen manualmente al árbol documental o carece de puentes automáticos para conectar el trabajo diario en el **Chatter** con las subcarpetas de negocio (CRM, Ventas, Proyectos, Tareas y Facturación).

**`ifdw_dms_automation_workflow`** elimina por completo la fricción operativa permitiendo que los técnicos, comerciales y operarios trabajen exclusivamente desde el clip de adjuntos (`📎`) del Chatter de cualquier registro, mientras el motor clasifica, renombra, etiqueta y traslada los documentos en segundo plano según reglas definidas por el administrador.

---

## ⚙️ Características Principales

* **Panel de Control Centralizado (`Documentos > Configuración > Organizar > Automatización DMS`):**
  * Conecta directamente con las **Plantillas DMS embebidas** (`dms.field.template`) respetando íntegramente sus almacenamientos físicos (*Filestore*), modelos asociados, grupos de seguridad y estructura de subcarpetas.
  * Clonado automático del árbol de carpetas al crear nuevos registros con soporte para **filtro de dominio dinámico** (por ejemplo, para excluir proyectos plantilla o presupuestos cancelados).
  * Activación/desactivación de **Smart Buttons `Documentos`** dinámicos en las vistas de formulario con contador jerárquico real y vista previa interactiva en la propia regla.

* **Auto-Renombrado Inteligente y Truncado Seguro (KISS):**
  * Estandariza la nomenclatura de los archivos subidos desde dispositivos móviles u ordenador con 7 formatos seleccionables (`[NombreOriginal]`, `[001]-[NombreOriginal]`, `[AAAAMMDD-HHMM]_[Origen/Tarea]_[NombreOriginal]`, `[AA-MM-DD]_[Usuario]_[Origen/Tarea]_[NombreOriginal]`, etc.).
  * Incluye **truncado inteligente a 180 caracteres** conservando intacta la extensión original para prevenir errores de límite de sistema de archivos en Linux y PostgreSQL (`255 bytes`).

* **Filtro Anti-Basura para Firmas de Correo:**
  * Umbral regulable entre **1 KB y 100 KB** (por defecto `20 KB` / `30 KB`) que descarta automáticamente logotipos e iconos diminutos incrustados en correos entrantes, protegiendo siempre los archivos subidos manualmente por usuarios internos, gráficos vectoriales (`.svg`) y planos CAD (`.dwg`, `.dxf`).

* **Pestaña 1 — Auto-Clasificación Inteligente desde el Chatter (`Reg. Chatter Auto-clasific.`):**
  * Evaluación prioritaria de **Planos CAD/BIM/Mediciones** (`.dwg`, `.dxf`, `.dwf`, `.ifc`, `.bc3` y planos en `.pdf` por palabras clave) antes de la evaluación de imagen bitmap, evitando falsos positivos por tipos MIME (`image/vnd.dwg`).
  * Clasificación automática de fotografías (`JPG`, `PNG`, `HEIC`, `HEIF`, `AVIF`, `WEBP`, `RAW`), vídeos, notas de voz/audios (`OGG`, `OPUS`, `MP3`, `WAV`, `M4A`), documentos ofimáticos y archivos comprimidos, asignando automáticamente su **Categoría DMS**.
  * Publicación de una **nota interna agrupada en el Chatter** detallando el usuario, el nombre original, el nombre final asignado en el DMS y la subcarpeta de destino (ignorando automáticamente los PDFs autogenerados por informes de Odoo).

* **Pestaña 2 — Enrutamiento desde Modelos Satélite (`Reg. Mod. Auto-clasific.`):**
  * Permite vincular modelos secundarios (como `project.task`, `sale.order` o `account.move`) al modelo principal de la regla con autodetección del campo relacional `Many2one`.
  * Los archivos subidos al Chatter del modelo satélite viajan directamente a la subcarpeta correspondiente del registro padre y pueden etiquetarse automáticamente con el nombre del registro origen (ej. el nombre de la Tarea).

* **Pestaña 3 — Espejo Bidireccional y Flujos Encadenados (`A ➔ B ➔ C`):**
  * Arquitectura de **doble canal independiente (Entrada y Salida)** sincronizada en espejo bidireccional: una misma regla intermedia (ej. *Proyectos*) puede recibir archivos desde un origen (*CRM*) y enviarlos hacia un destino posterior (*Administración*) sin colisión en las tablas de mapeo de subcarpetas.
  * Tres políticas de traslado tras el movimiento:
    1. **Opción 1:** Copiar al destino manteniendo intactos los originales en el origen.
    2. **Opción 2:** Mover al destino y eliminar archivos y carpetas residuales en el origen (incluyendo limpieza real de los adjuntos del Chatter de origen).
    3. **Opción 3:** Mover al destino y eliminar únicamente los archivos residuales en el origen manteniendo la estructura de carpetas vacía.

* **Control Granular en CRM (`Ops. Documentos`) y Borrado Estanco:**
  * Pestaña específica en `crm.lead` para decidir el comportamiento documental cuando una misma oportunidad genera múltiples proyectos o ampliaciones (*Opción A: Regla global*, *Opción B: Solo archivos nuevos no enviados previamente*, *Opción C: No traspasar*), acompañada de su tabla de **Historial de Traspasos Documentales**.
  * **Sincronización de papelera estanca por almacenamiento:** eliminar un adjunto en el Chatter de origen solo afecta a su almacenamiento DMS vinculado, sin destruir copias que ya hayan migrado a otros almacenamientos como Proyectos, y respetando de forma estricta el **candado nativo de bloqueo (`is_locked`)** del DMS.
  * Aplicación limpia del operador jerárquico `child_of` exclusivamente en la vista *Documentos > Archivos* y en los Smart Buttons para mantener impoluto el árbol jerárquico en *Documentos > Documentos*.
