#!/usr/bin/env python3
"""
Calcula la huella de los archivos que cubre un acta, para saber cuando vencio.

Por que existe: un acta que dice "el pago se verifico el 12/08" es oro hasta
que alguien toca el checkout el 20/08. A partir de ahi sigue diciendo que esta
probado, y miente. Es la VTV del auto: certifica marzo, no dice nada de los
frenos que se cambiaron en julio.

No usa git a proposito: hashlib funciona igual en un proyecto sin git, en
Windows y en una carpeta suelta. La portabilidad vale mas que reusar git aca.
"""

import hashlib
import os

LARGO = 6


def calcular(archivos, raiz):
    """Huella combinada de varios archivos. Determinista: ordena antes de sumar."""
    h = hashlib.sha256()
    for rel in sorted(archivos):
        h.update(rel.encode("utf-8"))
        ruta = os.path.join(raiz, rel)
        try:
            with open(ruta, "rb") as f:
                h.update(f.read())
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            # Un archivo borrado o ilegible tambien cambia la huella, que es
            # lo correcto: el acta que lo cubria ya no vale.
            h.update(b"<ausente>")
    return h.hexdigest()[:LARGO]


def vencidas(actas, raiz):
    """Las actas cuya huella ya no coincide con el estado real de sus archivos."""
    fuera = []
    for a in actas:
        if not a.get("cubre"):
            continue
        if calcular(a["cubre"], raiz) != a.get("huella"):
            fuera.append(a)
    return fuera


def _autotest():
    import tempfile, os
    d = tempfile.mkdtemp()
    a = os.path.join(d, "uno.py")
    open(a, "w").write("print(1)\n")

    h1 = calcular(["uno.py"], d)
    assert len(h1) == 6, h1
    # misma entrada, misma huella
    assert calcular(["uno.py"], d) == h1

    # cambiar el contenido cambia la huella
    open(a, "w").write("print(2)\n")
    h2 = calcular(["uno.py"], d)
    assert h2 != h1, (h1, h2)

    # un archivo que no existe no rompe
    assert len(calcular(["fantasma.py"], d)) == 6

    # el acta con huella vieja aparece vencida; la actualizada no
    actas = [{"que": "viejo", "cubre": ["uno.py"], "huella": h1},
             {"que": "nuevo", "cubre": ["uno.py"], "huella": h2}]
    v = vencidas(actas, d)
    assert [x["que"] for x in v] == ["viejo"], v

    print("huella.py OK")


if __name__ == "__main__":
    _autotest()
