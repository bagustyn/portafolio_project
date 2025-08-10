# inversiones/models.py
from django.db import models

class Operacion(models.Model):
    TIPO_CHOICES = [
        ('compra', 'Compra'),
        ('venta', 'Venta')
    ]
    portafolio = models.ForeignKey('Portafolio', on_delete=models.CASCADE)  # Eliminado el import
    activo = models.ForeignKey('Activo', on_delete=models.CASCADE)  # Eliminado el import
    fecha = models.DateField()
    cantidad = models.DecimalField(max_digits=20, decimal_places=2)
    tipo = models.CharField(max_length=6, choices=TIPO_CHOICES)

    def __str__(self):
        return f"{self.tipo.capitalize()} {self.cantidad} {self.activo} en {self.fecha}"

class Activo(models.Model):
    nombre = models.CharField(max_length=100)
    simbolo = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.simbolo}"

class Portafolio(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Precio(models.Model):
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE)
    fecha = models.DateField()
    precio = models.DecimalField(max_digits=20, decimal_places=6)

    class Meta:
        unique_together = ('activo', 'fecha')

class Weight(models.Model):
    portafolio = models.ForeignKey(Portafolio, on_delete=models.CASCADE)
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE)
    fecha = models.DateField()
    weight = models.DecimalField(max_digits=10, decimal_places=6)

    class Meta:
        unique_together = ('portafolio', 'activo', 'fecha')

class Cantidad(models.Model):
    portafolio = models.ForeignKey(Portafolio, on_delete=models.CASCADE)
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=20, decimal_places=6)

    class Meta:
        unique_together = ('portafolio', 'activo')

class ValorPortafolio(models.Model):
    portafolio = models.ForeignKey(Portafolio, on_delete=models.CASCADE)
    fecha = models.DateField()
    valor_total = models.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        unique_together = ('portafolio', 'fecha')
