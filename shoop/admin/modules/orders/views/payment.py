# -*- coding: utf-8 -*-
# This file is part of Shoop.
#
# Copyright (c) 2012-2016, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

from django import forms
from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic import UpdateView

from shoop.admin.toolbar import PostActionButton, Toolbar
from shoop.admin.utils.forms import add_form_errors_as_messages
from shoop.admin.utils.urls import get_model_url
from shoop.core.excs import NoPaymentToCreateException
from shoop.core.models import Order
from shoop.utils.money import Money


class OrderCreatePaymentView(UpdateView):
    model = Order
    template_name = "shoop/admin/orders/create_payment.jinja"
    context_object_name = "order"
    form_class = forms.Form  # Augmented manually

    def get_context_data(self, **kwargs):
        context = super(OrderCreatePaymentView, self).get_context_data(**kwargs)
        context["title"] = _("Create Payment -- %s") % context["order"]
        context["toolbar"] = Toolbar([
            PostActionButton(
                icon="fa fa-check-circle",
                form_id="create_payment",
                text=_("Create Payment"),
                extra_css_class="btn-success",
            ),
        ])
        return context

    def get_form_kwargs(self):
        kwargs = super(OrderCreatePaymentView, self).get_form_kwargs()
        kwargs.pop("instance")
        return kwargs

    def get_form(self, form_class):
        form = super(OrderCreatePaymentView, self).get_form(form_class)
        order = self.object
        form.fields["amount"] = forms.DecimalField(
            required=True,
            min_value=0,
            max_value=order.get_total_unpaid_amount().value,
            initial=0,
            label=_("Payment amount"),
        )
        return form

    def form_invalid(self, form):
        add_form_errors_as_messages(self.request, form)
        return super(OrderCreatePaymentView, self).form_invalid(form)

    def form_valid(self, form):
        order = self.object
        amount = Money(form.cleaned_data["amount"], order.currency)
        if amount.value == 0:
            messages.error(self.request, _("Payment amount cannot be 0"))
            return self.form_invalid(form)
        try:
            payment = order.create_payment(amount, description="Manual payment")
            messages.success(self.request, _("Payment %s created.") % payment.payment_identifier)
        except NoPaymentToCreateException:
            messages.error(self.request, _("Order has already been paid"))
            return self.form_invalid(form)
        else:
            return HttpResponseRedirect(get_model_url(order))
