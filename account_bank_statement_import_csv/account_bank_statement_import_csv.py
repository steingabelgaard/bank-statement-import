# -*- encoding: utf-8 -*-
##############################################################################
#
#    account_bank_statement_import_csv module for Odoo
#    Copyright (C) 2016 Stein & Gabelgaard
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from datetime import datetime
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import unicodecsv
import re
from cStringIO import StringIO
import hashlib

import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _get_hide_journal_field(self):
        """ Return False if the journal_id can't be provided by the parsed
        file and must be provided by the wizard.
        See account_bank_statement_import_qif """
        # pylint: disable=no-self-use
        return False
    
    @api.model
    def _prepare_csv_encoding(self):
        '''This method is designed to be inherited'''
        return 'latin1'

    @api.model
    def _prepare_csv_date_format(self, datestr):
        '''This method is designed to be inherited'''
        if '.' in datestr:
            return '%d.%m.%Y'
        elif '-' in datestr:
            return '%d-%m-%Y'
        
        
    @api.model
    def _csv_convert_amount(self, amount_str):
        '''This method is designed to be inherited'''
        valstr = re.sub(r'[^\d,.-]', '', amount_str)
        valstrdot = valstr.replace('.', '')
        valstrdot = valstrdot.replace(',', '.')
        return float(valstrdot)
    
    @api.model
    def _csv_get_note(self, line):
        note = False
        fields = []
        for f in ['Kommentar', 'Kategori', 'Underkategori', 'Egen bilagsreference']:
            if f in line:
                fields.append(line[f])
        if fields:
            note = ' '.join(filter(None, fields))
        return note
    
    @api.model
    def _parse_file(self, data_file):
        """ Import a file in Danish Bank CSV format"""
        
        f = StringIO()
        f.write(data_file)
        f.seek(0)
        transactions = []
        i = 0
        d = 0
        start_balance = end_balance = start_date_str = end_date_str = False
        vals_line = False
        company_currency_name = self.env.user.company_id.currency_id.name
        unique_hash = hashlib.sha1(bytearray(self.filename, 'utf-8') + data_file)
        # To confirm : is the encoding always latin1 ?
        date_format = False
        for line in unicodecsv.DictReader(
                f, encoding=self._prepare_csv_encoding(), delimiter=';'):
            
            if not date_format:
                date_format = self._prepare_csv_date_format(line['Dato'])
            i += 1
            
            if i == 1:
                # verify file format
                _logger.info("KEYS: %s", line.keys())
                if not set(['Dato', 'Tekst', 'Saldo', u'Beløb']).issubset(line.keys()):
                    return super(AccountBankStatementImport, self)._parse_file(data_file)
                
                start_date_str = line['Dato'] 
                date_dt = datetime.strptime(
                line['Dato'], date_format)
                start_saldo = self._csv_convert_amount(line[u'Saldo'])
                start_amount = self._csv_convert_amount(line[u'Beløb'])
                start_balance =  start_saldo - start_amount 
                 
            if end_date_str == line['Dato']:
                d += 1
            else:
                d = 1
            vals_line = {
                'date': datetime.strptime(line[
                                               'Dato'], date_format),
                'name': line['Tekst'],
                'unique_import_id': "%d-%s-%s-%s-%s" % (self.journal_id.id, line['Dato'], line['Tekst'], line[u'Beløb'], line[u'Saldo']),
                'amount': self._csv_convert_amount(line[u'Beløb']),
                'line_balance': self._csv_convert_amount(line[u'Saldo']),
                'bank_account_id': False,
                'ref' : self._csv_get_note(line),
                }
            end_date_str = line['Dato']
            end_balance = self._csv_convert_amount(line[u'Saldo'])
            end_amount = self._csv_convert_amount(line[u'Beløb'])
            _logger.debug("vals_line = %s" % vals_line)
            transactions.append(vals_line)
            
        if datetime.strptime(start_date_str, date_format) > datetime.strptime(end_date_str, date_format):
            #swap start / end
            swap_date = start_date_str
            start_date_str = end_date_str
            end_date_str = swap_date
            start_balance = end_balance - end_amount
            end_balance = start_saldo 

        vals_bank_statement = {
            'name': _('Import %s - %s')
            % (start_date_str, end_date_str),
            'balance_start': start_balance,
            'balance_end_real': end_balance,
            'transactions': transactions,
        }
        return None, None, [vals_bank_statement]

    @api.model
    def _create_bank_statement(self, stmt_vals):
        statement_id, notifications = super(AccountBankStatementImport, self)._create_bank_statement(stmt_vals)
        bs = self.env['account.bank.statement'].browse(statement_id)
        bsl = bs.line_ids.sorted(key=lambda r: r.date)[0]
        bs.balance_start = bsl.line_balance - bsl.amount
        return statement_id, notifications
    
class AccountBankStatementLine(models.Model):
    """Extend model account.bank.statement.line."""
    # pylint: disable=too-many-public-methods
    _inherit = "account.bank.statement.line"
    
    line_balance = fields.Float(digits_compute=dp.get_precision('Account'))
    

