# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import _, api, fields, models
from openerp.exceptions import Warning as UserError

import logging
_logger = logging.getLogger(__name__)

class AccountBankStatementImportReapplyRules(models.TransientModel):
    _inherit = 'account.bank.statement.import'
    _name = 'account.bank.statement.import.reapply.rules'

    data_file = fields.Binary(required=False)

    @api.multi
    def action_reapply_rules(self):
        statements = self.env['account.bank.statement'].browse(
            self.env.context.get('active_ids', [])
        )
        journal = statements.mapped('journal_id')
        if len(journal) != 1:
            raise UserError(_(
                'You can only reapply rules on statements with the same '
                'journal!'
            ))

        self.write({'journal_id': journal.id})
        #reconcile_rules = journal.statement_import_auto_reconcile_rule_ids\
        #    .get_rules()
        #     _logger.info('Rules: %s', len(reconcile_rules))
        for line in self.env['account.bank.statement.line'].search([
                ('statement_id', 'in', statements.ids),
                ('journal_entry_id', '=', False),
        ]):
            for rule in journal.statement_import_auto_reconcile_rule_ids:
                _logger.info('Line %s rule: %s', line, rule._name)
                if self.env[rule.rule_type].reconcile(line):
                    _logger.info('BREAK Line %s rule: %s', line, rule)
                    break
        return {'type': 'ir.actions.act_window_close'}
