# -*- coding: utf-8 -*-
# Copyright 2018 Stein & Gabelgaard ApS
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class AccountReconcileModel(models.Model):

    _inherit = 'account.reconcile.model'
    
    match = fields.Char('Match text', help='If the text is found on the statement line it will be auto reconciled using thsi setup')
