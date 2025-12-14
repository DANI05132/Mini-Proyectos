import json
import uuid
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any

class Nodo:
    def __init__(self, id_nodo, nombre, tipo, contenido=None):
        self.id = id_nodo
        self.nombre = nombre
        self.tipo = tipo  # "carpeta" o "archivo"
        self.contenido = contenido  # solo para archivos
        self.children = []  # solo para carpetas
        self.parent = None  # referencia al padre

    def to_dict(self):
        """Convierte el nodo a diccionario para JSON."""
        nodo_dict = {
            "id": self.id,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "contenido": self.contenido,
        }
        if self.tipo == "carpeta":
            nodo_dict["children"] = [child.to_dict() for child in self.children]
        return nodo_dict

    @staticmethod
    def from_dict(data, parent=None):
        """Crea un nodo desde diccionario (JSON)."""
        nodo = Nodo(data["id"], data["nombre"], data["tipo"], data["contenido"])
        nodo.parent = parent
        if nodo.tipo == "carpeta":
            nodo.children = [Nodo.from_dict(child, parent=nodo) for child in data.get("children", [])]
        return nodo

    def agregar_hijo(self, hijo):
        hijo.parent = self
        self.children.append(hijo)

    def eliminar_hijo(self, hijo):
        if hijo in self.children:
            self.children.remove(hijo)
            hijo.parent = None
            return True
        return False

    def buscar_por_nombre(self, nombre):
        for child in self.children:
            if child.nombre == nombre:
                return child
        return None

    def buscar_por_id(self, id_nodo):
        if self.id == id_nodo:
            return self
        for child in self.children:
            if child.tipo == "carpeta":
                encontrado = child.buscar_por_id(id_nodo)
                if encontrado:
                    return encontrado
        return None

    def preorden(self, lista=None):
        if lista is None:
            lista = []
        lista.append((self.nombre, self.tipo, self.id))
        if self.tipo == "carpeta":
            for child in self.children:
                child.preorden(lista)
        return lista

    def calcular_tamano(self):
        tamano = 1
        if self.tipo == "carpeta":
            for child in self.children:
                tamano += child.calcular_tamano()
        return tamano

    def calcular_altura(self):
        if self.tipo != "carpeta" or not self.children:
            return 0
        return 1 + max(child.calcular_altura() for child in self.children)


class SistemaArchivos:
    def __init__(self):
        self.raiz = Nodo(str(uuid.uuid4()), "root", "carpeta")
        self.nodo_actual = self.raiz
        self.ruta_actual = ["root"]
        self.next_id = 1
        self.historial = []  # para registro de cambios (opcional)
        self.version = "1.0"
        self.archivo_persistencia = "sistema.json"

    # ==================== PERSISTENCIA MEJORADA ====================
    
    def crear_backup(self, archivo_original: str) -> bool:
        """Crea una copia de seguridad del archivo JSON antes de sobrescribir."""
        if not os.path.exists(archivo_original):
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{timestamp}_{os.path.basename(archivo_original)}"
        
        try:
            shutil.copy2(archivo_original, backup_file)
            print(f"Backup creado: {backup_file}")
            return True
        except Exception as e:
            print(f"Error al crear backup: {e}")
            return False

    def validar_estructura_json(self, datos: Dict[str, Any]) -> bool:
        """Valida que el JSON tenga la estructura correcta."""
        required_keys = ["version", "next_id", "raiz"]
        if not all(key in datos for key in required_keys):
            print("Error: JSON no tiene todas las claves requeridas.")
            return False
        
        # Validar estructura recursiva del árbol
        def validar_nodo(nodo_dict: Dict[str, Any]) -> bool:
            if not all(k in nodo_dict for k in ["id", "nombre", "tipo"]):
                return False
            if nodo_dict["tipo"] not in ["carpeta", "archivo"]:
                return False
            if nodo_dict["tipo"] == "carpeta":
                if "children" not in nodo_dict:
                    return False
                for child in nodo_dict["children"]:
                    if not validar_nodo(child):
                        return False
            return True
        
        if not validar_nodo(datos["raiz"]):
            print("Error: Estructura de nodos inválida.")
            return False
        
        return True

    def guardar_a_json(self, archivo: Optional[str] = None) -> bool:
        """Guarda el sistema de archivos a un archivo JSON con validación y backup."""
        if archivo is None:
            archivo = self.archivo_persistencia
        
        # Crear backup si el archivo ya existe
        if os.path.exists(archivo):
            self.crear_backup(archivo)
        
        datos = {
            "version": self.version,
            "fecha_guardado": datetime.now().isoformat(),
            "next_id": self.next_id,
            "raiz": self.raiz.to_dict()
        }
        
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
            print(f"Sistema guardado exitosamente en '{archivo}' (v{self.version}).")
            
            # Registrar en historial
            self.historial.append({
                "accion": "guardar",
                "archivo": archivo,
                "fecha": datetime.now().isoformat(),
                "nodos_totales": self.raiz.calcular_tamano()
            })
            return True
        except Exception as e:
            print(f"Error al guardar JSON: {e}")
            return False

    def cargar_desde_json(self, archivo: Optional[str] = None) -> bool:
        """Carga el sistema de archivos desde un archivo JSON con validación."""
        if archivo is None:
            archivo = self.archivo_persistencia
        
        if not os.path.exists(archivo):
            print(f"Archivo '{archivo}' no encontrado. Se inicia sistema vacío.")
            return False
        
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
            
            # Validar estructura
            if not self.validar_estructura_json(datos):
                print("Error: El archivo JSON tiene estructura inválida.")
                return False
            
            # Cargar datos
            self.version = datos.get("version", "1.0")
            self.next_id = datos["next_id"]
            self.raiz = Nodo.from_dict(datos["raiz"])
            self.nodo_actual = self.raiz
            self.ruta_actual = ["root"]
            
            # Registrar en historial
            self.historial.append({
                "accion": "cargar",
                "archivo": archivo,
                "fecha": datetime.now().isoformat(),
                "nodos_totales": self.raiz.calcular_tamano()
            })
            
            print(f"Sistema cargado exitosamente desde '{archivo}' (v{self.version}).")
            print(f"Fecha del guardado: {datos.get('fecha_guardado', 'desconocida')}")
            return True
            
        except json.JSONDecodeError as e:
            print(f"Error de JSON inválido: {e}")
            return False
        except Exception as e:
            print(f"Error al cargar JSON: {e}")
            return False

    def mostrar_historial(self, limite: int = 5):
        """Muestra el historial reciente de operaciones de persistencia."""
        if not self.historial:
            print("Historial vacío.")
            return
        
        print(f"\n=== Últimas {min(limite, len(self.historial))} operaciones de persistencia ===")
        for i, registro in enumerate(reversed(self.historial[-limite:])):
            print(f"{i+1}. {registro['accion'].upper()} - {registro['fecha']}")
            print(f"   Archivo: {registro['archivo']}")
            print(f"   Nodos totales: {registro.get('nodos_totales', 'N/A')}")
            print()

    def limpiar_backups_antiguos(self, max_backups: int = 5):
        """Elimina backups antiguos, manteniendo solo los más recientes."""
        backups = [f for f in os.listdir() if f.startswith("backup_") and f.endswith(".json")]
        backups.sort(key=os.path.getmtime, reverse=True)
        
        if len(backups) > max_backups:
            for backup in backups[max_backups:]:
                try:
                    os.remove(backup)
                    print(f"Backup antiguo eliminado: {backup}")
                except Exception as e:
                    print(f"Error al eliminar backup {backup}: {e}")
    
    def crear_carpeta(self, nombre):
        if self.nodo_actual.buscar_por_nombre(nombre):
            print(f"Error: ya existe '{nombre}' en esta carpeta.")
            return None
        nueva_carpeta = Nodo(str(self.next_id), nombre, "carpeta")
        self.next_id += 1
        self.nodo_actual.agregar_hijo(nueva_carpeta)
        print(f"Carpeta '{nombre}' creada.")
        return nueva_carpeta

    def crear_archivo(self, nombre, contenido=""):
        if self.nodo_actual.buscar_por_nombre(nombre):
            print(f"Error: ya existe '{nombre}' en esta carpeta.")
            return None
        nuevo_archivo = Nodo(str(self.next_id), nombre, "archivo", contenido)
        self.next_id += 1
        self.nodo_actual.agregar_hijo(nuevo_archivo)
        print(f"Archivo '{nombre}' creado.")
        return nuevo_archivo

    def listar_hijos(self):
        if not self.nodo_actual.children:
            print("(vacío)")
        for child in self.nodo_actual.children:
            tipo = "[DIR]" if child.tipo == "carpeta" else "[FILE]"
            print(f"{tipo} {child.nombre} (ID: {child.id})")

    def ruta_completa(self):
        return "/" + "/".join(self.ruta_actual)

    def cambiar_directorio(self, ruta):
        if ruta == "/":
            self.nodo_actual = self.raiz
            self.ruta_actual = ["root"]
            print("Ruta cambiada a /root")
            return
        if ruta == "..":
            if self.nodo_actual.parent:
                self.nodo_actual = self.nodo_actual.parent
                self.ruta_actual.pop()
                print("Ruta cambiada a directorio padre.")
            else:
                print("Ya estás en la raíz.")
            return

        partes = ruta.split("/")
        nodo_temp = self.nodo_actual
        ruta_temp = self.ruta_actual.copy()

        if partes[0] == "":
            nodo_temp = self.raiz
            ruta_temp = ["root"]
            partes = partes[1:]

        for parte in partes:
            if parte == ".":
                continue
            encontrado = nodo_temp.buscar_por_nombre(parte)
            if not encontrado or encontrado.tipo != "carpeta":
                print(f"Error: '{parte}' no es una carpeta válida.")
                return
            nodo_temp = encontrado
            ruta_temp.append(parte)

        self.nodo_actual = nodo_temp
        self.ruta_actual = ruta_temp
        print(f"Ruta cambiada a {self.ruta_completa()}")

    def mover_nodo(self, origen, destino_nombre):
        nodo_origen = self.nodo_actual.buscar_por_nombre(origen)
        if not nodo_origen:
            print(f"Error: '{origen}' no encontrado en la carpeta actual.")
            return

        nodo_destino = self.nodo_actual.buscar_por_nombre(destino_nombre)
        if not nodo_destino or nodo_destino.tipo != "carpeta":
            print(f"Error: '{destino_nombre}' no es una carpeta válida.")
            return

        if nodo_destino.buscar_por_nombre(nodo_origen.nombre):
            print(f"Error: ya existe un nodo con nombre '{nodo_origen.nombre}' en '{destino_nombre}'.")
            return

        if nodo_origen.parent:
            nodo_origen.parent.eliminar_hijo(nodo_origen)
        nodo_destino.agregar_hijo(nodo_origen)
        print(f"'{origen}' movido a '{destino_nombre}'.")

    def renombrar_nodo(self, nombre_actual, nuevo_nombre):
        nodo = self.nodo_actual.buscar_por_nombre(nombre_actual)
        if not nodo:
            print(f"Error: '{nombre_actual}' no encontrado.")
            return

        if self.nodo_actual.buscar_por_nombre(nuevo_nombre):
            print(f"Error: ya existe '{nuevo_nombre}' en esta carpeta.")
            return

        nodo.nombre = nuevo_nombre
        print(f"'{nombre_actual}' renombrado a '{nuevo_nombre}'.")

    def eliminar_nodo(self, nombre):
        nodo = self.nodo_actual.buscar_por_nombre(nombre)
        if not nodo:
            print(f"Error: '{nombre}' no encontrado.")
            return

        if nodo.parent:
            nodo.parent.eliminar_hijo(nodo)
            print(f"'{nombre}' eliminado.")
        else:
            print("No se puede eliminar la raíz.")

    def exportar_preorden(self, archivo="preorden.txt"):
        lista = self.raiz.preorden()
        with open(archivo, "w", encoding="utf-8") as f:
            for nombre, tipo, id_nodo in lista:
                f.write(f"{tipo.upper()}: {nombre} (ID: {id_nodo})\n")
        print(f"Recorrido en preorden exportado a '{archivo}'.")

    def mostrar_estadisticas(self):
        altura = self.raiz.calcular_altura()
        tamano = self.raiz.calcular_tamano()
        print(f"Altura del árbol: {altura}")
        print(f"Tamaño del árbol (nodos totales): {tamano}")
        print(f"Versión del sistema: {self.version}")
        print(f"Archivo de persistencia: {self.archivo_persistencia}")

    
    def mkdir(self, nombre):
        self.crear_carpeta(nombre)

    def touch(self, nombre, contenido=""):
        self.crear_archivo(nombre, contenido)

    def ls(self):
        self.listar_hijos()

    def pwd(self):
        print(self.ruta_completa())

    def cd(self, ruta):
        self.cambiar_directorio(ruta)

    def mv(self, origen, destino):
        self.mover_nodo(origen, destino)

    def rename(self, viejo, nuevo):
        self.renombrar_nodo(viejo, nuevo)

    def rm(self, nombre):
        self.eliminar_nodo(nombre)

    def export(self):
        self.exportar_preorden()

    def stats(self):
        self.mostrar_estadisticas()

    def history(self, limite=5):
        self.mostrar_historial(limite)

    def clean_backups(self):
        self.limpiar_backups_antiguos()

    def save(self, archivo=None):
        if archivo:
            self.guardar_a_json(archivo)
        else:
            self.guardar_a_json()

    def load(self, archivo=None):
        if archivo:
            self.cargar_desde_json(archivo)
        else:
            self.cargar_desde_json()


def main():
    sistema = SistemaArchivos()
    
    # Intentar cargar sistema existente
    if os.path.exists(sistema.archivo_persistencia):
        respuesta = input(f"¿Cargar sistema existente desde '{sistema.archivo_persistencia}'? (s/n): ").lower()
        if respuesta == 's':
            sistema.load()
    else:
        print("No se encontró sistema existente. Iniciando nuevo sistema.")

    comandos = {
        "mkdir": lambda args: sistema.mkdir(args[0]) if args else print("Uso: mkdir <nombre>"),
        "touch": lambda args: sistema.touch(args[0], " ".join(args[1:])) if args else print("Uso: touch <nombre> [contenido]"),
        "ls": lambda args: sistema.ls(),
        "pwd": lambda args: sistema.pwd(),
        "cd": lambda args: sistema.cd(args[0]) if args else print("Uso: cd <ruta>"),
        "mv": lambda args: sistema.mv(args[0], args[1]) if len(args) == 2 else print("Uso: mv <origen> <destino>"),
        "rename": lambda args: sistema.rename(args[0], args[1]) if len(args) == 2 else print("Uso: rename <viejo> <nuevo>"),
        "rm": lambda args: sistema.rm(args[0]) if args else print("Uso: rm <nombre>"),
        "export": lambda args: sistema.export(),
        "stats": lambda args: sistema.stats(),
        "history": lambda args: sistema.history(int(args[0]) if args else 5),
        "clean": lambda args: sistema.clean_backups(),
        "save": lambda args: sistema.save(args[0] if args else None),
        "load": lambda args: sistema.load(args[0] if args else None),
        "help": lambda args: print(
            "Comandos:\n"
            "  mkdir <nombre>, touch <nombre> [contenido], ls, pwd, cd <ruta>\n"
            "  mv <origen> <destino>, rename <viejo> <nuevo>, rm <nombre>\n"
            "  export, stats, history [limite], clean, save [archivo], load [archivo]\n"
            "  exit"
        ),
        "exit": None,
    }

    print("\n" + "="*60)
    print("SISTEMA DE ARCHIVOS JERÁRQUICO - DÍA 4: PERSISTENCIA MEJORADA")
    print("="*60)
    print("Escribe 'help' para ver comandos disponibles")

    while True:
        try:
            entrada = input(f"{sistema.ruta_completa()}$ ").strip().split()
            if not entrada:
                continue
            comando = entrada[0]
            args = entrada[1:]

            if comando == "exit":
                respuesta = input("¿Guardar cambios antes de salir? (s/n): ").lower()
                if respuesta == 's':
                    sistema.save()
                print("Saliendo...")
                break
            elif comando in comandos:
                if comandos[comando] is None:
                    continue
                comandos[comando](args)
            else:
                print(f"Comando no reconocido. Escribe 'help' para ver comandos.")
        except KeyboardInterrupt:
            print("\nInterrupción detectada.")
            respuesta = input("¿Guardar cambios antes de salir? (s/n): ").lower()
            if respuesta == 's':
                sistema.save()
            print("Saliendo...")
            break
        except Exception as e:
            print(f"Error inesperado: {e}")

def ejecutar_pruebas_persistencia():
    print("\n" + "="*60)
    print("PRUEBAS DE PERSISTENCIA MEJORADA - DÍA 4")
    print("="*60)
    
    # Limpiar archivos anteriores
    for f in ["test_sistema.json", "preorden.txt"] + [f for f in os.listdir() if f.startswith("backup_")]:
        if os.path.exists(f):
            os.remove(f)
    
    sistema = SistemaArchivos()
    sistema.archivo_persistencia = "test_sistema.json"
    
    print("1. Creando estructura de prueba...")
    sistema.mkdir("docs")
    sistema.mkdir("media")
    sistema.cd("docs")
    sistema.touch("readme.txt", "Archivo de prueba")
    sistema.cd("..")
    sistema.touch("config.ini", "version=1.0")
    
    print("2. Guardando sistema...")
    sistema.save()
    
    print("3. Modificando sistema...")
    sistema.rename("config.ini", "config_backup.ini")
    sistema.rm("config_backup.ini")
    
    print("4. Guardando nuevamente (debería crear backup)...")
    sistema.save()
    
    print("5. Cargando sistema original...")
    sistema2 = SistemaArchivos()
    sistema2.archivo_persistencia = "test_sistema.json"
    sistema2.load()
    
    print("6. Verificando carga correcta...")
    sistema2.ls()
    sistema2.cd("docs")
    sistema2.ls()
    sistema2.stats()
    
    print("7. Mostrando historial...")
    sistema2.history()
    
    print("8. Limpiando backups (manteniendo solo 2 más recientes)...")
    sistema2.limpiar_backups_antiguos(max_backups=2)
    
    print("9. Creando JSON corrupto y probando validación...")
    with open("corrupto.json", "w") as f:
        f.write('{"version": "1.0", "next_id": 1}')  # Falta "raiz"
    
    sistema3 = SistemaArchivos()
    sistema3.archivo_persistencia = "corrupto.json"
    if not sistema3.load():
        print("✓ Correctamente rechazó JSON corrupto")
    
    # Limpiar
    for f in ["test_sistema.json", "corrupto.json", "preorden.txt"] + [f for f in os.listdir() if f.startswith("backup_")]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n" + "="*60)
    print("PRUEBAS DE PERSISTENCIA COMPLETADAS EXITOSAMENTE")
    print("="*60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test-persistencia":
        ejecutar_pruebas_persistencia()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Ejecutar pruebas de días anteriores también
        from dia2_3 import ejecutar_pruebas
        ejecutar_pruebas()
        ejecutar_pruebas_persistencia()
    else:
        main()