from django.contrib import admin
from .models import User
from .models import Medicine, Brand,CartItems,Orders,OrderItem,Cart,Products


admin.site.register(Brand)
admin.site.register(Medicine)
admin.site.register(CartItems)
admin.site.register(Orders)
admin.site.register(User)
admin.site.register(Cart)
admin.site.register(Products)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'medicine', 'quantity', 'has_prescription')
    readonly_fields = ('has_prescription',)
    
    def has_prescription(self, obj):
        return bool(obj.prescription)
    has_prescription.boolean = True
    has_prescription.short_description = 'Prescription Uploaded'

admin.site.register(OrderItem, OrderItemAdmin)

