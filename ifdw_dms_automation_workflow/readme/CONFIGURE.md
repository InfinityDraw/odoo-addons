# Guía de Configuración (`ifdw_dms_automation_workflow`)

Para poner en marcha las reglas de automatización documental del módulo en **Odoo 18**, sigue estos pasos en orden lógico desde un usuario con permisos de **Administrador de Documentos (`DMS Manager`)** o **Ajustes (`System`)**:

---

## 1. Requisitos Previos en el DMS Base (OCA)

Antes de crear tu primera regla de automatización, asegúrate de tener configurada la base en el módulo estándar **Documentos (`dms`)**:

1. **Almacenamientos (`Documentos > Configuración > Almacenamientos`):**
   * Crea tus almacenamientos físicos con tipo de guardado **Almacenamiento / Archivos (`Filestore`)**, por ejemplo:
     * `Almacenamiento CRM / Ventas`
     * `Almacenamiento Proyectos`
     * `Almacenamiento Administración`
2. **Carpetas Molde y Subcarpetas (`Documentos > Carpetas`):**
   * Crea la carpeta raíz que servirá de molde para cada flujo (ej. `Molde CRM`, `Molde Proyectos`) y dentro de ella crea sus subcarpetas numeradas (ej. `01 - Fotos`, `02 - Vídeos y Audios`, `03 - Planos y Croquis`, `04 - Documentos`, `99 - Otros y Comprimidos`).
3. **Plantillas DMS Embebidas (`Documentos > Configuración > Organizar > Plantillas DMS embebidas`):**
   * Vincula cada carpeta molde con su almacenamiento y su modelo de Odoo correspondiente (`crm.lead`, `project.project`, etc.).

---

## 2. Creación de una Regla de Automatización DMS

1. Dirígete a **`Documentos > Configuración > Organizar > Automatización DMS`** y pulsa en **Nuevo**.
2. **Cabecera de la Regla:**
   * **Nombre de la Regla:** Asigna un nombre claro (ej. `Archivos de CRM` o `Archivos de Proyectos`).
   * **Seleccionar "Plantilla DMS embeb.":** Elige la plantilla creada previamente. El sistema rellenará automáticamente en modo lectura el *Almacenamiento*, el *Modelo*, los *Grupos de acceso* y la *Carpeta Raíz del Molde*.
   * **Clonar plantilla automáticamente con cada nuevo registro:** Actívalo para que Odoo genere el árbol de carpetas automáticamente al crear registros. Puedes definir un **Filtro de registros** (dominio) para excluir, por ejemplo, proyectos que sean plantillas.
   * **Mostrar botones Inteligentes `[Documentos]`:** Actívalo para mostrar el Smart Button en la cabecera del formulario del modelo principal y de sus modelos satélite.
   * **Auto-renombrado de archivos subidos al Chatter:** Actívalo y elige entre los 7 formatos disponibles (`[NombreOriginal]`, `[001]-[NombreOriginal]`, `[AAAAMMDD-HHMM]_[Origen/Tarea]_[NombreOriginal]`, etc.).
   * **Filtro anti-archivos basura chicos (Firmas Email):** Actívalo y ajusta el umbral en KB (rango `1 KB` a `100 KB`, recomendado `20 KB` - `30 KB`) para descartar firmas de correo sin afectar a archivos `.svg`, `.dwg` ni subidas manuales.
   * **Sincronizar papelera Chatter <-> DMS:** Actívalo si deseas que al borrar un adjunto desde el Chatter se elimine su copia vinculada en este almacenamiento DMS (respetando siempre los archivos bloqueados con candado `🔒` en el DMS).

---

## 3. Configuración de las 3 Pestañas Operativas

### Pestaña 1: `Reg. Chatter Auto-clasific.`
1. Pulsa el botón **`Sincronizar subcarpetas de la plantilla`** para cargar automáticamente todas las subcarpetas de tu molde.
2. En cada fila, selecciona el **Tipo de Archivo a Clasificar** (*Fotografías e Imágenes*, *Vídeos y Notas de Voz*, *Planos CAD/BIM/Mediciones*, *Documentos Ofimáticos y PDF Estándar*, *Archivos Comprimidos*, *Resto de Archivos / Catch-All* o *Solo Herencia / Movimiento*).
3. Opcionalmente, define **Palabras clave en nombre** (ej. `plano, croquis, medicion` para distinguir planos en PDF de presupuestos en PDF), **Extensiones extra** y la **Categoría DMS a aplicar**.

### Pestaña 2: `Reg. Mod. Auto-clasific.` (Modelos Satélite)
1. Añade una línea por cada modelo secundario cuyos adjuntos del Chatter deban viajar a la carpeta del modelo principal:
   * En la regla de **CRM (`crm.lead`)**: añade **Pedido de Venta (`sale.order`)** (detectará automáticamente el campo `opportunity_id`).
   * En la regla de **Proyectos (`project.project`)**: añade **Tarea (`project.task`)** (detectará automáticamente el campo `project_id`).
2. Puedes forzar una subcarpeta fija o dejarlo en blanco para que aplique las reglas de la Pestaña 1, y marcar **Etiquetar con nombre del registro** para crear etiquetas automáticas en el DMS con el nombre de la tarea o pedido.

### Pestaña 3: `Reg. Mov. Archiv.` (Espejo Bidireccional `A ➔ B ➔ C`)
1. Marca **Activar movimiento/copia de archivos entre flujos**.
2. Selecciona el **Modo de Configuración (Espejo)**:
   * **Canal de Entrada:** Para configurar de qué regla de origen recibes archivos (ej. estando en `Archivos de Proyectos`, recibir desde `Archivos de CRM`).
   * **Canal de Salida:** Para configurar hacia qué regla de destino envías archivos (ej. estando en `Archivos de CRM`, enviar hacia `Archivos de Proyectos`).
3. Elige la **Acción tras trasladar archivos** (*Opción 1: Copiar manteniendo originales*, *Opción 2: Mover y borrar archivos/carpetas en origen*, o *Opción 3: Mover y borrar solo archivos dejando carpetas vacías en origen*).
4. Activa **Publicar nota de trazabilidad en el Chatter** y selecciona en **Modelos donde publicar nota** en qué registros deseas dejar constancia del traspaso (`Oportunidad`, `Pedido de Venta`, `Proyecto`).
5. Rellena la tabla inferior de **Mapeo de Subcarpetas** emparejando cada subcarpeta de origen con su subcarpeta de destino correspondiente. Al guardar, ambos extremos quedarán sincronizados en espejo automáticamente.
