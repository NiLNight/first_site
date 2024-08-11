from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView

import orders
from carts.models import Cart
from common.mixins import CacheMixins
from orders.models import OrderItem, Order
from users.forms import UserLoginForm, UserRegisterForm, ProfileForm


class UserLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = UserLoginForm

    def get_success_url(self):
        redirect_page = self.request.GET.get('next', None)
        if redirect_page and redirect_page != reverse('users:logout'):
            return redirect_page
        return reverse_lazy('main:index')

    def form_valid(self, form):
        session_key = self.request.session.session_key
        user = form.get_user()

        if user:
            auth.login(self.request, user)
            if session_key:
                forgot_carts = Cart.objects.filter(user=user)
                if forgot_carts.exists():
                    forgot_carts.delete()
                Cart.objects.filter(session_key=session_key).update(user=user)

                messages.success(self.request, f'Вы вошли в аккаунт {user.username}')
                return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Home - авторизация'
        return context


# def login(request):
#     if request.method == 'POST':
#         form = UserLoginForm(data=request.POST)
#         if form.is_valid():
#             username = request.POST['username']
#             password = request.POST['password']
#             user = auth.authenticate(username=username, password=password)
#
#             session_key = request.session.session_key
#
#             if user:
#                 auth.login(request, user)
#                 messages.success(request, f'Вы вошли в аккаунт {username}')
#
#                 if session_key:
#                     forgot_carts = Cart.objects.filter(user=user)
#                     if forgot_carts.exists():
#                         forgot_carts.delete()
#                     Cart.objects.filter(session_key=session_key).update(user=user)
#
#                 redirect_page = request.POST.get('next', None)
#
#                 if redirect_page and redirect_page != reverse('users:logout'):
#                     return HttpResponseRedirect(request.POST.get('next'))
#                 return HttpResponseRedirect(reverse('main:index'))
#     else:
#         form = UserLoginForm()
#     context = {
#         'title': 'Home - авторизация',
#         'form': form,
#     }
#     return render(request, 'users/login.html', context)


class UserRegisterView(CreateView):
    template_name = 'users/registration.html'
    form_class = UserRegisterForm
    success_url = reverse_lazy('users:profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Home - Регистрация'
        return context

    def form_valid(self, form):
        session_key = self.request.session.session_key
        user = form.instance
        if user:
            form.save()
            auth.login(self.request, user)

        if session_key:
            Cart.objects.filter(session_key=session_key).update(user=user)
        messages.success(self.request, f'Пользователь {user.username} зарегистрирован')
        return HttpResponseRedirect(self.success_url)


# def registration(request):
#     if request.method == 'POST':
#         form = UserRegisterForm(data=request.POST)
#         if form.is_valid():
#             form.save()
#
#             session_key = request.session.session_key
#
#             user = form.instance
#             auth.login(request, user)
#             if session_key:
#                 Cart.objects.filter(session_key=session_key).update(user=user)
#             messages.success(request, f'Пользователь {request.user.username} зарегистрирован')
#             return HttpResponseRedirect(reverse('main:index'))
#     else:
#         form = UserRegisterForm()
#     context = {
#         'title': 'Home - Регистрация',
#         'form': form,
#     }
#     return render(request, 'users/registration.html', context)


class UsrProfileView(LoginRequiredMixin, CacheMixins, UpdateView):
    template_name = 'users/profile.html'
    form_class = ProfileForm
    success_url = reverse_lazy('users:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Профиль обновлен')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Home - Кабинет"

        orders = Order.objects.filter(user=self.request.user).prefetch_related(
            Prefetch(
                'orderitem_set',
                queryset=OrderItem.objects.select_related('product'),
            )
        ).order_by('-id')

        context['orders'] = self.set_get_cache(orders, f'user_{self.request.user.id}_orders', 60 * 2)
        return context

    def form_invalid(self, form):
        messages.error(self.request, 'Произошла ошибка')
        return super().form_invalid(form)


# @login_required(login_url='users:login')
# def profile(request):
#     if request.method == 'POST':
#         form = ProfileForm(data=request.POST, instance=request.user, files=request.FILES)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Профиль обновлен')
#             return HttpResponseRedirect(reverse('users:profile'))
#     else:
#         form = ProfileForm(instance=request.user)
#
#     orders = Order.objects.filter(user=request.user).prefetch_related(
#         Prefetch(
#             "orderitem_set",
#             queryset=OrderItem.objects.select_related("product"),
#         )
#     ).order_by("-id")
#     context = {
#         'title': "Home - Кабинет",
#         'form': form,
#         'orders': orders,
#     }
#     return render(request, 'users/profile.html', context)


class UserCartView(TemplateView):
    template_name = 'users/users_cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Home - Kорзина'
        return context


# def users_cart(request):
#     return render(request, 'users/users_cart.html')


@login_required
def logout(request):
    messages.success(request, f'Вы вышли из аккаунта "{request.user.username}"')
    auth.logout(request)
    return redirect(reverse('main:index'))
