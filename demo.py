# demo.py - Demostración mínima
print("Demo del Sistema de Archivos")

from proyectof import SistemaArchivos

s = SistemaArchivos()
s.crear_carpeta("demo_folder")
s.crear_archivo("demo_file.txt", "Contenido de prueba")

print("✅ Sistema funcionando")
print("Ejecuta 'python proyectof.py' para usar")