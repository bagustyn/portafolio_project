from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from inversiones.models import Activo, Portafolio, Precio, Weight

from datetime import datetime
from decimal import Decimal
import pandas as pd


class Command(BaseCommand):
    help = "Importa activos, precios y weights desde un Excel (datos.xlsx)."

    def add_arguments(self, parser):
        parser.add_argument("xlsx_path", type=str, help="Ruta al archivo datos.xlsx")
        parser.add_argument("--weights-sheet", default="Weights", help="Nombre de la hoja con weights")
        parser.add_argument("--precios-sheet", default="Precios", help="Nombre de la hoja con precios")
        parser.add_argument("--fecha-inicial", default="2022-02-15", help="Fecha inicial t0 (YYYY-MM-DD)")
        parser.add_argument("--pf1", default="Portafolio 1", help="Nombre del primer portafolio")
        parser.add_argument("--pf2", default="Portafolio 2", help="Nombre del segundo portafolio")

    def handle(self, *args, **opts):
        xlsx_path = opts["xlsx_path"]
        hoja_w = opts["weights_sheet"]
        hoja_p = opts["precios_sheet"]
        fecha_inicial = datetime.strptime(opts["fecha_inicial"], "%Y-%m-%d").date()
        pf1_name = opts["pf1"]
        pf2_name = opts["pf2"]

        # Abre el Excel (case-insensitive para nombres de hoja)
        try:
            xls = pd.ExcelFile(xlsx_path)
        except Exception as e:
            raise CommandError(f"No se pudo abrir el Excel: {e}")

        sheets_lower = {s.lower(): s for s in xls.sheet_names}
        if hoja_w.lower() not in sheets_lower or hoja_p.lower() not in sheets_lower:
            raise CommandError(f"No se encontraron las hojas requeridas. Disponibles: {xls.sheet_names}")

        hoja_w_real = sheets_lower[hoja_w.lower()]
        hoja_p_real = sheets_lower[hoja_p.lower()]

        try:
            df_w = pd.read_excel(xls, hoja_w_real)
            df_p = pd.read_excel(xls, hoja_p_real)
        except Exception as e:
            raise CommandError(f"Error leyendo hojas: {e}")

        df_w.columns = [str(c).strip() for c in df_w.columns]
        df_p.columns = [str(c).strip() for c in df_p.columns]

        # --- Detectar columnas de Weights ---
        # numéricas (dos pesos pf1/pf2)
        num_cols_w = df_w.select_dtypes(include="number").columns.tolist()
        if len(num_cols_w) < 2:
            raise CommandError("La hoja Weights debe tener al menos dos columnas numéricas (pf1/pf2).")
        col_pf1, col_pf2 = num_cols_w[:2]

        # identificador de activo: prioridad a 'activos', si no existe toma la primera no numérica que no sea fecha
        lower_map = {c.lower(): c for c in df_w.columns}
        if "activos" in lower_map:
            col_activo_w = lower_map["activos"]
        else:
            non_num_cols_w = [c for c in df_w.columns if c not in num_cols_w]
            fecha_aliases = {"fecha", "fechas", "date", "dates"}
            candidatos = [c for c in non_num_cols_w if c.lower() not in fecha_aliases]
            if not candidatos:
                raise CommandError("No se encontró columna de identificador de activo en Weights.")
            col_activo_w = candidatos[0]

        # --- Detectar si los weights vienen en porcentaje (>1) y normalizar ---
        pf1_max = pd.to_numeric(df_w[col_pf1], errors="coerce").max()
        pf2_max = pd.to_numeric(df_w[col_pf2], errors="coerce").max()
        # Si cualquiera supera 1, asumimos porcentaje (ej: 25 -> 0.25)
        weights_are_percent = (pd.notna(pf1_max) and pf1_max > 1) or (pd.notna(pf2_max) and pf2_max > 1)
        percent_divisor = Decimal("100") if weights_are_percent else Decimal("1")

        # --- Precios: primera columna fecha ---
        col_fecha_p = df_p.columns[0]
        try:
            df_p[col_fecha_p] = pd.to_datetime(df_p[col_fecha_p]).dt.date
        except Exception:
            raise CommandError("La primera columna de Precios debe ser una fecha válida.")

        activos_cols = df_p.columns[1:]
        if len(activos_cols) == 0:
            raise CommandError("La hoja Precios debe tener columnas de activos.")

        with transaction.atomic():
            pf1, _ = Portafolio.objects.get_or_create(nombre=pf1_name)
            pf2, _ = Portafolio.objects.get_or_create(nombre=pf2_name)

            # Crea/obtiene activos a partir de columnas de Precios
            activos = {}
            for col in activos_cols:
                simbolo = str(col).strip()
                a, _ = Activo.objects.get_or_create(simbolo=simbolo, defaults={"nombre": simbolo})
                activos[simbolo] = a

            # Carga precios
            precios_bulk = []
            for _, row in df_p.iterrows():
                fecha = row[col_fecha_p]
                for col in activos_cols:
                    val = row[col]
                    if pd.isna(val):
                        continue
                    precios_bulk.append(
                        Precio(activo=activos[str(col)], fecha=fecha, precio=Decimal(str(val)))
                    )
            if precios_bulk:
                #inserta la operación en la base de datos
                Precio.objects.bulk_create(precios_bulk, ignore_conflicts=True)

            # Carga weights en t0 (normalizando si venían en %)
            weights_bulk = []
            for _, row in df_w.iterrows():
                simbolo = str(row[col_activo_w]).strip()
                if simbolo not in activos:
                    a, _ = Activo.objects.get_or_create(simbolo=simbolo, defaults={"nombre": simbolo})
                    activos[simbolo] = a
                a = activos[simbolo]

                w1 = row[col_pf1]
                w2 = row[col_pf2]

                if pd.notna(w1):
                    w1_dec = (Decimal(str(w1)) / percent_divisor).quantize(Decimal("0.000000"))
                    weights_bulk.append(
                        Weight(portafolio=pf1, activo=a, fecha=fecha_inicial, weight=w1_dec)
                    )
                if pd.notna(w2):
                    w2_dec = (Decimal(str(w2)) / percent_divisor).quantize(Decimal("0.000000"))
                    weights_bulk.append(
                        Weight(portafolio=pf2, activo=a, fecha=fecha_inicial, weight=w2_dec)
                    )

            if weights_bulk:
                #inserta la operación en la base de datos
                Weight.objects.bulk_create(weights_bulk, ignore_conflicts=True)

        escala_txt = " (normalizados desde %)" if weights_are_percent else ""
        self.stdout.write(self.style.SUCCESS(f"Importación completada correctamente{escala_txt}."))
