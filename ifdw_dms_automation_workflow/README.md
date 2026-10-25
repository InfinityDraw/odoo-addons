# Document Management System Automation of organization and workflows (`ifdw_dms_automation_workflow`)

![Version](https://img.shields.io/badge/Odoo-18.0%20Community-875A7B.svg)
![License](https://img.shields.io/badge/License-LGPL--3.0-blue.svg)
![OCA DMS](https://img.shields.io/badge/OCA-DMS%20Ready-success.svg)

Módulo desarrollado por **Infinity Draw** ([https://infinitydraw.es](https://infinitydraw.es)) para automatizar de forma universal la creación de estructuras de carpetas, el auto-renombrado, la clasificación inteligente de archivos desde cualquier **Chatter de Odoo** y el traspaso documental en espejo entre flujos encadenados sobre el motor oficial **OCA DMS** (`dms` y `dms_field`).

---

## 🚀 Características Principales (v18.0.7.0.0)

1. **Motor Universal sobre `mail.thread`:**
   - Cualquier modelo de Odoo con Chatter (**CRM, Ventas, Proyectos, Tareas, Empleados, Contratos, Flota, Compras, Fabricación, Facturación...**) puede actuar como modelo principal o como modelo satélite sin límite de aplicaciones.
2. **Respeto de `Carpeta Padre` y Herencia Limpia de Permisos:**
   - Al clonar una *Plantilla DMS embebida*, la carpeta del nuevo registro nace dentro de la **`Carpeta padre`** configurada en la plantilla (ej. `Ventas`, `Proyectos`, `Administración`), manteniendo limpia la raíz del almacenamiento y aplicando `inherit_group_ids = True` sin duplicar grupos explícitos en las subcarpetas hijas.
3. **Modo Global Automático de 10 Carpetas en `Ajustes > Documentos`:**
   - Incluye la sección **Ajustes generales de Automatización DMS** para capturar automáticamente cualquier archivo subido a Chatters que no tengan una regla específica, creando un almacenamiento exclusivo (`Almacenamiento general Automatizado del Chatter`) con **10 carpetas estándar editables por extensión**, renombrado automático `[NombreOriginal]_[AAMMDD-HHMM]` y etiquetado con el nombre de la aplicación.
4. **Clasificación Inteligente con Prioridad de Palabras Clave (Sin Tildes):**
   - Evalúa con prioridad las filas con palabras clave ignorando mayúsculas y tildes (`Prevención` = `prevencion`), incluye la opción mixta **Documentos e Imágenes**, prioriza planos CAD/BIM (`.dwg`, `.dxf`, `.dwf`, `.ifc`, `.bc3`) y protege archivos `.svg` frente al filtro anti-firmas (1 KB a 100 KB).
5. **Flujos Encadenados `A ➔ B ➔ C` en Espejo Bidireccional:**
   - Separación de canales de Entrada y Salida en la Pestaña 3 para permitir que una regla intermedia (ej. *Proyectos*) reciba archivos desde *CRM/Ventas* y a la vez los envíe hacia *Administración* sin pisar sus mapeos, complementado con la pestaña **`Ops. Documentos`** en CRM.
6. **Smart Button Dinámico `Doc. DMS` y Borrado Estanco:**
   - Inyecta en tiempo real el botón inteligente **`Doc. DMS`** en cualquier formulario con regla activa (ocultando botones redundantes de `ir.attachment` independientemente del orden de instalación de módulos), sincroniza la papelera de forma estanca por almacenamiento y respeta el candado nativo (`🔒`) del DMS.

---

## ⚙️ Requisitos e Instalación

1. Instalar previamente los módulos oficiales de la **OCA** para Odoo 18.0:
   - `dms` (*Document Management System*)
   - `dms_field` (*DMS Field / Embedded Templates*)
2. Copiar la carpeta `ifdw_dms_automation_workflow` en tu ruta de `addons-extra` y actualizar la lista de aplicaciones.
3. Configurar tus reglas personalizadas en **`Documentos > Configuración > Automatización DMS`** o activar el modo rápido en **`Ajustes > Documentos > Ajustes generales de Automatización DMS`**.

---

## 📄 Licencia y Autoría

- **Autor:** Infinity Draw ([https://infinitydraw.es](https://infinitydraw.es))
- **Contacto:** contacta@infinitydraw.es · `@inffinitydraw`
- **Licencia:** GNU Lesser General Public License v3.0 or later (`LGPL-3`)
