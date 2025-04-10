from django.contrib import admin
from .models import User
from .models import Medicine, Brand,CartItems,Orders,OrderItem,Cart,Products


admin.site.register(Brand)
admin.site.register(Medicine)
admin.site.register(CartItems)
admin.site.register(Orders)
admin.site.register(User)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(Products)


