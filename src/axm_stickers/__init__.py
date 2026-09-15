"""Portable sticker definitions and registry; Python standard library only."""
from .core import Registry, digest, instance, resolve, validate
from .placement import attachment_matrix, placement_2d

__all__ = ['Registry', 'digest', 'instance', 'resolve', 'validate',
           'attachment_matrix', 'placement_2d']
