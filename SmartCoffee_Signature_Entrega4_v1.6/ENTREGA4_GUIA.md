# Entrega 4 — Guía para el documento de liberación

**Proyecto:** Smart Coffee Menú (CaféSmart AI) — Midnight Espresso Signature  
**Asignatura:** Fundamentos de Inteligencia Artificial  
**Modalidad:** Equipo · Demostración académica local

## A. Código fuente y despliegue

- **Repositorio público:** [AGREGAR URL REAL DE GITHUB DESPUÉS DE SUBIRLO].
- **Rama congelada:** [AGREGAR RAMA Y HASH DEL COMMIT REAL].
- **Despliegue cloud:** No disponible. **Acceso local:** `http://127.0.0.1:8765` (solo cuando el servidor esté encendido en esa computadora).
- **Tecnologías:** Python 3.11+ (stdlib), HTML5, CSS3, JavaScript, JSON.

## B. Ejecución técnica

1. Instalar Python 3.11 o superior.
2. Abrir la carpeta del proyecto en Visual Studio Code.
3. Ejecutar `python app.py` o `INICIAR_WINDOWS.bat`.
4. Abrir `http://127.0.0.1:8765`.
5. Usuario inicial: `admin`; contraseña aleatoria mostrada en terminal en el primer arranque.
6. Dependencias: ninguna externa (`requirements.txt` documentado). Variable opcional `SMARTCOFFEE_ADMIN_PASSWORD` para configurar contraseña **antes del primer arranque**.
7. Los datos persisten en `data/*.json`.

## C. Matriz preliminar de cumplimiento

| ID | Requisito de formulación | Implementación en esta versión | Observaciones |
|---|---|---|---|
| RF01 | Captura y actualización de lote, cantidad, unidad, costo y caducidad | Implementado | Validaciones básicas de servidor; requiere batería formal de pruebas. |
| RF02 | Semáforo vencido/rojo/amarillo/verde | Implementado | Fecha local de la PC; vencidos excluidos. |
| RF03 | Hasta 3 propuestas con soporte, confianza y lift | Implementado parcialmente | Motor de asociaciones de pares recalculado en Python; no integra el `.joblib` original. |
| RF04 | Editar, aprobar, rechazar; editar revoca aprobación | Implementado | Control administrativo y persistencia JSON. |
| RF05 | Mostrar solo promociones aprobadas, vigentes y con stock | Implementado | Evaluación al cargar el menú; no descuenta stock por venta. |
| RF06 | Estados de carga, errores y ausencia de propuesta | Parcial | Mensajes de error y ausencia; no todas las pantallas incluyen animación de carga. |
| RF07 | Avisos y reportes de merma/promociones, exportación CSV | Parcial | Alertas, resumen de merma, exportación CSV de inventario; no filtros por periodo ni CSV completo de reportes. |
| RF08 | Acceso por roles y protección de costos/cambios/aprobaciones | Implementado para demo | Administrador y operador; autenticación local, no apta para despliegue público sin endurecimiento. |

**No afirmar:** resultados medidos de reducción de merma, métricas de precisión experimental verificadas, disponibilidad cloud o cumplimiento de pruebas de aceptación que no se hayan realizado.

## D. Video de respaldo

- **URL:** [AGREGAR LINK AL VIDEO REAL].
- Duración sugerida: 5–8 minutos, grabación continua.
- Mostrar: arranque, login, resumen, datos de entrada, inventario, reglas Apriori, generación de combos, aprobación, vista pública, edición que revoca aprobación, usuarios y roles, reportes.
- Conservar copia local del MP4 y otra copia accesible al docente.

**Antes de entregar:** crear repositorio público, ejecutar pruebas, grabar video, comprobar el ZIP en otra computadora, anotar versión de Python exacta y congelar rama/commit. La Entrega 4 requiere documento final de 4–6 páginas; este archivo es un borrador de contenido, no el PDF final.
