"""Thin Win32 Credential Manager FFI, verified by a real external smoke."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

from govor_provider_interfaces import ProviderAuthenticationError

from .secrets import _validate_secret, validate_credential_target

_TARGET_PREFIX = "govor.ai/provider/"


class _CredentialW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialStore:
    """Current-user generic credentials protected by Windows Credential Manager."""

    _GENERIC = 1
    _PERSIST_LOCAL_MACHINE = 2
    _NOT_FOUND = 1168

    def __init__(self) -> None:
        if os.name != "nt":
            raise RuntimeError("Windows Credential Manager is available only on Windows")
        self._api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self._api.CredWriteW.argtypes = [ctypes.POINTER(_CredentialW), wintypes.DWORD]
        self._api.CredWriteW.restype = wintypes.BOOL
        self._api.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(_CredentialW)),
        ]
        self._api.CredReadW.restype = wintypes.BOOL
        self._api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self._api.CredDeleteW.restype = wintypes.BOOL
        self._api.CredFree.argtypes = [ctypes.c_void_p]
        self._api.CredFree.restype = None

    def get_secret(self, target: str) -> str:
        pointer = ctypes.POINTER(_CredentialW)()
        if not self._api.CredReadW(self._target(target), self._GENERIC, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == self._NOT_FOUND:
                raise ProviderAuthenticationError("provider credential is not configured")
            raise ProviderAuthenticationError("provider credential could not be read")
        try:
            credential = pointer.contents
            value = ctypes.string_at(
                credential.CredentialBlob, credential.CredentialBlobSize
            ).decode("utf-8")
            _validate_secret(value)
            return value
        except (UnicodeDecodeError, ValueError) as error:
            raise ProviderAuthenticationError("provider credential is invalid") from error
        finally:
            self._api.CredFree(pointer)

    def set_secret(self, target: str, secret: str) -> None:
        _validate_secret(secret)
        encoded = secret.encode("utf-8")
        blob = (ctypes.c_ubyte * len(encoded)).from_buffer_copy(encoded)
        credential = _CredentialW(
            Type=self._GENERIC,
            TargetName=self._target(target),
            CredentialBlobSize=len(encoded),
            CredentialBlob=ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte)),
            Persist=self._PERSIST_LOCAL_MACHINE,
            UserName="govor.ai",
        )
        if not self._api.CredWriteW(ctypes.byref(credential), 0):
            raise ProviderAuthenticationError("provider credential could not be stored")

    def delete_secret(self, target: str) -> bool:
        if self._api.CredDeleteW(self._target(target), self._GENERIC, 0):
            return True
        if ctypes.get_last_error() == self._NOT_FOUND:
            return False
        raise ProviderAuthenticationError("provider credential could not be deleted")

    @staticmethod
    def _target(target: str) -> str:
        return _TARGET_PREFIX + validate_credential_target(target)
