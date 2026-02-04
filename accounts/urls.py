from django.urls import path   
from .views import home, sign_up, signin_view, success, logout_view, profile_view, category_products, product_detail,cart_view,add_to_cart, remove_from_cart, buy_now, checkout, payment_page
from . import views

urlpatterns = [
    path('', home, name = "home"),
    path('signup/', sign_up, name="signup"),
    path("signin/", signin_view, name="signin"),
    path('success/', success, name='success'),
    path('logout/', logout_view, name="logout"),
    path('profile/', profile_view, name='profile'),
    path('category/<int:category_id>/', category_products, name='category_products'),
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', cart_view, name='cart_view'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('buy-now/<int:product_id>/', buy_now, name='buy_now'),
    path('checkout/', checkout, name='checkout'),
    #path("payment/", payment, name="payment_page"),
    path('save-card/', views.save_card, name='save_card'),
    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path("success/", success, name="success"),
    path("payment/", payment_page, name="payment_page"),
    #path("payment-success/", views.payment_success, name="payment_success"),
    path('order-placed/', views.order_placed, name='order_placed'),
    path('search/', views.search, name='search'),
    path('favourites/', views.favourite_products, name='favourite_products'),
    path("favourites/add/<int:product_id>/", views.add_to_favourites, name="add_to_favourites"),
    path("favourites/remove/<int:product_id>/", views.remove_from_favourites, name="remove_from_favourites"),
    path('select-address/<int:address_id>/', views.select_address, name='select_address'),
    path('address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('chatbot/',views.chatbot, name='chatbot'),
] 