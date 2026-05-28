import sys
import os

def obtener_ruta_base():
    """
    Obtiene la ruta base de la app, ya sea compilada (PyInstaller)
    o como un script normal.
    """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path

# -------------------------------------------------------------------
# CONFIGURACIÓN DE CONEXIÓN A MYSQL (phpMyAdmin)
# Edita estos valores con los datos de tu servidor
# -------------------------------------------------------------------
DB_HOST     = "localhost"       # Host del servidor MySQL (normalmente localhost)
DB_PORT     = 3307              # Puerto MySQL (por defecto 3306)
DB_USER     = "root"            # Usuario de MySQL
DB_PASSWORD = ""                # Contraseña de MySQL
DB_NAME     = "frutos_secos_db"    # Nombre de la base de datos en phpMyAdmin