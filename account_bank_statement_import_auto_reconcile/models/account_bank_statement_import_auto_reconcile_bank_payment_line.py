# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models


# pylint: disable=R7980
class AccountBankStatementImportAutoReconcileBankPaymentLine(models.AbstractModel):
    _inherit = 'account.bank.statement.import.auto.reconcile'
    _name = 'account.bank.statement.import.auto.reconcile.bank.payment.line'
    _description = 'Ref is Bank Payment Line Ref'

    
    @api.multi
    def reconcile(self, statement_line):
        if not statement_line.partner_id or (
            not statement_line.ref and not statement_line.name
        ):
            return
        
        if not statement_line.ref.startswith('L'):
            return
        
        bnkl = self.env['bank.payment.line'].search([('name', '=', statement_line.ref)])
        
        if statement_line.amount < bnkl[0].amount_company_currency:
            return
        
        counterpart_aml_dicts = []
        for payl in bnkl.payment_line_ids:
            counterpart_aml_dicts.append(statement_line._prepare_reconciliation_move_line(payl.move_line_id, payl.amount_company_currency))

        statement_line.process_reconciliation(counterpart_aml_dicts=counterpart_aml_dicts)
        return True
