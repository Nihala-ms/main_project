from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signin/', views.signin, name='signin'),
    path('service/', views.service, name='service'),
    path('about/', views.about, name='about'),
    path('doctor/', views.doctor, name='doctor'),
    path('doctorsdetails/<int:doctor_id>/', views.doctorsdetails, name='doctorsdetails'),
    path('department/', views.department, name='department'),
    path('appointment/', views.appointment, name='appointment'),
    path('signup/', views.signup, name='signup'),
    path('signup/registration_success', views.registration_success, name='registration_success'),   
    path('signin/patient_dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('signin/doctor_dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('signin/doctor_dashboard/doctor_profile', views.doctor_profile, name='doctor_profile'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('payment/<int:appointment_id>/', views.payment, name='payment'),
    path('logout/', views.logout_view, name='logout'),
    path('edit_doctor/<int:doctor_id>/', views.edit_doctor, name='edit_doctor'),
    path('delete_doctor/<int:doctor_id>/', views.delete_doctor, name='delete_doctor'),
    path('approve_doctor/<int:doctor_id>/', views.approve_doctor, name='approve_doctor'),
    path('write-prescription/<int:appointment_id>/', views.write_prescription, name='write_prescription'),
    path('view-prescription/<int:appointment_id>/', views.view_prescription, name='view_prescription'),
    path("add_medicine/", views.add_medicine, name="add_medicine"),
    path('edit_medicine/<int:medicine_id>/', views.edit_medicine, name='edit_medicine'),
    path('delete_medicine/<int:medicine_id>/', views.delete_medicine, name='delete_medicine'),
    path('contact/', views.contact, name='contact'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment/<int:appointment_id>/', views.payment, name='payment'),
    path('payment/success/<int:appointment_id>/', views.payment_success, name='payment_success'),
    path('payment/failed/<int:appointment_id>/', views.payment_failed, name='payment_failed'),
    path('patient/appointments/', views.patient_appointments, name='patient_appointments'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),
    path('update-order-status/<int:pk>/<str:status>/', views.update_order_status, name='update_order_status'),
    path('orders/<int:order_id>/update-status/<str:status>/', views.update_order_statuss, name='update_order_statuss'),

]
