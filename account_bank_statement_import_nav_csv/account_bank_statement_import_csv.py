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
from openerp.exceptions import Warning as UserError
import unicodecsv
import re
from cStringIO import StringIO
import hashlib
from openerp.tools import ustr

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
            return '%d-%m-%y'
        
        
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
        """ Import a file from SAF Navision CSV format"""
        
        f = StringIO()
        f.write(data_file.lstrip())
        f.seek(0)
        transactions = []
        i = 0
        d = 0
        start_balance = end_balance = start_date_str = end_date_str = False
        vals_line = False
        company_currency_name = self.env.user.company_id.currency_id.name
        unique_hash = hashlib.sha1(bytearray(self.filename, 'utf-8') + data_file)
        # To confirm : is the encoding always latin1 ?
        date_format = '%d-%m-%y'
        date_field = 'date'
        try:
            for line in unicodecsv.DictReader(
                    f, encoding=self._prepare_csv_encoding(), delimiter=';', fieldnames=['date', 'ref', 'partner', 'amount']):
                
                
                i += 1
                
                if i == 1:
                    # verify file format
                    _logger.info("KEYS: %s", line.keys())
                    if not date_format:
                        date_format = self._prepare_csv_date_format(line[date_field].strip())
                    
                    start_date_str = line[date_field].strip() 
                    date_dt = datetime.strptime(
                    line[date_field].strip(), date_format)
                    
                    start_balance = 0 
                    end_balance = 0
                     
                if end_date_str == line[date_field].strip():
                    d += 1
                else:
                    d = 1
                _logger.info('Procsessing line: %d', i)
                try:
                    partner_name = False

                    currency = self.env.user.company_id.currency_id                    
                    p = self.env['res.partner'].search([('ref', '=', line['partner'])])
                    if p:
                        partner_name = p.ref
                        currency = p.commercial_partner_id.property_account_receivable.currency_id
                    vals_line = {
                        'date': datetime.strptime(line[date_field].strip(), date_format),
                        'name': "%s %s" % (line['partner'], partner_name),
                        'unique_import_id': "%d-%s-%s-%s-%s" % (self.journal_id.id, line[date_field].strip(), line['ref'], line['partner'], line[u'amount']),
                        'amount': self._csv_convert_amount(line['amount']),
                        'bank_account_id': False,
                        'ref' : line['ref'],
                        'partner_name': line['partner'],
                        'partner_id': p.id if p else False,
                        
                        }
                    
                   
                    
                    _logger.info("vals_line = %s" % vals_line)
                    if currency == self.journal_id.currency:
                        end_balance += self._csv_convert_amount(line[u'amount'])
                        transactions.append(vals_line)
                except Exception as e:
                    raise UserError(_('Format Error\nLine %d could not be processed\n%s') % (i + 1, ustr(e)))
        except Exception as e:
            raise UserError(_('File parse error:\n%s') % ustr(e))

        vals_bank_statement = {
            'name': _('Import %s')
            % (start_date_str),
            'balance_start': start_balance,
            'balance_end_real': end_balance,
            'transactions': transactions,
            
        }
        currency_code = self.journal_id.currency.name if self.journal_id.currency else self.env.user.company_id.currency_id.name
        _logger.info("vals_stmt = %s" % vals_bank_statement)
        return currency_code, None, [vals_bank_statement]

