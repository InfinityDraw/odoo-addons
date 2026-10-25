===========================================================================
Document Management System Automation of organization and workflows (Odoo)
===========================================================================

.. |badge1| image:: https://img.shields.io/badge/Odoo-18.0%20Community-875A7B.svg
    :alt: Odoo 18.0 Community
.. |badge2| image:: https://img.shields.io/badge/License-LGPL--3-blue.svg
    :alt: License: LGPL-3

|badge1| |badge2|

Módulo desarrollado por **Infinity Draw** (https://infinitydraw.es) para gobernar desde interfaz gráfica toda la automatización documental sobre el ecosistema **OCA DMS** (``dms`` y ``dms_field``).

Características y Arquitectura (v18.0.7.0.0)
============================================

1. **Conector Universal sobre cualquier Chatter de Odoo (``mail.thread``)**

   * Cualquier aplicación de Odoo con Chatter (**CRM, Ventas, Proyectos, Tareas, Empleados, Contratos, Flota, Compras, Fabricación, Facturación...**) puede actuar como Modelo Principal o como Modelo Satélite.
   * Clonado automático al crear un registro (según filtro de dominio) o bajo demanda en el instante en que un usuario suelta el primer archivo en el Chatter o en un campo de descripción.

2. **Respeto de Carpeta Padre y Herencia Limpia de Permisos**

   * Cuando la *Plantilla DMS embebida* tiene definida una **Carpeta padre** (ej. ``Ventas``, ``Proyectos``, ``Administración``), las carpetas clonadas nacen dentro de esa carpeta maestra con ``is_root_directory = False`` e ``inherit_group_ids = True``, manteniendo limpia la raíz del almacenamiento y evitando duplicar grupos explícitos en las subcarpetas hijas.

3. **Modo Global Automático de 10 Carpetas en Ajustes > Documentos**

   * Nueva sección **Ajustes generales de Automatización DMS** dentro de ``Ajustes > Documentos``.
   * Al activar el check, genera automáticamente un almacenamiento exclusivo (``Almacenamiento general Automatizado del Chatter``) con **10 carpetas estándar editables en nombre y extensiones**:

     * ``01 - Imágenes``
     * ``02 - Videos``
     * ``03 - Audios``
     * ``04 - Documentos y PDF``
     * ``05 - Tablas, Datos y CSV``
     * ``06 - Dibujos y Archivos Vectoriales``
     * ``07 - 3D``
     * ``08 - Desarrollo y Programación``
     * ``09 - Comprimidos y ZIP``
     * ``10 - Otros`` (Cajón de sastre automático)

   * Aplica auto-renombrado transparente ``[NombreOriginal]_[AAMMDD-HHMM]`` y etiqueta cada archivo con el nombre del modelo de Odoo de procedencia.

4. **Auto-Clasificación Inteligente (Pestañas 1 y 2)**

   * Prioridad de evaluación para las filas con **Palabras clave**, normalizando automáticamente mayúsculas y tildes (``Prevención`` = ``prevencion``).
   * Incluye el selector mixto **Documentos e Imágenes (PDF, Word, Excel, JPG, PNG, HEIC, WEBP...)** ideal para documentación de RR.HH. y administración.
   * Evaluación prioritaria de planos CAD/BIM (``.dwg``, ``.dxf``, ``.dwf``, ``.ifc``, ``.bc3``) y exclusión de ``.svg`` del filtro anti-firmas (1 KB a 100 KB).

5. **Flujos Encadenados A -> B -> C en Espejo Bidireccional (Pestaña 3)**

   * Separación interna de canales de Entrada y Salida para soportar cadenas multi-etapa (ej. ``CRM -> Proyectos -> Administración``) sin sobrescribir mapeos.
   * Pestaña **Ops. Documentos** en ``crm.lead`` para controlar el traspaso en ampliaciones o múltiples proyectos e historial de traspasos.

6. **Smart Button Dinámico ``Doc. DMS``, Borrado Estanco y Candado DMS**

   * Inyección en tiempo real mediante ``_get_view()`` del botón inteligente ``Doc. DMS`` y ocultación automática de botones redundantes de ``ir.attachment`` (independientemente del orden de instalación de módulos).
   * Sincronización de borrado estanca por almacenamiento físico y protección total de archivos bloqueados con candado (``🔒``) en el DMS.

Guía de Configuración Rápida
============================

1. Asegúrate de tener instalados los módulos oficiales de la OCA ``dms`` y ``dms_field``.
2. Para el **Modo Automático Global**, ve a ``Ajustes > Documentos``, baja hasta **Ajustes generales de Automatización DMS**, activa la casilla y pulsa **Guardar**.
3. Para **Flujos con Plantillas por Modelo**, ve a ``Documentos > Configuración > Automatización DMS``, crea una regla vinculada a tu *Plantilla DMS embebida*, pulsa **Sincronizar subcarpetas de la plantilla** y ajusta las pestañas 1, 2 y 3 según tu flujo de trabajo.

Changelog
=========

18.0.7.0.0 (2026-10)
--------------------
* Motor universal sobre ``mail.thread`` compatible con cualquier modelo de Odoo con Chatter.
* Respeto de ``parent_directory_id`` (*Carpeta padre*) y herencia limpia de permisos al clonar plantillas.
* Nuevo Modo Global Automático en ``Ajustes > Documentos`` con almacenamiento exclusivo y 10 carpetas estándar editables por extensión.
* Opción combinada *Documentos e Imágenes* y comparador de palabras clave insensible a tildes/acentos.
* Inyección dinámica en tiempo real del Smart Button ``Doc. DMS`` y ocultación de botones ``ir.attachment`` redundantes.

Autoría y Soporte
=================

* **Autor:** Infinity Draw (https://infinitydraw.es)
* **Contacto:** contacta@infinitydraw.es · ``@inffinitydraw``
* **Licencia:** LGPL-3.0 or later
