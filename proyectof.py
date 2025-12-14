# sistema_completo_dias_1_a_11.py
# Proyecto de Árboles - Estructura de Datos
# Días 1-11 completos: Árbol general, Trie, Papelera, Interfaz, Pruebas de Integración

import json
import uuid
import os
import shutil
import sys
import time
import random
import string
import statistics
from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Tuple, Callable
from collections import defaultdict, deque
from enum import Enum

# ==================== CONSTANTES Y CONFIGURACIÓN ====================
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

# ==================== ESTRUCTURA TRIE ====================
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

# ==================== PAPELERA TEMPORAL ====================
class TrashItem:
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
    def __init__(self, capacidad_maxima=100):
        self.items = []
        self.capacidad_maxima = capacidad_maxima
        self.archivo_trash = "trash.json"
    
    def agregar(self, nodo: 'Nodo', ruta_original: str):
        if len(self.items) >= self.capacidad_maxima:
            self.items.pop(0)
        
        item = TrashItem(nodo, ruta_original, datetime.now().isoformat())
        self.items.append(item)
        return item
    
    def listar(self) -> List[Dict[str, Any]]:
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
        if 0 <= indice < len(self.items):
            item = self.items.pop(indice)
            return item.nodo, item.ruta_original
        return None
    
    def vaciar(self):
        self.items.clear()
    
    def guardar(self):
        datos = {
            "capacidad_maxima": self.capacidad_maxima,
            "items": [item.to_dict() for item in self.items]
        }
        try:
            with open(self.archivo_trash, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2)
        except Exception:
            pass
    
    def cargar(self):
        try:
            if os.path.exists(self.archivo_trash):
                with open(self.archivo_trash, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                self.capacidad_maxima = datos.get("capacidad_maxima", 100)
                self.items = [TrashItem.from_dict(item) for item in datos.get("items", [])]
        except Exception:
            self.items = []

# ==================== NODO ====================
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

# ==================== SISTEMA DE ARCHIVOS PRINCIPAL ====================
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
    
    # ==================== MANEJO DE ERRORES ====================
    class SistemaError(Exception):
        def __init__(self, tipo: ErrorType, detalle: str = ""):
            self.tipo = tipo
            self.detalle = detalle
            super().__init__(f"{tipo.value}: {detalle}")
    
    def _manejar_error(self, error: Exception, operacion: str):
        if isinstance(error, self.SistemaError):
            mensaje = f"{Colors.RED}Error: {error}{Colors.RESET}"
        else:
            mensaje = f"{Colors.RED}Error inesperado en {operacion}: {error}{Colors.RESET}"
        
        print(mensaje)
        
        if self.log_activo:
            self._log(f"ERROR en {operacion}: {error}")
    
    def _log(self, mensaje: str):
        if self.log_activo:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {mensaje}\n")
            except Exception:
                pass
    
    # ==================== MANEJO DE ÍNDICES ====================
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
    
    # ==================== OPERACIONES BÁSICAS ====================
    def crear_carpeta(self, nombre: str):
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
        try:
            nodo = self.nodo_actual.buscar_por_nombre(nombre)
            if not nodo:
                raise self.SistemaError(ErrorType.NOT_FOUND, f"'{nombre}'")
            
            if not nodo.parent:
                raise self.SistemaError(ErrorType.PERMISSION_DENIED, "No se puede eliminar la raíz")
            
            if mover_a_papelera:
                ruta_original = self._obtener_ruta(nodo)
                self.papelera.agregar(nodo, ruta_original)
                self.papelera.guardar()
                mensaje = f"'{nombre}' movido a la papelera"
            else:
                self._actualizar_indices(nodo, eliminar=True)
                mensaje = f"'{nombre}' eliminado permanentemente"
            
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
    
    # ==================== PAPELERA ====================
    def mostrar_papelera(self):
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
        try:
            resultado = self.papelera.restaurar(indice)
            if not resultado:
                raise self.SistemaError(ErrorType.NOT_FOUND, f"Índice {indice} en papelera")
            
            nodo, ruta_original = resultado
            
            partes = ruta_original.split("/")[1:-1]
            destino = self.raiz
            
            for parte in partes:
                if parte:
                    encontrado = destino.buscar_por_nombre(parte)
                    if not encontrado or encontrado.tipo != NodeType.FOLDER.value:
                        print(f"{Colors.YELLOW}Advertencia: Carpeta original no encontrada. Restaurando en /root{Colors.RESET}")
                        destino = self.raiz
                        break
                    destino = encontrado
            
            if destino.buscar_por_nombre(nodo.nombre):
                nuevo_nombre = f"{nodo.nombre}_restaurado"
                print(f"{Colors.YELLOW}Advertencia: Ya existe '{nodo.nombre}'. Renombrando a '{nuevo_nombre}'{Colors.RESET}")
                nodo.nombre = nuevo_nombre
            
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
    
    # ==================== NAVEGACIÓN ====================
    def cambiar_directorio(self, ruta: str):
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
    
    # ==================== BÚSQUEDA ====================
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
    
    # ==================== VISUALIZACIÓN ====================
    def listar_hijos(self, detallado: bool = False):
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
        if nodo is None:
            nodo = self.nodo_actual
        
        connector = "└── " if es_ultimo else "├── "
        
        if nodo == self.nodo_actual:
            color = Colors.GREEN + Colors.BOLD
        elif nodo.tipo == NodeType.FOLDER.value:
            color = Colors.BLUE
        else:
            color = Colors.WHITE
        
        icono = "📁" if nodo.tipo == NodeType.FOLDER.value else "📄"
        
        print(f"{prefijo}{connector}{color}{icono} {nodo.nombre}{Colors.RESET}")
        
        if nodo.tipo == NodeType.FOLDER.value:
            extension = "    " if es_ultimo else "│   "
            nuevo_prefijo = prefijo + extension
            
            for i, child in enumerate(nodo.children):
                es_ultimo_hijo = (i == len(nodo.children) - 1)
                self.mostrar_arbol(child, nuevo_prefijo, es_ultimo_hijo)
    
    def ruta_completa(self):
        return "/" + "/".join(self.ruta_actual)
    
    # ==================== EXPORTACIÓN ====================
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
    
    # ==================== ESTADÍSTICAS ====================
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
    
    # ==================== PERSISTENCIA ====================
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
            
            self.trie = Trie()
            self.indice_nombre = defaultdict(set)
            self.indice_id = {}
            
            self.version = datos.get("version", "1.0")
            self.next_id = datos["next_id"]
            self.raiz = Nodo.from_dict(datos["raiz"])
            self.nodo_actual = self.raiz
            self.ruta_actual = ["root"]
            
            self._actualizar_indices(self.raiz)
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
    
    # ==================== LOG ====================
    def toggle_log(self, activar: Optional[bool] = None):
        if activar is None:
            activar = not self.log_activo
        
        self.log_activo = activar
        estado = "activado" if activar else "desactivado"
        color = Colors.GREEN if activar else Colors.YELLOW
        print(f"{color}Log {estado}.{Colors.RESET}")
    
    # ==================== INTERFAZ DE CONSOLA ====================
    def mostrar_ayuda(self, comando_especifico: str = None):
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
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def obtener_prompt(self) -> str:
        ruta = self.ruta_completa()
        usuario = os.getenv('USERNAME') or os.getenv('USER') or "usuario"
        
        prompt = f"{Colors.GREEN}{usuario}{Colors.RESET}:"
        prompt += f"{Colors.BLUE}{ruta}{Colors.RESET}"
        prompt += f"{Colors.YELLOW}$ {Colors.RESET}"
        
        return prompt

# ==================== CLASES DE TESTING (DÍAS 10-11) ====================
class PerformanceMonitor:
    """Monitor de performance para operaciones."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def start_operation(self, operation_name: str):
        self.start_time = time.time()
    
    def end_operation(self, operation_name: str) -> Dict[str, Any]:
        if not hasattr(self, 'start_time') or self.start_time is None:
            return {}
        
        elapsed_time = time.time() - self.start_time
        
        metrics = {
            'operation': operation_name,
            'time_ms': elapsed_time * 1000,
            'timestamp': datetime.now().isoformat()
        }
        
        self.metrics[operation_name].append(metrics)
        self.start_time = None
        
        return metrics
    
    def get_statistics(self, operation_name: str) -> Dict[str, Any]:
        if operation_name not in self.metrics or not self.metrics[operation_name]:
            return {}
        
        times = [m['time_ms'] for m in self.metrics[operation_name]]
        
        return {
            'operation': operation_name,
            'count': len(times),
            'time_avg_ms': statistics.mean(times),
            'time_min_ms': min(times),
            'time_max_ms': max(times),
            'time_std_ms': statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def generate_report(self) -> str:
        report = []
        report.append("=" * 80)
        report.append("REPORTE DE PERFORMANCE DEL SISTEMA DE ARCHIVOS")
        report.append("=" * 80)
        
        for operation in sorted(self.metrics.keys()):
            stats = self.get_statistics(operation)
            if stats:
                report.append(f"\nOperación: {operation}")
                report.append(f"  Ejecuciones: {stats['count']}")
                report.append(f"  Tiempo promedio: {stats['time_avg_ms']:.2f} ms")
                report.append(f"  Tiempo mínimo: {stats['time_min_ms']:.2f} ms")
                report.append(f"  Tiempo máximo: {stats['time_max_ms']:.2f} ms")
                report.append(f"  Desviación estándar: {stats['time_std_ms']:.2f} ms")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)
    
    def save_report(self, filename: str = "performance_report.txt"):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())
        print(f"Reporte de performance guardado en '{filename}'")

class TreeGenerator:
    """Generador de árboles aleatorios para testing."""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
    
    def generate_random_name(self, length: int = 8) -> str:
        letters = string.ascii_lowercase + string.digits
        return ''.join(random.choice(letters) for _ in range(length))
    
    def generate_random_tree(self, sistema, max_depth: int = 5, max_children: int = 5, 
                           max_files_per_folder: int = 3, probability_file: float = 0.3):
        def generate_recursive(current_node, current_depth, path):
            if current_depth >= max_depth:
                return
            
            num_children = random.randint(0, max_children)
            
            for _ in range(num_children):
                is_file = random.random() < probability_file and current_depth < max_depth - 1
                
                if is_file:
                    nombre = f"file_{self.generate_random_name(6)}.txt"
                    contenido = f"Contenido aleatorio {self.generate_random_name(10)}"
                    
                    old_node = sistema.nodo_actual
                    old_path = sistema.ruta_actual.copy()
                    
                    sistema.nodo_actual = current_node
                    sistema.ruta_actual = path.copy()
                    
                    sistema.crear_archivo(nombre, contenido)
                    
                    sistema.nodo_actual = old_node
                    sistema.ruta_actual = old_path
                else:
                    nombre = f"dir_{self.generate_random_name(6)}"
                    
                    old_node = sistema.nodo_actual
                    old_path = sistema.ruta_actual.copy()
                    
                    sistema.nodo_actual = current_node
                    sistema.ruta_actual = path.copy()
                    
                    nueva_carpeta = sistema.crear_carpeta(nombre)
                    
                    if nueva_carpeta:
                        new_path = path + [nombre]
                        generate_recursive(nueva_carpeta, current_depth + 1, new_path)
                    
                    sistema.nodo_actual = old_node
                    sistema.ruta_actual = old_path
        
        generate_recursive(sistema.raiz, 0, ["root"])
    
    def generate_stress_tree(self, sistema, num_nodes: int = 1000):
        print(f"Generando árbol de estrés con {num_nodes} nodos...")
        
        nodes_created = 0
        current_folder = sistema.raiz
        
        while nodes_created < num_nodes:
            files_to_create = min(10, num_nodes - nodes_created)
            for i in range(files_to_create):
                nombre = f"stress_file_{nodes_created + i:06d}.txt"
                contenido = f"Contenido de archivo de estrés {nodes_created + i}"
                
                old_node = sistema.nodo_actual
                sistema.nodo_actual = current_folder
                
                sistema.crear_archivo(nombre, contenido)
                
                sistema.nodo_actual = old_node
                nodes_created += 1
            
            if nodes_created < num_nodes and nodes_created % 100 == 0:
                folder_name = f"stress_folder_{nodes_created // 100:04d}"
                
                old_node = sistema.nodo_actual
                sistema.nodo_actual = current_folder
                
                nueva_carpeta = sistema.crear_carpeta(folder_name)
                
                sistema.nodo_actual = old_node
                
                if nueva_carpeta:
                    current_folder = nueva_carpeta
        
        print(f"Árbol de estrés generado con {nodes_created} nodos.")

class IntegrationTester:
    """Ejecutor de pruebas de integración."""
    
    def __init__(self, sistema_class):
        self.sistema_class = sistema_class
        self.test_results = []
        self.performance_monitor = PerformanceMonitor()
    
    def run_test(self, test_name: str, test_func: Callable, *args, **kwargs) -> bool:
        print(f"\n{'='*60}")
        print(f"Ejecutando prueba: {test_name}")
        print(f"{'='*60}")
        
        try:
            self.performance_monitor.start_operation(test_name)
            
            result = test_func(*args, **kwargs)
            
            metrics = self.performance_monitor.end_operation(test_name)
            
            if result:
                print(f"✅ {test_name}: PASÓ")
                self.test_results.append((test_name, True, metrics))
                return True
            else:
                print(f"❌ {test_name}: FALLÓ")
                self.test_results.append((test_name, False, metrics))
                return False
                
        except Exception as e:
            self.performance_monitor.end_operation(test_name)
            print(f"❌ {test_name}: ERROR - {e}")
            self.test_results.append((test_name, False, {"error": str(e)}))
            return False
    
    def run_edge_case_tests(self):
        print(f"\n{'#'*80}")
        print("PRUEBAS DE CASOS LÍMITE")
        print(f"{'#'*80}")
        
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Nombre con caracteres especiales
        def test_nombres_especiales():
            sistema = self.sistema_class()
            
            valid_names = ["normal", "con_guion", "con.pto", "123", "a"*50]
            for name in valid_names:
                if not sistema.crear_carpeta(name):
                    return False
            
            invalid_names = ["", "con/slash", "/raiz", "..", ".", " "*5]
            for name in invalid_names:
                sistema.crear_carpeta(name)
                if sistema.nodo_actual.buscar_por_nombre(name):
                    return False
            
            return True
        
        tests_total += 1
        if self.run_test("Nombres especiales", test_nombres_especiales):
            tests_passed += 1
        
        # Test 2: Rutas muy profundas
        def test_rutas_profundas():
            sistema = self.sistema_class()
            
            depth = 20
            current = sistema.raiz
            path = ["root"]
            
            for i in range(depth):
                folder_name = f"nivel_{i}"
                sistema.nodo_actual = current
                sistema.ruta_actual = path
                
                nueva = sistema.crear_carpeta(folder_name)
                if not nueva:
                    return False
                
                current = nueva
                path.append(folder_name)
            
            sistema.cambiar_directorio("/")
            return sistema.ruta_completa() == "/root"
        
        tests_total += 1
        if self.run_test("Rutas profundas (20 niveles)", test_rutas_profundas):
            tests_passed += 1
        
        # Test 3: Papelera con muchos elementos
        def test_papelera_estres():
            sistema = self.sistema_class()
            
            num_files = 20
            for i in range(num_files):
                sistema.crear_archivo(f"temp_{i}.txt", f"content {i}")
                sistema.eliminar_nodo(f"temp_{i}.txt")
            
            items = sistema.papelera.listar()
            if len(items) != num_files:
                return False
            
            for i in range(5):
                if not sistema.restaurar_de_papelera(0):
                    return False
            
            if not sistema.vaciar_papelera():
                return False
            
            return len(sistema.papelera.items) == 0
        
        tests_total += 1
        if self.run_test("Papelera bajo estrés", test_papelera_estres):
            tests_passed += 1
        
        # Test 4: Búsqueda en árbol grande
        def test_busqueda_masiva():
            sistema = self.sistema_class()
            generator = TreeGenerator(seed=42)
            
            generator.generate_random_tree(sistema, max_depth=4, max_children=3, 
                                         max_files_per_folder=2)
            
            resultados = sistema.buscar_por_patron("file")
            if len(resultados) == 0:
                return False
            
            all_nodes = sistema.indice_nombre
            if not all_nodes:
                return False
            
            some_name = list(all_nodes.keys())[0]
            exact_results = sistema.buscar_exacto(some_name)
            if len(exact_results) == 0:
                return False
            
            suggestions = sistema.autocompletar("dir")
            if len(suggestions) == 0:
                return False
            
            return True
        
        tests_total += 1
        if self.run_test("Búsqueda en árbol grande", test_busqueda_masiva):
            tests_passed += 1
        
        print(f"\n{'#'*80}")
        print(f"RESUMEN CASOS LÍMITE: {tests_passed}/{tests_total} pruebas pasadas")
        print(f"{'#'*80}")
        
        return tests_passed, tests_total
    
    def run_performance_tests(self):
        print(f"\n{'#'*80}")
        print("PRUEBAS DE PERFORMANCE")
        print(f"{'#'*80}")
        
        # Test de performance con árbol pequeño
        def test_performance_pequeno():
            sistema = self.sistema_class()
            generator = TreeGenerator(seed=1)
            
            generator.generate_random_tree(sistema, max_depth=3, max_children=3)
            
            sistema.search("file")
            sistema.autocompletar("dir")
            sistema.exportar_preorden("test_small_perf.txt")
            
            if os.path.exists("test_small_perf.txt"):
                os.remove("test_small_perf.txt")
            
            return True
        
        self.run_test("Performance árbol pequeño", test_performance_pequeno)
        
        # Test de performance con árbol mediano
        def test_performance_mediano():
            sistema = self.sistema_class()
            generator = TreeGenerator(seed=2)
            
            generator.generate_random_tree(sistema, max_depth=4, max_children=4)
            
            sistema.search("file")
            sistema.autocompletar("dir")
            
            return True
        
        self.run_test("Performance árbol mediano", test_performance_mediano)
        
        # Test de operaciones individuales
        def test_operaciones_individuales():
            sistema = self.sistema_class()
            
            for i in range(50):
                sistema.crear_archivo(f"perf_file_{i}.txt", "test")
            
            for i in range(10):
                sistema.search(f"perf_file_{i}")
            
            sistema.crear_carpeta("perf_folder")
            for i in range(20):
                sistema.mover_nodo(f"perf_file_{i}.txt", "perf_folder")
            
            return True
        
        self.run_test("Operaciones individuales", test_operaciones_individuales)
        
        self.performance_monitor.save_report("performance_tests_report.txt")
    
    def run_integration_test(self):
        print(f"\n{'#'*80}")
        print("PRUEBA DE INTEGRACIÓN COMPLETA")
        print(f"{'#'*80}")
        
        def integration_test():
            sistema = self.sistema_class()
            sistema.archivo_persistencia = "integration_test.json"
            
            sistema.crear_carpeta("Docs")
            sistema.crear_carpeta("Media")
            
            sistema.cd("Docs")
            sistema.crear_archivo("report.pdf", "PDF content")
            sistema.crear_archivo("notes.txt", "Important notes")
            sistema.crear_carpeta("Projects")
            
            sistema.cd("Projects")
            sistema.crear_archivo("project1.txt", "Project 1")
            sistema.crear_archivo("project2.txt", "Project 2")
            
            sistema.cd("/Docs/Projects")
            sistema.renombrar_nodo("project1.txt", "project1_renamed.txt")
            sistema.mover_nodo("project2.txt", "..")
            
            sistema.cd("/Docs")
            if not sistema.buscar_por_nombre("project2.txt"):
                return False
            
            sistema.eliminar_nodo("project2.txt")
            sistema.eliminar_nodo("notes.txt")
            
            if len(sistema.papelera.items) != 2:
                return False
            
            sistema.restaurar_de_papelera(0)
            
            resultados = sistema.search("proj")
            if len(resultados) == 0:
                return False
            
            if not sistema.guardar_a_json():
                return False
            
            sistema2 = self.sistema_class()
            sistema2.archivo_persistencia = "integration_test.json"
            
            if not sistema2.cargar_desde_json():
                return False
            
            if sistema2.raiz.calcular_tamano() != sistema.raiz.calcular_tamano():
                return False
            
            if not sistema2.exportar_preorden("integration_export.txt"):
                return False
            
            for f in ["integration_test.json", "integration_export.txt", "trash.json"]:
                if os.path.exists(f):
                    os.remove(f)
            
            return True
        
        if self.run_test("Integración completa", integration_test):
            print(f"\n✅ PRUEBA DE INTEGRACIÓN COMPLETADA EXITOSAMENTE")
            return True
        else:
            print(f"\n❌ PRUEBA DE INTEGRACIÓN FALLÓ")
            return False
    
    def run_all_tests(self):
        print(f"\n{'='*80}")
        print("SUITE COMPLETA DE PRUEBAS - DÍAS 10-11")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        edge_results = self.run_edge_case_tests()
        self.run_performance_tests()
        integration_result = self.run_integration_test()
        
        total_time = time.time() - start_time
        
        self.generate_final_report(total_time, edge_results, integration_result)
    
    def generate_final_report(self, total_time: float, edge_results: tuple, 
                            integration_result: bool):
        edge_passed, edge_total = edge_results
        
        report = []
        report.append("=" * 80)
        report.append("REPORTE FINAL DE PRUEBAS - SISTEMA DE ARCHIVOS")
        report.append("=" * 80)
        report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Tiempo total de ejecución: {total_time:.2f} segundos")
        report.append("")
        
        report.append("RESUMEN DE PRUEBAS:")
        report.append(f"  - Casos límite: {edge_passed}/{edge_total} pasados")
        report.append(f"  - Integración: {'PASÓ' if integration_result else 'FALLÓ'}")
        report.append("  - Performance: Ver reporte 'performance_tests_report.txt'")
        report.append("")
        
        report.append("DETALLES CASOS LÍMITE:")
        for test_name, passed, metrics in self.test_results:
            status = "✅ PASÓ" if passed else "❌ FALLÓ"
            time_info = f"{metrics.get('time_ms', 0):.2f} ms" if 'time_ms' in metrics else "N/A"
            report.append(f"  {status} - {test_name} ({time_info})")
        
        perf_data = {}
        for test_name in self.performance_monitor.metrics:
            stats = self.performance_monitor.get_statistics(test_name)
            if stats and 'time_avg_ms' in stats:
                perf_data[test_name] = stats['time_avg_ms']
        
        if perf_data:
            slowest = max(perf_data.items(), key=lambda x: x[1])
            fastest = min(perf_data.items(), key=lambda x: x[1])
            
            report.append("")
            report.append("RECOMENDACIONES:")
            report.append(f"  - Operación más lenta: {slowest[0]} ({slowest[1]:.2f} ms)")
            report.append(f"  - Operación más rápida: {fastest[0]} ({fastest[1]:.2f} ms)")
            
            if slowest[1] > 100:
                report.append(f"  ⚠️  {slowest[0]} podría necesitar optimización")
        
        all_passed = edge_passed == edge_total and integration_result
        report.append("")
        report.append("VEREDICTO FINAL: " + 
                     ("✅ SISTEMA ESTABLE Y CONFIABLE" if all_passed else 
                      "⚠️  SISTEMA NECESITA AJUSTES"))
        
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        print(report_text)
        
        with open("test_final_report.txt", "w", encoding="utf-8") as f:
            f.write(report_text)
        
        print(f"\nReporte final guardado en 'test_final_report.txt'")

# ==================== FUNCIONES PRINCIPALES ====================
def limpiar_archivos_prueba():
    """Limpia archivos generados por las pruebas."""
    test_files = [
        "test_stress.json", "test_fast_operations.txt", "test_small_perf.txt",
        "integration_test.json", "integration_export.txt", "trash.json",
        "performance_tests_report.txt", "test_final_report.txt",
        "test_interfaz.json", "test_busqueda.json", "sistema.log",
        "preorden.txt", "sistema.json"
    ]
    
    test_files += [f for f in os.listdir() if f.startswith("backup_")]
    
    for file in test_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"Eliminado: {file}")
            except Exception as e:
                print(f"No se pudo eliminar {file}: {e}")

def ejecutar_pruebas_completas():
    """Ejecuta la suite completa de pruebas."""
    tester = IntegrationTester(SistemaArchivos)
    
    try:
        tester.run_all_tests()
        return True
    except Exception as e:
        print(f"Error ejecutando pruebas: {e}")
        return False

def main_interfaz():
    """Función principal del programa - Modo interactivo."""
    sistema = SistemaArchivos()
    
    print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}SISTEMA DE ARCHIVOS JERÁRQUICO - DÍAS 1-11 COMPLETOS{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}Versión: {sistema.version} | Papelera temporal activada{Colors.RESET}")
    print(f"{Colors.YELLOW}Escriba 'help' para ver los comandos disponibles{Colors.RESET}\n")
    
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
        "search": lambda args: print("Ejecute 'search' desde la interfaz interactiva o use --test"),
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
            entrada = input(sistema.obtener_prompt()).strip()
            if not entrada:
                continue
            
            # Manejo especial para search
            if entrada.startswith("search "):
                partes = entrada.split()
                if len(partes) < 2:
                    print(f"{Colors.RED}Uso: search <término> [--exact] [--type dir/file]{Colors.RESET}")
                    continue
                
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
                
                # Ejecutar búsqueda
                if exacto:
                    resultados = sistema.buscar_exacto(termino)
                else:
                    resultados_dict = sistema.buscar_por_patron(termino, tipo)
                    resultados = [sistema.buscar_por_id(r["id"]) for r in resultados_dict]
                
                if not resultados:
                    print(f"{Colors.YELLOW}No se encontraron resultados para '{termino}'{Colors.RESET}")
                    continue
                
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

# ==================== PUNTO DE ENTRADA PRINCIPAL ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema de Archivos Jerárquico - Proyecto Árboles')
    parser.add_argument('--test', action='store_true', help='Ejecutar pruebas automáticas')
    parser.add_argument('--clean', action='store_true', help='Limpiar archivos de prueba')
    parser.add_argument('--mode', choices=['interactive', 'test'], default='interactive',
                       help='Modo de ejecución (interactive/test)')
    
    args = parser.parse_args()
    
    if args.clean:
        limpiar_archivos_prueba()
        sys.exit(0)
    
    if args.test or args.mode == 'test':
        print(f"{Colors.CYAN}Ejecutando pruebas automáticas...{Colors.RESET}")
        if ejecutar_pruebas_completas():
            print(f"{Colors.GREEN} Todas las pruebas completadas exitosamente{Colors.RESET}")
        else:
            print(f"{Colors.RED} Algunas pruebas fallaron{Colors.RESET}")
        sys.exit(0)
    else:
        main_interfaz()