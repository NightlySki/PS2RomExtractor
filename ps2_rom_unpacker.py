import os
import tempfile
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class ModuleInfo:
    index: int
    name: str
    offset: int
    size: int 
    size_padded: int

class PS2ROMUnpacker:
    def __init__(self, rom_path: str):
        self.rom_path = rom_path
        self.rom_size = os.path.getsize(rom_path)
        self.modules = []

    def fix_size16(self, size: int) -> int:
        remainder = size % 16
        padding = 16 - remainder if remainder else 0
        return size + padding

    def parse_size(self, file, offset: int) -> int:
        file.seek(offset)
        data = file.read(4)
        # Convert little-endian bytes to int
        return int.from_bytes(data, 'little')

    def find_romdir_size(self, rom_file) -> Tuple[int, int]:
        logger.debug("Buscando ROMDIR")
        
        for i in range(0, self.rom_size):
            rom_file.seek(i)
            if rom_file.read(1)[0] == 0x52:  # R
                next_bytes = rom_file.read(4)
                if next_bytes == b'ESET':
                    pos = rom_file.tell()
                    romdir_start = pos - 5
                    logger.debug(f"RESET encontrado en: {hex(romdir_start)}")

                    # Leer tamaño de ROMDIR
                    romdir_size = self.parse_size(rom_file, romdir_start + 0x10 + 2 + 10)
                    logger.debug(f"Tamaño ROMDIR: {hex(romdir_size)}")

                    return romdir_start, romdir_size
                    
        raise ValueError("No se encontró ROMDIR en el archivo")

    def parse_romdir(self, rom_file, romdir_loc: Tuple[int, int]) -> List[ModuleInfo]:
        modules = []
        start, size = romdir_loc
        num_modules = (size // 16) - 1

        logger.debug(f"Parseando {num_modules} módulos")
        
        offset = 0
        rom_file.seek(start)

        for i in range(num_modules):
            # Leer nombre (10 bytes)
            name = rom_file.read(10).decode('ascii').rstrip('\0')
            # Skip 2 bytes
            rom_file.seek(2, 1)
            # Leer tamaño (4 bytes)
            size = self.parse_size(rom_file, rom_file.tell())
            size_padded = self.fix_size16(size)

            module = ModuleInfo(
                index=i,
                name=name,
                offset=offset,
                size=size,
                size_padded=size_padded
            )
            modules.append(module)
            offset += size_padded

        return modules

    def extract_module(self, index: int) -> bytes:
        if not self.modules:
            with open(self.rom_path, 'rb') as rom:
                romdir_loc = self.find_romdir_size(rom)
                self.modules = self.parse_romdir(rom, romdir_loc)

        if 0 <= index < len(self.modules):
            module = self.modules[index]
            with open(self.rom_path, 'rb') as rom:
                rom.seek(module.offset)
                return rom.read(module.size_padded)
        else:
            raise ValueError(f"Índice de módulo inválido: {index}")

    def get_modules(self) -> List[ModuleInfo]:
        if not self.modules:
            with open(self.rom_path, 'rb') as rom:
                romdir_loc = self.find_romdir_size(rom)
                self.modules = self.parse_romdir(rom, romdir_loc)
        return self.modules
