import json
import uuid
import os
import shutil
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Tuple
from collections import defaultdict, deque
from enum import Enum
class Colors:
    """Códigos ANSI para colores en terminal."""
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class NodeType(Enum):
    FOLDER = "carpeta"
    FILE = "archivo"

class ErrorType(Enum):
    NOT_FOUND = "no encontrado"
    ALREADY_EXISTS = "ya existe"
    INVALID_TYPE = "tipo inválido"
    PERMISSION_DENIED = "permiso denegado"
    INVALID_PATH = "ruta inválida"
    TRASH_EMPTY = "papelera vacía"


class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.node_ids = set()

class Trie:
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, palabra: str, node_id: str):
        nodo = self.root
        for char in palabra.lower():
            if char not in nodo.children:
                nodo.children[char] = TrieNode()
            nodo = nodo.children[char]
        nodo.is_end_of_word = True
        nodo.node_ids.add(node_id)
    
    def search_exact(self, palabra: str) -> Set[str]:
        nodo = self.root
        for char in palabra.lower():
            if char not in nodo.children:
                return set()
            nodo = nodo.children[char]
        return nodo.node_ids if nodo.is_end_of_word else set()
    
    def search_prefix(self, prefijo: str) -> Set[str]:
        nodo = self.root
        for char in prefijo.lower():
            if char not in nodo.children:
                return set()
            nodo = nodo.children[char]
        
        ids = set()
        self._collect_ids(nodo, ids)
        return ids
    
    def _collect_ids(self, nodo: TrieNode, ids: Set[str]):
        if nodo.is_end_of_word:
            ids.update(nodo.node_ids)
        for child in nodo.children.values():
            self._collect_ids(child, ids)
    
    def delete(self, palabra: str, node_id: str) -> bool:
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
        self.delete(viejo_nombre, node_id)
        self.insert(nuevo_nombre, node_id)

class TrashItem:
    """Elemento en la papelera."""
    def __init__(self, nodo, ruta_original, fecha_eliminacion):
        self.nodo = nodo
        self.ruta_original = ruta_original
        self.fecha_eliminacion = fecha_eliminacion
        self.id = str(uuid.uuid4())
    
    def to_dict(self):
        return {
            "id": self.id,
            "nodo": self.nodo.to_dict(),
            "ruta_original": self.ruta_original,
            "fecha_eliminacion": self.fecha_eliminacion
        }
    
    @staticmethod
    def from_dict(data):
        nodo = Nodo.from_dict(data["nodo"])
        item = TrashItem(nodo, data["ruta_original"], data["fecha_eliminacion"])
        item.id = data["id"]
        return item

class TrashBin:
    """Papelera temporal para recuperación de archivos."""
    def __init__(self, capacidad_maxima=100):
        self.items = []
        self.capacidad_maxima = capacidad_maxima
        self.archivo_trash = "trash.json"
    
    def agregar(self, nodo: 'Nodo', ruta_original: str):
        """Agrega un nodo a la papelera."""
        if len(self.items) >= self.capacidad_maxima:
            # Eliminar el más antiguo
            self.items.pop(0)
        
        item = TrashItem(nodo, ruta_original, datetime.now().isoformat())
        self.items.append(item)
        return item
    
    def listar(self) -> List[Dict[str, Any]]:
        """Lista los elementos en la papelera."""
        resultado = []
        for i, item in enumerate(self.items):
            resultado.append({
                "indice": i,
                "nombre": item.nodo.nombre,
                "tipo": item.nodo.tipo,
                "ruta_original": item.ruta_original,
                "fecha": item.fecha_eliminacion,
                "id": item.id
            })
        return resultado
    
    def restaurar(self, indice: int) -> Optional[Tuple['Nodo', str]]:
        """Restaura un elemento de la papelera."""
        if 0 <= indice < len(self.items):
            item = self.items.pop(indice)
            return item.nodo, item.ruta_original
        return None
    
    def vaciar(self):
        """Vacía completamente la papelera."""
        self.items.clear()
    
    def guardar(self):
        """Guarda la papelera en disco."""
        datos = {
            "capacidad_maxima": self.capacidad_maxima,
            "items": [item.to_dict() for item in self.items]
        }
        try:
            with open(self.archivo_trash, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2)
        except Exception:
            pass  # Silencioso, no crítico
    
    def cargar(self):
        """Carga la papelera desde disco."""
        try:
            if os.path.exists(self.archivo_trash):
                with open(self.archivo_trash, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                self.capacidad_maxima = datos.get("capacidad_maxima", 100)
                self.items = [TrashItem.from_dict(item) for item in datos.get("items", [])]
        except Exception:
            self.items = []  # Reiniciar si hay error


class Nodo:
    def __init__(self, id_nodo, nombre, tipo, contenido=None):
        self.id = id_nodo
        self.nombre = nombre
        self.tipo = tipo
        self.contenido = contenido
        self.children = []
        self.parent = None
    
    def to_dict(self):
        nodo_dict = {
            "id": self.id,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "contenido": self.contenido,
        }
        if self.tipo == NodeType.FOLDER.value:
            nodo_dict["children"] = [child.to_dict() for child in self.children]
        return nodo_dict
    
    @staticmethod
    def from_dict(data, parent=None):
        nodo = Nodo(data["id"], data["nombre"], data["tipo"], data["contenido"])
        nodo.parent = parent
        if nodo.tipo == NodeType.FOLDER.value:
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
            if child.tipo == NodeType.FOLDER.value:
                encontrado = child.buscar_por_id(id_nodo)
                if encontrado:
                    return encontrado
        return None
    
    def preorden(self, lista=None):
        if lista is None:
            lista = []
        lista.append((self.nombre, self.tipo, self.id))
        if self.tipo == NodeType.FOLDER.value:
            for child in self.children:
                child.preorden(lista)
        return lista
    
    def calcular_tamano(self):
        tamano = 1
        if self.tipo == NodeType.FOLDER.value:
            for child in self.children:
                tamano += child.calcular_tamano()
        return tamano
    
    def calcular_altura(self):
        if self.tipo != NodeType.FOLDER.value or not self.children:
            return 0
        return 1 + max(child.calcular_altura() for child in self.children)

class SistemaArchivos:
    def __init__(self):
        self.raiz = Nodo(str(uuid.uuid4()), "root", NodeType.FOLDER.value)
        self.nodo_actual = self.raiz
        self.ruta_actual = ["root"]
        self.next_id = 1
        self.historial = []
        self.version = "1.0"
        self.archivo_persistencia = "sistema.json"
        self.log_activo = False
        self.log_file = "sistema.log"
        
        # Índices
        self.trie = Trie()
        self.indice_nombre = defaultdict(set)
        self.indice_id = {}
        
        # Papelera
        self.papelera = TrashBin()
        self.papelera.cargar()
        
        # Inicializar
        self._actualizar_indices(self.raiz)
    
    class SistemaError(Exception):
        """Excepción personalizada para errores del sistema."""
        def __init__(self, tipo: ErrorType, detalle: str = ""):
            self.tipo = tipo
            self.detalle = detalle
            super().__init__(f"{tipo.value}: {detalle}")
    
    def _manejar_error(self, error: Exception, operacion: str):
        """Registra y muestra errores de forma consistente."""
        if isinstance(error, self.SistemaError):
            mensaje = f"{Colors.RED}Error: {error}{Colors.RESET}"
        else:
            mensaje = f"{Colors.RED}Error inesperado en {operacion}: {error}{Colors.RESET}"
        
        print(mensaje)
        
        if self.log_activo:
            self._log(f"ERROR en {operacion}: {error}")
    
    def _log(self, mensaje: str):
        """Registra mensajes en el log si está activo."""
        if self.log_activo:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {mensaje}\n")
            except Exception:
                pass
    
    def _actualizar_indices(self, nodo: Nodo, eliminar: bool = False):
        if eliminar:
            self.trie.delete(nodo.nombre, nodo.id)
            self.indice_nombre[nodo.nombre].discard(nodo.id)
            if not self.indice_nombre[nodo.nombre]:
                del self.indice_nombre[nodo.nombre]
            if nodo.id in self.indice_id:
                del self.indice_id[nodo.id]
        else:
            self.trie.insert(nodo.nombre, nodo.id)
            self.indice_nombre[nodo.nombre].add(nodo.id)
            self.indice_id[nodo.id] = nodo
        
        if nodo.tipo == NodeType.FOLDER.value:
            for child in nodo.children:
                self._actualizar_indices(child, eliminar)
    
    def _actualizar_indices_renombre(self, nodo: Nodo, viejo_nombre: str):
        self.trie.update(viejo_nombre, nodo.nombre, nodo.id)
        self.indice_nombre[viejo_nombre].discard(nodo.id)
        if not self.indice_nombre[viejo_nombre]:
            del self.indice_nombre[viejo_nombre]
        self.indice_nombre[nodo.nombre].add(nodo.id)
    
    def crear_carpeta(self, nombre: str):
        """Crea una nueva carpeta."""
        try:
            if not nombre or '/' in nombre:
                raise self.SistemaError(ErrorType.INVALID_PATH, "Nombre inválido")
            
            if self.nodo_actual.buscar_por_nombre(nombre):
                raise self.SistemaError(ErrorType.ALREADY_EXISTS, f"'{nombre}'")
            
            nueva_carpeta = Nodo(str(self.next_id), nombre, NodeType.FOLDER.value)
            self.next_id += 1
            self.nodo_actual.agregar_hijo(nueva_carpeta)
            self._actualizar_indices(nueva_carpeta)
            
            self._log(f"Carpeta creada: {nombre}")
            print(f"{Colors.GREEN}Carpeta '{nombre}' creada exitosamente.{Colors.RESET}")
            return nueva_carpeta
            
        except self.SistemaError as e:
            self._manejar_error(e, "crear_carpeta")
            return None
        except Exception as e:
            self._manejar_error(e, "crear_carpeta")
            return None
    
    def crear_archivo(self, nombre: str, contenido: str = ""):
        """Crea un nuevo archivo."""
        try:
            if not nombre or '/' in nombre:
                raise self.SistemaError(ErrorType.INVALID_PATH, "Nombre inválido")
            
            if self.nodo_actual.buscar_por_nombre(nombre):
                raise self.SistemaError(ErrorType.ALREADY_EXISTS, f"'{nombre}'")
            
            nuevo_archivo = Nodo(str(self.next_id), nombre, NodeType.FILE.value, contenido)
            self.next_id += 1
            self.nodo_actual.agregar_hijo(nuevo_archivo)
            self._actualizar_indices(nuevo_archivo)
            
            self._log(f"Archivo creado: {nombre}")
            print(f"{Colors.GREEN}Archivo '{nombre}' creado exitosamente.{Colors.RESET}")
            return nuevo_archivo
            
        except self.SistemaError as e:
            self._manejar_error(e, "crear_archivo")
            return None
        except Exception as e:
            self._manejar_error(e, "crear_archivo")
            return None
    
    def eliminar_nodo(self, nombre: str, mover_a_papelera: bool = True):
        """Elimina un nodo, opcionalmente moviéndolo a la papelera."""
        try:
            nodo = self.nodo_actual.buscar_por_nombre(nombre)
            if not nodo:
                raise self.SistemaError(ErrorType.NOT_FOUND, f"'{nombre}'")
            
            if not nodo.parent:
                raise self.SistemaError(ErrorType.PERMISSION_DENIED, "No se puede eliminar la raíz")
            
            if mover_a_papelera:
                # Mover a papelera
                ruta_original = self._obtener_ruta(nodo)
                self.papelera.agregar(nodo, ruta_original)
                self.papelera.guardar()
                mensaje = f"'{nombre}' movido a la papelera"
            else:
                # Eliminar permanentemente
                self._actualizar_indices(nodo, eliminar=True)
                mensaje = f"'{nombre}' eliminado permanentemente"
            
            # Eliminar del árbol
            nodo.parent.eliminar_hijo(nodo)
            
            self._log(f"Nodo eliminado: {nombre}")
            print(f"{Colors.YELLOW}{mensaje}.{Colors.RESET}")
            return True
            
        except self.SistemaError as e:
            self._manejar_error(e, "eliminar_nodo")
            return False
        except Exception as e:
            self._manejar_error(e, "eliminar_nodo")
            return False
    
    def renombrar_nodo(self, nombre_actual: str, nuevo_nombre: str):
        """Renombra un nodo."""
        try:
            if not nuevo_nombre or '/' in nuevo_nombre:
                raise self.SistemaError(ErrorType.INVALID_PATH, "Nombre inválido")
            
            nodo = self.nodo_actual.buscar_por_nombre(nombre_actual)
            if not nodo:
                raise self.SistemaError(ErrorType.NOT_FOUND, f"'{nombre_actual}'")
            
            if self.nodo_actual.buscar_por_nombre(nuevo_nombre):
                raise self.SistemaError(ErrorType.ALREADY_EXISTS, f"'{nuevo_nombre}'")
            
            viejo_nombre = nodo.nombre
            nodo.nombre = nuevo_nombre
            self._actualizar_indices_renombre(nodo, viejo_nombre)
            
            self._log(f"Nodo renombrado: {viejo_nombre} -> {nuevo_nombre}")
            print(f"{Colors.GREEN}'{nombre_actual}' renombrado a '{nuevo_nombre}'.{Colors.RESET}")
            return True
            
        except self.SistemaError as e:
            self._manejar_error(e, "renombrar_nodo")
            return False
        except Exception as e:
            self._manejar_error(e, "renombrar_nodo")
            return False
    
    def mover_nodo(self, origen: str, destino_nombre: str):
        """Mueve un nodo a otra carpeta."""
        try:
            nodo_origen = self.nodo_actual.buscar_por_nombre(origen)
            if not nodo_origen:
                raise self.SistemaError(ErrorType.NOT_FOUND, f"'{origen}'")
            
            nodo_destino = self.nodo_actual.buscar_por_nombre(destino_nombre)
            if not nodo_destino or nodo_destino.tipo != NodeType.FOLDER.value:
                raise self.SistemaError(ErrorType.INVALID_TYPE, f"'{destino_nombre}' no es carpeta")
            
            if nodo_destino.buscar_por_nombre(nodo_origen.nombre):
                raise self.SistemaError(ErrorType.ALREADY_EXISTS, 
                                      f"'{nodo_origen.nombre}' en '{destino_nombre}'")
            
            if nodo_origen.parent:
                nodo_origen.parent.eliminar_hijo(nodo_origen)
            nodo_destino.agregar_hijo(nodo_origen)
            
            self._log(f"Nodo movido: {origen} -> {destino_nombre}")
            print(f"{Colors.GREEN}'{origen}' movido a '{destino_nombre}'.{Colors.RESET}")
            return True
            
        except self.SistemaError as e:
            self._manejar_error(e, "mover_nodo")
            return False
        except Exception as e:
            self._manejar_error(e, "mover_nodo")
            return False
    
    def mostrar_papelera(self):
        """Muestra el contenido de la papelera."""
        items = self.papelera.listar()
        if not items:
            print(f"{Colors.YELLOW}La papelera está vacía.{Colors.RESET}")
            return
        
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}PAPELERA ({len(items)} elementos):{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        
        for item in items:
            tipo = "[DIR]" if item["tipo"] == NodeType.FOLDER.value else "[FILE]"
            color = Colors.BLUE if item["tipo"] == NodeType.FOLDER.value else Colors.WHITE
            print(f"{Colors.YELLOW}{item['indice']:3}.{Colors.RESET} {color}{tipo} {item['nombre']}{Colors.RESET}")
            print(f"     Ruta original: {item['ruta_original']}")
            print(f"     Fecha eliminación: {item['fecha']}")
            print()
    
    def restaurar_de_papelera(self, indice: int):
        """Restaura un elemento de la papelera."""
        try:
            resultado = self.papelera.restaurar(indice)
            if not resultado:
                raise self.SistemaError(ErrorType.NOT_FOUND, f"Índice {indice} en papelera")
            
            nodo, ruta_original = resultado
            
            # Reconstruir ruta y encontrar carpeta destino
            partes = ruta_original.split("/")[1:-1]  # Excluir root y el nombre del nodo
            destino = self.raiz
            
            for parte in partes:
                if parte:  # Ignorar strings vacíos
                    encontrado = destino.buscar_por_nombre(parte)
                    if not encontrado or encontrado.tipo != NodeType.FOLDER.value:
                        # Si la carpeta ya no existe, restaurar en la raíz
                        print(f"{Colors.YELLOW}Advertencia: Carpeta original no encontrada. Restaurando en /root{Colors.RESET}")
                        destino = self.raiz
                        break
                    destino = encontrado
            
            # Verificar que no haya conflicto de nombres
            if destino.buscar_por_nombre(nodo.nombre):
                nuevo_nombre = f"{nodo.nombre}_restaurado"
                print(f"{Colors.YELLOW}Advertencia: Ya existe '{nodo.nombre}'. Renombrando a '{nuevo_nombre}'{Colors.RESET}")
                nodo.nombre = nuevo_nombre
            
            # Restaurar
            destino.agregar_hijo(nodo)
            self._actualizar_indices(nodo)
            self.papelera.guardar()
            
            self._log(f"Restaurado de papelera: {nodo.nombre}")
            print(f"{Colors.GREEN}'{nodo.nombre}' restaurado exitosamente.{Colors.RESET}")
            return True
            
        except self.SistemaError as e:
            self._manejar_error(e, "restaurar_de_papelera")
            return False
        except Exception as e:
            self._manejar_error(e, "restaurar_de_papelera")
            return False
    
    def vaciar_papelera(self):
        """Vacía completamente la papelera."""
        try:
            if not self.papelera.items:
                raise self.SistemaError(ErrorType.TRASH_EMPTY, "")
            
            cantidad = len(self.papelera.items)
            self.papelera.vaciar()
            self.papelera.guardar()
            
            self._log(f"Papelera vaciada ({cantidad} elementos)")
            print(f"{Colors.YELLOW}Papelera vaciada ({cantidad} elementos eliminados permanentemente).{Colors.RESET}")
            return True
            
        except self.SistemaError as e:
            self._manejar_error(e, "vaciar_papelera")
            return False
        except Exception as e:
            self._manejar_error(e, "vaciar_papelera")
            return False
    

    def cambiar_directorio(self, ruta: str):
        """Cambia el directorio actual."""
        try:
            if ruta == "/":
                self.nodo_actual = self.raiz
                self.ruta_actual = ["root"]
                print(f"{Colors.BLUE}Ruta cambiada a /root{Colors.RESET}")
                return True
            
            if ruta == "..":
                if self.nodo_actual.parent:
                    self.nodo_actual = self.nodo_actual.parent
                    self.ruta_actual.pop()
                    print(f"{Colors.BLUE}Ruta cambiada a directorio padre.{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}Ya estás en la raíz.{Colors.RESET}")
                return True
            
            # Navegación relativa/absoluta
            partes = ruta.split("/")
            nodo_temp = self.nodo_actual
            ruta_temp = self.ruta_actual.copy()
            
            if partes[0] == "":
                nodo_temp = self.raiz
                ruta_temp = ["root"]
                partes = partes[1:]
            
            for parte in partes:
                if parte == "." or parte == "":
                    continue
                
                encontrado = nodo_temp.buscar_por_nombre(parte)
                if not encontrado:
                    raise self.SistemaError(ErrorType.NOT_FOUND, f"'{parte}'")
                
                if encontrado.tipo != NodeType.FOLDER.value:
                    raise self.SistemaError(ErrorType.INVALID_TYPE, f"'{parte}' no es carpeta")
                
                nodo_temp = encontrado
                ruta_temp.append(parte)
            
            self.nodo_actual = nodo_temp
            self.ruta_actual = ruta_temp
            print(f"{Colors.BLUE}Ruta cambiada a {self.ruta_completa()}{Colors.RESET}")
            return True
            
        except self.SistemaError as e:
            self._manejar_error(e, "cambiar_directorio")
            return False
        except Exception as e:
            self._manejar_error(e, "cambiar_directorio")
            return False
    
   
    def buscar_exacto(self, nombre: str) -> List[Nodo]:
        ids = self.indice_nombre.get(nombre, set())
        return [self.indice_id[id_] for id_ in ids if id_ in self.indice_id]
    
    def buscar_por_id(self, id_nodo: str) -> Optional[Nodo]:
        return self.indice_id.get(id_nodo)
    
    def autocompletar(self, prefijo: str, limite: int = 10) -> List[str]:
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
        partes = []
        actual = nodo
        while actual and actual.nombre != "root":
            partes.append(actual.nombre)
            actual = actual.parent
        partes.reverse()
        return "/" + "/".join(partes) if partes else "/root"
    
   
    def listar_hijos(self, detallado: bool = False):
        """Lista los hijos del directorio actual."""
        if not self.nodo_actual.children:
            print(f"{Colors.YELLOW}(vacío){Colors.RESET}")
            return
        
        for child in self.nodo_actual.children:
            if child.tipo == NodeType.FOLDER.value:
                icono = "📁"
                color = Colors.BLUE
            else:
                icono = "📄"
                color = Colors.WHITE
            
            if detallado:
                tamaño = child.calcular_tamano() if child.tipo == NodeType.FOLDER.value else "1"
                print(f"{color}{icono} {child.nombre:<30} {child.tipo:<10} ID: {child.id:<8} Tamaño: {tamaño}{Colors.RESET}")
            else:
                print(f"{color}{icono} {child.nombre}{Colors.RESET}")
    
    def mostrar_arbol(self, nodo: Optional[Nodo] = None, prefijo: str = "", es_ultimo: bool = True):
        """Muestra el árbol de directorios en formato árbol."""
        if nodo is None:
            nodo = self.nodo_actual
        
        # Determinar prefijo visual
        connector = "└── " if es_ultimo else "├── "
        
        # Color según tipo
        if nodo == self.nodo_actual:
            color = Colors.GREEN + Colors.BOLD
        elif nodo.tipo == NodeType.FOLDER.value:
            color = Colors.BLUE
        else:
            color = Colors.WHITE
        
        # Icono según tipo
        icono = "📁" if nodo.tipo == NodeType.FOLDER.value else "📄"
        
        print(f"{prefijo}{connector}{color}{icono} {nodo.nombre}{Colors.RESET}")
        
        # Recursión para hijos
        if nodo.tipo == NodeType.FOLDER.value:
            extension = "    " if es_ultimo else "│   "
            nuevo_prefijo = prefijo + extension
            
            for i, child in enumerate(nodo.children):
                es_ultimo_hijo = (i == len(nodo.children) - 1)
                self.mostrar_arbol(child, nuevo_prefijo, es_ultimo_hijo)
    
    def ruta_completa(self):
        return "/" + "/".join(self.ruta_actual)

    def exportar_preorden(self, archivo: str = "preorden.txt"):
        try:
            lista = self.raiz.preorden()
            with open(archivo, "w", encoding="utf-8") as f:
                for nombre, tipo, id_nodo in lista:
                    f.write(f"{tipo.upper()}: {nombre} (ID: {id_nodo})\n")
            
            self._log(f"Exportado preorden a {archivo}")
            print(f"{Colors.GREEN}Recorrido en preorden exportado a '{archivo}'.{Colors.RESET}")
            return True
        except Exception as e:
            self._manejar_error(e, "exportar_preorden")
            return False
    
    def mostrar_estadisticas(self):
        altura = self.raiz.calcular_altura()
        tamano = self.raiz.calcular_tamano()
        carpetas = sum(1 for id_ in self.indice_id.values() if id_.tipo == NodeType.FOLDER.value)
        archivos = sum(1 for id_ in self.indice_id.values() if id_.tipo == NodeType.FILE.value)
        
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}ESTADÍSTICAS DEL SISTEMA:{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.WHITE}Altura del árbol: {Colors.GREEN}{altura}{Colors.RESET}")
        print(f"{Colors.WHITE}Tamaño total (nodos): {Colors.GREEN}{tamano}{Colors.RESET}")
        print(f"{Colors.WHITE}Carpetas: {Colors.BLUE}{carpetas}{Colors.RESET}")
        print(f"{Colors.WHITE}Archivos: {Colors.WHITE}{archivos}{Colors.RESET}")
        print(f"{Colors.WHITE}Elementos en papelera: {Colors.YELLOW}{len(self.papelera.items)}{Colors.RESET}")
        print(f"{Colors.WHITE}Tamaño del índice: {Colors.MAGENTA}{len(self.indice_nombre)} nombres únicos{Colors.RESET}")
        print(f"{Colors.WHITE}Versión del sistema: {Colors.CYAN}{self.version}{Colors.RESET}")
    
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
            
            # Guardar papelera también
            self.papelera.guardar()
            
            self.historial.append({
                "accion": "guardar",
                "archivo": archivo,
                "fecha": datetime.now().isoformat(),
                "nodos_totales": self.raiz.calcular_tamano()
            })
            
            self._log(f"Sistema guardado en {archivo}")
            print(f"{Colors.GREEN}Sistema guardado exitosamente en '{archivo}'.{Colors.RESET}")
            return True
        except Exception as e:
            self._manejar_error(e, "guardar_a_json")
            return False
    
    def cargar_desde_json(self, archivo: Optional[str] = None) -> bool:
        if archivo is None:
            archivo = self.archivo_persistencia
        
        if not os.path.exists(archivo):
            print(f"{Colors.YELLOW}Archivo '{archivo}' no encontrado. Se inicia sistema vacío.{Colors.RESET}")
            return False
        
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
            
            if not self._validar_estructura_json(datos):
                print(f"{Colors.RED}Error: El archivo JSON tiene estructura inválida.{Colors.RESET}")
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
            
            # Reconstruir índices
            self._actualizar_indices(self.raiz)
            
            # Cargar papelera
            self.papelera.cargar()
            
            self.historial.append({
                "accion": "cargar",
                "archivo": archivo,
                "fecha": datetime.now().isoformat(),
                "nodos_totales": self.raiz.calcular_tamano()
            })
            
            self._log(f"Sistema cargado desde {archivo}")
            print(f"{Colors.GREEN}Sistema cargado exitosamente desde '{archivo}'.{Colors.RESET}")
            return True
            
        except Exception as e:
            self._manejar_error(e, "cargar_desde_json")
            return False
    
    def _crear_backup(self, archivo_original: str) -> bool:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{timestamp}_{os.path.basename(archivo_original)}"
        try:
            shutil.copy2(archivo_original, backup_file)
            print(f"{Colors.YELLOW}Backup creado: {backup_file}{Colors.RESET}")
            return True
        except Exception as e:
            print(f"{Colors.RED}Error al crear backup: {e}{Colors.RESET}")
            return False
    
    def _validar_estructura_json(self, datos: Dict[str, Any]) -> bool:
        required_keys = ["version", "next_id", "raiz"]
        if not all(key in datos for key in required_keys):
            return False
        
        def validar_nodo(nodo_dict: Dict[str, Any]) -> bool:
            if not all(k in nodo_dict for k in ["id", "nombre", "tipo"]):
                return False
            if nodo_dict["tipo"] not in [NodeType.FOLDER.value, NodeType.FILE.value]:
                return False
            if nodo_dict["tipo"] == NodeType.FOLDER.value:
                if "children" not in nodo_dict:
                    return False
                for child in nodo_dict["children"]:
                    if not validar_nodo(child):
                        return False
            return True
        
        return validar_nodo(datos["raiz"])
    
    def toggle_log(self, activar: Optional[bool] = None):
        """Activa o desactiva el log."""
        if activar is None:
            activar = not self.log_activo
        
        self.log_activo = activar
        estado = "activado" if activar else "desactivado"
        color = Colors.GREEN if activar else Colors.YELLOW
        print(f"{color}Log {estado}.{Colors.RESET}")
    
   
    def mostrar_ayuda(self, comando_especifico: str = None):
        """Muestra ayuda general o específica de un comando."""
        ayuda_general = {
            "mkdir": "mkdir <nombre> - Crea una nueva carpeta",
            "touch": "touch <nombre> [contenido] - Crea un nuevo archivo",
            "ls": "ls [-l] - Lista el contenido del directorio (-l para detalles)",
            "pwd": "pwd - Muestra la ruta actual completa",
            "cd": "cd <ruta> - Cambia de directorio (.. para subir, / para raíz)",
            "mv": "mv <origen> <destino> - Mueve un nodo a otra carpeta",
            "rename": "rename <viejo> <nuevo> - Renombra un nodo",
            "rm": "rm <nombre> [-p] - Elimina un nodo (-p para eliminación permanente)",
            "trash": "trash - Muestra el contenido de la papelera",
            "restore": "restore <índice> - Restaura un elemento de la papelera",
            "emptytrash": "emptytrash - Vacía la papelera permanentemente",
            "tree": "tree [ruta] - Muestra la estructura en formato árbol",
            "search": "search <término> [--exact] [--type dir/file] - Busca nodos",
            "autocomplete": "autocomplete <prefijo> [límite] - Autocompletado de nombres",
            "find": "find <nombre_exacto> - Busca nodos con nombre exacto",
            "export": "export [archivo] - Exporta recorrido en preorden",
            "stats": "stats - Muestra estadísticas del sistema",
            "history": "history [límite] - Muestra historial de operaciones",
            "log": "log [on/off] - Activa/desactiva el registro de log",
            "clear": "clear - Limpia la pantalla",
            "save": "save [archivo] - Guarda el sistema en disco",
            "load": "load [archivo] - Carga el sistema desde disco",
            "help": "help [comando] - Muestra esta ayuda",
            "exit": "exit - Sale del sistema (pregunta para guardar)"
        }
        
        if comando_especifico:
            if comando_especifico in ayuda_general:
                print(f"\n{Colors.CYAN}{ayuda_general[comando_especifico]}{Colors.RESET}")
                # Ayuda detallada para comandos complejos
                if comando_especifico == "search":
                    print(f"\n{Colors.YELLOW}Ejemplos:{Colors.RESET}")
                    print("  search docu           - Busca nodos que contengan 'docu'")
                    print("  search .txt --exact   - Busca exactamente '.txt'")
                    print("  search arch --type file - Busca archivos con 'arch'")
                elif comando_especifico == "tree":
                    print(f"\n{Colors.YELLOW}Ejemplos:{Colors.RESET}")
                    print("  tree           - Muestra árbol desde directorio actual")
                    print("  tree /         - Muestra árbol completo desde raíz")
                    print("  tree documentos - Muestra árbol de la carpeta documentos")
            else:
                print(f"{Colors.RED}Comando '{comando_especifico}' no encontrado.{Colors.RESET}")
        else:
            print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
            print(f"{Colors.BOLD}AYUDA DEL SISTEMA DE ARCHIVOS JERÁRQUICO{Colors.RESET}")
            print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
            
            categorias = {
                "Navegación y visualización": ["ls", "pwd", "cd", "tree"],
                "Manipulación de archivos": ["mkdir", "touch", "mv", "rename", "rm"],
                "Papelera": ["trash", "restore", "emptytrash"],
                "Búsqueda": ["search", "autocomplete", "find"],
                "Exportación y estadísticas": ["export", "stats"],
                "Sistema y utilidades": ["history", "log", "clear", "save", "load", "help", "exit"]
            }
            
            for categoria, comandos in categorias.items():
                print(f"\n{Colors.BOLD}{categoria}:{Colors.RESET}")
                for cmd in comandos:
                    if cmd in ayuda_general:
                        print(f"  {ayuda_general[cmd]}")
            
            print(f"\n{Colors.YELLOW}Nota: Use 'help <comando>' para ayuda detallada.{Colors.RESET}")
    
    def clear_screen(self):
        """Limpia la pantalla de la consola."""
        os.system('cls' if os.name == 'nt' else 'clear')
    

    def obtener_prompt(self) -> str:
        """Genera un prompt personalizado con colores."""
        ruta = self.ruta_completa()
        usuario = os.getenv('USERNAME') or os.getenv('USER') or "usuario"
        
        prompt = f"{Colors.GREEN}{usuario}{Colors.RESET}:"
        prompt += f"{Colors.BLUE}{ruta}{Colors.RESET}"
        prompt += f"{Colors.YELLOW}$ {Colors.RESET}"
        
        return prompt

def main():
    """Función principal del programa."""
    sistema = SistemaArchivos()
    
    # Mostrar banner
    print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}SISTEMA DE ARCHIVOS JERÁRQUICO - DÍAS 7-9{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}Versión: {sistema.version} | Papelera temporal activada{Colors.RESET}")
    print(f"{Colors.YELLOW}Escriba 'help' para ver los comandos disponibles{Colors.RESET}\n")
    
    # Intentar cargar sistema existente
    if os.path.exists(sistema.archivo_persistencia):
        respuesta = input(f"¿Cargar sistema existente desde '{sistema.archivo_persistencia}'? (s/n): ").lower()
        if respuesta == 's':
            sistema.cargar_desde_json()
    else:
        print(f"{Colors.YELLOW}No se encontró sistema existente. Iniciando nuevo sistema.{Colors.RESET}")
    
    # Diccionario de comandos
    comandos = {
        # Navegación y visualización
        "mkdir": lambda args: sistema.crear_carpeta(args[0]) if args else print(f"{Colors.RED}Uso: mkdir <nombre>{Colors.RESET}"),
        "touch": lambda args: sistema.crear_archivo(args[0], " ".join(args[1:])) if args else print(f"{Colors.RED}Uso: touch <nombre> [contenido]{Colors.RESET}"),
        "ls": lambda args: sistema.listar_hijos(detallado=("-l" in args)),
        "pwd": lambda args: print(f"{Colors.BLUE}{sistema.ruta_completa()}{Colors.RESET}"),
        "cd": lambda args: sistema.cambiar_directorio(args[0]) if args else print(f"{Colors.RED}Uso: cd <ruta>{Colors.RESET}"),
        "tree": lambda args: sistema.mostrar_arbol() if not args else sistema.cambiar_directorio(args[0]) and sistema.mostrar_arbol(),
        
        # Manipulación
        "mv": lambda args: sistema.mover_nodo(args[0], args[1]) if len(args) == 2 else print(f"{Colors.RED}Uso: mv <origen> <destino>{Colors.RESET}"),
        "rename": lambda args: sistema.renombrar_nodo(args[0], args[1]) if len(args) == 2 else print(f"{Colors.RED}Uso: rename <viejo> <nuevo>{Colors.RESET}"),
        "rm": lambda args: sistema.eliminar_nodo(args[0], mover_a_papelera=("-p" not in args)) if args else print(f"{Colors.RED}Uso: rm <nombre> [-p para permanente]{Colors.RESET}"),
        
        # Papelera
        "trash": lambda args: sistema.mostrar_papelera(),
        "restore": lambda args: sistema.restaurar_de_papelera(int(args[0])) if args and args[0].isdigit() else print(f"{Colors.RED}Uso: restore <índice>{Colors.RESET}"),
        "emptytrash": lambda args: sistema.vaciar_papelera(),
        
        # Búsqueda
        "search": lambda args: (
            sistema.search(args[0]) if args else print(f"{Colors.RED}Uso: search <término> [--exact] [--type dir/file]{Colors.RESET}")
        ),
        "autocomplete": lambda args: (
            sistema.autocomplete(args[0], int(args[1]) if len(args) > 1 else 5) 
            if args else print(f"{Colors.RED}Uso: autocomplete <prefijo> [límite]{Colors.RESET}")
        ),
        "find": lambda args: sistema.find(args[0]) if args else print(f"{Colors.RED}Uso: find <nombre_exacto>{Colors.RESET}"),
        
        # Exportación y estadísticas
        "export": lambda args: sistema.exportar_preorden(args[0] if args else "preorden.txt"),
        "stats": lambda args: sistema.mostrar_estadisticas(),
        "history": lambda args: sistema.history(int(args[0]) if args and args[0].isdigit() else 5),
        
        # Sistema
        "log": lambda args: sistema.toggle_log({"on": True, "off": False}.get(args[0] if args else None)),
        "clear": lambda args: sistema.clear_screen(),
        "save": lambda args: sistema.guardar_a_json(args[0] if args else None),
        "load": lambda args: sistema.cargar_desde_json(args[0] if args else None),
        "help": lambda args: sistema.mostrar_ayuda(args[0] if args else None),
        "exit": None,
    }
    
    # Bucle principal
    while True:
        try:
            # Mostrar prompt personalizado
            entrada = input(sistema.obtener_prompt()).strip()
            if not entrada:
                continue
            
            # Manejo especial para search con opciones
            if entrada.startswith("search ") and ("--exact" in entrada or "--type" in entrada):
                partes = entrada.split()
                termino = partes[1]
                exacto = "--exact" in partes
                tipo = None
                if "--type" in partes:
                    idx = partes.index("--type")
                    if idx + 1 < len(partes):
                        tipo_str = partes[idx + 1]
                        if tipo_str not in ["dir", "file"]:
                            print(f"{Colors.RED}Error: tipo debe ser 'dir' o 'file'{Colors.RESET}")
                            continue
                        tipo = NodeType.FOLDER.value if tipo_str == "dir" else NodeType.FILE.value
                
                # Crear función de búsqueda temporal
                def buscar():
                    resultados = sistema.buscar_exacto(termino) if exacto else [
                        sistema.buscar_por_id(r["id"]) 
                        for r in sistema.buscar_por_patron(termino, tipo)
                    ]
                    
                    if not resultados:
                        print(f"{Colors.YELLOW}No se encontraron resultados para '{termino}'{Colors.RESET}")
                        return
                    
                    print(f"\n{Colors.CYAN}Resultados de búsqueda para '{termino}':{Colors.RESET}")
                    for i, nodo in enumerate(resultados, 1):
                        if nodo:
                            ruta = sistema._obtener_ruta(nodo)
                            tipo_str = "DIR" if nodo.tipo == NodeType.FOLDER.value else "FILE"
                            color = Colors.BLUE if nodo.tipo == NodeType.FOLDER.value else Colors.WHITE
                            print(f"{Colors.YELLOW}{i:2}.{Colors.RESET} {color}[{tipo_str}] {nodo.nombre} (ID: {nodo.id}){Colors.RESET}")
                            print(f"    Ruta: {ruta}")
                            if nodo.tipo == NodeType.FILE.value and nodo.contenido:
                                contenido_preview = nodo.contenido[:50] + "..." if len(nodo.contenido) > 50 else nodo.contenido
                                print(f"    Contenido: {contenido_preview}")
                
                buscar()
                continue
            
            # Comandos normales
            partes = entrada.split()
            comando = partes[0]
            args = partes[1:]
            
            if comando == "exit":
                respuesta = input(f"{Colors.YELLOW}¿Guardar cambios antes de salir? (s/n): {Colors.RESET}").lower()
                if respuesta == 's':
                    sistema.guardar_a_json()
                print(f"{Colors.GREEN}Saliendo...{Colors.RESET}")
                break
            elif comando in comandos:
                if comandos[comando] is None:
                    continue
                comandos[comando](args)
            else:
                print(f"{Colors.RED}Comando '{comando}' no reconocido. Escribe 'help' para ver comandos.{Colors.RESET}")
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}\nInterrupción detectada.{Colors.RESET}")
            respuesta = input(f"{Colors.YELLOW}¿Guardar cambios antes de salir? (s/n): {Colors.RESET}").lower()
            if respuesta == 's':
                sistema.guardar_a_json()
            print(f"{Colors.GREEN}Saliendo...{Colors.RESET}")
            break
        except Exception as e:
            sistema._manejar_error(e, "consola")

def ejecutar_pruebas_interfaz():
    print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}PRUEBAS DE INTERFAZ Y PAPELERA - DÍAS 7-9{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
    
    # Limpiar archivos anteriores
    for f in ["test_interfaz.json", "trash.json", "preorden.txt", "sistema.log"] + \
             [f for f in os.listdir() if f.startswith("backup_")]:
        if os.path.exists(f):
            os.remove(f)
    
    sistema = SistemaArchivos()
    sistema.archivo_persistencia = "test_interfaz.json"
    sistema.log_activo = True
    
    print(f"\n{Colors.BOLD}1. Creando estructura de prueba...{Colors.RESET}")
    sistema.mkdir("Proyecto")
    sistema.mkdir("Personal")
    sistema.cd("Proyecto")
    sistema.touch("main.py", "print('Hola mundo')")
    sistema.touch("README.md", "# Mi Proyecto")
    sistema.mkdir("src")
    sistema.cd("src")
    sistema.touch("utilidades.py", "def ayuda(): pass")
    sistema.cd("/")
    
    print(f"\n{Colors.BOLD}2. Probando papelera...{Colors.RESET}")
    sistema.rm("README.md")  # A la papelera
    sistema.trash()
    
    print(f"\n{Colors.BOLD}3. Probando restauración...{Colors.RESET}")
    sistema.restore("0")
    sistema.ls()
    
    print(f"\n{Colors.BOLD}4. Probando eliminación permanente...{Colors.RESET}")
    sistema.rm("README.md -p")
    sistema.trash()
    
    print(f"\n{Colors.BOLD}5. Probando árbol...{Colors.RESET}")
    sistema.tree()
    
    print(f"\n{Colors.BOLD}6. Probando estadísticas...{Colors.RESET}")
    sistema.stats()
    
    print(f"\n{Colors.BOLD}7. Probando log...{Colors.RESET}")
    sistema.toggle_log(False)
    
    print(f"\n{Colors.BOLD}8. Guardando...{Colors.RESET}")
    sistema.save()
    
    # Limpiar
    for f in ["test_interfaz.json", "trash.json", "preorden.txt", "sistema.log"] + \
             [f for f in os.listdir() if f.startswith("backup_")]:
        if os.path.exists(f):
            os.remove(f)
    
    print(f"\n{Colors.GREEN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}PRUEBAS COMPLETADAS EXITOSAMENTE{Colors.RESET}")
    print(f"{Colors.GREEN}{'='*70}{Colors.RESET}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test-interfaz":
        ejecutar_pruebas_interfaz()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Ejecutar pruebas anteriores si existen
        try:
            from dia5_6 import ejecutar_pruebas_busqueda
            ejecutar_pruebas_busqueda()
        except ImportError:
            pass
        ejecutar_pruebas_interfaz()
    else:
        main()