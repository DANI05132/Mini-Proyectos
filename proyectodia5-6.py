import json
import uuid
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from collections import defaultdict

class TrieNode:
    """Nodo del Trie para autocompletado."""
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.node_ids = set()  # IDs de nodos que terminan aquí

class Trie:
    """Trie para búsqueda de prefijos."""
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, palabra: str, node_id: str):
        """Inserta una palabra en el Trie asociada a un ID de nodo."""
        nodo = self.root
        for char in palabra.lower():
            if char not in nodo.children:
                nodo.children[char] = TrieNode()
            nodo = nodo.children[char]
        nodo.is_end_of_word = True
        nodo.node_ids.add(node_id)
    
    def search_exact(self, palabra: str) -> Set[str]:
        """Busca una palabra exacta y devuelve los IDs asociados."""
        nodo = self.root
        for char in palabra.lower():
            if char not in nodo.children:
                return set()
            nodo = nodo.children[char]
        return nodo.node_ids if nodo.is_end_of_word else set()
    
    def search_prefix(self, prefijo: str) -> Set[str]:
        """Busca todos los IDs cuyos nombres empiezan con el prefijo."""
        nodo = self.root
        for char in prefijo.lower():
            if char not in nodo.children:
                return set()
            nodo = nodo.children[char]
        
        # Recoger todos los IDs desde este nodo hacia abajo
        ids = set()
        self._collect_ids(nodo, ids)
        return ids
    
    def _collect_ids(self, nodo: TrieNode, ids: Set[str]):
        """Recoge recursivamente todos los IDs desde un nodo del Trie."""
        if nodo.is_end_of_word:
            ids.update(nodo.node_ids)
        for child in nodo.children.values():
            self._collect_ids(child, ids)
    
    def delete(self, palabra: str, node_id: str) -> bool:
        """Elimina un ID asociado a una palabra."""
        nodo = self.root
        for char in palabra.lower():
            if char not in nodo.children:
                return False
            nodo = nodo.children[char]
        
        if nodo.is_end_of_word and node_id in nodo.node_ids:
            nodo.node_ids.remove(node_id)
            if not nodo.node_ids:
                nodo.is_end_of_word = False
            return True
        return False
    
    def update(self, viejo_nombre: str, nuevo_nombre: str, node_id: str):
        """Actualiza el nombre de un nodo en el Trie."""
        self.delete(viejo_nombre, node_id)
        self.insert(nuevo_nombre, node_id)

class Nodo:
    def __init__(self, id_nodo, nombre, tipo, contenido=None):
        self.id = id_nodo
        self.nombre = nombre
        self.tipo = tipo  # "carpeta" o "archivo"
        self.contenido = contenido  # solo para archivos
        self.children = []  # solo para carpetas
        self.parent = None  # referencia al padre

    def to_dict(self):
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
        self.historial = []
        self.version = "1.0"
        self.archivo_persistencia = "sistema.json"
        
        # ÍNDICES PARA BÚSQUEDA
        self.trie = Trie()  # Para autocompletado por prefijo
        self.indice_nombre = defaultdict(set)  # nombre -> set de IDs
        self.indice_id = {}  # id -> objeto Nodo
        
        # Inicializar índices con la raíz
        self._actualizar_indices(self.raiz)

    def _actualizar_indices(self, nodo: Nodo, eliminar: bool = False):
        """Actualiza todos los índices para un nodo (añadir o eliminar)."""
        if eliminar:
            # Eliminar de índices
            self.trie.delete(nodo.nombre, nodo.id)
            self.indice_nombre[nodo.nombre].discard(nodo.id)
            if not self.indice_nombre[nodo.nombre]:
                del self.indice_nombre[nodo.nombre]
            if nodo.id in self.indice_id:
                del self.indice_id[nodo.id]
        else:
            # Añadir a índices
            self.trie.insert(nodo.nombre, nodo.id)
            self.indice_nombre[nodo.nombre].add(nodo.id)
            self.indice_id[nodo.id] = nodo
        
        # Actualizar recursivamente para hijos
        if nodo.tipo == "carpeta":
            for child in nodo.children:
                self._actualizar_indices(child, eliminar)

    def _actualizar_indices_renombre(self, nodo: Nodo, viejo_nombre: str):
        """Actualiza índices después de renombrar un nodo."""
        # Actualizar Trie
        self.trie.update(viejo_nombre, nodo.nombre, nodo.id)
        
        # Actualizar índice de nombres
        self.indice_nombre[viejo_nombre].discard(nodo.id)
        if not self.indice_nombre[viejo_nombre]:
            del self.indice_nombre[viejo_nombre]
        self.indice_nombre[nodo.nombre].add(nodo.id)

    def buscar_exacto(self, nombre: str) -> List[Nodo]:
        """Busca nodos con nombre exacto."""
        ids = self.indice_nombre.get(nombre, set())
        return [self.indice_id[id_] for id_ in ids if id_ in self.indice_id]

    def buscar_por_id(self, id_nodo: str) -> Optional[Nodo]:
        """Busca un nodo por su ID."""
        return self.indice_id.get(id_nodo)

    def autocompletar(self, prefijo: str, limite: int = 10) -> List[str]:
        """Devuelve nombres que empiezan con el prefijo."""
        ids = self.trie.search_prefix(prefijo)
        nombres = set()
        resultados = []
        
        for id_ in ids:
            if id_ in self.indice_id:
                nombre = self.indice_id[id_].nombre
                if nombre not in nombres:
                    nombres.add(nombre)
                    resultados.append(nombre)
                    if len(resultados) >= limite:
                        break
        
        return resultados

    def buscar_por_patron(self, patron: str, tipo: str = None) -> List[Dict[str, Any]]:
        """Busca nodos cuyo nombre contenga el patrón (no solo prefijo)."""
        resultados = []
        patron_lower = patron.lower()
        
        for nombre, ids in self.indice_nombre.items():
            if patron_lower in nombre.lower():
                for id_ in ids:
                    if id_ in self.indice_id:
                        nodo = self.indice_id[id_]
                        if tipo is None or nodo.tipo == tipo:
                            resultados.append({
                                "id": nodo.id,
                                "nombre": nodo.nombre,
                                "tipo": nodo.tipo,
                                "ruta": self._obtener_ruta(nodo)
                            })
        
        return resultados

    def _obtener_ruta(self, nodo: Nodo) -> str:
        """Obtiene la ruta completa de un nodo."""
        partes = []
        actual = nodo
        while actual and actual.nombre != "root":
            partes.append(actual.nombre)
            actual = actual.parent
        partes.reverse()
        return "/" + "/".join(partes) if partes else "/root"

    def crear_carpeta(self, nombre):
        if self.nodo_actual.buscar_por_nombre(nombre):
            print(f"Error: ya existe '{nombre}' en esta carpeta.")
            return None
        
        nueva_carpeta = Nodo(str(self.next_id), nombre, "carpeta")
        self.next_id += 1
        self.nodo_actual.agregar_hijo(nueva_carpeta)
        
        # Actualizar índices
        self._actualizar_indices(nueva_carpeta)
        
        print(f"Carpeta '{nombre}' creada.")
        return nueva_carpeta

    def crear_archivo(self, nombre, contenido=""):
        if self.nodo_actual.buscar_por_nombre(nombre):
            print(f"Error: ya existe '{nombre}' en esta carpeta.")
            return None
        
        nuevo_archivo = Nodo(str(self.next_id), nombre, "archivo", contenido)
        self.next_id += 1
        self.nodo_actual.agregar_hijo(nuevo_archivo)
        
        # Actualizar índices
        self._actualizar_indices(nuevo_archivo)
        
        print(f"Archivo '{nombre}' creado.")
        return nuevo_archivo

    def eliminar_nodo(self, nombre):
        nodo = self.nodo_actual.buscar_por_nombre(nombre)
        if not nodo:
            print(f"Error: '{nombre}' no encontrado.")
            return

        if nodo.parent:
            # Actualizar índices (eliminar recursivamente)
            self._actualizar_indices(nodo, eliminar=True)
            
            # Eliminar del árbol
            nodo.parent.eliminar_hijo(nodo)
            print(f"'{nombre}' eliminado.")
        else:
            print("No se puede eliminar la raíz.")

    def renombrar_nodo(self, nombre_actual, nuevo_nombre):
        nodo = self.nodo_actual.buscar_por_nombre(nombre_actual)
        if not nodo:
            print(f"Error: '{nombre_actual}' no encontrado.")
            return

        if self.nodo_actual.buscar_por_nombre(nuevo_nombre):
            print(f"Error: ya existe '{nuevo_nombre}' en esta carpeta.")
            return

        viejo_nombre = nodo.nombre
        nodo.nombre = nuevo_nombre
        
        # Actualizar índices
        self._actualizar_indices_renombre(nodo, viejo_nombre)
        
        print(f"'{nombre_actual}' renombrado a '{nuevo_nombre}'.")

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

        # Mover en el árbol
        if nodo_origen.parent:
            nodo_origen.parent.eliminar_hijo(nodo_origen)
        nodo_destino.agregar_hijo(nodo_origen)
        
        # Índices NO necesitan actualización porque el nodo no cambia de ID/ nombre
        
        print(f"'{origen}' movido a '{destino_nombre}'.")

    def guardar_a_json(self, archivo: Optional[str] = None) -> bool:
        if archivo is None:
            archivo = self.archivo_persistencia
        
        if os.path.exists(archivo):
            self._crear_backup(archivo)
        
        datos = {
            "version": self.version,
            "fecha_guardado": datetime.now().isoformat(),
            "next_id": self.next_id,
            "raiz": self.raiz.to_dict()
        }
        
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
            
            self.historial.append({
                "accion": "guardar",
                "archivo": archivo,
                "fecha": datetime.now().isoformat(),
                "nodos_totales": self.raiz.calcular_tamano()
            })
            
            print(f"Sistema guardado exitosamente en '{archivo}' (v{self.version}).")
            return True
        except Exception as e:
            print(f"Error al guardar JSON: {e}")
            return False

    def cargar_desde_json(self, archivo: Optional[str] = None) -> bool:
        if archivo is None:
            archivo = self.archivo_persistencia
        
        if not os.path.exists(archivo):
            print(f"Archivo '{archivo}' no encontrado. Se inicia sistema vacío.")
            return False
        
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
            
            if not self._validar_estructura_json(datos):
                print("Error: El archivo JSON tiene estructura inválida.")
                return False
            
            # Reiniciar índices
            self.trie = Trie()
            self.indice_nombre = defaultdict(set)
            self.indice_id = {}
            
            # Cargar datos
            self.version = datos.get("version", "1.0")
            self.next_id = datos["next_id"]
            self.raiz = Nodo.from_dict(datos["raiz"])
            self.nodo_actual = self.raiz
            self.ruta_actual = ["root"]
            
            # Reconstruir índices desde el árbol cargado
            self._actualizar_indices(self.raiz)
            
            self.historial.append({
                "accion": "cargar",
                "archivo": archivo,
                "fecha": datetime.now().isoformat(),
                "nodos_totales": self.raiz.calcular_tamano()
            })
            
            print(f"Sistema cargado exitosamente desde '{archivo}' (v{self.version}).")
            return True
            
        except Exception as e:
            print(f"Error al cargar JSON: {e}")
            return False

    def _crear_backup(self, archivo_original: str) -> bool:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{timestamp}_{os.path.basename(archivo_original)}"
        try:
            shutil.copy2(archivo_original, backup_file)
            print(f"Backup creado: {backup_file}")
            return True
        except Exception as e:
            print(f"Error al crear backup: {e}")
            return False

    def _validar_estructura_json(self, datos: Dict[str, Any]) -> bool:
        required_keys = ["version", "next_id", "raiz"]
        if not all(key in datos for key in required_keys):
            return False
        
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
        
        return validar_nodo(datos["raiz"])

    def search(self, termino: str, tipo: str = None, exacto: bool = False):
        """Busca nodos por término."""
        if exacto:
            resultados = self.buscar_exacto(termino)
        else:
            resultados_dict = self.buscar_por_patron(termino, tipo)
            resultados = [self.buscar_por_id(r["id"]) for r in resultados_dict]
        
        if not resultados:
            print(f"No se encontraron resultados para '{termino}'")
            return
        
        print(f"\nResultados de búsqueda para '{termino}':")
        for i, nodo in enumerate(resultados, 1):
            ruta = self._obtener_ruta(nodo)
            tipo_str = "DIR" if nodo.tipo == "carpeta" else "FILE"
            print(f"{i:2}. [{tipo_str}] {nodo.nombre} (ID: {nodo.id})")
            print(f"    Ruta: {ruta}")
            if nodo.tipo == "archivo" and nodo.contenido:
                contenido_preview = nodo.contenido[:50] + "..." if len(nodo.contenido) > 50 else nodo.contenido
                print(f"    Contenido: {contenido_preview}")

    def autocomplete(self, prefijo: str, limite: int = 5):
        """Muestra sugerencias de autocompletado."""
        sugerencias = self.autocompletar(prefijo, limite)
        
        if not sugerencias:
            print(f"No hay sugerencias para '{prefijo}'")
            return
        
        print(f"\nSugerencias para '{prefijo}':")
        for i, nombre in enumerate(sugerencias, 1):
            print(f"  {i}. {nombre}")

    def find(self, nombre: str):
        """Busca exactamente por nombre."""
        resultados = self.buscar_exacto(nombre)
        
        if not resultados:
            print(f"No se encontró ningún nodo con nombre '{nombre}'")
            return
        
        print(f"\nNodos con nombre '{nombre}':")
        for i, nodo in enumerate(resultados, 1):
            ruta = self._obtener_ruta(nodo)
            tipo_str = "DIR" if nodo.tipo == "carpeta" else "FILE"
            print(f"{i:2}. [{tipo_str}] ID: {nodo.id}")
            print(f"    Ruta: {ruta}")

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
        print(f"Tamaño del índice de nombres: {len(self.indice_nombre)}")
        print(f"Tamaño del Trie: {self._contar_nodos_trie()} nodos")

    def _contar_nodos_trie(self) -> int:
        """Cuenta los nodos en el Trie (para estadísticas)."""
        def contar(nodo):
            total = 1
            for child in nodo.children.values():
                total += contar(child)
            return total
        return contar(self.root)

    def mostrar_historial(self, limite: int = 5):
        if not self.historial:
            print("Historial vacío.")
            return
        
        print(f"\n=== Últimas {min(limite, len(self.historial))} operaciones ===")
        for i, registro in enumerate(reversed(self.historial[-limite:])):
            print(f"{i+1}. {registro['accion'].upper()} - {registro['fecha']}")
            print(f"   Archivo: {registro['archivo']}")
            print(f"   Nodos totales: {registro.get('nodos_totales', 'N/A')}")
            print()

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

def main():
    sistema = SistemaArchivos()
    
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
        
        # NUEVOS COMANDOS DE BÚSQUEDA
        "search": lambda args: (
            sistema.search(args[0]) if args else print("Uso: search <término> [--exact] [--type dir/file]")
        ),
        "autocomplete": lambda args: (
            sistema.autocomplete(args[0], int(args[1]) if len(args) > 1 else 5) 
            if args else print("Uso: autocomplete <prefijo> [limite]")
        ),
        "find": lambda args: sistema.find(args[0]) if args else print("Uso: find <nombre_exacto>"),
        
        "save": lambda args: sistema.save(args[0] if args else None),
        "load": lambda args: sistema.load(args[0] if args else None),
        "help": lambda args: print(
            "Comandos básicos:\n"
            "  mkdir, touch, ls, pwd, cd, mv, rename, rm, export, stats, history\n"
            "Búsqueda:\n"
            "  search <término>        - Busca nodos que contengan el término\n"
            "  autocomplete <prefijo>  - Muestra sugerencias de autocompletado\n"
            "  find <nombre_exacto>    - Busca nodos con nombre exacto\n"
            "Persistencia:\n"
            "  save [archivo], load [archivo]\n"
            "  help, exit"
        ),
        "exit": None,
    }

    print("\n" + "="*70)
    print("SISTEMA DE ARCHIVOS JERÁRQUICO - DÍAS 5-6: BÚSQUEDA Y TRIE")
    print("="*70)
    print("Escribe 'help' para ver comandos disponibles")

    while True:
        try:
            entrada = input(f"{sistema.ruta_completa()}$ ").strip()
            if not entrada:
                continue
            
            # Manejo especial para búsqueda con opciones
            if entrada.startswith("search ") and ("--exact" in entrada or "--type" in entrada):
                partes = entrada.split()
                termino = partes[1]
                exacto = "--exact" in partes
                tipo = None
                if "--type" in partes:
                    idx = partes.index("--type")
                    if idx + 1 < len(partes):
                        tipo = partes[idx + 1]
                        if tipo not in ["dir", "file"]:
                            print("Error: tipo debe ser 'dir' o 'file'")
                            continue
                        tipo = "carpeta" if tipo == "dir" else "archivo"
                
                sistema.search(termino, tipo, exacto)
                continue
            
            # Comandos normales
            partes = entrada.split()
            comando = partes[0]
            args = partes[1:]

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

def ejecutar_pruebas_busqueda():
    print("\n" + "="*70)
    print("PRUEBAS DE BÚSQUEDA Y AUTCOMPLETADO - DÍAS 5-6")
    print("="*70)
    
    # Limpiar archivos anteriores
    for f in ["test_busqueda.json", "preorden.txt"] + [f for f in os.listdir() if f.startswith("backup_")]:
        if os.path.exists(f):
            os.remove(f)
    
    sistema = SistemaArchivos()
    sistema.archivo_persistencia = "test_busqueda.json"
    
    print("1. Creando estructura de prueba...")
    sistema.mkdir("documentos")
    sistema.mkdir("descargas")
    sistema.mkdir("documentos_old")
    sistema.cd("documentos")
    sistema.touch("tarea1.txt", "Contenido de tarea 1")
    sistema.touch("tarea2.doc", "Contenido de tarea 2")
    sistema.touch("presentacion.ppt", "Diapositivas")
    sistema.mkdir("tareas_pendientes")
    sistema.cd("tareas_pendientes")
    sistema.touch("tarea_urgente.txt", "¡Hacer pronto!")
    sistema.cd("/")
    sistema.touch("documento_final.pdf", "PDF importante")
    
    print("\n2. Probando búsqueda exacta...")
    print("   Buscando 'tarea1.txt':")
    sistema.search("tarea1.txt", exacto=True)
    
    print("\n3. Probando búsqueda por patrón...")
    print("   Buscando 'tarea':")
    sistema.search("tarea")
    
    print("\n4. Probando autocompletado...")
    print("   Autocompletar 'doc':")
    sistema.autocomplete("doc")
    
    print("\n5. Probando 'find' (búsqueda exacta por nombre)...")
    print("   find 'presentacion.ppt':")
    sistema.find("presentacion.ppt")
    
    print("\n6. Probando búsqueda con tipo...")
    print("   search 'ta' --type file:")
    sistema.search("ta", tipo="archivo")
    
    print("\n7. Probando índices después de renombrar...")
    sistema.cd("documentos")
    sistema.rename("tarea1.txt", "tarea1_renombrado.txt")
    print("   Buscando 'tarea1_renombrado.txt':")
    sistema.search("tarea1_renombrado.txt", exacto=True)
    print("   Buscando 'tarea1.txt' (debería no encontrar):")
    sistema.search("tarea1.txt", exacto=True)
    
    print("\n8. Probando índices después de eliminar...")
    sistema.rm("tarea2.doc")
    print("   Buscando 'tarea2.doc' (debería no encontrar):")
    sistema.search("tarea2.doc", exacto=True)
    
    print("\n9. Estadísticas del sistema...")
    sistema.stats()
    
    print("\n10. Guardando y cargando con índices...")
    sistema.save()
    
    sistema2 = SistemaArchivos()
    sistema2.archivo_persistencia = "test_busqueda.json"
    sistema2.load()
    
    print("   Buscando 'presentacion' en sistema cargado:")
    sistema2.search("presentacion")
    
    # Limpiar
    for f in ["test_busqueda.json", "preorden.txt"] + [f for f in os.listdir() if f.startswith("backup_")]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n" + "="*70)
    print("PRUEBAS DE BÚSQUEDA COMPLETADAS EXITOSAMENTE")
    print("="*70)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test-busqueda":
        ejecutar_pruebas_busqueda()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Importar pruebas anteriores si existen
        try:
            from dia4 import ejecutar_pruebas_persistencia
            ejecutar_pruebas_persistencia()
        except ImportError:
            pass
        ejecutar_pruebas_busqueda()
    else:
        main()