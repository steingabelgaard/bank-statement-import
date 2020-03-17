# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models, _

import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare

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
        _logger.info('BNKL %s %d', bnkl, bnkl[0].id)
        
        _logger.info('STM: %s %s', statement_line.amount, statement_line.name)
        if statement_line.amount == 0.0 and (_(' - Rejected') in statement_line.name or 'Afvist' in statement_line.name or '- Annulleret' in statement_line.name or '- Cancelled' in statement_line.name):
            vals = {'statement_id': statement_line.statement_id.id,
                    'name': statement_line.name,
                    'date': statement_line.date,
                    'amount': statement_line.amount,
                    'partner_id': statement_line.partner_id.id,
                    'partner_name': statement_line.partner_name,
                    'ref': statement_line.ref,
                    'note': statement_line.note,
                    'amount_currency': statement_line.amount_currency,
                    'bank_payment_line_id': bnkl[0].id if bnkl else False,
                    }
            _logger.info('VALS: %s', vals)
            reject = self.env['pbs.reject'].create(vals)
            if reject:
                statement_line.unlink()
            return True
        
        if not bnkl:
            return
                
        if len(bnkl) > 1:
            return
                
        if not (float_compare(
                statement_line.amount, bnkl.amount_currency,
                precision_digits=self._digits
            ) == 0):
            return

        counterpart_aml_dicts = []
        payment_aml_rec = self.env['account.move.line']
        for payl in bnkl.payment_line_ids:
            aml = payl.move_line_id
            if aml.reconcile_id:
                return  # If one or more of the payments lines is payed - Skip this bank statement line
                
            
            if aml.account_id.type == 'liquidity':
                payment_aml_rec = (payment_aml_rec | aml)
            else:
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                if amount > 0:
                    if not (float_compare(
                            statement_line.amount, amount,
                            precision_digits=self._digits
                            ) == 0):
                        return  # Open amount dosn't match paided amount
                    move_line_dict = self.env['account.bank.statement']\
                        ._prepare_bank_move_line(
                            statement_line, aml.id, -amount,
                            statement_line.statement_id.company_id.currency_id.id,
                        )
                    move_line_dict['counterpart_move_line_id'] = aml.id
                    counterpart_aml_dicts.append(move_line_dict)
                
        _logger.info('COUNTERPART: %s', counterpart_aml_dicts)
        _logger.info('statement_line: %s', statement_line)
        self.pool.get('account.bank.statement.line').process_reconciliation(statement_line._cr, statement_line._uid, statement_line.id, counterpart_aml_dicts, context=statement_line._context)
        return True
