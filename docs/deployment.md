# Despliegue de la versión 3.0 sin afectar la versión estable

La aplicación publicada hoy (v2) se despliega desde la rama `main`. La v3 vive en la rama `v3`. **No fusione `v3` en `main` hasta comprobar la nueva versión.**

## 1. Desplegar la v3 como aplicación aparte (recomendado)

1. En https://share.streamlit.io elija **Create app → Deploy a public app from GitHub**.
2. Repositorio: `dannyibarra-IA/waste-simulation-app`; rama: `v3`; archivo principal: `app.py`.
3. Python 3.11 o superior (en *Advanced settings*). No requiere secretos.
4. Elija una URL distinta, por ejemplo `waste-observatory-v3`.

La aplicación v2 sigue funcionando en su URL actual, sin cambios.

## 2. Verificación antes de reemplazar la v2

- [ ] Las 12 páginas cargan en español y en inglés.
- [ ] El mapa nacional muestra las 32 capitales.
- [ ] Las ciudades con bases SSPD cargadas aparecen como «con datos» y tienen un nivel de confiabilidad A, B o C.
- [ ] La descarga del PDF y del ZIP funciona.
- [ ] `python -m pytest` pasa en local (72 pruebas).

## 3. Reemplazar la v2

Cuando la v3 esté verificada:

```bash
git checkout main
git merge --no-ff v3
git push origin main
```

La v2 sigue disponible en `legacy/app_v2.py`. Para revertir, basta con volver a desplegar el commit anterior de `main`.

## Actualizar datos

```bash
# copiar las bases nuevas como data/raw/sspd_*.xlsx
python data/build_data.py
python -m pytest
git add data/ && git commit -m "Actualiza datos SSPD" && git push
```

El hash de cada archivo procesado queda registrado en `data/processed/data_version.json` y en el manifiesto de cada ejecución.
