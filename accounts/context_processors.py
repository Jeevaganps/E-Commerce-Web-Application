from .models import Address

def selected_address(request):
    address = None
    if request.user.is_authenticated:
        address_id = request.session.get('selected_address_id')
        if address_id:
            try:
                address = Address.objects.get(id=address_id, user=request.user)
            except Address.DoesNotExist:
                address = None
    return {'selected_address': address}
