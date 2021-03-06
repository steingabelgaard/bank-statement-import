# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models
import logging
_logger = logging.getLogger(__name__)

# pylint: disable=R7980
class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    auto_reconcile = fields.Boolean('Auto reconcile', default=True)

    @api.model
    def _create_bank_statements(self, stmt_vals):
        _logger.info('ACCOUNT BANK')
        statement_id, notifications = super(
            AccountBankStatementImport, self
        )._create_bank_statements(stmt_vals)
        if not statement_id or len(statement_id) > 1:
            return statement_id, notifications
        statement = self.env['account.bank.statement'].browse(statement_id)
        if (
                not self.auto_reconcile or
                not statement.journal_id.statement_import_auto_reconcile_rule_ids
        ):
            return statement_id, notifications
        reconcile_rules = statement.journal_id\
            .statement_import_auto_reconcile_rule_ids.mapped(
                lambda x: self.env[x.rule_type].new({
                    'wizard_id': self.id,
                    'options': x.options
                })
            )
        auto_reconciled_ids = []
        for line in statement.line_ids:
            for rule in reconcile_rules:
                if rule.reconcile(line):
                    auto_reconciled_ids.append(line.id)
                    break
            # commit line by line to avoid concurrent update error on long running import
            self._cr.commit()
        if auto_reconciled_ids:
            notifications.append({
                'type': 'warning',
                'message':
                _("%d transactions were reconciled automatically.") %
                len(auto_reconciled_ids),
                'details': {
                    'name': _('Automatically reconciled'),
                    'model': 'account.bank.statement.line',
                    'ids': auto_reconciled_ids,
                },
            })
        if statement.reject_ids:
            notifications.append({
                'type': 'warning',
                'message':
                _("%d transactions were rejected.") %
                len(statement.reject_ids),
                'details': {
                    'name': _('Rejected payments'),
                    'model': 'pbs.reject',
                    'ids': statement.reject_ids.ids,
                },
            })
        return statement_id, notifications
