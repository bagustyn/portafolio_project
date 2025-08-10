from django.contrib import admin
from .models import Operacion, Portafolio, Activo, Precio, Weight, Cantidad, ValorPortafolio

# Registra el modelo Operacion
admin.site.register(Operacion)

# Registra el modelo Portafolio
admin.site.register(Portafolio)

# Registra el modelo Activo
admin.site.register(Activo)

# Registra el modelo Precio
admin.site.register(Precio)

# Registra el modelo Weight
admin.site.register(Weight)

# Registra el modelo Cantidad
admin.site.register(Cantidad)

# Registra el modelo ValorPortafolio
admin.site.register(ValorPortafolio)

admin.site.site_url = "/api/viz/"