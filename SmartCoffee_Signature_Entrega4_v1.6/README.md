# Smart Coffee Menú — Midnight Espresso Signature

Aplicación web local funcional para demostración académica de **Fundamentos de Inteligencia Artificial — Entrega 4**. Desarrollada con Python 3.11+ (biblioteca estándar), HTML, CSS y JavaScript; no requiere servidor de base de datos ni instalación de paquetes.

## Ejecución en Windows / Visual Studio Code

1. Descomprime el ZIP en una carpeta, por ejemplo `Documentos/SmartCoffee_Signature`.
2. Abre esa carpeta en **Visual Studio Code** (`Archivo > Abrir carpeta`).
3. Comprueba que tienes **Python 3.11 o superior**: `python --version` o `py -3 --version`.
4. Haz doble clic en `INICIAR_WINDOWS.bat`, **o** abre la terminal de VS Code y ejecuta:
   ```powershell
   python app.py
   ```
5. Abre **http://127.0.0.1:8765** (normalmente se abre automáticamente).
6. En el **primer arranque**, la terminal muestra la contraseña inicial aleatoria de `admin`. **Cópiala antes de cerrar la terminal**. Inicia sesión con usuario `admin` y esa contraseña. Cámbiala desde **Cambiar contraseña**.
7. Para detener el servidor, presiona **Ctrl+C** en la terminal.

**Importante:** No cierres la terminal mientras grabas el video. El servidor debe estar ejecutándose.

### Configuración opcional de la contraseña inicial

Si quieres definirla antes del primer arranque, en PowerShell:
```powershell
$env:SMARTCOFFEE_ADMIN_PASSWORD="TuClaveSeguraDe12Caracteres!"
python app.py
```
Solo se aplica al crear por primera vez `data/users.json`. No copies `.env.example` como `.env` esperando que se lea automáticamente: este proyecto no usa cargador de `.env`.

### Comandos alternativos

```powershell
py -3 app.py
python app.py --port 8899
python app.py --no-browser
python -m unittest discover -s tests -v
```

## Roles y credenciales

- **Administrador**: puede crear/desactivar usuarios, restablecer contraseñas, registrar/editar lotes, importar tickets, generar/editar/aprobar/rechazar promociones y registrar merma.
- **Operador**: consulta dashboard, inventario sin costos, datos, recomendaciones y reportes; no puede modificar ni aprobar ni gestionar usuarios.
- No existe registro público. Las contraseñas se almacenan con **PBKDF2-HMAC-SHA256**, sal aleatoria y 260 000 iteraciones. Las sesiones viven en memoria y caducan al reiniciar el servidor.
- El servidor solo escucha en `127.0.0.1` (equipo local). **No es un producto endurecido para Internet**: no exponer el puerto públicamente ni usarlo con datos reales sensibles sin una revisión de seguridad.

## Persistencia

Los datos se crean automáticamente en `data/*.json` y se guardan mediante escritura temporal + reemplazo atómico. La información persiste después de cerrar y reabrir la aplicación. Para respaldarla, copia la carpeta `data/` con el servidor detenido. `data/*.json` está excluido por `.gitignore`.

## Modelo de recomendación

- Se calcula **Apriori para reglas de pares de productos** directamente sobre los tickets cargados, con soporte mínimo **0.15**, confianza mínima **0.70** y lift mínimo **1.40**.
- Las reglas se cruzan con lotes críticos de 0–5 días y complementos con stock vigente.
- Se muestran **hasta tres** propuestas; editar revoca la aprobación; solo promociones aprobadas, no vencidas y con stock aparecen en el menú público.
- **Limitación importante:** esta es una **nueva implementación local del cálculo de asociaciones**, no una integración del archivo `apriori_rules_v1.joblib` ni de `src/models/predict.py` reportados en la Entrega 3, porque no se proporcionaron esos archivos. No se deben afirmar las métricas de precisión experimental de la Entrega 3 como resultados verificados de esta aplicación.
- El algoritmo implementa asociaciones de **dos productos**, no minería general de itemsets de tamaño arbitrario. El precio propuesto es **ilustrativo**, calculado a partir de costos de ejemplo; el administrador puede editarlo. No hay ajuste automático de precios comercial ni cálculo de margen certificado.

## Datos de demostración

En el primer arranque se crean **10 lotes** y **100 tickets simulados** con fechas relativas al día de ejecución, para que la demo siga siendo válida. Los datos NO son registros reales de una cafetería. Los resultados cambian si importas otros tickets o editas inventario, siempre que existan reglas de asociación viables. **Agregar solo inventario no crea reglas nuevas**. Los tickets de ejemplo contienen un conjunto fijo de pares; para recomendar un producto nuevo, agrega tickets que incluyan ese producto junto a otros. Se requieren soporte ≥15 %, confianza ≥70 % y lift ≥1.40. Al generar, las propuestas automáticas pendientes se actualizan o retiran si dejan de ser viables; las aprobadas, rechazadas y editadas manualmente se conservan (el menú público sigue filtrando vigencia y stock). La aprobación no registra ventas ni descuenta existencias automáticamente.

## Flujo para grabar el video

1. Ejecuta `python app.py` y accede con `admin`.
2. Muestra **Resumen** y los estados de caducidad.
3. Abre **Datos de entrada** y explica las reglas Apriori calculadas.
4. En **Inventario crítico**, registra o edita un lote.
5. Abre **Combos sugeridos** y pulsa **Generar recomendaciones**.
6. Explica soporte, confianza y lift; **aprueba** un combo.
7. Abre **Vista de cafetería**: el combo debe aparecer.
8. Regresa, **edita** ese combo y muestra que desaparece del menú hasta aprobarlo nuevamente.
9. Muestra **Gestión de usuarios** y crea un operador; cierra sesión e inicia con ese usuario para demostrar restricciones.
10. Muestra **Reportes** y exportación CSV de inventario.

Graba pantalla y terminal en una sola toma continua. Si una asociación no es viable, revisa fechas y existencias de inventario; no inventes resultados.

## Alcance y pendientes para la entrega

Esta versión cubre un recorrido local demostrable. **No** incluye despliegue público, URL cloud ni repositorio GitHub creado automáticamente: el equipo debe subir el código a un repositorio público (sin `data/*.json`) y anotar la rama/commit final. La app funciona sin conexión a Internet. No procesa pagos, no envía notificaciones y no sincroniza inventario con ventas reales.

## Estructura

- `app.py`: servidor HTTP, autenticación, reglas Apriori, API, archivos JSON.
- `static/index.html`, `static/style.css`, `static/app.js`: interfaz Midnight Espresso Signature.
- `data/`: almacenamiento local automático.
- `tests/`: pruebas unitarias.
- `INICIAR_WINDOWS.bat`: inicio rápido en Windows.
- `ENTREGA4_GUIA.md`: texto base para la documentación y la matriz de cumplimiento.


## Actualización v1.2
- Hasta 15 recomendaciones, priorizando productos con 0–2 días y luego 3–5 días para caducar.
- Se requieren reglas de asociación Apriori y existencias vigentes; no se inventan ventas.
- Guardar inventario o importar tickets regenera automáticamente las propuestas pendientes.
- Las propuestas aprobadas, rechazadas y editadas manualmente no se sobrescriben.
- Se muestra un diagnóstico de productos sin historial, sin regla o sin complemento.
- El historial de tickets no incrementa automáticamente el stock: las ventas históricas no son entradas de mercancía.


## v1.3 — Cantidad configurable de combos
En **Combos sugeridos**, selecciona 3, 5, 10, 15, 20, 50, una cantidad personalizada (1–1000) o **Todos los disponibles**, y pulsa **Generar recomendaciones**. El sistema genera como máximo las asociaciones válidas disponibles, prioriza lotes próximos a caducar y no inventa métricas. La última cantidad solicitada se guarda localmente en `data/generation_settings.json` y se usa al actualizar automáticamente las propuestas pendientes después de modificar inventario o tickets. Las promociones aprobadas o editadas manualmente se conservan.
