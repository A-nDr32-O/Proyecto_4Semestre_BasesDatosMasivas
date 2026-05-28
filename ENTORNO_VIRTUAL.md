# Guía del entorno virtual

Este proyecto usa un entorno virtual de Python en `.venv` para aislar las dependencias del sistema.

## 1. Crear el entorno virtual

Desde la raíz del proyecto, ejecuta:

```powershell
python -m venv .venv
```

## 2. Activar el entorno virtual

En PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la ejecución de scripts, puedes abrir una sesión con permisos y ejecutar:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Instalar dependencias dentro del entorno

Una vez activado el entorno, instala las librerías necesarias:

```powershell
python -m pip install --upgrade pip
python -m pip install customtkinter pillow mysql-connector-python
```

## 4. Ejecutar el proyecto

Con el entorno activado, inicia la app:

```powershell
python login.py
```

## 5. Verificar que el entorno está activo

El prompt de PowerShell mostrará algo similar a:

```powershell
(.venv) PS C:\ruta\del\proyecto>
```

## 6. Desactivar el entorno

Cuando termines:

```powershell
deactivate
```

## 7. Reinstalar el entorno si hace falta

Si el entorno se corrompe o falta, puedes recrearlo:

```powershell
Remove-Item -Recurse -Force .venv
python -m venv .venv
```
