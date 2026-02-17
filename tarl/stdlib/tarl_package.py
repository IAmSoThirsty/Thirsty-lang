"""
Thirsty-Lang Package Registry System
Package manager and dependency resolution

Provides:
- Package: Package metadata and versioning
- Registry: Package registry operations
- Resolver: Dependency resolution
- Installer: Package installation
"""

import json
import os
import hashlib
import tarfile
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import re


@dataclass
class PackageVersion:
    """Semantic version"""
    major: int
    minor: int
    patch: int
    
    @staticmethod
    def parse(version_str: str) -> 'PackageVersion':
        """Parse semantic version"""
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
        if not match:
            raise ValueError(f"Invalid version: {version_str}")
        return PackageVersion(int(match[1]), int(match[2]), int(match[3]))
    
    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __lt__(self, other):
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __le__(self, other):
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)
    
    def __gt__(self, other):
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)
    
    def __ge__(self, other):
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)
    
    def __eq__(self, other):
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
    
    def satisfies(self, requirement: str) -> bool:
        """Check if version satisfies requirement
        
        Supports: =, >=, <=, >, <, ~, ^
        """
        if requirement.startswith('>='):
            min_ver = PackageVersion.parse(requirement[2:].strip())
            return self >= min_ver
        elif requirement.startswith('<='):
            max_ver = PackageVersion.parse(requirement[2:].strip())
            return self <= max_ver
        elif requirement.startswith('>'):
            min_ver = PackageVersion.parse(requirement[1:].strip())
            return self > min_ver
        elif requirement.startswith('<'):
            max_ver = PackageVersion.parse(requirement[1:].strip())
            return self < max_ver
        elif requirement.startswith('~'):
            # ~1.2.3 means >=1.2.3 <1.3.0
            base = PackageVersion.parse(requirement[1:].strip())
            return self >= base and self.major == base.major and self.minor == base.minor
        elif requirement.startswith('^'):
            # ^1.2.3 means >=1.2.3 <2.0.0
            base = PackageVersion.parse(requirement[1:].strip())
            return self >= base and self.major == base.major
        else:
            # Exact match
            target = PackageVersion.parse(requirement.strip())
            return self == target


@dataclass
class Package:
    """Package metadata"""
    name: str
    version: PackageVersion
    dependencies: Dict[str, str]  # name -> version requirement
    description: str = ""
    author: str = ""
    license: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'version': str(self.version),
            'dependencies': self.dependencies,
            'description': self.description,
            'author': self.author,
            'license': self.license
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Package':
        """Create from dictionary"""
        return Package(
            name=data['name'],
            version=PackageVersion.parse(data['version']),
            dependencies=data.get('dependencies', {}),
            description=data.get('description', ''),
            author=data.get('author', ''),
            license=data.get('license', '')
        )


class DependencyResolver:
    """Resolve package dependencies"""
    
    def __init__(self, registry: 'Registry'):
        self.registry = registry
    
    def resolve(self, package_name: str, version_req: str = '*') -> List[Package]:
        """Resolve dependencies and return installation order"""
        resolved: Dict[str, Package] = {}
        self._resolve_recursive(package_name, version_req, resolved)
        
        # Topological sort
        return self._topological_sort(resolved)
    
    def _resolve_recursive(
        self,
        name: str,
        version_req: str,
        resolved: Dict[str, Package]
    ):
        """Recursively resolve dependencies"""
        if name in resolved:
            return
        
        # Find suitable version
        package = self.registry.find_package(name, version_req)
        if not package:
            raise ValueError(f"Cannot find package {name} matching {version_req}")
        
        resolved[name] = package
        
        # Resolve dependencies
        for dep_name, dep_req in package.dependencies.items():
            self._resolve_recursive(dep_name, dep_req, resolved)
    
    def _topological_sort(self, packages: Dict[str, Package]) -> List[Package]:
        """Sort packages by dependencies"""
        result = []
        visited = set()
        
        def visit(pkg: Package):
            if pkg.name in visited:
                return
            visited.add(pkg.name)
            
            for dep_name in pkg.dependencies:
                if dep_name in packages:
                    visit(packages[dep_name])
            
            result.append(pkg)
        
        for pkg in packages.values():
            visit(pkg)
        
        return result


class Registry:
    """Package registry"""
    
    def __init__(self, registry_dir: str = '.tarl_packages'):
        self.registry_dir = registry_dir
        os.makedirs(registry_dir, exist_ok=True)
        self.index_file = os.path.join(registry_dir, 'index.json')
        self.packages: Dict[str, List[Package]] = {}
        self._load_index()
    
    def _load_index(self):
        """Load package index"""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                data = json.load(f)
                for name, versions in data.items():
                    self.packages[name] = [
                        Package.from_dict(v) for v in versions
                    ]
    
    def _save_index(self):
        """Save package index"""
        data = {}
        for name, versions in self.packages.items():
            data[name] = [v.to_dict() for v in versions]
        
        with open(self.index_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def publish(self, package: Package, package_file: str):
        """Publish package to registry"""
        if package.name not in self.packages:
            self.packages[package.name] = []
        
        # Check if version already exists
        for existing in self.packages[package.name]:
            if existing.version == package.version:
                raise ValueError(f"Version {package.version} already exists")
        
        self.packages[package.name].append(package)
        self._save_index()
        
        # Copy package file
        pkg_dir = os.path.join(self.registry_dir, package.name)
        os.makedirs(pkg_dir, exist_ok=True)
        
        import shutil
        dest = os.path.join(pkg_dir, f"{package.name}-{package.version}.tpkg")
        shutil.copy(package_file, dest)
    
    def find_package(self, name: str, version_req: str = '*') -> Optional[Package]:
        """Find package matching version requirement"""
        if name not in self.packages:
            return None
        
        candidates = self.packages[name]
        
        if version_req == '*':
            # Return latest
            return max(candidates, key=lambda p: p.version)
        
        # Find matching version
        for pkg in sorted(candidates, key=lambda p: p.version, reverse=True):
            if pkg.version.satisfies(version_req):
                return pkg
        
        return None
    
    def list_packages(self) -> List[str]:
        """List all package names"""
        return list(self.packages.keys())


# Export package classes
__all__ = ['Package', 'PackageVersion', 'Registry', 'DependencyResolver']
