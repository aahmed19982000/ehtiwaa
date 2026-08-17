from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView

from apps.dashboard.models import WishlistItem
from apps.reviews.models import Review

from .models import CartItem, Product
from .services import add_to_cart, create_order_from_cart, get_cart, set_cart_item_quantity


class ProductListView(ListView):
    model = Product
    template_name = "store/list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        return Product.objects.filter(is_active=True).order_by("-created_at")


class ProductDetailView(DetailView):
    model = Product
    template_name = "store/detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).prefetch_related("images")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_cart(self.request)
        cart_items = list(cart.items.select_related("product"))
        context["cart_items"] = cart_items
        context["cart_subtotal"] = sum((item.line_total for item in cart_items), start=0)

        content_type = ContentType.objects.get_for_model(Product)
        context["reviews"] = (
            Review.objects.filter(content_type=content_type, object_id=self.object.pk)
            .select_related("user")
            .order_by("-created_at")[:20]
        )

        context["is_wishlisted"] = (
            self.request.user.is_authenticated
            and WishlistItem.objects.filter(
                user=self.request.user, content_type=content_type, object_id=self.object.pk
            ).exists()
        )
        return context


class CartAddView(View):
    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)
        try:
            quantity = int(request.POST.get("quantity", 1))
        except ValueError:
            quantity = 1
        quantity = max(quantity, 1)

        if not product.is_in_stock:
            messages.error(request, _("هذا المنتج غير متوفر حاليًا."))
        else:
            item = add_to_cart(get_cart(request), product, quantity)
            if item:
                messages.success(request, _("تمت إضافة المنتج للسلة."))
            else:
                messages.error(request, _("الكمية المتاحة من هذا المنتج غير كافية."))
        return redirect("store:detail", slug=slug)


class CartView(View):
    template_name = "store/cart.html"

    def get(self, request):
        cart = get_cart(request)
        items = list(cart.items.select_related("product"))
        subtotal = sum((item.line_total for item in items), start=0)
        return render(
            request, self.template_name, {"cart": cart, "items": items, "subtotal": subtotal}
        )


class CartItemUpdateView(View):
    def post(self, request, item_id):
        item = get_object_or_404(CartItem, pk=item_id, cart=get_cart(request))
        try:
            quantity = int(request.POST.get("quantity", 0))
        except ValueError:
            quantity = 0

        if quantity <= 0:
            item.delete()
            messages.success(request, _("تم حذف المنتج من السلة."))
        else:
            updated = set_cart_item_quantity(item, quantity)
            if not updated:
                messages.error(request, _("تم حذف المنتج من السلة — غير متوفر بالمخزون."))
            elif updated.quantity < quantity:
                messages.error(request, _("تم تعديل الكمية حسب المتاح بالمخزون."))
            else:
                messages.success(request, _("تم تحديث الكمية."))
        return redirect("store:cart")


class CartCheckoutView(LoginRequiredMixin, View):
    login_url = "accounts:login"

    def post(self, request):
        cart = get_cart(request)
        if not cart.items.exists():
            messages.error(request, _("سلتك فارغة."))
            return redirect("store:cart")

        order = create_order_from_cart(request.user, cart)
        return redirect("payments:checkout", order_id=order.pk)
