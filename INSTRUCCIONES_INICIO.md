# Instrucciones de inicio del proyecto

## 1. Requisitos previos
- Python 3.14 (o una versión compatible con el entorno del proyecto)
- MySQL/MariaDB en ejecución
- Acceso a la base de datos configurada en `config.py`

## 2. Preparar el entorno
1. Abrir una terminal en la raíz del proyecto.
2. Instalar dependencias:

   ```powershell
   pip install customtkinter pillow mysql-connector-python
   ```

   Si el entorno ya tiene las librerías, puedes omitir este paso.

## 3. Configurar la base de datos
1. Verifica los datos de conexión en `config.py`:
   - `DB_HOST`
   - `DB_PORT`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`
2. Asegúrate de que MySQL esté corriendo.
3. Si la base no existe o necesita inicializarse, ejecuta:

   ```powershell
   python crear_db.py
   ```

## 4. Ejecutar la aplicación
### Opción recomendada: iniciar desde el login
```powershell
python login.py
```

### Alternativa: abrir directamente la pantalla principal
```powershell
python main.py
```

> El flujo normal del proyecto inicia con `login.py`, que valida credenciales y luego abre `main.py`.

## 5. Credenciales de prueba
Si ya tienes usuarios cargados en la base de datos, usa esas credenciales en el login.

## 6. Verificación rápida
- El login debe abrir la ventana de autenticación.
- Si la conexión a MySQL falla, revisa `config.py` y que el servidor esté activo.
- El resumen del día y el resto de módulos dependen de la base de datos activa.
