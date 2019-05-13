# -*- coding: utf-8 -*-
# Copyright 2018 Stein & Gabelgaard ApS
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models, _


class AccountReconcileModel(models.Model):
    # In v10 + this model is account.reconcile.model
    _inherit = 'account.statement.operation.template'
    
    match = fields.Char('Match text', help='If the text is found on the statement line it will be auto reconciled using thsi setup')
    journal_id = fields.Many2one('account.journal', 'Journal')