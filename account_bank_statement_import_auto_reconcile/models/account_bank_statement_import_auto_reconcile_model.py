# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models

import odoo.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)


# pylint: disable=R7980 
class AccountBankStatementImportAutoReconcileModel(models.AbstractModel):
    _inherit = 'account.bank.statement.import.auto.reconcile'
    _name = 'account.bank.statement.import.auto.reconcile.model'
    _description = 'Use reg-ex to find account.reconcile.model to use'

    @api.multi
    def reconcile(self, statement_line):
        _logger.info('RECON %s', statement_line)
        if not statement_line.name:
            return

        for arm in self.env['account.reconcile.model'].search([('journal_id', '=', statement_line.journal_id.id), ('company_id', '=', statement_line.company_id.id), ('match', '!=', False)]):
            if arm.match.lower() in statement_line.name.lower():
                _logger.info("RECON with %s", arm.name)
                if arm.amount_type == 'fixed':
                    amount = arm.amount
                else:
                    amount = statement_line.amount * arm.amount / 100
                new_aml = [{'name': arm.label if arm.label else statement_line.name,
                            'debit': amount < 0 and -amount or 0,
                            'credit': amount > 0 and amount or 0,
                            'account_id': arm.account_id.id,
                            }]
                _logger.info('NEW_AML: %s', new_aml)
                statement_line.process_reconciliation(new_aml_dicts=new_aml)
                return True 
