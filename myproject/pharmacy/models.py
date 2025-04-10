from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from decimal import Decimal
from django.utils import timezone
import uuid



# Create your models here.
# Custom User Model
class User(models.Model):
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=100)
    password = models.CharField(max_length=255, null=True, blank=True)
    

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Medicine(models.Model):
    name = models.CharField(max_length=100)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='medicines')
    dosage = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to='medicine_images/')
    description = models.TextField(blank=True, null=True)
    key_benefits = models.TextField(blank=True,null=True)
    how_to_use = models.TextField(blank=True,null=True)
    safety_information = models.TextField(blank=True,null=True)
    other_information = models.TextField(blank=True,null=True)

    
    # Additional required fields
    manufacturer = models.CharField(max_length=100)
    manufacturer_address = models.TextField(max_length=500,default="thrissur round ,kerala")
    expiry_date = models.DateField()
    category = models.CharField(max_length=100)
    prescription_required = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.dosage}"

class Products(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to='products/')
    category = models.CharField(max_length=100)
    is_trending = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    stock = models.PositiveIntegerField(default=0)


    def discount_percentage(self):
        if self.discount_price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0
    
    def get_discount_amount(self):
        return self.price - self.discount_price
    
    def __str__(self):
        return self.name

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart #{self.id} - {self.user.name}"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

class CartItems(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE,null=True, blank=True)
    product = models.ForeignKey(Products, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    prescription = models.FileField(upload_to='prescriptions/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(medicine__isnull=False) | models.Q(product__isnull=False),
                name='cart_item_has_medicine_or_product'
            ),
            models.CheckConstraint(
                check=~models.Q(medicine__isnull=False, product__isnull=False),
                name='cart_item_not_both_medicine_and_product'
            )
        ]

    def __str__(self):
        if self.medicine:
            return f"{self.quantity} x {self.medicine.name}"
        elif self.product:
            return f"{self.quantity} x {self.product.name}"
        return f"Cart item #{self.id}"

    @property
    def total_price(self):
        return Decimal(self.medicine.price) * Decimal(self.quantity)

class Orders(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHODS = [
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    order_number = models.CharField(max_length=20, unique=True,blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=100, blank=True, null=True)
    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        return f"ORD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Orders, related_name='items', on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True)
    product = models.ForeignKey(Products, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(medicine__isnull=False) | models.Q(product__isnull=False),
                name='order_item_has_medicine_or_product'
            ),
            models.CheckConstraint(
                check=~models.Q(medicine__isnull=False, product__isnull=False),
                name='order_item_not_both_medicine_and_product'
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.medicine.name if self.medicine else 'Deleted Medicine'}"

    @property
    def total_price(self):
        return Decimal(self.price) * Decimal(self.quantity)

# models.py



