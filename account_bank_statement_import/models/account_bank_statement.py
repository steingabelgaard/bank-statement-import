# -*- coding: utf-8 -*-
# Copyright 2009-2016 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp import api, models, fields, _
import openerp.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)

class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @api.model
    def create(self, vals):
        if vals.get('name'):
            journal = self.env['account.journal'].browse(
                vals.get('journal_id'))
            if journal.enforce_sequence:
                vals['name'] = '/'
        return super(AccountBankStatement, self).create(vals)
    
    account_balance = fields.Float('Account balance', digits_compute=dp.get_precision('Account'), compute = '_compute_balance')
    account_balance_red = fields.Float('Account balance', digits_compute=dp.get_precision('Account'), compute = '_compute_balance')
    account_balance_label = fields.Char('Account Balance Label', compute = '_compute_balance')
    account_balance_label_red = fields.Char('Account Balance Label', compute = '_compute_balance')
    account_balance_color = fields.Char('Account Balance Color', compute = '_compute_balance')
    
    @api.multi
    @api.depends('date', 'balance_end_real')
    def _compute_balance(self):
        for abs in self:
            ctx = {
                'date_from': '1900/01/01',
                'date_to': abs.date,
                }
            values = abs.journal_id.default_debit_account_id.with_context(ctx)._account_account__compute(['balance'])
            bal = values[abs.journal_id.default_debit_account_id.id]['balance']
            abs.account_balance = bal
            abs.account_balance_red = bal
            label = _('Balance pr %s for account %s') % (self.env.user.partner_id.format_date(abs.date), abs.journal_id.default_debit_account_id.code)
            abs.account_balance_label = label 
            abs.account_balance_label_red = label
            abs.account_balance_color = bool(bal != abs.balance_end_real)
            _logger.info("BAL %s, val: %s", bool(bal != abs.balance_end_real), values)
