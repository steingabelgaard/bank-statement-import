# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _

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
        if (not statement_line.ref and not statement_line.name):
            return

        if not statement_line.ref.startswith('L'):
            return

        bnkl = self.env['bank.payment.line'].search([('name', '=', statement_line.ref)])
        if not statement_line.partner_id and len(bnkl) == 1:
            statement_line.partner_id = bnkl[0].partner_id
        _logger.info('BNKL %s', bnkl)
        
        _logger.info('STM: %s %s', statement_line.amount, statement_line.name)
        if statement_line.amount == 0.0 and (_(' - Rejected') in statement_line.name or 'Afvist' in statement_line.name or '- Annulleret' in statement_line.name or '- Cancelled' in statement_line.name):
            reject = self.env['pbs.reject'].create({'statement_id': statement_line.statement_id.id,
                                                   'name': statement_line.name,
                                                   'date': statement_line.date,
                                                   'amount': statement_line.amount,
                                                   'partner_id': statement_line.partner_id.id,
                                                   'partner_name': statement_line.partner_name,
                                                   'ref': statement_line.ref,
                                                   'note': statement_line.note,
                                                   'amount_currency': statement_line.amount_currency,
                                                   'bank_payment_line_id': bnkl[0].id if bnkl else False})
            if reject:
                statement_line.unlink()
            return True
        
        if not bnkl:
            return
        
        if len(bnkl) > 1:
            return
                
        if not (float_compare(
                statement_line.amount, bnkl.amount_company_currency,
                precision_digits=self._digits
            ) == 0):
            return

        counterpart_aml_dicts = []
        payment_aml_rec = self.env['account.move.line']
        for payl in bnkl.payment_line_ids:
            aml = payl.move_line_id
            if aml.account_id.internal_type == 'liquidity':
                payment_aml_rec = (payment_aml_rec | aml)
            else:
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                if amount > 0:
                    counterpart_aml_dicts.append({
                        'name': aml.name if aml.name != '/' else aml.move_id.name,
                        'debit': amount < 0 and -amount or 0,
                        'credit': amount > 0 and amount or 0,
                        'move_line': aml
                        })
                
        _logger.info('COUNTERPART: %s', counterpart_aml_dicts)
        statement_line.process_reconciliation(counterpart_aml_dicts=counterpart_aml_dicts, payment_aml_rec=payment_aml_rec)
        return True
