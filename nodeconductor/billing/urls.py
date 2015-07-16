from django.conf.urls import patterns

from nodeconductor.billing import views


def register_in(router):
    router.register(r'billing', views.BillingViewSet, base_name='billing')
    router.register(r'invoices', views.InvoiceViewSet)
    router.register(r'payments', views.PaymentView, base_name='payment')


urlpatterns = patterns(
    '',
)
