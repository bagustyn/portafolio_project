from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal, InvalidOperation
from datetime import datetime

from inversiones.models import (
    Activo, Portafolio, Precio, Weight, Cantidad, ValorPortafolio
)

class Command(BaseCommand):
    help = (
        "Calcula C_{i,0} = (w_{i,0} * V0) / P_{i,0} para todos los activos y portafolios "
        "en la fecha t0 y guarda en la tabla Cantidad."
    )

    def add_arguments(self, parser):
        parser.add_argument("--t0", default="2022-02-15",
                            help="Fecha inicial t0 (YYYY-MM-DD). Default: 2022-02-15")
        parser.add_argument("--v0", default="1000000000",
                            help="Valor inicial del portafolio (entero o decimal). Default: 1,000,000,000")
        parser.add_argument("--pf1", default="Portafolio 1",
                            help="Nombre del portafolio 1 (debe existir o se creará).")
        parser.add_argument("--pf2", default="Portafolio 2",
                            help="Nombre del portafolio 2 (debe existir o se creará).")
        parser.add_argument("--overwrite", action="store_true",
                            help="Si existe una Cantidad para (portafolio, activo), la reemplaza.")

    def handle(self, *args, **opts):
        try:
            t0 = datetime.strptime(opts["t0"], "%Y-%m-%d").date()
        except Exception:
            raise CommandError("Parámetro --t0 inválido. Use formato YYYY-MM-DD.")

        try:
            V0 = Decimal(str(opts["v0"]))
        except InvalidOperation:
            raise CommandError("Parámetro --v0 inválido.")

        pf_names = [opts["pf1"], opts["pf2"]]

        # Asegura portafolios
        pfs = []
        for name in pf_names:
            pf, _ = Portafolio.objects.get_or_create(nombre=name)
            pfs.append(pf)

        # Trae weights y precios en t0
        weights = Weight.objects.filter(fecha=t0).select_related("portafolio", "activo")
        if not weights.exists():
            raise CommandError(f"No hay weights en t0={t0}. Importe primero los datos.")

        precios = {
            (pr.activo_id, pr.fecha): pr.precio
            for pr in Precio.objects.filter(fecha=t0).only("activo_id", "fecha", "precio")
        }
        if not precios:
            raise CommandError(f"No hay precios en t0={t0}.")

        creados = 0
        actualizados = 0
        omitidos = 0

        with transaction.atomic():
            # procesa por portafolio-activo
            for w in weights:
                key = (w.activo_id, t0)
                if key not in precios:
                    omitidos += 1
                    continue
                Pi0 = precios[key]              # precio P_{i,0}
                wi0 = w.weight                  # weight w_{i,0}
                try:
                    Ci0 = (wi0 * V0) / Pi0
                except (InvalidOperation, ZeroDivisionError):
                    omitidos += 1
                    continue

                if opts["overwrite"]:
                    obj, created = Cantidad.objects.update_or_create(
                        portafolio=w.portafolio, activo=w.activo,
                        defaults={"cantidad": Ci0}
                    )
                    if created:
                        creados += 1
                    else:
                        actualizados += 1
                else:
                    obj, created = Cantidad.objects.get_or_create(
                        portafolio=w.portafolio, activo=w.activo,
                        defaults={"cantidad": Ci0}
                    )
                    if created:
                        creados += 1
                    else:
                        # ya existe y no se sobreescribe
                        omitidos += 1

            # Guarda el valor total del portafolio en t0 (útil para checks posteriores)
            for pf in pfs:
                ValorPortafolio.objects.update_or_create(
                    portafolio=pf, fecha=t0, defaults={"valor_total": V0}
                )

        self.stdout.write(self.style.SUCCESS(
            f"Listo. Cantidades creadas: {creados}, actualizadas: {actualizados}, omitidas: {omitidos}."
        ))
