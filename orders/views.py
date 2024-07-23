from django.shortcuts import render


def create_order(request):
    return render(request, 'create_orders.html')
