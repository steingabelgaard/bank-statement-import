# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models

import odoo.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)


# pylint: disable=R7980
class AccountBankStatementImportAutoReconcileBankPaymentLine(models.AbstractModel):
    _inherit = 'account.bank.statement.import.auto.reconcile'
    _name = 'account.bank.statement.import.auto.reconcile.bank.payment.line'
    _description = 'Ref is Bank Payment Line Ref'


    @api.multi
    def reconcile(self, statement_line):
        _logger.info('RECON %s', statement_line)
        if not statement_line.partner_id or (
            not statement_line.ref and not statement_line.name
        ):
            return

        if not statement_line.ref.startswith('L'):
            return

        bnkl = self.env['bank.payment.line'].search([('name', '=', statement_line.ref)])
        _logger.info('BNKL %s', bnkl)
        if statement_line.amount < bnkl[0].amount_company_currency:
            return

        counterpart_aml_dicts = []
        payment_aml_rec = self.env['account.move.line']
        for payl in bnkl.payment_line_ids:
            aml = payl.move_line_id
            if aml.account_id.internal_type == 'liquidity':
                payment_aml_rec = (payment_aml_rec | aml)
            else:
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                counterpart_aml_dicts.append({
                    'name': aml.name if aml.name != '/' else aml.move_id.name,
                    'debit': amount < 0 and -amount or 0,
                    'credit': amount > 0 and amount or 0,
                    'move_line': aml
                })

        _logger.info('COUNTERPART: %s', counterpart_aml_dicts)
        statement_line.process_reconciliation(counterpart_aml_dicts=counterpart_aml_dicts, payment_aml_rec=payment_aml_rec)
        return True
