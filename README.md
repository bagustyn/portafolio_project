````markdown
# Proyecto Portafolio de Inversiones

Este proyecto en **Django** permite gestionar portafolios de inversión, registrar operaciones de compra/venta, y visualizar la evolución del valor total y las ponderaciones de activos mediante gráficos interactivos.

## Características

- Carga inicial de datos desde un archivo `datos.xlsx` (precios y pesos iniciales).
- API para registrar operaciones (`compra` y `venta`).
- Cálculo de cantidades (`c_i,0`) y evolución diaria del portafolio.
- Gráficos interactivos de:
  - Valor total del portafolio (`V_t`).
  - Pesos de cada activo en el tiempo (`w_{i,t}`).
- Filtro por rango de fechas y selección de activos en el gráfico.
- Integración con **Django Admin**:
  - Botón "View site" lleva directo a la vista de evolución de portafolios.
  - Botón en la vista de gráficos para volver al panel de administración.
- Redirección de la página raíz (`/`) al panel de administración.

## Requisitos

- Python 3.10 o superior
- pipenv o virtualenv
- SQLite (por defecto) u otro motor de base de datos compatible con Django

## Instalación

1. Clonar este repositorio:
   ```bash
   git clone <URL_REPO>
   cd <CARPETA_PROYECTO>
````

2. Crear y activar un entorno virtual:

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows
   ```

3. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Aplicar migraciones:

   ```bash
   python manage.py migrate
   ```

5. Crear superusuario para acceder al admin:

   ```bash
   python manage.py createsuperuser
   ```

6. Cargar datos iniciales desde Excel:

   ```bash
   python manage.py import_datos ruta/al/archivo/datos.xlsx
   ```

7. Calcular cantidades iniciales (`c_i,0`):

   ```bash
   python manage.py calc_cantidades_iniciales
   ```

## Ejecución

Levantar el servidor de desarrollo:

```bash
python manage.py runserver
```

* **Admin:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
* **Vista de evolución:** accesible desde el botón "View site" en el admin o directamente en
  [http://127.0.0.1:8000/api/viz/](http://127.0.0.1:8000/api/viz/)

## API

### Registrar operaciones

**Endpoint:**

```
POST /api/portafolios/<pf_id>/operaciones/
```

**Ejemplo:**

```bash
curl -X POST "http://127.0.0.1:8000/api/portafolios/1/operaciones/" \
  -H "Content-Type: application/json" \
  -d '[
    {"fecha": "2022-03-01", "activo": "EEUU", "cantidad": 100000, "tipo": "compra"},
    {"fecha": "2022-06-01", "activo": "Latam", "cantidad": 50000, "tipo": "venta"}
  ]'
```

### Obtener evolución del portafolio

**Endpoint:**

```
GET /api/portafolios/<pf_id>/evolucion/?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD
```

**Ejemplo:**

```bash
curl "http://127.0.0.1:8000/api/portafolios/1/evolucion/?fecha_inicio=2022-02-15&fecha_fin=2023-02-16"
```

## Notas

* El proyecto está configurado para aceptar peticiones POST sin token CSRF en endpoints de API.
* La carga de datos desde Excel requiere que las hojas se llamen `weights` y `precios` (sin importar mayúsculas/minúsculas).
* Si se utiliza otra base de datos, modificar `settings.py` en la sección `DATABASES`.
