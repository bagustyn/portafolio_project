# inversiones/views.py
import json  # Importa el módulo json para cargar los datos JSON
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.utils.dateparse import parse_date
from django.db import transaction
from django.db.models import F  # Asegúrate de importar 'F'
from .models import Operacion, Cantidad, Portafolio, Activo, Precio
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from decimal import Decimal

class RegistrarOperacionAPIView(View):
    @method_decorator(csrf_exempt)  # Desactiva CSRF para esta vista
    def post(self, request, pf_id: int):
        try:
            # Usa json.loads para parsear el cuerpo de la solicitud
            data = json.loads(request.body.decode('utf-8'))  # Parseo del cuerpo JSON
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Formato JSON incorrecto."}, status=400)

        if not isinstance(data, list):
            return JsonResponse({"detail": "Formato de datos incorrecto."}, status=400)

        operaciones = []
        with transaction.atomic():
            for op in data:
                try:
                    pf = Portafolio.objects.get(id=pf_id)
                    activo = Activo.objects.get(simbolo=op["activo"])
                    fecha = op["fecha"]
                    cantidad = op["cantidad"]
                    tipo = op["tipo"]

                    if tipo == "compra":
                        # Aumentar cantidad de activo en portafolio
                        Cantidad.objects.filter(portafolio=pf, activo=activo).update(cantidad=F('cantidad') + cantidad)
                    elif tipo == "venta":
                        # Reducir cantidad de activo en portafolio
                        Cantidad.objects.filter(portafolio=pf, activo=activo).update(cantidad=F('cantidad') - cantidad)

                    # Registrar operación "crea objeto"
                    operaciones.append(Operacion(portafolio=pf, activo=activo, fecha=fecha, cantidad=cantidad, tipo=tipo))

                except Exception as e:
                    return JsonResponse({"detail": str(e)}, status=400)
            #inserta la operación en la base de datos
            Operacion.objects.bulk_create(operaciones)

            # Recalcular C_{i,t}, w_{i,t}, y V_t después de cada operación
            self.recalcular_portafolio(pf)

        return JsonResponse({"detail": "Operaciones registradas y portafolio recalculado."}, status=201)

    def recalcular_portafolio(self, pf: Portafolio):
        """
        Recalcula las cantidades, los pesos y el valor total del portafolio.
        """
        # Obtenemos todas las cantidades actualizadas
        cantidades = Cantidad.objects.filter(portafolio=pf).select_related("activo")
        activos = {c.activo_id: c for c in cantidades}

        # Calculamos el valor total V_t para cada fecha
        for cantidad in cantidades:
            activo = cantidad.activo
            precios = Precio.objects.filter(activo=activo)

            # Recalcular los pesos w_{i,t} y el valor total V_t
            for precio in precios:
                xi = precio.precio * cantidad.cantidad
                Vt = sum([p.precio * c.cantidad for c, p in zip(cantidades, precios)])

                # Actualizar los pesos y cantidades
                w = xi / Vt if Vt != 0 else 0

                # Actualizamos los datos en la base de datos
                Cantidad.objects.filter(portafolio=pf, activo=activo).update(cantidad=xi)  # Eliminado 'fecha'
                # Aquí puedes también actualizar el valor total en alguna tabla si es necesario

class EvolucionPortafolioAPIView(View):
    """
    GET /api/portafolios/<pf_id>/evolucion/?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD
    Devuelve Vt y w_{i,t} para el rango solicitado.
    """
    def get(self, request, pf_id: int):
        fecha_inicio = request.GET.get("fecha_inicio")
        fecha_fin = request.GET.get("fecha_fin")

        # Validación básica de fechas
        try:
            fi = parse_date(fecha_inicio) if fecha_inicio else None
            ff = parse_date(fecha_fin) if fecha_fin else None
        except Exception:
            return JsonResponse({"detail": "Parámetros de fecha inválidos."}, status=400)
        if not fi or not ff or fi > ff:
            return JsonResponse(
                {"detail": "Debe enviar fecha_inicio y fecha_fin válidas (YYYY-MM-DD) y fi <= ff."},
                status=400
            )

        try:
            pf = Portafolio.objects.get(pk=pf_id)
        except Portafolio.DoesNotExist:
            return JsonResponse({"detail": f"Portafolio {pf_id} no existe."}, status=404)

        # Cantidades fijas c_{i,0}
        cantidades_qs = Cantidad.objects.filter(portafolio=pf).select_related("activo")
        if not cantidades_qs.exists():
            return JsonResponse(
                {"detail": "No hay cantidades (C_{i,0}) para este portafolio. Ejecute calc_cantidades_iniciales."},
                status=400
            )

        cantidades = {c.activo_id: c.cantidad for c in cantidades_qs}  # activo_id -> c_i
        activos_map = {c.activo_id: c.activo.simbolo for c in cantidades_qs}
        activo_ids = list(cantidades.keys())

        # Precios en rango para esos activos
        precios_qs = (Precio.objects
                      .filter(activo_id__in=activo_ids, fecha__range=(fi, ff))
                      .values("activo_id", "fecha", "precio"))
        if not precios_qs:
            return JsonResponse({"detail": "No hay precios para el rango solicitado."}, status=400)

        # x_{i,t}, V_t y w_{i,t}
        by_date = {}  # fecha -> {"xi": {activo_id: xi}, "Vt": Decimal}
        for row in precios_qs:
            aid = row["activo_id"]
            fch = row["fecha"]
            p = row["precio"]
            ci = cantidades.get(aid)
            if ci is None:
                continue
            xi = p * ci
            d = by_date.setdefault(fch, {"xi": {}, "Vt": Decimal("0")})
            d["xi"][aid] = xi
            d["Vt"] += xi

        fechas = sorted(by_date.keys())
        vt_series, weights_series = [], []
        for fch in fechas:
            Vt = by_date[fch]["Vt"]
            vt_series.append({"fecha": fch.isoformat(), "valor": float(Vt)})

            xi_map = by_date[fch]["xi"]
            w_list = []
            if Vt != 0:
                for aid, xi in xi_map.items():
                    w_list.append({
                        "activo": activos_map.get(aid, str(aid)),
                        "valor": float(xi / Vt)
                    })
            weights_series.append({"fecha": fch.isoformat(), "w": w_list})

        data = {
            "portafolio": {"id": pf.id, "nombre": pf.nombre},
            "rango": {"inicio": fi.isoformat(), "fin": ff.isoformat()},
            "Vt": vt_series,
            "weights": weights_series,
        }
        return JsonResponse(data, status=200, json_dumps_params={"ensure_ascii": False})

def viz_evolucion(request):
    # defaults (primer portafolio + rango total de precios)
    pf = Portafolio.objects.order_by("id").first()
    fi = Precio.objects.order_by("fecha").values_list("fecha", flat=True).first()
    ff = Precio.objects.order_by("-fecha").values_list("fecha", flat=True).first()

    ctx = {
        "defaults": {
            "pf_id": pf.id if pf else 1,
            "fi": fi.isoformat() if fi else "2022-02-15",
            "ff": ff.isoformat() if ff else "2023-02-16",
        }
    }
    return render(request, "inversiones/evolucion.html", ctx)