"""
Патч DNS для Python/Windows — исправляет getaddrinfo через Google DNS.
Решает ошибку 'getaddrinfo failed' при подключении к Supabase.

Импортируй ПЕРВЫМ:
    import dns_fix
"""
import socket
import struct

GOOGLE_DNS = '8.8.8.8'
_CACHE = {}


def _dns_resolve(host):
    """Резолвит A-запись через Google DNS (UDP)."""
    if host in _CACHE:
        return _CACHE[host]
    q = struct.pack('>HHHHHH', 0xABCD, 0x0100, 1, 0, 0, 0)
    for p in host.split('.'):
        q += bytes([len(p)]) + p.encode()
    q += b'\x00' + struct.pack('>HH', 1, 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    try:
        s.sendto(q, (GOOGLE_DNS, 53))
        data, _ = s.recvfrom(1024)
    except Exception:
        return None
    finally:
        s.close()
    off = 12
    while data[off]:
        off += data[off] + 1
    off += 5
    while off < len(data) - 10:
        if data[off] & 0xC0 == 0xC0:
            off += 2
        else:
            while data[off]:
                off += data[off] + 1
            off += 1
        rt = struct.unpack('>H', data[off:off+2])[0]
        rl = struct.unpack('>H', data[off+8:off+10])[0]
        if rt == 1 and rl == 4:
            ip = '.'.join(str(b) for b in data[off+10:off+14])
            _CACHE[host] = ip
            return ip
        off += 10 + rl
    return None


# ── Патч 1: socket.getaddrinfo ─────────────────────────────────
_orig_gai = socket.getaddrinfo

def _patched_gai(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _orig_gai(host, port, family, type, proto, flags)
    except socket.gaierror:
        ip = _dns_resolve(host)
        if ip:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]
        raise

socket.getaddrinfo = _patched_gai


# ── Патч 2: httpcore.SyncBackend.connect_tcp ───────────────────
# httpcore вызывает socket.create_connection внутри,
# но CPython внутри create_connection вызывает свой C-level getaddrinfo,
# который НЕ проходит через наш Python-level патч.
# Поэтому патчим connect_tcp чтобы он разрешал DNS вручную.

try:
    import httpcore._backends.sync as _sync_backend
    from httpcore._exceptions import ConnectTimeout, ConnectError

    _orig_connect_tcp = _sync_backend.SyncBackend.connect_tcp

    def _patched_connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if socket_options is None:
            socket_options = []

        ip = _dns_resolve(host)
        if not ip:
            # Попробуем оригинальный путь если DNS не работает
            try:
                return _orig_connect_tcp(self, host, port, timeout=timeout,
                                         local_address=local_address, socket_options=socket_options)
            except Exception as e:
                raise ConnectError(f"Could not resolve {host}: {e}")

        exc_map = {socket.timeout: ConnectTimeout, OSError: ConnectError}
        address = (ip, port)

        try:
            sock = socket.create_connection(address, timeout=timeout)
        except Exception as e:
            raise ConnectError(str(e))

        for option in socket_options:
            try:
                sock.setsockopt(*option)
            except Exception:
                pass

        from httpcore._backends.sync import SyncStream
        return SyncStream(sock)

    _sync_backend.SyncBackend.connect_tcp = _patched_connect_tcp
except Exception:
    pass
