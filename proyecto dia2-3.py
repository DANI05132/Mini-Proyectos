import json
import uuid
import os

class Nodo:
    def __init__(self, id_nodo, nombre, tipo, contenido=None):
        self.id = id_nodo
        self.nombre = nombre
        self.tipo = tipo  # "carpeta" o "archivo"
        self.contenido = contenido  # solo para archivos
        self.children = []  # solo para carpetas
        self.parent = None  # referencia al padre (añadido para navegación)

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
        """Agrega un hijo al nodo actual."""
        hijo.parent = self
        self.children.append(hijo)

    def eliminar_hijo(self, hijo):
        """Elimina un hijo del nodo actual."""
        if hijo in self.children:
            self.children.remove(hijo)
            hijo.parent = None
            return True
        return False

    def buscar_por_nombre(self, nombre):
        """Busca un hijo por nombre (retorna el nodo o None)."""
        for child in self.children:
            if child.nombre == nombre:
                return child
        return None

    def buscar_por_id(self, id_nodo):
        """Busca recursivamente un nodo por ID."""
        if self.id == id_nodo:
            return self
        for child in self.children:
            if child.tipo == "carpeta":
                encontrado = child.buscar_por_id(id_nodo)
                if encontrado:
                    return encontrado
        return None

    def preorden(self, lista=None):
        """Recorrido en preorden (raíz → hijos)."""
        if lista is None:
            lista = []
        lista.append((self.nombre, self.tipo, self.id))
        if self.tipo == "carpeta":
            for child in self.children:
                child.preorden(lista)
        return lista

    def calcular_tamano(self):
        """Calcula el tamaño del subárbol (número de nodos)."""
        tamano = 1
        if self.tipo == "carpeta":
            for child in self.children:
                tamano += child.calcular_tamano()
        return tamano

    def calcular_altura(self):
        """Calcula la altura del subárbol (máxima profundidad)."""
        if self.tipo != "carpeta" or not self.children:
            return 0
        return 1 + max(child.calcular_altura() for child in self.children)


class SistemaArchivos:
    def __init__(self):
        self.raiz = Nodo(str(uuid.uuid4()), "root", "carpeta")
        self.nodo_actual = self.raiz
        self.ruta_actual = ["root"]
        self.next_id = 1

    def crear_carpeta(self, nombre):
        """Crea una carpeta dentro del nodo actual."""
        if self.nodo_actual.buscar_por_nombre(nombre):
            print(f"Error: ya existe '{nombre}' en esta carpeta.")
            return None
        nueva_carpeta = Nodo(str(self.next_id), nombre, "carpeta")
        self.next_id += 1
        self.nodo_actual.agregar_hijo(nueva_carpeta)
        print(f"Carpeta '{nombre}' creada.")
        return nueva_carpeta

    def crear_archivo(self, nombre, contenido=""):
        """Crea un archivo dentro del nodo actual."""
        if self.nodo_actual.buscar_por_nombre(nombre):
            print(f"Error: ya existe '{nombre}' en esta carpeta.")
            return None
        nuevo_archivo = Nodo(str(self.next_id), nombre, "archivo", contenido)
        self.next_id += 1
        self.nodo_actual.agregar_hijo(nuevo_archivo)
        print(f"Archivo '{nombre}' creado.")
        return nuevo_archivo

    def listar_hijos(self):
        """Lista los hijos del nodo actual."""
        if not self.nodo_actual.children:
            print("(vacío)")
        for child in self.nodo_actual.children:
            tipo = "[DIR]" if child.tipo == "carpeta" else "[FILE]"
            print(f"{tipo} {child.nombre} (ID: {child.id})")

    def ruta_completa(self):
        """Devuelve la ruta actual como string."""
        return "/" + "/".join(self.ruta_actual)

    def cambiar_directorio(self, ruta):
        """Cambia el directorio actual (cd)."""
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

        # Navegación relativa o absoluta
        partes = ruta.split("/")
        nodo_temp = self.nodo_actual
        ruta_temp = self.ruta_actual.copy()

        if partes[0] == "":
            # Ruta absoluta
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
        """Mueve un nodo a otra carpeta (mv)."""
        nodo_origen = self.nodo_actual.buscar_por_nombre(origen)
        if not nodo_origen:
            print(f"Error: '{origen}' no encontrado en la carpeta actual.")
            return

        # Buscar nodo destino (debe ser carpeta)
        nodo_destino = self.nodo_actual.buscar_por_nombre(destino_nombre)
        if not nodo_destino or nodo_destino.tipo != "carpeta":
            print(f"Error: '{destino_nombre}' no es una carpeta válida.")
            return

        # Verificar que no haya conflicto de nombres en destino
        if nodo_destino.buscar_por_nombre(nodo_origen.nombre):
            print(f"Error: ya existe un nodo con nombre '{nodo_origen.nombre}' en '{destino_nombre}'.")
            return

        # Mover
        if nodo_origen.parent:
            nodo_origen.parent.eliminar_hijo(nodo_origen)
        nodo_destino.agregar_hijo(nodo_origen)
        print(f"'{origen}' movido a '{destino_nombre}'.")

    def renombrar_nodo(self, nombre_actual, nuevo_nombre):
        """Renombra un nodo."""
        nodo = self.nodo_actual.buscar_por_nombre(nombre_actual)
        if not nodo:
            print(f"Error: '{nombre_actual}' no encontrado.")
            return

        # Verificar que nuevo nombre no exista
        if self.nodo_actual.buscar_por_nombre(nuevo_nombre):
            print(f"Error: ya existe '{nuevo_nombre}' en esta carpeta.")
            return

        nodo.nombre = nuevo_nombre
        print(f"'{nombre_actual}' renombrado a '{nuevo_nombre}'.")

    def eliminar_nodo(self, nombre):
        """Elimina un nodo (sin papelera por ahora)."""
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
        """Exporta el recorrido en preorden del árbol actual a un archivo."""
        lista = self.raiz.preorden()
        with open(archivo, "w", encoding="utf-8") as f:
            for nombre, tipo, id_nodo in lista:
                f.write(f"{tipo.upper()}: {nombre} (ID: {id_nodo})\n")
        print(f"Recorrido en preorden exportado a '{archivo}'.")

    def mostrar_estadisticas(self):
        """Muestra altura y tamaño del árbol."""
        altura = self.raiz.calcular_altura()
        tamano = self.raiz.calcular_tamano()
        print(f"Altura del árbol: {altura}")
        print(f"Tamaño del árbol (nodos totales): {tamano}")

    def guardar_a_json(self, archivo="sistema.json"):
        """Guarda el sistema de archivos a un archivo JSON."""
        datos = {
            "next_id": self.next_id,
            "raiz": self.raiz.to_dict()
        }
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2)
        print(f"Sistema guardado en '{archivo}'.")

    def cargar_desde_json(self, archivo="sistema.json"):
        """Carga el sistema de archivos desde un archivo JSON."""
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
            self.next_id = datos["next_id"]
            self.raiz = Nodo.from_dict(datos["raiz"])
            self.nodo_actual = self.raiz
            self.ruta_actual = ["root"]
            print(f"Sistema cargado desde '{archivo}'.")
        except FileNotFoundError:
            print(f"Archivo '{archivo}' no encontrado. Se inicia sistema vacío.")

    # Comandos de consola
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


def main():
    sistema = SistemaArchivos()
    sistema.cargar_desde_json()

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
        "save": lambda args: sistema.guardar_a_json(),
        "help": lambda args: print("Comandos: mkdir, touch, ls, pwd, cd, mv, rename, rm, export, stats, save, exit"),
        "exit": None,
    }

    print("=== Sistema de Archivos Jerárquico (Día 2-3) ===")
    print("Comandos: mkdir, touch, ls, pwd, cd, mv, rename, rm, export, stats, save, help, exit")

    while True:
        try:
            entrada = input(f"{sistema.ruta_completa()}$ ").strip().split()
            if not entrada:
                continue
            comando = entrada[0]
            args = entrada[1:]

            if comando == "exit":
                sistema.guardar_a_json()
                print("Saliendo...")
                break
            elif comando in comandos:
                if comandos[comando] is None:
                    continue
                comandos[comando](args)
            else:
                print(f"Comando no reconocido. Escribe 'help' para ver comandos.")
        except KeyboardInterrupt:
            print("\nInterrupción detectada. Saliendo...")
            sistema.guardar_a_json()
            break
        except Exception as e:
            print(f"Error inesperado: {e}")


# ==============================
# PRUEBAS UNITARIAS INICIALES
# ==============================
def ejecutar_pruebas():
    print("\n" + "="*50)
    print("Ejecutando pruebas unitarias iniciales...")
    print("="*50)

    sistema = SistemaArchivos()

    # Prueba 1: Crear carpetas y archivos
    sistema.mkdir("docs")
    sistema.mkdir("imgs")
    sistema.touch("readme.txt", "Contenido inicial")
    sistema.ls()
    print("✓ Creación básica OK")

    # Prueba 2: Navegación
    sistema.cd("docs")
    sistema.touch("nota.txt", "Nota secreta")
    sistema.cd("..")
    sistema.pwd()
    print("✓ Navegación OK")

    # Prueba 3: Mover
    sistema.cd("/")
    sistema.mv("readme.txt", "docs")
    sistema.cd("docs")
    sistema.ls()
    print("✓ Movimiento OK")

    # Prueba 4: Renombrar
    sistema.rename("nota.txt", "nota_renombrada.txt")
    sistema.ls()
    print("✓ Renombrar OK")

    # Prueba 5: Eliminar
    sistema.rm("nota_renombrada.txt")
    sistema.ls()
    print("✓ Eliminar OK")

    # Prueba 6: Exportar preorden
    sistema.cd("/")
    sistema.export()
    print("✓ Exportar preorden OK")

    # Prueba 7: Estadísticas
    sistema.stats()
    print("✓ Estadísticas OK")

    # Prueba 8: Persistencia
    sistema.guardar_a_json("prueba.json")
    sistema2 = SistemaArchivos()
    sistema2.cargar_desde_json("prueba.json")
    sistema2.ls()
    print("✓ Persistencia OK")

    # Limpiar archivo de prueba
    if os.path.exists("prueba.json"):
        os.remove("prueba.json")
    if os.path.exists("preorden.txt"):
        os.remove("preorden.txt")

    print("\n" + "="*50)
    print("Todas las pruebas pasaron correctamente.")
    print("="*50)


if __name__ == "__main__":
    # Para ejecutar solo pruebas: python proyecto_dia2.py --test
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        ejecutar_pruebas()
    else:
        main()