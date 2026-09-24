## Objetivo

Importación de información desde Excel, modelado de datos, validaciones, construcción de tableros de análisis y manejo de actualizaciones en tiempo real en el backend.

## Caso práctico

Se entrega un archivo Excel con las ventas realizadas durante el mes. Se debe desarrollar un módulo en Odoo que permita:

- Cargar un archivo Excel mediante un Wizard.
- Leer la información del archivo.
- Crear registros en un modelo personalizado.
- Mostrar la información en un tablero (Dashboard) para análisis comercial.
- Reflejar en tiempo real, en la vista de lista de ventas, los nuevos registros que se vayan creando (por importación u otros usuarios) sin recargar manualmente la página.

## Estructura del archivo Excel

| Fecha      | Cliente   | Vendedor   | Producto   | Cantidad | Valor Unitario | Valor Total | Estado     |
|------------|-----------|------------|------------|----------|----------------|-------------|------------|
| 2026-06-01 | Cliente A | Juan Pérez | Producto 1 | 2        | 50000          | 100000      | Confirmada |

## Dashboard requerido

- Total vendido en el mes.
- Número total de ventas.
- Ventas por vendedor.
- Ventas por cliente.
- Ventas por producto.
- Ventas por estado.
- Gráfico de barras o gráfico circular.
- Vista Pivot para análisis de información.

## Validaciones

- Fecha obligatoria.
- Cliente obligatorio.
- Vendedor obligatorio.
- Producto obligatorio.
- Cantidad mayor a cero.
- Valor total mayor a cero.
- Estado obligatorio.

## Requerimientos técnicos

- Modelo para almacenar las ventas importadas.
- Wizard para cargar el archivo Excel.
- Vistas Lista, Formulario, Búsqueda, Graph, Pivot.
- Menú de acceso al tablero.
- Archivo de seguridad `ir.model.access.csv`.
- Manejo de errores cuando el archivo contenga datos inválidos o incompletos.
- Notificaciones en tiempo real sobre la vista de lista de ventas ante la creación de nuevos registros (ver sección siguiente).

## Requisito adicional — Notificaciones en tiempo real sobre la vista de lista

**Escenario:** la vista de lista de ventas (u otro modelo que se defina) puede recibir registros nuevos generados por otros usuarios o procesos (por ejemplo, otra importación, otro vendedor cargando datos, o una integración externa) en cualquier momento. Hoy la única forma de verlos es recargando la página manualmente. El candidato debe resolver esto sin depender de un polling agresivo.

### Requisitos funcionales

- La lista debe reflejar un registro nuevo sin que el usuario tenga que recargar manualmente la página.
- No se puede depender de un polling agresivo (preguntar al servidor "¿hay algo nuevo?" cada pocos segundos sin parar); el mecanismo debe reaccionar al evento, no a un temporizador ciego.
- Si llegan varios registros nuevos casi al mismo tiempo (una ráfaga), la interfaz no debe recargarse una vez por cada uno.
- La solución debe integrarse con la vista de lista nativa existente, sin duplicar su lógica de renderizado (no se debe construir un componente de lista propio desde cero).
- Al cerrar o navegar fuera de la pantalla, no debe quedar nada escuchando eventos de forma innecesaria (sin fugas de memoria ni suscripciones huérfanas).

## Criterios de evaluación

- Estructura y calidad del código.
- Correcta lectura y validación del Excel.
- Uso adecuado de modelos y vistas de Odoo.
- Capacidad de análisis y visualización de información.
- Manejo de errores y experiencia de usuario.
- Diseño e implementación del mecanismo de notificaciones en tiempo real (nuevo).
