# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models, _

import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare

import logging
_logger = logging.getLogger(__name__)


# pylint: disable=R7980
class AccountBankStatementImportAutoReconcileFikPayment(models.AbstractModel):
    _inherit = 'account.bank.statement.import.auto.reconcile'
    _name = 'account.bank.statement.import.auto.reconcile.fik.payment'
    _description = 'FIK Indbetaling ID'


    @api.multi
    def reconcile(self, statement_line):
        #_logger.info('RECON %s', statement_line)
        
        if not 'Indbet.ID=0' in statement_line.name:
            return

        fik_code = statement_line.name.split('=')[1]
        invoice = self.env['account.invoice'].search([('id', '=', int(fik_code[:-1]))])
        
        if invoice and len(invoice) == 1:
        
            statement_line.write({'partner_id': invoice.partner_id.id,
                                  'ref': invoice.number})
        
                
            if not (float_compare(
                statement_line.amount, invoice.residual,
                precision_digits=self._digits
                ) == 0):
                return
            _logger.info('RECON invoice found %s', invoice)
            amount_field = 'debit'
            sign = 1
            if statement_line.currency_id or statement_line.journal_id.currency:
                if statement_line.amount < 0:
                    amount_field = 'credit'
                    sign = -1
                else:
                    amount_field = 'amount_currency'
    
            domain = [
                ('move_id', '=', invoice.move_id.id),
                ('reconcile_id', '=', False),
                ('state', '=', 'valid'),
                ('account_id.reconcile', '=', True),
                ('partner_id', '=', statement_line.partner_id.commercial_partner_id.id),
                (amount_field, '=', self._round(sign * statement_line.amount)),
            ]
            move_lines = self.env['account.move.line'].search(domain, limit=1)
            _logger.info('RECON move: %s domain : %s', move_lines, domain)
            if move_lines:
                self._reconcile_move_line(statement_line, move_lines.id)
                return True
        else:
            return
