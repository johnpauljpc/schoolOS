from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # Fee Categories
    path('categories/', views.fee_category_list, name='category-list'),
    path('categories/add/', views.fee_category_create, name='category-create'),
    path('categories/<int:pk>/edit/', views.fee_category_update, name='category-update'),
    # Fee Structures
    path('structures/', views.fee_structure_list, name='structure-list'),
    path('structures/add/', views.fee_structure_create, name='structure-create'),
    path('structures/<int:pk>/edit/', views.fee_structure_update, name='structure-update'),
    # Invoices
    path('invoices/', views.invoice_list_view, name='invoice-list'),
    path('invoices/generate/', views.generate_invoices_view, name='generate-invoices'),
    path('invoices/generate/single/<int:student_pk>/', views.invoice_generate_single_view, name='generate-single-invoice'),
    path('invoices/<int:pk>/', views.invoice_detail_view, name='invoice-detail'),
    # Payments
    path('pay/offline/', views.offline_payment_view, name='offline-payment'),
    path('pay/offline/<int:invoice_pk>/', views.offline_payment_view, name='offline-payment-invoice'),
    path('pay/online/<int:invoice_pk>/', views.online_payment_initiate_view, name='online-payment'),
    path('pay/callback/', views.paystack_callback_view, name='paystack-callback'),
    path('pay/webhook/', views.paystack_webhook_view, name='paystack-webhook'),
    # Receipts
    path('receipts/<int:pk>/', views.receipt_detail_view, name='receipt-detail'),
    path('receipts/<int:pk>/pdf/', views.receipt_pdf_view, name='receipt-pdf'),
    # Reports
    path('reports/history/', views.payment_history_view, name='payment-history'),
    path('reports/history/<int:student_pk>/', views.payment_history_view, name='payment-history-student'),
    path('reports/outstanding/', views.outstanding_fees_report_view, name='outstanding-fees'),
    path('reports/revenue/', views.revenue_report_view, name='revenue-report'),
    path('reports/summary/', views.financial_summary_view, name='financial-summary'),
    path('reports/export/excel/', views.export_report_excel_view, name='export-excel'),
    path('reports/export/pdf/', views.export_report_pdf_view, name='export-pdf'),
]
