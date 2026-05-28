# theme.py
import customtkinter as ctk
from tkinter import ttk
from typing import Any

# -------------------------------------------------------------------
# PALETA DE COLORES (Basada en el Logo)
# -------------------------------------------------------------------
COLOR_BACKGROUND = "#f5f3f0"     # Beige claro
COLOR_WHITE_FRAME = "#ffffff"    # Blanco puro
COLOR_ENTRY_BG = "#f0f0f0"       # Gris muy claro
COLOR_PRIMARY_NAV = "#5d4a44"     # Marrón oscuro
COLOR_PRIMARY_HOVER = "#4a3a35"  # Marrón oscuro (hover)
COLOR_ACCENT_BUTTON = "#95a43a"   # Verde pistacho
COLOR_ACCENT_HOVER = "#829032"  # Verde pistacho (hover)
COLOR_TEXT_PRIMARY = "#333333"   # Texto principal
COLOR_TEXT_NAV = "#ffffff"       # Texto en barra lateral
COLOR_SUCCESS = "#95a43a"         # Verde pistacho para éxito
COLOR_DANGER = "#e74c3c"         # Rojo para peligro/alertas
COLOR_LOGOUT_BTN = "#7f8c8d"      # Gris neutro
COLOR_LOGOUT_HOVER = "#95a5a6"     # Gris neutro (hover)
COLOR_INFO = "#3498db"            # Azul
COLOR_INFO_HOVER = "#2980b9"
COLOR_WARNING = "#f39c12"         # Naranja/Amarillo (Usado para Pendiente/Sobrante)
COLOR_AJUSTE_ADD = "#3498db"      # Azul para añadir stock
COLOR_AJUSTE_ADD_HOVER = "#2980b9"
COLOR_AJUSTE_REST = "#e67e22"     # Naranja para restar stock
COLOR_AJUSTE_REST_HOVER = "#d35400"

# -------------------------------------------------------------------
# ESTILO DEL TREEVIEW
# -------------------------------------------------------------------

def aplicar_estilo_treeview(widget_padre: Any) -> None:
    """
    Aplica un estilo personalizado al ttk.Treeview.
    'widget_padre' es la ventana (root o toplevel) donde
    se crea el estilo.
    """
    style = ttk.Style(widget_padre)
    style.theme_use("default")

    style.configure("Custom.Treeview",
                    background=COLOR_ENTRY_BG,
                    foreground=COLOR_TEXT_PRIMARY,
                    fieldbackground=COLOR_ENTRY_BG,
                    borderwidth=0,
                    highlightthickness=0,
                    rowheight=30,
                    font=("Arial", 11))
    
    style.configure("Custom.Treeview.Heading",
                    background=COLOR_PRIMARY_NAV,
                    foreground=COLOR_TEXT_NAV,
                    font=("Arial", 11, "bold"),
                    relief="flat",
                    padding=(5, 5))
    
    style.map("Custom.Treeview.Heading",
              background=[('active', COLOR_PRIMARY_HOVER)])
    
    style.map("Custom.Treeview",
              background=[('selected', COLOR_ACCENT_BUTTON)],
              foreground=[('selected', COLOR_TEXT_NAV)])
    
    style.layout("Custom.Treeview", [('Custom.Treeview.treearea', {'sticky': 'nswe'})])

# -------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# -------------------------------------------------------------------

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")