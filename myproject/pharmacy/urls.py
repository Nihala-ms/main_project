from django.urls import path
from . import views

urlpatterns = [
    path('', views.pharmacy, name='pharmacy'),
    path('order_medicine/', views.order_medicine, name='order_medicine'),
    path("detailed/<int:id>/", views.detailed, name="detailed"),
    path('search_medicine/', views.search_medicine, name='search_medicine'),
    path('beauty/', views.beauty, name='beauty'),
    path('cart/', views.view_cart, name='view_cart'),
    path('pharmacy_auth/', views.pharmacy_auth, name='pharmacy_auth'),
    path('order-summary/', views.order_summary, name='order_summary'),
    path('logout/', views.user_logout, name='logout'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('add-to-cart/<int:item_id>/<str:item_type>/', views.add_to_cart, name='add_to_cart'),
    path('upload_prescription/', views.upload_prescription, name='upload_prescription'),
    path('update_cart/<int:item_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('order/payment/failed/<int:order_id>/', views.order_payment_failed, name='order_payment_failed'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    path('beauty_section/', views.product_list, name='beauty_section'),
    #path('orders/<int:user_id>', views.history, name='history'),
    #path('orders/<int:order_id>/', views.order_detail, name='order_detail'),





]