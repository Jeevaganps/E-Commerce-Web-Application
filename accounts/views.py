from django.shortcuts import render
from django.http import HttpResponse
from .forms import UserForm, AddressForm
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import Category, Product, cart, Address, Favourite
from django.shortcuts import get_object_or_404
from django.contrib import messages
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
from .models import SavedCard
from openai import OpenAI
import os

# Create your views here.
def home(request):
    categories = Category.objects.all()
    products = Product.objects.all()
    # remove duplicate variable and pass context dict correctly
    return render(request, 'success.html', {
        'categories': categories,
        'products': products,
    })


def sign_up(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Get the password from the form
            password = form.cleaned_data.get('password')
            # Set the password (this handles the hashing)
            user.set_password(password)
            user.save()
            return render(request, "success.html")
    else:
        form = UserForm()
    return render(request, "signup.html", {'form': form})

# API + HTML view for signin
def signin_view(request):
    if request.method == "POST":
        email = request.POST.get("email")  # Form sends as email
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect("home")   # uses urls.py → path('', home, name="home")
        else:
            return render(request, "signin.html", {"error": "Invalid email or password"})
    return render(request, "signin.html")

def success(request):
    return render(request, "success.html") 

def logout_view(request):
    logout(request)
    return redirect("signin")

@login_required
def profile_view(request):
    user = request.user
    addresses = user.address_set.all()  # get all addresses for this user

    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = user  # link address to this user
            address.save()
            return redirect('profile')  # reload page after saving
    else:
        form = AddressForm()

    return render(request, "profile.html", {
        "user": user,
        "addresses": addresses,
        "form": form
    })

    #user = request.user
    #return render(request, "profile.html", {"user": user})
       #if user is not None:
            #login(request, user)
            #return JsonResponse({"status": "success", "message": "Login successful!"})
        #else:
           #return JsonResponse({"status": "error", "message": "Invalid email or password"})
    
    # GET request → render signin page

def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)
    return render(request, 'product.html', {
        'products': products
    })

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    in_stock = product.quantity > 0
    is_favourite = False
    if request.user.is_authenticated:
        is_favourite = Favourite.objects.filter(
            user=request.user,
            product=product
        ).exists()

    return render(request, 'product_detail.html', {
        'product': product,
        'in_stock': in_stock,
        'is_favourite': is_favourite,
    })

@login_required
def cart_view(request):
    # Only show cart items for active products
    cart_items = cart.objects.filter(user=request.user, product__is_active=True)

    total_price = sum(item.get_total_price() for item in cart_items)

    # Optionally remove inactive products silently
    removed_items = cart.objects.filter(user=request.user, product__is_active=False)
    if removed_items.exists():
        removed_items.delete()
        messages.warning(request, "Some inactive products were removed from your cart.")

    return render(request, "cart.html", {
        'cart_items': cart_items,
        'total_price': total_price
    })

@login_required
def remove_from_cart(request, item_id):
    if request.method == "POST":
        cart_item = get_object_or_404(cart, id=item_id, user=request.user)
        product_name = cart_item.product.name
        cart_item.delete()
        messages.success(request, f"'{product_name}' has been removed from your cart!")
        return redirect('cart_view')
    return redirect('cart_view')


@login_required
def add_to_cart(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.POST.get('quantity', 0))

        #Check if product is active
        if not product.is_active:
            messages.error(request, "This product is currently unavailable.")
            return redirect('product_detail', product_id=product_id)

        #Check if product is out of stock
        if product.quantity <= 0:
            messages.error(request, "Sorry, this product is out of stock.")
            return redirect('product_detail', product_id=product_id)

        #Prevent adding invalid quantity
        if quantity <= 0:
            messages.error(request, "Please select a valid quantity.")
            return redirect('product_detail', product_id=product_id)

        #Prevent adding more than available stock
        if quantity > product.quantity:
            messages.error(request, f"Only {product.quantity} items left in stock.")
            return redirect('product_detail', product_id=product_id)

        #Add or update cart item
        cart_item, created = cart.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity = quantity  # overwrite with new quantity
            cart_item.save()

        messages.success(request, f"{product.name} added to your cart.")
        return redirect('cart_view')

    # If not POST
    return redirect('home')

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
@csrf_exempt
def create_payment_intent(request):
    if request.method == "POST":
        data = json.loads(request.body)

        amount = int(data["amount"]) * 100  # convert to paise

        # Create Stripe Payment Intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="inr"
        )

        return JsonResponse({
            "clientSecret": intent.client_secret
        })


@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user_addresses = Address.objects.filter(user=request.user)

    price = product.discount_price if product.discount_price else product.price
    total_amount = price
    shipping = 99
    grand_total = price + shipping

    if request.method == "POST":
        selected_address_id = request.POST.get('selected_address')

        if selected_address_id == 'new':
            addr = Address.objects.create(
                user=request.user,
                full_name=request.POST['full_name'],
                phone=request.POST['phone'],
                address_line=request.POST['address_line'],
                city=request.POST['city'],
                state=request.POST['state'],
                pincode=request.POST['pincode']
            )
        else:
            addr = Address.objects.get(id=selected_address_id)

        # SAVE TO SESSION
        request.session["order_type"] = "buy_now"
        request.session["total_amount"] = float(total_amount)      # NEW
        request.session["shipping_amount"] = float(shipping)       # NEW
        request.session["grand_total"] = float(grand_total)
        request.session["product_id"] = product_id
        request.session["address_id"] = addr.id

        return redirect("payment_page")  # ← IMPORTANT

    return render(request, 'buy_now.html', {
        'product': product,
        'addresses': user_addresses,
        "total_amount": total_amount,
        "shipping_amount": shipping,
        "grand_total": grand_total,
    })

@login_required
def checkout(request):
    cart_items = cart.objects.filter(user=request.user)
    user_addresses = Address.objects.filter(user=request.user)

    total_amount = 0
    for item in cart_items:
        price = item.product.discount_price if item.product.discount_price else item.product.price
        total_amount += price * item.quantity

    shipping = 99
    grand_total = total_amount + shipping

    # GET
    if request.method == "GET":
        return render(request, "checkout.html", {
            "cart_items": cart_items,
            "addresses": user_addresses,
            "total_amount": total_amount,
            "shipping_amount": shipping,
            "grand_total": grand_total,
        })

    # POST
    if request.method == "POST":
        selected_address_id = request.POST.get("selected_address")

        if not selected_address_id:
            return render(request, "checkout.html", {
                "cart_items": cart_items,
                "addresses": user_addresses,
                "total_amount": total_amount,
                "shipping_amount": shipping,
                "grand_total": grand_total,
                "error": "Please select an address"
            })

        # NEW ADDRESS
        if selected_address_id == "new":
            addr = Address.objects.create(
                user=request.user,
                full_name=request.POST["full_name"],
                phone=request.POST["phone"],
                address_line=request.POST["address_line"],
                city=request.POST["city"],
                state=request.POST["state"],
                pincode=request.POST["pincode"],
            )
        else:
            addr = get_object_or_404(Address, id=selected_address_id, user=request.user)

        # SAVE TO SESSION
        request.session["order_type"] = "cart"
        request.session["total_amount"] = float(total_amount)      # NEW
        request.session["shipping_amount"] = float(shipping)       # NEW
        request.session["grand_total"] = float(grand_total)
        request.session["address_id"] = addr.id

        return redirect("payment_page")   # ← IMPORTANT


@login_required
@csrf_exempt
def save_card(request):
    data = json.loads(request.body)

    SavedCard.objects.create(
        user=request.user,
        payment_method=data["payment_method"],
        brand=data["brand"],
        last4=data["last4"],
        exp_month=data["exp_month"],
        exp_year=data["exp_year"],
    )

    return JsonResponse({"status": "saved"})

'''@login_required
def payment(request):
    grand_total = request.session.get("grand_total")
    order_type = request.session.get("order_type")
    address_id = request.session.get("address_id")

    if not grand_total:
        messages.error(request, "Payment session expired.")
        return redirect("home")

    selected_address = Address.objects.get(id=address_id)

    return render(request, "payment.html", {
        "grand_total": grand_total,
        "selected_address": selected_address,
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
    })'''

'''@login_required
def payment_page(request):
    total_amount = request.GET.get("amount")
    address_id = request.GET.get("address")

    address = Address.objects.get(id=address_id)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    intent = stripe.PaymentIntent.create(
        amount=int(total_amount) * 100,   # Convert rupees → paisa
        currency="inr",
        automatic_payment_methods={"enabled": True}
    )

    return render(request, "payment.html", {
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
        "clientSecret": intent.client_secret,
        "total_amount": total_amount,
        "shipping_amount": 99,
        "grand_total": int(total_amount) + 99,
        "selected_address": address
    })'''

@login_required
def payment_page(request):
    # Read the session data saved in checkout() or buy_now()
    total_amount = request.session.get("total_amount", 0)
    shipping_amount = request.session.get("shipping_amount", 0)
    product_id = request.session.get('product_id')
    grand_total = request.session.get('grand_total', 0)
    address_id = request.session.get('address_id')

    # Derive item price and shipping for the template
    item_price = float(total_amount)
    shipping = float(shipping_amount)

    # Fetch selected address object if available
    selected_address = None
    if address_id:
        try:
            selected_address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            selected_address = None

    context = {
        "total_amount": total_amount,
        "shipping_amount": shipping_amount,
        "grand_total": grand_total,
        "product_id": product_id,
        "selected_address": selected_address,
        "item_price": item_price,
        "shipping": shipping,
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
    }

    return render(request, "payment.html", context)


#def payment_success(request):
    #return render(request, "order placed.html")

def order_placed(request):
    return render(request, 'order_placed.html')

def search(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(name__icontains=query, is_active=True) if query else []
    return render(request, 'search.html', {
        'products': products,
        'query': query
    })

@login_required
def favourite_products(request):
    favs = Favourite.objects.filter(user=request.user)
    return render(request, "favourites.html", {"favs": favs})

@login_required
def add_to_favourites(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Favourite.objects.get_or_create(user=request.user, product=product)
    return redirect('product_detail', product_id=product.id)

@login_required
def remove_from_favourites(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Favourite.objects.filter(user=request.user, product=product).delete()
    return redirect('product_detail', product_id=product.id)

def select_address(request, address_id):
    address = Address.objects.get(id=address_id, user=request.user)
    request.session['selected_address_id'] = address.id
    return redirect('home')

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('profile')   # redirect to saved addresses page
    else:
        form = AddressForm(instance=address)

    return render(request, 'edit_address.html', {'form': form})

def category_products(request, category_id):
    products = Product.objects.filter(category_id=category_id)

    # SORT
    sort_by = request.GET.get("sort")
    if sort_by == "price_low":
        products = products.order_by("price")
    elif sort_by == "price_high":
        products = products.order_by("-price")
    elif sort_by == "newest":
        products = products.order_by("-id")
    elif sort_by == "oldest":
        products = products.order_by("id")

    # FILTER
    filter_by = request.GET.get("filter")
    if filter_by == "in_stock":
        products = products.filter(quantity__gt=0)
    elif filter_by == "out_stock":
        products = products.filter(quantity=0)

    return render(request, "product.html", {"products": products})

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@csrf_exempt
def chatbot(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body.decode("utf-8"))
    user_message = data.get("message", "")

    if not user_message:
        return JsonResponse({"error": "Message is required"}, status=400)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful ecommerce assistant. Answer briefly and clearly."},
                {"role": "user", "content": user_message},
            ],
        )

        answer = response.choices[0].message.content
        return JsonResponse({"reply": answer})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)