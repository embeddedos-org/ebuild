"""Compiler abstraction for GCC and Clang toolchains.

Generates correct compile and link commands for C and C++ sources,
handling include paths, defines, optimization flags, and object file tracking.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class Language(Enum):
    C = "c"
    CPP = "cpp"


def _detect_language(source_path: str) -> Language:
    """Infer language from file extension."""
    ext = Path(source_path).suffix.lower()
    if ext in (".cpp", ".cxx", ".cc", ".C"):
        return Language.CPP
    return Language.C


@dataclass
class CompileCommand:
    """A single compilation unit command."""

    compiler: str
    source: str
    output: str
    flags: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    defines: List[str] = field(default_factory=list)
    depfile: Optional[str] = None

    def to_args(self) -> List[str]:
        args = [self.compiler]
        args.extend(self.flags)
        for inc in self.includes:
            args.extend(["-I", inc])
        for define in self.defines:
            args.append(f"-D{define}")
        if self.depfile:
            args.extend(["-MD", "-MF", self.depfile])
        args.extend(["-c", self.source, "-o", self.output])
        return args

    def to_string(self) -> str:
        return " ".join(self.to_args())


@dataclass
class LinkCommand:
    """A link command for executables or shared libraries."""

    linker: str
    objects: List[str]
    output: str
    flags: List[str] = field(default_factory=list)
    libraries: List[str] = field(default_factory=list)

    def to_args(self) -> List[str]:
        args = [self.linker]
        args.extend(self.flags)
        args.extend(self.objects)
        args.extend(["-o", self.output])
        args.extend(self.libraries)
        return args

    def to_string(self) -> str:
        return " ".join(self.to_args())


@dataclass
class ArchiveCommand:
    """An archive (static library) command."""

    archiver: str
    objects: List[str]
    output: str

    def to_args(self) -> List[str]:
        return [self.archiver, "rcs", self.output] + self.objects

    def to_string(self) -> str:
        return " ".join(self.to_args())


class Compiler:
    """Abstraction over GCC / Clang compilers.

    Generates compile, link, and archive commands based on the
    configured toolchain prefix and compiler type.
    """

    def __init__(
        self,
        cc: str = "gcc",
        cxx: str = "g++",
        ar: str = "ar",
        prefix: str = "",
        sysroot: Optional[str] = None,
    ) -> None:
        self.cc = f"{prefix}{cc}" if prefix else cc
        self.cxx = f"{prefix}{cxx}" if prefix else cxx
        self.ar = f"{prefix}{ar}" if prefix else ar
        self.sysroot = sysroot

    @classmethod
    def from_name(cls, name: str, prefix: str = "", sysroot: Optional[str] = None) -> "Compiler":
        """Create a Compiler from a short name like 'gcc' or 'clang'."""
        compilers = {
            "gcc": ("gcc", "g++", "ar"),
            "clang": ("clang", "clang++", "llvm-ar"),
        }
        if name not in compilers:
            raise ValueError(f"Unknown compiler '{name}'. Supported: {list(compilers.keys())}")
        cc, cxx, ar = compilers[name]
        return cls(cc=cc, cxx=cxx, ar=ar, prefix=prefix, sysroot=sysroot)

    def _compiler_for(self, language: Language) -> str:
        return self.cxx if language == Language.CPP else self.cc

    def _base_flags(self) -> List[str]:
        flags: List[str] = []
        if self.sysroot:
            flags.append(f"--sysroot={self.sysroot}")
        return flags

    def compile(
        self,
        source: str,
        output: str,
        *,
        includes: Optional[List[str]] = None,
        defines: Optional[List[str]] = None,
        cflags: Optional[List[str]] = None,
        depfile: Optional[str] = None,
        language: Optional[Language] = None,
    ) -> CompileCommand:
        if language is None:
            language = _detect_language(source)
        flags = self._base_flags() + (cflags or [])
        return CompileCommand(
            compiler=self._compiler_for(language),
            source=source,
            output=output,
            flags=flags,
            includes=includes or [],
            defines=defines or [],
            depfile=depfile,
        )

    def link_executable(
        self,
        objects: List[str],
        output: str,
        *,
        ldflags: Optional[List[str]] = None,
        language: Language = Language.C,
    ) -> LinkCommand:
        return LinkCommand(
            linker=self._compiler_for(language),
            objects=objects,
            output=output,
            flags=self._base_flags() + (ldflags or []),
        )

    def link_shared(
        self,
        objects: List[str],
        output: str,
        *,
        ldflags: Optional[List[str]] = None,
        language: Language = Language.C,
    ) -> LinkCommand:
        flags = self._base_flags() + ["-shared"] + (ldflags or [])
        return LinkCommand(
            linker=self._compiler_for(language),
            objects=objects,
            output=output,
            flags=flags,
        )

    def archive(self, objects: List[str], output: str) -> ArchiveCommand:
        return ArchiveCommand(
            archiver=self.ar,
            objects=objects,
            output=output,
        )

    def is_available(self) -> bool:
        """Check if the compiler binary is on PATH."""
        return shutil.which(self.cc) is not None
